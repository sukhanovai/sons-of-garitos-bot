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
    if result.stderr:
        print(f"❌ Git pull error: {result.stderr}")
    
    # Перезапускаем
    Thread(target=delayed_restart, daemon=True).start()
    
    return "Updating and restarting..."

@app.route('/check-updates')
def check_updates():
    """Проверить наличие обновлений без перезапуска"""
    try:
        print("🔍 Checking for updates...")
        
        # Проверяем обновления
        result = subprocess.run(['git', 'fetch'], capture_output=True, text=True)
        status_result = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)
        
        has_updates = "Your branch is behind" in status_result.stdout
        
        if has_updates:
            return jsonify({
                "status": "updates_available",
                "message": "Доступны обновления! Используйте /update для установки."
            })
        else:
            return jsonify({
                "status": "up_to_date", 
                "message": "Бот обновлен до последней версии."
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Ошибка проверки обновлений: {e}"
        }), 500

def delayed_restart():
    """Отложенный перезапуск"""
    time.sleep(2)
    print("🔄 Restarting bot...")
    os._exit(0)

def check_updates_on_start():
    """Проверка обновлений при запуске"""
    print("🔍 Checking for updates on startup...")
    
    try:
        # Проверяем обновления
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        print(f"🔧 Git pull result: {result.stdout}")
        
        # Если были обновления, сообщаем об этом
        if "Already up to date" not in result.stdout:
            print("🔄 Updates were applied on startup")
            return True
        else:
            print("✅ Bot is up to date")
            return False
            
    except Exception as e:
        print(f"❌ Update check error: {e}")
        return False

def keep_alive():
    """Функция для поддержания активности приложения"""
    time.sleep(10)
    
    while True:
        try:
            # Пингуем локальный сервер вместо внешнего URL
            response = requests.get('http://localhost:5000/ping', timeout=5)
            print(f"🔄 Keep-alive ping: {response.status_code} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
        
        time.sleep(300)  # 5 минут

def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

# Основной код бота
async def main():
    # Проверяем обновления при запуске
    updates_applied = check_updates_on_start()
    
    if updates_applied:
        print("🔄 Restarting to apply updates...")
        time.sleep(2)
        os._exit(0)
    
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
    # Запускаем Flask в отдельном потоке
    Thread(target=run_flask, daemon=True).start()
    print("✅ Flask server started")
    
    # Запускаем keep-alive в отдельном потоке
    Thread(target=keep_alive, daemon=True).start()
    print("✅ Keep-alive started")
    
    print("🤖 Starting Sons of Garitos Bot...")
    asyncio.run(main())
    
