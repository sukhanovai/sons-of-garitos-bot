import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Путь к базе данных - исправленный для Replit
DB_PATH = os.path.join(os.getcwd(), 'clan_bot.db')

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    try:
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
        print(f"✅ Database initialized at: {DB_PATH}")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        raise

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    try:
        raise context.error
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️ Error handled: {error_msg}")
        
        # Игнорируем ошибки устаревших callback queries
        if "Query is too old" in error_msg or "query id is invalid" in error_msg:
            return
        
        # Для других ошибок можно отправить сообщение пользователю
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте снова."
                )
            except:
                pass

# Безопасное получение данных из кортежа
def safe_get(data, index, default="Неизвестно"):
    """Безопасно получает элемент из кортежа по индексу"""
    if data and len(data) > index:
        return data[index]
    return default

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
        [InlineKeyboardButton("⚙️ Управление контентом", callback_data='manage_content')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    if update.message:
        await update.message.reply_text(
            f'🏰 Добро пожаловать, {user.first_name}, в базу знаний клана Sons of Garitos!\n\n'
            'Теперь вы можете создавать разделы, подразделы и добавлять различные типы контента!',
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            f'🏰 Добро пожаловать, {user.first_name}, в базу знаний клана Sons of Garitos!\n\n'
            'Теперь вы можете создавать разделы, подразделы и добавлять различные типы контента!',
            reply_markup=reply_markup
        )

# Просмотр разделов
async def view_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
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
        
        section_name = safe_get(section, 1, "Без названия")
        keyboard.append([InlineKeyboardButton(
            f"{section_name} ({subs_count} подраз., {posts_count} зап.)", 
            callback_data=f"view_section_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📂 Выберите раздел:", reply_markup=reply_markup)

# Просмотр подразделов в разделе
async def view_subsections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    subsections = cursor.execute(
        'SELECT * FROM subsections WHERE section_id = ? ORDER BY id', 
        (section_id,)
    ).fetchall()
    conn.close()
    
    if not section:
        await query.edit_message_text("❌ Раздел не найден!")
        return
    
    section_name = safe_get(section, 1, "Без названия")
    
    if not subsections:
        keyboard = [
            [InlineKeyboardButton("📁 Создать подраздел", callback_data=f"create_subsection_{section_id}")],
            [InlineKeyboardButton("✏️ Редактировать раздел", callback_data=f"edit_section_{section_id}")],
            [InlineKeyboardButton("🗑️ Удалить раздел", callback_data=f"delete_section_{section_id}")],
            [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"В разделе '{section_name}' пока нет подразделов.\n\n"
            f"Создайте первый подраздел!",
            reply_markup=reply_markup
        )
        return
    
    keyboard = []
    for subsection in subsections:
        conn = get_db_connection()
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE subsection_id = ?', (subsection[0],)).fetchone()[0]
        conn.close()
        
        subsection_name = safe_get(subsection, 2, "Без названия")
        keyboard.append([InlineKeyboardButton(
            f"{subsection_name} ({posts_count} зап.)", 
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
    
    await query.edit_message_text(
        f"📁 Раздел: {section_name}\n\n"
        f"Выберите подраздел:",
        reply_markup=reply_markup
    )

# Просмотр записей в подразделе
async def view_subsection_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    subsection_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    subsection = cursor.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    if not subsection:
        await query.edit_message_text("❌ Подраздел не найден!")
        conn.close()
        return
    
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    posts = cursor.execute(
        'SELECT * FROM posts WHERE subsection_id = ? ORDER BY created_at DESC', 
        (subsection_id,)
    ).fetchall()
    conn.close()
    
    if not section:
        await query.edit_message_text("❌ Раздел не найден!")
        return
    
    section_name = safe_get(section, 1, "Без названия")
    subsection_name = safe_get(subsection, 2, "Без названия")
    
    if not posts:
        keyboard = [
            [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection_id}")],
            [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection_id}")],
            [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection_id}")],
            [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📁 Раздел: {section_name}\n"
            f"📂 Подраздел: {subsection_name}\n\n"
            f"Записей пока нет.\n\n"
            f"Создайте первую запись!",
            reply_markup=reply_markup
        )
        return
    
    # Показываем первую запись с навигацией
    context.user_data['current_subsection'] = subsection_id
    context.user_data['current_post_index'] = 0
    context.user_data['posts'] = posts
    
    await show_post(update, context, subsection, section, posts[0], 0, len(posts))

async def show_post(update: Update, context: ContextTypes.DEFAULT_TYPE, subsection, section, post, index, total):
    query = update.callback_query
    
    # Формируем текст записи
    section_name = safe_get(section, 1, "Без названия")
    subsection_name = safe_get(subsection, 2, "Без названия")
    post_title = safe_get(post, 4, "Без заголовка")
    post_content = safe_get(post, 6, "")
    post_author = safe_get(post, 3, "Неизвестно")
    post_date = safe_get(post, 10, "")
    link_url = safe_get(post, 8, "")
    link_title = safe_get(post, 9, "")
    
    post_text = f"📁 {section_name} → {subsection_name}\n\n"
    post_text += f"📌 {post_title}\n\n"
    
    if post_content:
        post_text += f"{post_content}\n\n"
    
    if link_url and link_title:
        post_text += f"🔗 {link_title}\n{link_url}\n\n"
    
    post_text += f"👤 Автор: {post_author}\n"
    if post_date:
        post_text += f"📅 {post_date}\n"
    post_text += f"📊 ({index + 1}/{total})"
    
    keyboard = []
    
    # Навигация по записям
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"prev_post_{index}"))
    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"next_post_{index}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Действия с записью
    keyboard.extend([
        [InlineKeyboardButton("✏️ Редактировать запись", callback_data=f"edit_post_{post[0]}")],
        [InlineKeyboardButton("🗑️ Удалить запись", callback_data=f"delete_post_{post[0]}")],
        [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection[0]}")],
        [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection[0]}")],
        [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection[0]}")],
        [InlineKeyboardButton("📂 К подразделам", callback_data=f"view_section_{section[0]}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если есть изображение, отправляем его с текстом
    image_file_id = safe_get(post, 7, "")
    if image_file_id:
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=image_file_id, caption=post_text),
                reply_markup=reply_markup
            )
        except:
            await query.edit_message_text(post_text, reply_markup=reply_markup)
    else:
        await query.edit_message_text(post_text, reply_markup=reply_markup)

# Навигация по записям
async def navigate_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    action, index = query.data.split('_')[0], int(query.data.split('_')[-1])
    
    subsection_id = context.user_data['current_subsection']
    posts = context.user_data['posts']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    subsection = cursor.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    if action == 'prev':
        new_index = index - 1
    else:  # next
        new_index = index + 1
    
    context.user_data['current_post_index'] = new_index
    await show_post(update, context, subsection, section, posts[new_index], new_index, len(posts))

# Выбор раздела для создания подраздела
async def create_subsection_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    keyboard = []
    for section in sections:
        section_name = safe_get(section, 1, "Без названия")
        keyboard.append([InlineKeyboardButton(
            section_name, 
            callback_data=f"create_subsection_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📁 **Создание подраздела**\n\nВыберите раздел:", reply_markup=reply_markup)

# Создание подраздела
async def create_subsection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    section_id = int(query.data.split('_')[-1])
    context.user_data['creating_subsection'] = {'section_id': section_id}
    
    conn = get_db_connection()
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    if not section:
        await query.edit_message_text("❌ Раздел не найден!")
        return
    
    section_name = safe_get(section, 1, "Без названия")
    
    await query.edit_message_text(
        f"📁 **Создание подраздела в разделе:** {section_name}\n\n"
        "Введите название для нового подраздела:"
    )
    context.user_data['awaiting_subsection_name'] = True

# Выбор раздела для добавления записи
async def add_post_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    keyboard = []
    for section in sections:
        section_name = safe_get(section, 1, "Без названия")
        keyboard.append([InlineKeyboardButton(
            section_name, 
            callback_data=f"add_post_choose_subsection_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📝 **Добавление записи**\n\nВыберите раздел:", reply_markup=reply_markup)

# Выбор подраздела для добавления записи
async def add_post_choose_subsection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    subsections = conn.execute('SELECT * FROM subsections WHERE section_id = ? ORDER BY id', (section_id,)).fetchall()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    if not section:
        await query.edit_message_text("❌ Раздел не найден!")
        return
    
    section_name = safe_get(section, 1, "Без названия")
    
    if not subsections:
        await query.edit_message_text(
            f"В разделе '{section_name}' нет подразделов. Сначала создайте подраздел."
        )
        return
    
    keyboard = []
    for subsection in subsections:
        subsection_name = safe_get(subsection, 2, "Без названия")
        keyboard.append([InlineKeyboardButton(
            subsection_name, 
            callback_data=f"add_post_{subsection[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='add_post_choose_section')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 **Добавление записи в раздел:** {section_name}\n\nВыберите подраздел:",
        reply_markup=reply_markup
    )

# НАЧАЛО ДОБАВЛЕНИЯ ЗАПИСИ - ПОЛНОСТЬЮ ПЕРЕПИСАННАЯ ФУНКЦИЯ
async def add_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    subsection_id = int(query.data.split('_')[-1])
    context.user_data['adding_post'] = {
        'subsection_id': subsection_id,
        'step': 'title'
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем данные подраздела
    subsection = cursor.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    
    if not subsection:
        await query.edit_message_text("❌ Подраздел не найден!")
        conn.close()
        return
    
    # Получаем данные раздела
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    if not section:
        await query.edit_message_text("❌ Раздел не найден!")
        return
    
    # Безопасно получаем названия
    section_name = safe_get(section, 1, "Без названия")
    subsection_name = safe_get(subsection, 2, "Без названия")
    
    await query.edit_message_text(
        f"📝 **Добавление записи**\n\n"
        f"📁 Раздел: {section_name}\n"
        f"📂 Подраздел: {subsection_name}\n\n"
        f"Введите заголовок записи:"
    )

# [ОСТАВШИЕСЯ ФУНКЦИИ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ...]

# Настройка бота
async def setup_bot(token: str):
    init_db()
    
    application = Application.builder().token(token).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики callback queries
    application.add_handler(CallbackQueryHandler(view_sections, pattern='^view_sections$'))
    application.add_handler(CallbackQueryHandler(view_subsections, pattern='^view_section_'))
    application.add_handler(CallbackQueryHandler(view_subsection_posts, pattern='^view_subsection_'))
    application.add_handler(CallbackQueryHandler(navigate_posts, pattern='^(prev|next)_post_'))
    application.add_handler(CallbackQueryHandler(create_subsection_choose_section, pattern='^create_subsection_choose_section$'))
    application.add_handler(CallbackQueryHandler(create_subsection, pattern='^create_subsection_'))
    application.add_handler(CallbackQueryHandler(add_post_choose_section, pattern='^add_post_choose_section$'))
    application.add_handler(CallbackQueryHandler(add_post_choose_subsection, pattern='^add_post_choose_subsection_'))
    application.add_handler(CallbackQueryHandler(add_post_start, pattern='^add_post_'))
    application.add_handler(CallbackQueryHandler(create_section, pattern='^create_section$'))
    application.add_handler(CallbackQueryHandler(manage_content, pattern='^manage_content$'))
    application.add_handler(CallbackQueryHandler(manage_sections, pattern='^manage_sections$'))
    application.add_handler(CallbackQueryHandler(edit_section, pattern='^edit_section_'))
    application.add_handler(CallbackQueryHandler(delete_section, pattern='^delete_section_'))
    application.add_handler(CallbackQueryHandler(confirm_delete_section, pattern='^confirm_delete_section_'))
    application.add_handler(CallbackQueryHandler(handle_content_type, pattern='^content_type_'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Bot setup completed")
    return application
    
