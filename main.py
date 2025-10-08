import os
import logging
import time
import subprocess
import requests
from flask import Flask, request, jsonify
from threading import Thread
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

app = Flask('')

@app.route('/')
def home():
    return "🤖 Sons of Garitos Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

@app.route('/restart')
def restart():
    """Ручной перезапуск"""
    print("🔄 Manual restart triggered")
    restart_bot()
    return "Restarting..."

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Webhook для GitHub"""
    if request.headers.get('X-GitHub-Event') == 'push':
        print("🔄 GitHub push received, pulling changes and restarting...")
        # Обновляем код
        subprocess.run(['git', 'pull'], capture_output=True)
        # Перезапускаем
        restart_bot()
    return jsonify({"status": "success"})

@app.route('/update')
def update():
    """Принудительное обновление и перезапуск"""
    print("🔄 Forced update triggered")
    subprocess.run(['git', 'pull'], capture_output=True)
    restart_bot()
    return "Updating and restarting..."

def restart_bot():
    """Перезапускает бота"""
    time.sleep(1)
    os._exit(0)

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Запускаем Flask
Thread(target=run_flask, daemon=True).start()
print("✅ Flask server started on port 8080")

# Основной код бота
async def main():
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ BOT_TOKEN not found!")
        return
    
    print(f"✅ Bot token: {TOKEN[:10]}...")
    
    from bot import setup_bot
    application = await setup_bot(TOKEN)
    
    print("✅ Bot started successfully!")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
