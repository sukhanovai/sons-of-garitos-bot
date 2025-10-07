import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clan_bot.db')

def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            title TEXT NOT NULL,
            image_file_id TEXT,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (section_id) REFERENCES sections (id)
        )
    ''')
    
    # Создаем базовые разделы
    cursor.execute('''
        INSERT OR IGNORE INTO sections (id, name, description) 
        VALUES (1, '📚 Гайды по игре', 'Полезные гайды и стратегии'),
               (2, '⚔️ Библиотека сборок', 'Эффективные сборки персонажей'),
               (3, '📝 Заметки клана', 'Важные объявления и заметки')
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user = update.effective_user
    await update.message.reply_text(
        f'🏰 Добро пожаловать, {user.first_name}, в базу знаний клана Sons of Garitos!\n\n'
        'Здесь вы можете найти полезные материалы по игре RAID: Shadow Legends.',
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
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE section_id = ?', (section[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{section[1]} ({posts_count} записей)", 
            callback_data=f"view_section_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📂 Выберите раздел:", reply_markup=reply_markup)

# Просмотр записей в разделе
async def view_section_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    section = cursor.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
    posts = cursor.execute(
        'SELECT * FROM posts WHERE section_id = ? ORDER BY created_at DESC', 
        (section_id,)
    ).fetchall()
    conn.close()
    
    if not posts:
        keyboard = [
            [InlineKeyboardButton("📝 Добавить первую запись", callback_data=f"add_post_to_{section_id}")],
            [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"В разделе '{section[1]}' пока нет записей.\n\n"
            f"Будьте первым, кто добавит материал!",
            reply_markup=reply_markup
        )
        return
    
    # Показываем первую запись
    await show_post(query, posts[0], 0, len(posts), section_id)

# Показ конкретной записи
async def show_post(query, post, current_index, total_posts, section_id):
    keyboard = []
    
    # Навигация между записями
    if total_posts > 1:
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_post_{section_id}_{current_index-1}"))
        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_posts}", callback_data="noop"))
        if current_index < total_posts - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"nav_post_{section_id}_{current_index+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    # Кнопки действий
    keyboard.extend([
        [InlineKeyboardButton("📝 Добавить запись в этот раздел", callback_data=f"add_post_to_{section_id}")],
        [InlineKeyboardButton("📂 К разделам", callback_data='view_sections')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_main')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = (
        f"📖 **{post[4]}**\n\n"
        f"📝 {post[6] or 'Описание отсутствует'}\n\n"
        f"👤 Автор: {post[3]}\n"
        f"📅 {post[7]}\n"
    )
    
    try:
        if post[5]:
            await query.message.reply_photo(
                photo=post[5],
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
    
    _, _, section_id, index = query.data.split('_')
    section_id = int(section_id)
    index = int(index)
    
    conn = get_db_connection()
    posts = conn.execute(
        'SELECT * FROM posts WHERE section_id = ? ORDER BY created_at DESC', 
        (section_id,)
    ).fetchall()
    conn.close()
    
    if posts and 0 <= index < len(posts):
        await show_post(query, posts[index], index, len(posts), section_id)

# Создание раздела
async def create_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏗️ **Создание нового раздела**\n\n"
        "Введите название для нового раздела:"
    )
    context.user_data['awaiting_section_name'] = True

# Выбор раздела для добавления записи
async def add_post_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    sections = conn.execute('SELECT * FROM sections ORDER BY id').fetchall()
    conn.close()
    
    keyboard = []
    for section in sections:
        conn = get_db_connection()
        posts_count = conn.execute('SELECT COUNT(*) FROM posts WHERE section_id = ?', (section[0],)).fetchone()[0]
        conn.close()
        
        keyboard.append([InlineKeyboardButton(
            f"{section[1]} ({posts_count} зап.)", 
            callback_data=f"add_post_to_{section[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📝 **Добавление записи**\n\nВыберите раздел:", reply_markup=reply_markup)

# Начало добавления записи
async def start_add_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section_id = int(query.data.split('_')[-1])
    context.user_data['adding_post'] = {'section_id': section_id}
    
    conn = get_db_connection()
    section = conn.execute('SELECT name FROM sections WHERE id = ?', (section_id,)).fetchone()
    conn.close()
    
    await query.edit_message_text(
        f"📝 **Добавление записи в раздел:** {section[0]}\n\n"
        "Введите заголовок для вашей записи:"
    )
    context.user_data['awaiting_post_title'] = True

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user = update.effective_user
    
    if user_data.get('awaiting_section_name'):
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
    
    elif user_data.get('awaiting_post_title'):
        user_data['adding_post']['title'] = update.message.text
        user_data['awaiting_post_title'] = False
        user_data['awaiting_post_image'] = True
        
        await update.message.reply_text(
            "✅ Заголовок сохранен!\n\n"
            "Теперь отправьте картинку для этой записи 📷\n"
            "Или отправьте /skip чтобы пропустить добавление картинки"
        )
    
    elif user_data.get('awaiting_post_content'):
        user_data['adding_post']['content'] = update.message.text
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO posts (section_id, user_id, user_name, title, image_file_id, content) VALUES (?, ?, ?, ?, ?, ?)',
            (
                user_data['adding_post']['section_id'],
                user.id,
                user.full_name,
                user_data['adding_post']['title'],
                user_data['adding_post'].get('image_file_id'),
                user_data['adding_post']['content']
            )
        )
        conn.commit()
        conn.close()
        
        conn = get_db_connection()
        section = conn.execute('SELECT name FROM sections WHERE id = ?', (user_data['adding_post']['section_id'],)).fetchone()
        conn.close()
        
        user_data.clear()
        await update.message.reply_text(f"✅ Запись успешно добавлена в раздел '{section[0]}'!")
        await show_main_menu(update, context)

# Обработка картинок
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    if user_data.get('awaiting_post_image'):
        photo_file_id = update.message.photo[-1].file_id
        user_data['adding_post']['image_file_id'] = photo_file_id
        user_data['awaiting_post_image'] = False
        user_data['awaiting_post_content'] = True
        
        await update.message.reply_text("📷 Картинка сохранена!\n\nТеперь введите текст записи:")

# Пропуск добавления картинки
async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    
    if user_data.get('awaiting_post_image'):
        user_data['awaiting_post_image'] = False
        user_data['awaiting_post_content'] = True
        
        await update.message.reply_text("⏭️ Пропускаем картинку. Теперь введите текст записи:")

# Пустой обработчик
async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

# Главное меню
async def show_main_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text('🏰 Главное меню базы знаний клана Sons of Garitos:', reply_markup=reply_markup)

async def show_main_menu_from_query(query):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text('🏰 Главное меню базы знаний клана:', reply_markup=reply_markup)

# Возврат в главное меню
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main_menu_from_query(query)

def main():
    print("🚀 Запуск бота Sons of Garitos...")
    
    if not TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не установлен!")
        return
    
    init_db()
    
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("skip", skip_photo))
    
    # Обработчики callback queries
    application.add_handler(CallbackQueryHandler(view_sections, pattern='^view_sections$'))
    application.add_handler(CallbackQueryHandler(create_section, pattern='^create_section$'))
    application.add_handler(CallbackQueryHandler(add_post_choose_section, pattern='^add_post_choose_section$'))
    application.add_handler(CallbackQueryHandler(start_add_post, pattern='^add_post_to_'))
    application.add_handler(CallbackQueryHandler(view_section_posts, pattern='^view_section_'))
    application.add_handler(CallbackQueryHandler(navigate_post, pattern='^nav_post_'))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(noop, pattern='^noop$'))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("✅ Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == '__main__':
    main()
