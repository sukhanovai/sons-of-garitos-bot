import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = "8108913508:AAH0Cp-Tweu-JQLxjPHfM7q6d2VF-L5HTHI" 

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
        query.edit_message_text(f"В разделе '{section[1]}' пока нет подразделов.\n\nСоздайте первый подраздел!", reply_markup=reply_markup)
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
            [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection_id}")],
            [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection_id}")],
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
        [InlineKeyboardButton("✏️ Редактировать подраздел", callback_data=f"edit_subsection_{subsection_id}")],
        [InlineKeyboardButton("🗑️ Удалить подраздел", callback_data=f"delete_subsection_{subsection_id}")],
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

def create_section(query, context):
    context.user_data['creating_section'] = True
    query.edit_message_text(
        "➕ **Создание раздела**\n\n"
        "Введите название для нового раздела:"
    )

def create_subsection_choose_section(query, context):
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
    query.edit_message_text("📁 **Создание подраздела**\n\nВыберите раздел:", reply_markup=reply_markup)

def create_subsection(query, context):
    section_id = int(query.data.split('_')[-1])
    context.user_data['creating_subsection'] = {'section_id': section_id}
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    query.edit_message_text(
        f"📁 **Создание подраздела в разделе:** {section[1]}\n\n"
        "Введите название для нового подраздела:"
    )
    context.user_data['awaiting_subsection_name'] = True

def manage_content(query, context):
    keyboard = [
        [InlineKeyboardButton("📚 Управление разделами", callback_data='manage_sections')],
        [InlineKeyboardButton("📁 Управление подразделами", callback_data='manage_subsections')],
        [InlineKeyboardButton("📝 Управление записями", callback_data='manage_posts')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("⚙️ **Управление контентом**\n\nВыберите что хотите управлять:", reply_markup=reply_markup)

def manage_sections(query, context):
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    if not sections:
        keyboard = [
            [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
            [InlineKeyboardButton("◀️ Назад", callback_data='manage_content')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("Разделы пока не созданы.", reply_markup=reply_markup)
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
    
    keyboard.append([InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='manage_content')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📚 **Управление разделами**\n\nВыберите раздел для редактирования или удаления:", reply_markup=reply_markup)

def edit_section(query, context):
    section_id = int(query.data.split('_')[-1])
    context.user_data['editing_section'] = section_id
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    query.edit_message_text(
        f"✏️ **Редактирование раздела**\n\n"
        f"Текущее название: {section[1]}\n"
        f"Текущее описание: {section[2]}\n\n"
        f"Введите новое название раздела:"
    )
    context.user_data['awaiting_section_name'] = True

def delete_section(query, context):
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    
    if not section:
        query.edit_message_text("❌ Раздел не найден!")
        conn.close()
        return
    
    # Проверяем есть ли подразделы
    subs_count = conn.execute('SELECT COUNT(*) FROM subsections WHERE section_id = ?', (section_id,)).fetchone()[0]
    
    if subs_count > 0:
        conn.close()
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить всё", callback_data=f"confirm_delete_section_{section_id}")],
            [InlineKeyboardButton("❌ Нет, отмена", callback_data='manage_sections')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
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
    
    query.edit_message_text(f"✅ Раздел '{section[1]}' успешно удален!")
    manage_sections(query, context)

def confirm_delete_section(query, context):
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    
    if not section:
        query.edit_message_text("❌ Раздел не найден!")
        conn.close()
        return
    
    # Удаляем все связанные записи и подразделы
    subsections = conn.execute('SELECT id FROM subsections WHERE section_id = ?', (section_id,)).fetchall()
    for subsection in subsections:
        conn.execute('DELETE FROM posts WHERE subsection_id = ?', (subsection[0],))
    
    conn.execute('DELETE FROM subsections WHERE section_id = ?', (section_id,))
    conn.execute('DELETE FROM sections WHERE id = ?', (section_id,))
    conn.commit()
    conn.close()
    
    query.edit_message_text(f"✅ Раздел '{section[1]}' и все его содержимое успешно удалены!")
    manage_sections(query, context)

def back_to_main(query, context):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📁 Создать подраздел", callback_data='create_subsection_choose_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')],
        [InlineKeyboardButton("⚙️ Управление контентом", callback_data='manage_content')]
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
            back_to_main_message(update, context)
    
    elif user_data.get('awaiting_subsection_name'):
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
        update.message.reply_text(f"✅ Подраздел '{subsection_name}' успешно создан!")
        back_to_main_message(update, context)
    
    elif user_data.get('awaiting_section_name'):
        section_name = update.message.text
        
        if user_data.get('editing_section'):
            # Редактирование существующего раздела
            section_id = user_data['editing_section']
            conn = get_db_connection()
            conn.execute('UPDATE sections SET name = ? WHERE id = ?', (section_name, section_id))
            conn.commit()
            conn.close()
            
            user_data.clear()
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
            
            user_data.clear()
            update.message.reply_text(f"✅ Раздел '{section_name}' успешно создан!")
        
        back_to_main_message(update, context)
    
    else:
        update.message.reply_text("✅ Бот работает! Используйте /start для меню.")

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

def handle_photo(update: Update, context: CallbackContext):
    user_data = context.user_data
    
    if user_data.get('adding_post'):
        post_data = user_data['adding_post']
        
        # Сохраняем file_id изображения
        photo = update.message.photo[-1]
        post_data['image_file_id'] = photo.file_id
        
        update.message.reply_text("🖼️ Изображение сохранено! Теперь введите текст записи:")

def main():
    TOKEN = BOT_TOKEN    
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