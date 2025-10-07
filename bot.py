import logging
import sqlite3
import os
import time
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')

# Проверка токена при запуске
if not TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    print("📝 Убедитесь, что переменная BOT_TOKEN добавлена в Environment Variables в настройках Render")
    print("🔄 Перезапуск через 10 секунд...")
    time.sleep(10)
    sys.exit(1)

print(f"✅ Токен бота получен: {TOKEN[:10]}...")

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clan_bot.db')

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
            content_type TEXT CHECK(content_type IN ('text', 'image', 'link', 'mixed')),
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
    print("✅ База данных инициализирована")

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    await update.message.reply_text(
        f'🏰 Добро пожаловать, {user.first_name}, в базу знаний клана Sons of Garitos!\n\n'
        'Теперь вы можете создавать разделы, подразделы и добавлять различные типы контента!',
        reply_markup=reply_markup
    )

# Просмотр разделов
async def view_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    sections = cursor.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    if not sections:
        await query.edit_message_text("Разделы пока не созданы.")
        return
    
    keyboard = []
    for section in sections:
        # Считаем количество подразделов и записей
        conn = get_db_connection()
        subs_count = conn.execute('SELECT COUNT(*) FROM subsections WHERE section_id = ?', (section[0],)).fetchone()[0]
        posts_count = conn.execute('''
            SELECT COUNT(*) FROM posts p 
            JOIN subsections s ON p.subsection_id = s.id 
            WHERE s.section_id = ?
        ''', (section[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{section[1]} ({subs_count} подраз., {posts_count} зап.)", 
            callback_data=f"view_section_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📂 Выберите раздел:", reply_markup=reply_markup)

# Просмотр подразделов в разделе
async def view_subsections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    subsections = cursor.execute(
        'SELECT * FROM subsections WHERE section_id = ? ORDER BY id', 
        (section_id,)
    ).fetchall()
    conn.close()
    
    if not subsections:
        keyboard = [
            [InlineKeyboardButton("📁 Создать подраздел", callback_data=f"create_subsection_{section_id}")],
            [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"В разделе '{section[1]}' пока нет подразделов.\n\n"
            f"Создайте первый подраздел!",
            reply_markup=reply_markup
        )
        return
    
    keyboard = []
    for subsection in subsections:
        # Считаем количество записей в подразделе
        conn = get_db_connection()
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE subsection_id = ?', (subsection[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{subsection[2]} ({posts_count} зап.)", 
            callback_data=f"view_subsection_{subsection[0]}"
        )])
    
    keyboard.extend([
        [InlineKeyboardButton("📁 Создать подраздел", callback_data=f"create_subsection_{section_id}")],
        [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📁 Раздел: {section[1]}\n\n"
        f"Выберите подраздел:",
        reply_markup=reply_markup
    )

# Просмотр записей в подразделе
async def view_subsection_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subsection_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    subsection = cursor.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    posts = cursor.execute(
        'SELECT * FROM posts WHERE subsection_id = ? ORDER BY created_at DESC', 
        (subsection_id,)
    ).fetchall()
    conn.close()
    
    if not posts:
        keyboard = [
            [InlineKeyboardButton("📝 Добавить первую запись", callback_data=f"add_post_to_{subsection_id}")],
            [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📁 {section[1]} → {subsection[2]}\n\n"
            f"В этом подразделе пока нет записей.\n"
            f"Будьте первым, кто добавит материал!",
            reply_markup=reply_markup
        )
        return
    
    # Показываем первую запись
    await show_post(query, posts[0], 0, len(posts), subsection_id)

# Показ конкретной записи
async def show_post(query, post, current_index, total_posts, subsection_id):
    keyboard = []
    
    # Навигация между записями
    if total_posts > 1:
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_post_{subsection_id}_{current_index-1}"))
        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_posts}", callback_data="noop"))
        if current_index < total_posts - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"nav_post_{subsection_id}_{current_index+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    # Получаем информацию о подразделе и разделе для кнопки назад
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section_id = subsection[1]
    conn.close()
    
    # Кнопки действий
    keyboard.extend([
        [InlineKeyboardButton("📝 Добавить запись сюда", callback_data=f"add_post_to_{subsection_id}")],
        [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section_id}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем контент в зависимости от типа
    content_parts = []
    
    if post[6]:  # content_text
        content_parts.append(f"📝 {post[6]}")
    
    if post[7]:  # image_file_id
        content_parts.append("🖼️ Есть изображение")
    
    if post[8]:  # link_url
        link_display = post[9] if post[9] else post[8]
        content_parts.append(f"🔗 {link_display}")
    
    content_display = "\n".join(content_parts) if content_parts else "📄 Текстовая запись"
    
    caption = (
        f"📖 **{post[4]}**\n\n"  # title
        f"{content_display}\n\n"
        f"👤 Автор: {post[3]}\n"  # user_name
        f"📅 {post[10]}\n"  # created_at
        f"📊 Тип: {post[5]}\n"  # content_type
    )
    
    try:
        if post[7]:  # Если есть картинка
            await query.message.reply_photo(
                photo=post[7],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            await query.message.delete()
        else:
            await query.edit_message_text(
                caption, 
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка при отображении записи: {str(e)}",
            reply_markup=reply_markup
        )

# Навигация по записям
async def navigate_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, _, subsection_id, index = query.data.split('_')
    subsection_id = int(subsection_id)
    index = int(index)
    
    conn = get_db_connection()
    posts = conn.execute(
        'SELECT * FROM posts WHERE subsection_id = ? ORDER BY created_at DESC', 
        (subsection_id,)
    ).fetchall()
    conn.close()
    
    if posts and 0 <= index < len(posts):
        await show_post(query, posts[index], index, len(posts), subsection_id)

# Создание раздела
async def create_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏗️ **Создание нового раздела**\n\n"
        "Введите название для нового раздела:"
    )
    context.user_data['awaiting_section_name'] = True

# Выбор раздела для создания подраздела
async def create_subsection_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(
            section[1], 
            callback_data=f"create_subsection_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📁 **Создание подраздела**\n\nВыберите раздел:", reply_markup=reply_markup)

# Создание подраздела
async def create_subsection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    context.user_data['creating_subsection'] = {'section_id': section_id}
    
    # Получаем название раздела для сообщения
    conn = get_db_connection()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    await query.edit_message_text(
        f"📁 **Создание подраздела в разделе:** {section[0]}\n\n"
        "Введите название для нового подраздела:"
    )
    context.user_data['awaiting_subsection_name'] = True

# Выбор раздела для добавления записи
async def add_post_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    keyboard = []
    for section in sections:
        # Считаем количество подразделов
        conn = get_db_connection()
        subs_count = conn.execute('SELECT COUNT(*) FROM subsections WHERE section_id = ?', (section[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{section[1]} ({subs_count} подраз.)", 
            callback_data=f"add_post_choose_subsection_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📝 **Добавление записи**\n\nВыберите раздел:", reply_markup=reply_markup)

# Выбор подраздела для добавления записи
async def add_post_choose_subsection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    subsections = conn.execute('SELECT * FROM subsections WHERE section_id = ? ORDER BY id', (section_id,)).fetchall()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    keyboard = []
    for subsection in subsections:
        # Считаем количество записей
        conn = get_db_connection()
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE subsection_id = ?', (subsection[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{subsection[2]} ({posts_count} зап.)", 
            callback_data=f"add_post_to_{subsection[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад к разделам", callback_data='add_post_choose_section')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 **Добавление записи в раздел:** {section[0]}\n\n"
        f"Выберите подраздел:",
        reply_markup=reply_markup
    )

# Начало добавления записи - выбор типа контента
async def start_add_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subsection_id = int(query.data.split('_')[-1])
    context.user_data['adding_post'] = {'subsection_id': subsection_id}
    
    # Получаем информацию о подразделе и разделе
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("📝 Только текст", callback_data='content_type_text')],
        [InlineKeyboardButton("🖼️ Текст + картинка", callback_data='content_type_image')],
        [InlineKeyboardButton("🔗 Текст + ссылка", callback_data='content_type_link')],
        [InlineKeyboardButton("🎨 Все вместе", callback_data='content_type_mixed')],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"add_post_choose_subsection_{subsection[1]}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 **Добавление записи**\n\n"
        f"Раздел: {section[0]}\n"
        f"Подраздел: {subsection[2]}\n\n"
        f"Выберите тип контента:",
        reply_markup=reply_markup
    )

# Обработка выбора типа контента
async def choose_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    content_type = query.data.replace('content_type_', '')
    context.user_data['adding_post']['content_type'] = content_type
    
    await query.edit_message_text(
        "✏️ **Введите заголовок для вашей записи:**"
    )
    context.user_data['awaiting_post_title'] = True

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user = update.effective_user
    
    if user_data.get('awaiting_section_name'):
        # Создание раздела
        section_name = update.message.text
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO sections (name, description, created_by) VALUES (?, ?, ?)',
            (section_name, "Описание раздела", user.id)
        )
        conn.commit()
        conn.close()
        
        user_data.clear()
        await update.message.reply_text(f"✅ Раздел '{section_name}' успешно создан!")
        await show_main_menu(update, context)
    
    elif user_data.get('awaiting_subsection_name'):
        # Создание подраздела
        subsection_name = update.message.text
        section_id = user_data['creating_subsection']['section_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO subsections (section_id, name, description, created_by) VALUES (?, ?, ?, ?)',
            (section_id, subsection_name, "Описание подраздела", user.id)
        )
        conn.commit()
        conn.close()
        
        user_data.clear()
        await update.message.reply_text(f"✅ Подраздел '{subsection_name}' успешно создан!")
        await show_main_menu(update, context)
    
    elif user_data.get('awaiting_post_title'):
        # Получили заголовок записи
        user_data['adding_post']['title'] = update.message.text
        user_data['awaiting_post_title'] = False
        
        content_type = user_data['adding_post']['content_type']
        
        if content_type in ['text', 'link']:
            # Для текста и ссылок сразу запрашиваем текст
            user_data['awaiting_post_text'] = True
            if content_type == 'link':
                await update.message.reply_text(
                    "✅ Заголовок сохранен!\n\n"
                    "Теперь введите текст записи:"
                )
            else:
                await update.message.reply_text(
                    "✅ Заголовок сохранен!\n\n"
                    "Теперь введите текст записи:"
                )
        elif content_type in ['image', 'mixed']:
            # Для картинок запрашиваем изображение
            user_data['awaiting_post_image'] = True
            await update.message.reply_text(
                "✅ Заголовок сохранен!\n\n"
                "Теперь отправьте картинку для этой записи 📷"
            )
    
    elif user_data.get('awaiting_post_text'):
        # Получили текст записи
        user_data['adding_post']['content_text'] = update.message.text
        user_data['awaiting_post_text'] = False
        
        content_type = user_data['adding_post']['content_type']
        
        if content_type == 'link':
            # Для ссылок запрашиваем URL
            user_data['awaiting_post_link'] = True
            await update.message.reply_text(
                "✅ Текст сохранен!\n\n"
                "Теперь отправьте ссылку (URL):"
            )
        else:
            # Для текста сохраняем запись
            await save_post_to_db(update, context)
    
    elif user_data.get('awaiting_post_link'):
        # Получили ссылку
        link_text = update.message.text
        
        # Простая проверка URL
        if link_text.startswith(('http://', 'https://')):
            user_data['adding_post']['link_url'] = link_text
            user_data['awaiting_post_link'] = False
            user_data['awaiting_post_link_title'] = True
            
            await update.message.reply_text(
                "✅ Ссылка сохранена!\n\n"
                "Теперь введите название для ссылки (или отправьте /skip чтобы использовать URL как название):"
            )
        else:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректный URL (должен начинаться с http:// или https://)\n\n"
                "Попробуйте еще раз:"
            )
    
    elif user_data.get('awaiting_post_link_title'):
        # Получили название ссылки
        if update.message.text != '/skip':
            user_data['adding_post']['link_title'] = update.message.text
        else:
            user_data['adding_post']['link_title'] = user_data['adding_post']['link_url']
        
        user_data['awaiting_post_link_title'] = False
        await save_post_to_db(update, context)
    
    elif user_data.get('awaiting_post_content_after_image'):
        # Получили текст после картинки
        user_data['adding_post']['content_text'] = update.message.text
        user_data['awaiting_post_content_after_image'] = False
        
        content_type = user_data['adding_post']['content_type']
        
        if content_type == 'mixed':
            # Для mixed типа запрашиваем ссылку после текста
            user_data['awaiting_post_link'] = True
            await update.message.reply_text(
                "✅ Текст сохранен!\n\n"
                "Теперь отправьте ссылку (URL) или /skip чтобы пропустить:"
            )
        else:
            # Для image типа сохраняем запись
            await save_post_to_db(update, context)

# Сохранение записи в БД
async def save_post_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user = update.effective_user
    
    # Определяем тип контента на основе заполненных полей
    content_type = user_data['adding_post']['content_type']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO posts 
        (subsection_id, user_id, user_name, title, content_type, content_text, image_file_id, link_url, link_title) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            user_data['adding_post']['subsection_id'],
            user.id,
            user.full_name,
            user_data['adding_post']['title'],
            content_type,
            user_data['adding_post'].get('content_text'),
            user_data['adding_post'].get('image_file_id'),
            user_data['adding_post'].get('link_url'),
            user_data['adding_post'].get('link_title')
        )
    )
    conn.commit()
    conn.close()
    
    # Получаем информацию о подразделе и разделе для сообщения
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (user_data['adding_post']['subsection_id'],)).fetchone()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    user_data.clear()
    
    content_types = {
        'text': '📝 текстовую запись',
        'image': '🖼️ запись с картинкой',
        'link': '🔗 запись со ссылкой',
        'mixed': '🎨 запись с картинкой и ссылкой'
    }
    
    await update.message.reply_text(
        f"✅ Вы успешно добавили {content_types[content_type]} в подраздел '{subsection[2]}' раздела '{section[0]}'!"
    )
    await show_main_menu(update, context)

