import os
import logging
import sqlite3
import time
from typing import Dict, Any, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Импортируем конфиг
try:
    from config import BOT_TOKEN
except ImportError:
    print("❌ Файл config.py не найден! Создайте его из config.example.py")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Путь к базе данных
DB_PATH = 'clan_bot.db'

# Глобальный словарь для хранения сессий пользователей
user_sessions: Dict[int, Dict[str, Any]] = {}
SESSION_TIMEOUT = 3600  # 1 час в секундах

class UserSession:
    """Класс для управления сессией пользователя"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.created_at = time.time()
        self.current_section: Optional[int] = None
        self.current_subsection: Optional[int] = None
        self.current_post_index: int = 0
        self.posts: List[Any] = []
        
        # Состояния для добавления контента
        self.adding_post: Optional[Dict[str, Any]] = None
        self.creating_section: bool = False
        self.creating_subsection: Optional[Dict[str, Any]] = None
        self.editing_section: Optional[int] = None
        self.editing_subsection: Optional[int] = None
        self.editing_post: Optional[int] = None
        
        # Флаги ожидания ввода
        self.awaiting_section_name: bool = False
        self.awaiting_subsection_name: bool = False
        self.awaiting_post_title: bool = False
        self.awaiting_post_content: bool = False
    
    def is_valid(self) -> bool:
        """Проверяет, действительна ли сессия"""
        return time.time() - self.created_at < SESSION_TIMEOUT
    
    def update_time(self):
        """Обновляет время сессии"""
        self.created_at = time.time()
    
    def clear_adding_state(self):
        """Очищает состояние добавления контента"""
        self.adding_post = None
        self.creating_section = False
        self.creating_subsection = None
        self.editing_section = None
        self.editing_subsection = None
        self.editing_post = None
        self.awaiting_section_name = False
        self.awaiting_subsection_name = False
        self.awaiting_post_title = False
        self.awaiting_post_content = False

def get_user_session(user_id: int) -> Optional[UserSession]:
    """Получает сессию пользователя"""
    session = user_sessions.get(user_id)
    if session and session.is_valid():
        session.update_time()
        return session
    elif session:
        # Удаляем просроченную сессию
        del user_sessions[user_id]
    return None

def create_user_session(user_id: int) -> UserSession:
    """Создает новую сессию пользователя"""
    session = UserSession(user_id)
    user_sessions[user_id] = session
    return session

def clear_user_session(user_id: int):
    """Очищает сессию пользователя"""
    if user_id in user_sessions:
        del user_sessions[user_id]

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица разделов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица подразделов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subsections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections (id)
        )
    ''')
    
    # Таблица записей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subsection_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            title TEXT NOT NULL,
            content_type TEXT,
            content_text TEXT,
            image_file_id TEXT,
            link_url TEXT,
            link_title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subsection_id) REFERENCES subsections (id)
        )
    ''')
    
    # Создаем базовые разделы
    cursor.execute('''
        INSERT OR IGNORE INTO sections (id, name, description) 
        VALUES 
            (1, '📚 Гайды по игре', 'Полезные гайды и стратегии'),
            (2, '⚔️ Библиотека сборок', 'Эффективные сборки персонажей'),
            (3, '📝 Заметки клана', 'Важные объявления и заметки'),
            (4, '🔗 Полезные ссылки', 'Ссылки на ресурсы и инструменты')
    ''')
    
    # Создаем базовые подразделы
    cursor.execute('''
        INSERT OR IGNORE INTO subsections (id, section_id, name, description) 
        VALUES 
            (1, 1, '🎯 Основы игры', 'Базовые гайды для новичков'),
            (2, 1, '🏆 Продвинутые стратегии', 'Стратегии для опытных игроков'),
            (3, 2, '⚔️ PvP сборки', 'Сборки для арены'),
            (4, 2, '🐉 PvE сборки', 'Сборки для против боссов'),
            (5, 3, '📢 Объявления', 'Важные объявления клана'),
            (6, 3, '💡 Идеи и предложения', 'Предложения по развитию клана'),
            (7, 4, '🌐 Официальные ресурсы', 'Официальные сайты и соцсети'),
            (8, 4, '🛠️ Калькуляторы и инструменты', 'Полезные инструменты для игры')
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def safe_get(data, index, default="Неизвестно"):
    """Безопасно получает элемент из кортежа по индексу"""
    if data and len(data) > index:
        return data[index]
    return default

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Создаем новую сессию для пользователя
    session = create_user_session(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
        [InlineKeyboardButton("⚙️ Управление контентом", callback_data='manage_content')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    welcome_text = (
        f'🏰 Добро пожаловать, {user.first_name}, в базу знаний клана Sons of Garitos!\n\n'
        'Теперь вы можете создавать разделы, подразделы и добавлять различные типы контента!'
    )
    
    if update.message:
        update.message.reply_text(welcome_text, reply_markup=reply_markup)
    else:
        update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Проверяем сессию для всех callback, кроме back_to_main
    if query.data != 'back_to_main':
        session = get_user_session(user_id)
        if not session:
            query.answer("❌ Сессия устарела. Используйте /start", show_alert=True)
            return
    
    query.answer()
    
    if query.data == 'view_sections':
        show_sections(query, context)
    elif query.data.startswith('view_section_'):
        show_subsections(query, context)
    elif query.data.startswith('view_subsection_'):
        show_subsection_posts(query, context)
    elif query.data.startswith('prev_post_') or query.data.startswith('next_post_'):
        navigate_posts(query, context)
    elif query.data == 'add_post_choose_section':
        add_post_choose_section(query, context)
    elif query.data.startswith('add_post_choose_subsection_'):
        add_post_choose_subsection(query, context)
    elif query.data.startswith('add_post_'):
        add_post_start(query, context)
    elif query.data == 'create_section':
        create_section(query, context)
    elif query.data == 'create_subsection_choose_section':
        create_subsection_choose_section(query, context)
    elif query.data.startswith('create_subsection_'):
        create_subsection(query, context)
    elif query.data == 'manage_content':
        manage_content(query, context)
    elif query.data == 'manage_sections':
        manage_sections(query, context)
    elif query.data.startswith('edit_section_'):
        edit_section(query, context)
    elif query.data.startswith('delete_section_'):
        delete_section(query, context)
    elif query.data.startswith('confirm_delete_section_'):
        confirm_delete_section(query, context)
    elif query.data.startswith('edit_subsection_'):
        edit_subsection(query, context)
    elif query.data.startswith('delete_subsection_'):
        delete_subsection(query, context)
    elif query.data.startswith('confirm_delete_subsection_'):
        confirm_delete_subsection(query, context)
    elif query.data.startswith('edit_post_'):
        edit_post(query, context)
    elif query.data.startswith('delete_post_'):
        delete_post(query, context)
    elif query.data.startswith('confirm_delete_post_'):
        confirm_delete_post(query, context)
    elif query.data == 'back_to_main':
        back_to_main(query, context)

def show_sections(query, context):
    user_id = query.from_user.id
    session = get_user_session(user_id)
    if not session:
        query.edit_message_text("❌ Сессия устарела. Используйте /start")
        return
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    if not sections:
        query.edit_message_text("Разделы пока не созданы.")
        return
    
    keyboard = []
    for section in sections:
        conn = get_db_connection()
        subs_count = conn.execute('SELECT COUNT(*) FROM subsections WHERE section_id = ?', (section[0],)).fetchone()[0]
        posts_count = conn.execute('''
            SELECT COUNT(*) FROM posts p 
            JOIN subsections s ON p.subsection_id = s.id 
            WHERE s.section_id = ?
        ''', (section[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{safe_get(section, 1)} ({subs_count} подраз., {posts_count} зап.)", 
            callback_data=f"view_section_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📂 Выберите раздел:", reply_markup=reply_markup)

def show_subsections(query, context):
    user_id = query.from_user.id
    session = get_user_session(user_id)
    if not session:
        query.edit_message_text("❌ Сессия устарела. Используйте /start")
        return
    
    section_id = int(query.data.split('_')[-1])
    
    # Обновляем сессию
    session.current_section = section_id
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    subsections = conn.execute(
        'SELECT * FROM subsections WHERE section_id = ? ORDER BY id', 
        (section_id,)
    ).fetchall()
    conn.close()
    
    if not section:
        query.edit_message_text("❌ Раздел не найден!")
        return
    
    if not subsections:
        keyboard = [
            [InlineKeyboardButton("📁 Создать подраздел", callback_data=f"create_subsection_{section_id}")],
            [InlineKeyboardButton("✏️ Редактировать раздел", callback_data=f"edit_section_{section_id}")],
            [InlineKeyboardButton("🗑️ Удалить раздел", callback_data=f"delete_section_{section_id}")],
            [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(f"В разделе '{safe_get(section, 1)}' пока нет подразделов.\n\nСоздайте первый подраздел!", reply_markup=reply_markup)
        return
    
    keyboard = []
    for subsection in subsections:
        conn = get_db_connection()
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE subsection_id = ?', (subsection[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{safe_get(subsection, 2)} ({posts_count} зап.)", 
            callback_data=f"view_subsection_{subsection[0]}"
        )])
    
    keyboard.extend([
        [InlineKeyboardButton("📁 Создать подраздел", callback_data=f"create_subsection_{section_id}")],
        [InlineKeyboardButton("✏️ Редактировать раздел", callback_data=f"edit_section_{section_id}")],
        [InlineKeyboardButton("🗑️ Удалить раздел", callback_data=f"delete_section_{section_id}")],
        [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"📁 Раздел: {safe_get(section, 1)}\n\nВыберите подраздел:", reply_markup=reply_markup)

def show_subsection_posts(query, context):
    user_id = query.from_user.id
    session = get_user_session(user_id)
    if not session:
        query.edit_message_text("❌ Сессия устарела. Используйте /start")
        return
    
    subsection_id = int(query.data.split('_')[-1])
    
    # Обновляем сессию пользователя
    session.current_subsection = subsection_id
    session.current_post_index = 0
    
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    posts = conn.execute(
        'SELECT * FROM posts WHERE subsection_id = ? ORDER BY created_at DESC', 
        (subsection_id,)
    ).fetchall()
    conn.close()
    
    # Сохраняем посты в сессии пользователя
    session.posts = posts
    
    if not posts:
        keyboard = [
            [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection_id}")],
            [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection_id}")],
            [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection_id}")],
            [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"📁 Раздел: {safe_get(section, 1)}\n"
            f"📂 Подраздел: {safe_get(subsection, 2)}\n\n"
            f"Записей пока нет.\n\n"
            f"Создайте первую запись!",
            reply_markup=reply_markup
        )
        return
    
    # Показываем первую запись с навигацией
    show_post_navigation(query, context, posts[0], 0, len(posts), subsection, section)

def show_post_navigation(query, context, post, index, total, subsection, section):
    post_text = f"📁 {safe_get(section, 1)} → {safe_get(subsection, 2)}\n\n"
    post_text += f"📌 {safe_get(post, 4)}\n\n"
    
    if safe_get(post, 6):  # content_text
        post_text += f"{safe_get(post, 6)}\n\n"
    
    if safe_get(post, 8) and safe_get(post, 9):  # link_url и link_title
        post_text += f"🔗 {safe_get(post, 9)}\n{safe_get(post, 8)}\n\n"
    
    post_text += f"👤 Автор: {safe_get(post, 3)}\n"
    post_text += f"📅 {safe_get(post, 10)}\n"
    post_text += f"📊 ({index + 1}/{total})"
    
    # Кнопки навигации
    keyboard = []
    
    # Навигация между записями
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"prev_post_{index}"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"next_post_{index}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопки действий
    keyboard.extend([
        [InlineKeyboardButton("✏️ Редактировать запись", callback_data=f"edit_post_{post[0]}")],
        [InlineKeyboardButton("🗑️ Удалить запись", callback_data=f"delete_post_{post[0]}")],
        [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection[0]}")],
        [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection[0]}")],
        [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection[0]}")],
        [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if safe_get(post, 7):  # image_file_id
        query.edit_message_caption(caption=post_text, reply_markup=reply_markup)
    else:
        query.edit_message_text(post_text, reply_markup=reply_markup)

def navigate_posts(query, context):
    user_id = query.from_user.id
    session = get_user_session(user_id)
    if not session:
        query.edit_message_text("❌ Сессия устарела. Используйте /start")
        return
    
    action = query.data.split('_')[0]  # 'prev' или 'next'
    current_index = int(query.data.split('_')[-1])
    
    subsection_id = session.current_subsection
    posts = session.posts
    
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    if action == 'prev':
        new_index = current_index - 1
    else:  # next
        new_index = current_index + 1
    
    session.current_post_index = new_index
    show_post_navigation(query, context, posts[new_index], new_index, len(posts), subsection, section)

# ... (остальные функции остаются похожими, но с проверкой сессии)

def handle_message(update: Update, context: CallbackContext):
    """Обработчик текстовых сообщений - реагирует только на активные сессии"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Если нет активной сессии - ИГНОРИРУЕМ сообщение (бот молчит)
    if not session:
        return
    
    user = update.effective_user
    
    if session.awaiting_subsection_name:
        subsection_name = update.message.text
        
        if session.editing_subsection:
            # Редактирование существующего подраздела
            subsection_id = session.editing_subsection
            conn = get_db_connection()
            conn.execute('UPDATE subsections SET name = ? WHERE id = ?', (subsection_name, subsection_id))
            conn.commit()
            conn.close()
            
            session.clear_adding_state()
            update.message.reply_text(f"✅ Подраздел '{subsection_name}' успешно обновлен!")
        else:
            # Создание нового подраздела
            section_id = session.creating_subsection['section_id']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO subsections (section_id, name, description, created_by) VALUES (?, ?, ?, ?)',
                (section_id, subsection_name, "Описание подраздела", user.id)
            )
            conn.commit()
            conn.close()
            
            session.clear_adding_state()
            update.message.reply_text(f"✅ Подраздел '{subsection_name}' успешно создан!")
        
        back_to_main_message(update, context)
    
    elif session.awaiting_section_name:
        section_name = update.message.text
        
        if session.editing_section:
            # Редактирование существующего раздела
            section_id = session.editing_section
            conn = get_db_connection()
            conn.execute('UPDATE sections SET name = ? WHERE id = ?', (section_name, section_id))
            conn.commit()
            conn.close()
            
            session.clear_adding_state()
            update.message.reply_text(f"✅ Раздел '{section_name}' успешно обновлен!")
        else:
            # Создание нового раздела
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sections (name, description, created_by) VALUES (?, ?, ?)',
                (section_name, "Описание раздела", user.id)
            )
            conn.commit()
            conn.close()
            
            session.clear_adding_state()
            update.message.reply_text(f"✅ Раздел '{section_name}' успешно создан!")
        
        back_to_main_message(update, context)
    
    elif session.adding_post:
        post_data = session.adding_post
        
        if post_data['step'] == 'title':
            post_data['title'] = update.message.text
            post_data['step'] = 'content_text'
            
            update.message.reply_text(
                f"📝 Заголовок сохранен: {post_data['title']}\n\n"
                f"Теперь введите текст записи:"
            )
        
        elif post_data['step'] == 'content_text':
            post_data['content_text'] = update.message.text
            
            # Сохраняем запись в БД
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posts (subsection_id, user_id, user_name, title, content_type, content_text)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                post_data['subsection_id'],
                user.id,
                user.first_name,
                post_data['title'],
                'text',
                post_data['content_text']
            ))
            conn.commit()
            conn.close()
            
            session.clear_adding_state()
            update.message.reply_text("✅ Запись успешно добавлена!")
            back_to_main_message(update, context)
    
    # УБРАН блок else - бот больше не отвечает "✅ Бот работает! Используйте /start для меню."

