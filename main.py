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
            
            # Логируем полученные данные
            data = request.json
            if data:
                repo_name = data.get('repository', {}).get('name', 'Unknown')
                commit_message = data.get('head_commit', {}).get('message', 'No message')
                print(f"📦 Repository: {repo_name}")
                print(f"📝 Commit: {commit_message}")
            
            # Обновляем код
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
            print(f"🔧 Git pull result: {result.stdout}")
            if result.stderr:
                print(f"❌ Git pull error: {result.stderr}")
            
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
    time.sleep(10)  # Ждем запуска сервера
    
    while True:
        try:
            # Получаем URL нашего приложения
            repl_slug = os.environ.get('REPL_SLUG', 'sons-of-garitos-bot')
            repl_owner = os.environ.get('REPL_OWNER', 'aleksandrisukha')
            base_url = f"https://{repl_slug}.{repl_owner}.repl.co"
            
            # Пингуем себя
            response = requests.get(f"{base_url}/ping", timeout=10)
            print(f"🔄 Keep-alive ping: {response.status_code} at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Keep-alive request error: {e}")
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
        
        # Ждем 5 минут перед следующим пингом
        time.sleep(300)

def auto_updater():
    """Автоматическая проверка обновлений каждые 30 минут"""
    time.sleep(60)  # Ждем 1 минуту после запуска
    
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
        
        # Ждем 30 минут перед следующей проверкой
        time.sleep(1800)

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
    
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ BOT_TOKEN not found in environment variables!")
        return
    
    print(f"✅ Bot token: {TOKEN[:10]}...")
    
    try:
        from bot import setup_bot
        application = await setup_bot(TOKEN)
        
        print("✅ Bot started successfully!")
        await application.run_polling()
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
        
        # Перезапуск при ошибке через 10 секунд
        print("🔄 Restarting in 10 seconds...")
        time.sleep(10)
        os._exit(1)

if __name__ == '__main__':
    print("🤖 Starting Sons of Garitos Bot...")
    asyncio.run(main())
    
