import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
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
            [InlineKeyboardButton("✏️ Редактировать раздел", callback_data=f"edit_section_{section_id}")],
            [InlineKeyboardButton("🗑️ Удалить раздел", callback_data=f"delete_section_{section_id}")],
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
        [InlineKeyboardButton("✏️ Редактировать раздел", callback_data=f"edit_section_{section_id}")],
        [InlineKeyboardButton("🗑️ Удалить раздел", callback_data=f"delete_section_{section_id}")],
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
            [InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_post_{subsection_id}")],
            [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection_id}")],
            [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection_id}")],
            [InlineKeyboardButton("📁 К подразделам", callback_data=f"view_section_{section[0]}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📁 Раздел: {section[1]}\n"
            f"📂 Подраздел: {subsection[2]}\n\n"
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
    post_text = f"📁 {section[1]} → {subsection[2]}\n\n"
    post_text += f"📌 {post[4]}\n\n"
    
    if post[6]:  # content_text
        post_text += f"{post[6]}\n\n"
    
    if post[8] and post[9]:  # link_url и link_title
        post_text += f"🔗 {post[9]}\n{post[8]}\n\n"
    
    post_text += f"👤 Автор: {post[3]}\n"
    post_text += f"📅 {post[10]}\n"
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
    if post[7]:  # image_file_id
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=post[7], caption=post_text),
                reply_markup=reply_markup
            )
        except:
            await query.edit_message_text(post_text, reply_markup=reply_markup)
    else:
        await query.edit_message_text(post_text, reply_markup=reply_markup)

# Навигация по записям
async def navigate_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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

# Выбор раздела для добавления записи
async def add_post_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
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
    
    if not subsections:
        await query.edit_message_text(
            f"В разделе '{section[0]}' нет подразделов. Сначала создайте подраздел."
        )
        return
    
    keyboard = []
    for subsection in subsections:
        keyboard.append([InlineKeyboardButton(
            subsection[2], 
            callback_data=f"add_post_{subsection[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='add_post_choose_section')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 **Добавление записи в раздел:** {section[0]}\n\nВыберите подраздел:",
        reply_markup=reply_markup
    )

# Начало добавления записи
async def add_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subsection_id = int(query.data.split('_')[-1])
    context.user_data['adding_post'] = {
        'subsection_id': subsection_id,
        'step': 'title'
    }
    
    conn = get_db_connection()
    subsection = conn.execute('SELECT * FROM subsections WHERE id = ?', (subsection_id,)).fetchone()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (subsection[1],)).fetchone()
    conn.close()
    
    await query.edit_message_text(
        f"📝 **Добавление записи**\n\n"
        f"📁 Раздел: {section[1]}\n"
        f"📂 Подраздел: {subsection[2]}\n\n"
        f"Введите заголовок записи:"
    )

# Создание раздела
async def create_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['creating_section'] = True
    
    await query.edit_message_text(
        "➕ **Создание раздела**\n\n"
        "Введите название для нового раздела:"
    )

# Управление контентом
async def manage_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📚 Управление разделами", callback_data='manage_sections')],
        [InlineKeyboardButton("📁 Управление подразделами", callback_data='manage_subsections')],
        [InlineKeyboardButton("📝 Управление записями", callback_data='manage_posts')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("⚙️ **Управление контентом**\n\nВыберите что хотите управлять:", reply_markup=reply_markup)

# Управление разделами
async def manage_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    if not sections:
        await query.edit_message_text("Разделы пока не созданы.")
        return
    
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(
            f"✏️ {section[1]}", 
            callback_data=f"edit_section_{section[0]}"
        )])
        keyboard.append([InlineKeyboardButton(
            f"🗑️ Удалить {section[1]}", 
            callback_data=f"delete_section_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='manage_content')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📚 **Управление разделами**\n\nВыберите раздел для редактирования или удаления:", reply_markup=reply_markup)

# Редактирование раздела
async def edit_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    context.user_data['editing_section'] = section_id
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    await query.edit_message_text(
        f"✏️ **Редактирование раздела**\n\n"
        f"Текущее название: {section[1]}\n"
        f"Текущее описание: {section[2] or 'нет'}\n\n"
        f"Введите новое название раздела:"
    )
    context.user_data['awaiting_section_name'] = True

# Удаление раздела
async def delete_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    
    # Проверяем есть ли подразделы
    subs_count = conn.execute('SELECT COUNT(*) FROM subsections WHERE section_id = ?', (section_id,)).fetchone()[0]
    
    if subs_count > 0:
        conn.close()
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить всё", callback_data=f"confirm_delete_section_{section_id}")],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data='manage_sections')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ **Удаление раздела**\n\n"
            f"Раздел '{section[1]}' содержит {subs_count} подразделов.\n"
            f"Все подразделы и записи в них будут также удалены!\n\n"
            f"Вы уверены что хотите удалить раздел?",
            reply_markup=reply_markup
        )
        return
    
    # Удаляем раздел если нет подразделов
    conn.execute('DELETE FROM sections WHERE id = ?', (section_id,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ Раздел '{section[1]}' успешно удален!")
    await manage_sections(update, context)

# Подтверждение удаления раздела
async def confirm_delete_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    
    # Удаляем все связанные записи и подразделы
    subsections = conn.execute('SELECT id FROM subsections WHERE section_id = ?', (section_id,)).fetchall()
    for subsection in subsections:
        conn.execute('DELETE FROM posts WHERE subsection_id = ?', (subsection[0],))
    
    conn.execute('DELETE FROM subsections WHERE section_id = ?', (section_id,))
    conn.execute('DELETE FROM sections WHERE id = ?', (section_id,))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(f"✅ Раздел '{section[1]}' и все его содержимое успешно удалены!")
    await manage_sections(update, context)

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
        await start(update, context)
    
    elif user_data.get('awaiting_section_name'):
        section_name = update.message.text
        section_id = user_data.get('editing_section')
        
        conn = get_db_connection()
        if section_id:  # Редактирование существующего
            conn.execute('UPDATE sections SET name = ? WHERE id = ?', (section_name, section_id))
            action = "обновлен"
        else:  # Создание нового
            conn.execute(
                'INSERT INTO sections (name, description, created_by) VALUES (?, ?, ?)',
                (section_name, "Описание раздела", user.id)
            )
            action = "создан"
        
        conn.commit()
        conn.close()
        
        user_data.clear()
        await update.message.reply_text(f"✅ Раздел '{section_name}' успешно {action}!")
        await start(update, context)
    
    elif user_data.get('adding_post'):
        post_data = user_data['adding_post']
        
        if post_data['step'] == 'title':
            post_data['title'] = update.message.text
            post_data['step'] = 'content'
            
            keyboard = [
                [InlineKeyboardButton("📝 Только текст", callback_data='content_type_text')],
                [InlineKeyboardButton("🖼️ Только изображение", callback_data='content_type_image')],
                [InlineKeyboardButton("🔗 Только ссылка", callback_data='content_type_link')],
                [InlineKeyboardButton("📄 Текст + изображение", callback_data='content_type_mixed')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📝 Заголовок сохранен: {post_data['title']}\n\n"
                f"Выберите тип контента:",
                reply_markup=reply_markup
            )
        
        elif post_data['step'] == 'content_text':
            post_data['content_text'] = update.message.text
            post_data['step'] = 'complete'
            
            # Сохраняем запись
            await save_post(update, context, post_data, user)
    
    else:
        await update.message.reply_text("✅ Бот работает! Используйте /start для меню.")

# Обработка изображений
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    if user_data.get('adding_post'):
        post_data = user_data['adding_post']
        
        if post_data.get('content_type') == 'image' or post_data.get('content_type') == 'mixed':
            # Сохраняем file_id изображения
            photo = update.message.photo[-1]
            post_data['image_file_id'] = photo.file_id
            
            if post_data['content_type'] == 'image':
                post_data['step'] = 'complete'
                await save_post(update, context, post_data, update.effective_user)
            else:
                post_data['step'] = 'content_text'
                await update.message.reply_text("🖼️ Изображение сохранено! Теперь введите текст:")

# Сохранение записи в БД
async def save_post(update: Update, context: ContextTypes.DEFAULT_TYPE, post_data, user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Определяем тип контента
    content_type = post_data.get('content_type', 'text')
    
    cursor.execute('''
        INSERT INTO posts (subsection_id, user_id, user_name, title, content_type, 
                          content_text, image_file_id, link_url, link_title)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        post_data['subsection_id'],
        user.id,
        user.first_name,
        post_data['title'],
        content_type,
        post_data.get('content_text'),
        post_data.get('image_file_id'),
        post_data.get('link_url'),
        post_data.get('link_title')
    ))
    
    conn.commit()
    conn.close()
    
    context.user_data.clear()
    await update.message.reply_text("✅ Запись успешно добавлена!")
    await start(update, context)

# Обработка выбора типа контента
async def handle_content_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    content_type = query.data.split('_')[-1]
    user_data = context.user_data
    
    if user_data.get('adding_post'):
        user_data['adding_post']['content_type'] = content_type
        
        if content_type == 'text':
            user_data['adding_post']['step'] = 'content_text'
            await query.edit_message_text("📝 Введите текст записи:")
        
        elif content_type == 'image':
            user_data['adding_post']['step'] = 'content_image'
            await query.edit_message_text("🖼️ Отправьте изображение:")
        
        elif content_type == 'link':
            user_data['adding_post']['step'] = 'link_url'
            await query.edit_message_text("🔗 Введите URL ссылки:")
        
        elif content_type == 'mixed':
            user_data['adding_post']['step'] = 'content_image'
            await query.edit_message_text("🖼️ Сначала отправьте изображение:")

# Обработка ссылок
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    if user_data.get('adding_post') and user_data['adding_post'].get('step') == 'link_url':
        link_url = update.message.text
        
        # Простая валидация URL
        if not link_url.startswith(('http://', 'https://')):
            link_url = 'https://' + link_url
        
        user_data['adding_post']['link_url'] = link_url
        user_data['adding_post']['step'] = 'link_title'
        
        await update.message.reply_text("🔗 Введите заголовок для ссылки:")

# Возврат в главное меню
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
        [InlineKeyboardButton("⚙️ Управление контентом", callback_data='manage_content')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text('🏰 Главное меню базы знаний клана:', reply_markup=reply_markup)

# Настройка бота
async def setup_bot(token: str):
    init_db()
    
    application = Application.builder().token(token).build()
    
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
    
