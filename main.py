import os
import logging
from flask import Flask
from threading import Thread
from telegram.ext import Application

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Flask app для поддержания активности
app = Flask('')

@app.route('/')
def home():
    return "🤖 Sons of Garitos Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Запускаем Flask в отдельном потоке
Thread(target=run_flask, daemon=True).start()
print("✅ Flask server started on port 8080")

# Основной код бота
async def main():
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ BOT_TOKEN not found in environment variables!")
        return
    
    print(f"✅ Bot token loaded: {TOKEN[:10]}...")
    
    # Импортируем и запускаем бота
    from bot import setup_bot
    application = await setup_bot(TOKEN)
    
    print("✅ Bot is starting...")
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
  
