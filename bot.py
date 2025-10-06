import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
import os

# Токен берется из переменных окружения
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = [123456789]  # Замените на ваш ID

def init_db():
    conn = sqlite3.connect('clan_bot.db', check_same_thread=False)
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
    
    cursor.execute('''
        INSERT OR IGNORE INTO sections (id, name, description) 
        VALUES (1, '📚 Гайды по игре', 'Полезные гайды и стратегии'),
               (2, '⚔️ Библиотека сборок', 'Эффективные сборки персонажей'),
               (3, '📝 Заметки клана', 'Важные объявления и заметки')
    ''')
    
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📚 Просмотреть разделы", callback_data='view_sections')],
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("➕ Создать раздел", callback_data='create_section')])
        keyboard.append([InlineKeyboardButton("📝 Добавить запись", callback_data='add_post_choose_section')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🏰 Добро пожаловать в базу знаний клана Sons of Garitos!',
        reply_markup=reply_markup
    )

# ... (остальной код бота из предыдущего примера) ...

def main():
    init_db()
    
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(view_sections, pattern='^view_sections$'))
    # ... добавьте остальные обработчики ...
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