def handle_photo(update: Update, context: CallbackContext):
    """Обработчик фото - реагирует только на активные сессии"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Если нет активной сессии - ИГНОРИРУЕМ фото (бот молчит)
    if not session:
        return
    
    if session.adding_post:
        post_data = session.adding_post
        
        # Сохраняем file_id изображения
        photo = update.message.photo[-1]
        post_data['image_file_id'] = photo.file_id
        
        update.message.reply_text("🖼️ Изображение сохранено! Теперь введите текст записи:")

def back_to_main_message(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
        [InlineKeyboardButton("⚙️ Управление контентом", callback_data='manage_content')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('🏰 Главное меню базы знаний клана:', reply_markup=reply_markup)

def main():
    # Используем токен из config.py
    TOKEN = BOT_TOKEN
    
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ BOT_TOKEN не настроен! Проверьте файл config.py")
        return
    
    try:
        # Инициализируем базу данных
        init_db()
        
        # Создаем updater и dispatcher
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Добавляем обработчики - ВАЖНО: правильный порядок
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CallbackQueryHandler(button_handler))
        
        # Обработчики сообщений - будут срабатывать ТОЛЬКО при активной сессии
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dp.add_handler(MessageHandler(Filters.photo, handle_photo))
        
        print("✅ Bot started successfully! Will only respond to /start and active sessions.")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()