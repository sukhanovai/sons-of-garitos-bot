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

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Sons of Garitos Bot is running!"

@app.route('/health')
def health():
    return "✅ OK"

@app.route('/ping')
def ping():
    return "🏓 Pong"

@app.route('/restart')
def restart():
    """Ручной перезапуск"""
    print("🔄 Manual restart triggered")
    Thread(target=delayed_restart, daemon=True).start()
    return "Restarting..."

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Webhook для GitHub"""
    try:
        if request.headers.get('X-GitHub-Event') == 'push':
            print("🔄 GitHub push received, pulling changes and restarting...")
            
            # Обновляем код
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
            print(f"🔧 Git pull result: {result.stdout}")
            
            # Перезапускаем
            Thread(target=delayed_restart, daemon=True).start()
            
            return jsonify({"status": "success", "message": "Update triggered"})
        
        return jsonify({"status": "ignored", "message": "Not a push event"})
    
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update')
def update():
    """Принудительное обновление и перезапуск"""
    print("🔄 Forced update triggered")
    
    # Обновляем код
    result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
    print(f"🔧 Git pull result: {result.stdout}")
    
    # Перезапускаем
    Thread(target=delayed_restart, daemon=True).start()
    
    return "Updating and restarting..."

def delayed_restart():
    """Отложенный перезапуск"""
    time.sleep(2)
    print("🔄 Restarting bot...")
    os._exit(0)

def keep_alive():
    """Функция для поддержания активности приложения"""
    time.sleep(10)
    
    while True:
        try:
            # Пингуем локальный сервер вместо внешнего URL
            response = requests.get('http://localhost:8080/ping', timeout=5)
            print(f"🔄 Keep-alive ping: {response.status_code}")
            
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
        
        time.sleep(300)  # 5 минут

def auto_updater():
    """Автоматическая проверка обновлений каждые 30 минут"""
    time.sleep(60)
    
    while True:
        try:
            print("🔄 Auto-update check...")
            
            # Проверяем обновления
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
            print(f"🔧 Git pull result: {result.stdout}")
            
            # Если есть обновления, перезапускаем
            if "Already up to date" not in result.stdout:
                print("🔄 New updates found, restarting...")
                time.sleep(5)
                os._exit(0)
                
        except Exception as e:
            print(f"❌ Auto-update error: {e}")
        
        time.sleep(1800)  # 30 минут

def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

# Запускаем Flask в отдельном потоке
Thread(target=run_flask, daemon=True).start()
print("✅ Flask server started")

# Запускаем keep-alive в отдельном потоке
Thread(target=keep_alive, daemon=True).start()
print("✅ Keep-alive started")

# Запускаем авто-апдейтер в отдельном потоке
Thread(target=auto_updater, daemon=True).start()
print("✅ Auto-updater started")

# Основной код бота
async def main():
    # Даем время серверу запуститься
    time.sleep(3)
    
    # Получаем токен из переменных окружения
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ BOT_TOKEN not found in environment variables!")
        print("💡 Please add BOT_TOKEN to Replit Secrets")
        return
    
    print(f"✅ Bot token found: {TOKEN[:10]}...")
    
    try:
        from bot import setup_bot
        application = await setup_bot(TOKEN)
        
        print("✅ Bot started successfully!")
        await application.run_polling()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
        
        print("🔄 Restarting in 10 seconds...")
        time.sleep(10)
        os._exit(1)

if __name__ == '__main__':
    print("🤖 Starting Sons of Garitos Bot...")
    asyncio.run(main())
    