# Обработка картинок
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    if user_data.get('awaiting_post_image'):
        # Сохраняем file_id картинки
        photo_file_id = update.message.photo[-1].file_id
        user_data['adding_post']['image_file_id'] = photo_file_id
        user_data['awaiting_post_image'] = False
        
        content_type = user_data['adding_post']['content_type']
        
        if content_type == 'mixed':
            user_data['awaiting_post_content_after_image'] = True
            await update.message.reply_text(
                "📷 Картинка сохранена!\n\n"
                "Теперь введите текст записи:"
            )
        else:
            # Для типа image сохраняем запись
            await save_post_to_db(update, context)

# Пропуск добавления ссылки
async def skip_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    if user_data.get('awaiting_post_link'):
        user_data['awaiting_post_link'] = False
        await save_post_to_db(update, context)

# Пустой обработчик
async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

# Главное меню
async def show_main_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text('🏰 Главное меню базы знаний клана Sons of Garitos:', reply_markup=reply_markup)

async def show_main_menu_from_query(query):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text('🏰 Главное меню базы знаний клана:', reply_markup=reply_markup)

# Возврат в главное меню
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main_menu_from_query(query)

# Основная функция запуска
def main():
    print("🚀 Запуск улучшенного бота Sons of Garitos...")
    
    if not TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не установлен!")
        return
    
    init_db()
    
    # Создаем приложение для версии 20.0
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("skip", skip_link))
    
    # Обработчики callback queries
    application.add_handler(CallbackQueryHandler(view_sections, pattern='^view_sections$'))
    application.add_handler(CallbackQueryHandler(create_section, pattern='^create_section$'))
    application.add_handler(CallbackQueryHandler(create_subsection_choose_section, pattern='^create_subsection_choose_section$'))
    application.add_handler(CallbackQueryHandler(create_subsection, pattern='^create_subsection_'))
    application.add_handler(CallbackQueryHandler(add_post_choose_section, pattern='^add_post_choose_section$'))
    application.add_handler(CallbackQueryHandler(add_post_choose_subsection, pattern='^add_post_choose_subsection_'))
    application.add_handler(CallbackQueryHandler(start_add_post, pattern='^add_post_to_'))
    application.add_handler(CallbackQueryHandler(choose_content_type, pattern='^content_type_'))
    application.add_handler(CallbackQueryHandler(view_subsections, pattern='^view_section_'))
    application.add_handler(CallbackQueryHandler(view_subsection_posts, pattern='^view_subsection_'))
    application.add_handler(CallbackQueryHandler(navigate_post, pattern='^nav_post_'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(noop, pattern='^noop$'))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Запускаем бота
    print("✅ Улучшенный бот запущен и готов к работе!")
    application.run_polling()

if __name__ == '__main__':
    main()
