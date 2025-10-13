import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

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
    
    # Создаем базовые разделы
    cursor.execute('''
        INSERT OR IGNORE INTO sections (id, name, description) 
        VALUES 
            (1, '📚 Гайды по игре', 'Полезные гайды и стратегии'),
            (2, '⚔️ Библиотека сборок', 'Эффективные сборки персонажей'),
            (3, '📝 Заметки клана', 'Важные объявления и заметки'),
            (4, '🔗 Полезные ссылки', 'Ссылки на ресурсы и инструменты')
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
        [InlineKeyboardButton("📝 Добавить запись", callback_data='add_post')],
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
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("📂 Выберите раздел:", reply_markup=reply_markup)
    
    elif query.data.startswith('view_section_'):
        section_id = int(query.data.split('_')[-1])
        
        conn = get_db_connection()
        section = conn.execute('SELECT * FROM sections WHERE id = ?', (section_id,)).fetchone()
        subsections = conn.execute(
            'SELECT * FROM subsections WHERE section_id = ? ORDER BY id', 
            (section_id,)
        ).fetchall()
        conn.close()
        
        if not subsections:
            query.edit_message_text(f"В разделе '{section[1]}' пока нет подразделов.")
            return
        
        keyboard = []
        for subsection in subsections:
            keyboard.append([InlineKeyboardButton(
                subsection[2], 
                callback_data=f"view_subsection_{subsection[0]}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(f"📁 Раздел: {section[1]}\n\nВыберите подраздел:", reply_markup=reply_markup)

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
        
        print("✅ Bot started successfully!")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
