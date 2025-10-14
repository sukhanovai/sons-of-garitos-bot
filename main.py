import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from stay_alive import keep_alive

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Путь к базе данных
DB_PATH = 'clan_bot.db'

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

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        '🏰 Добро пожаловать в базу знаний клана Sons of Garitos!\n\n'
        'Выберите действие:',
        reply_markup=reply_markup
    )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == 'view_sections':
        show_sections(query, context)
    elif query.data.startswith('view_section_'):
        show_subsections(query, context)
    elif query.data.startswith('view_subsection_'):
        show_subsection_posts(query, context)
    elif query.data == 'add_post_choose_section':
        add_post_choose_section(query, context)
    elif query.data.startswith('add_post_choose_subsection_'):
        add_post_choose_subsection(query, context)
    elif query.data.startswith('add_post_'):
        add_post_start(query, context)
    elif query.data == 'back_to_main':
        back_to_main(query, context)

def show_sections(query, context):
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    if not sections:
        query.edit_message_text("Разделы пока не созданы.")
        return
    
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(
            section[1], 
            callback_data=f"view_section_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📂 Выберите раздел:", reply_markup=reply_markup)

def show_subsections(query, context):
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    subsections = conn.execute(
        'SELECT * FROM subsections WHERE section_id = ? ORDER BY id', 
        (section_id,)
    ).fetchall()
    conn.close()
    
    if not subsections:
        keyboard = [
            [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_choose_subsection_{section_id}")],
            [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(f"В разделе '{section[1]}' пока нет подразделов.", reply_markup=reply_markup)
        return
    
    keyboard = []
    for subsection in subsections:
        conn = get_db_connection()
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE subsection_id = ?', (subsection[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{subsection[2]} ({posts_count} зап.)", 
            callback_data=f"view_subsection_{subsection[0]}"
        )])
    
    keyboard.extend([
        [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_choose_subsection_{section_id}")],
        [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"📁 Раздел: {section[1]}\n\nВыберите подраздел:", reply_markup=reply_markup)

def show_subsection_posts(query, context):
    subsection_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    posts = conn.execute(
        'SELECT * FROM posts WHERE subsection_id = ? ORDER BY created_at DESC', 
        (subsection_id,)
    ).fetchall()
    conn.close()
    
    if not posts:
        keyboard = [
            [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection_id}")],
            [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"📁 Раздел: {section[1]}\n"
            f"📂 Подраздел: {subsection[2]}\n\n"
            f"Записей пока нет.\n\n"
            f"Создайте первую запись!",
            reply_markup=reply_markup
        )
        return
    
    # Показываем первую запись
    post = posts[0]
    post_text = f"📁 {section[1]} → {subsection[2]}\n\n"
    post_text += f"📌 {post[4]}\n\n"
    
    if post[6]:  # content_text
        post_text += f"{post[6]}\n\n"
    
    if post[8] and post[9]:  # link_url и link_title
        post_text += f"🔗 {post[9]}\n{post[8]}\n\n"
    
    post_text += f"👤 Автор: {post[3]}\n"
    post_text += f"📅 {post[10]}\n"
    post_text += f"📊 (1/{len(posts)})"
    
    keyboard = [
        [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection_id}")],
        [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if post[7]:  # image_file_id
        query.edit_message_caption(caption=post_text, reply_markup=reply_markup)
    else:
        query.edit_message_text(post_text, reply_markup=reply_markup)

def add_post_choose_section(query, context):
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(
            section[1], 
            callback_data=f"add_post_choose_subsection_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📝 **Добавление записи**\n\nВыберите раздел:", reply_markup=reply_markup)

def add_post_choose_subsection(query, context):
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    subsections = conn.execute('SELECT * FROM subsections WHERE section_id = ? ORDER BY id', (section_id,)).fetchall()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    if not subsections:
        query.edit_message_text(f"В разделе '{section[1]}' нет подразделов.")
        return
    
    keyboard = []
    for subsection in subsections:
        keyboard.append([InlineKeyboardButton(
            subsection[2], 
            callback_data=f"add_post_{subsection[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='add_post_choose_section')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"📝 **Добавление записи в раздел:** {section[1]}\n\nВыберите подраздел:", reply_markup=reply_markup)

def add_post_start(query, context):
    subsection_id = int(query.data.split('_')[-1])
    context.user_data['adding_post'] = {
        'subsection_id': subsection_id,
        'step': 'title'
    }
    
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    query.edit_message_text(
        f"📝 **Добавление записи**\n\n"
        f"📁 Раздел: {section[1]}\n"
        f"📂 Подраздел: {subsection[2]}\n\n"
        f"Введите заголовок записи:"
    )

def back_to_main(query, context):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text('🏰 Главное меню базы знаний клана:', reply_markup=reply_markup)

def handle_message(update: Update, context: CallbackContext):
    user_data = context.user_data
    user = update.effective_user
    
    if user_data.get('adding_post'):
        post_data = user_data['adding_post']
        
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
            
            user_data.clear()
            update.message.reply_text("✅ Запись успешно добавлена!")
            
            # Возвращаем в главное меню
            keyboard = [
                [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
                [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text('🏰 Главное меню:', reply_markup=reply_markup)

def handle_photo(update: Update, context: CallbackContext):
    user_data = context.user_data
    
    if user_data.get('adding_post'):
        post_data = user_data['adding_post']
        
        # Сохраняем file_id изображения
        photo = update.message.photo[-1]
        post_data['image_file_id'] = photo.file_id
        
        update.message.reply_text("🖼️ Изображение сохранено! Теперь введите текст записи:")

def main():
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ BOT_TOKEN not found!")
        return
    
    try:
        # Инициализируем базу данных
        init_db()
        
        # Создаем updater и dispatcher
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Добавляем обработчики
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CallbackQueryHandler(button_handler))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dp.add_handler(MessageHandler(Filters.photo, handle_photo))
        
        print("✅ Bot started successfully!")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
