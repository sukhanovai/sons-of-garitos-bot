import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Путь к базе данных
DB_PATH = '/home/runner/sons-of-garitos-bot/clan_bot.db'

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
    print("✅ Database initialized")

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
    
    conn = get_db_connection()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    await query.edit_message_text(
        f"📁 **Создание подраздела в разделе:** {section[0]}\n\n"
        "Введите название для нового подраздела:"
    )
    context.user_data['awaiting_subsection_name'] = True

# Возврат в главное меню
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text('🏰 Главное меню базы знаний клана:', reply_markup=reply_markup)

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user = update.effective_user
    
    if user_data.get('awaiting_subsection_name'):
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
        
        keyboard = [
            [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
            [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
            [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
            [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('🏰 Главное меню:', reply_markup=reply_markup)
    
    else:
        await update.message.reply_text("✅ Бот работает! Используйте /start для меню.")

# Настройка бота
async def setup_bot(token: str):
    init_db()
    
    application = Application.builder().token(token).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики callback queries
    application.add_handler(CallbackQueryHandler(view_sections, pattern='^view_sections$'))
    application.add_handler(CallbackQueryHandler(view_subsections, pattern='^view_section_'))
    application.add_handler(CallbackQueryHandler(create_subsection_choose_section, pattern='^create_subsection_choose_section$'))
    application.add_handler(CallbackQueryHandler(create_subsection, pattern='^create_subsection_'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot setup completed")
    return application
    
