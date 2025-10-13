import os
import logging
import time
import subprocess
import requests
from flask import Flask, request, jsonify
import asyncio
import sys

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
    return "Restarting... (Please restart manually via Replit interface)"

@app.route('/github-webhook', methods=['POST'])
def github_webhook():
    """Webhook для GitHub"""
    try:
        if request.headers.get('X-GitHub-Event') == 'push':
            print("🔄 GitHub push received, pulling changes...")
            
            # Обновляем код
            result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
            print(f"🔧 Git pull result: {result.stdout}")
            if result.stderr:
                print(f"❌ Git pull error: {result.stderr}")
            
            return jsonify({"status": "success", "message": "Updates pulled. Please restart manually."})
        
        return jsonify({"status": "ignored", "message": "Not a push event"})
    
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update')
def update():
    """Принудительное обновление"""
    print("🔄 Forced update triggered")
    
    # Обновляем код
    result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
    print(f"🔧 Git pull result: {result.stdout}")
    if result.stderr:
        print(f"❌ Git pull error: {result.stderr}")
    
    return "Updates pulled. Please restart manually via Replit interface."

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

async def run_bot():
    """Запуск бота"""
    TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TOKEN:
        print("❌ BOT_TOKEN not found!")
        return
    
    try:
        from bot import setup_bot
        application = await setup_bot(TOKEN)
        print("✅ Bot started successfully!")
        await application.run_polling()
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()
        # Не перезапускаем автоматически, чтобы избежать бесконечного цикла
        sys.exit(1)

def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

def main():
    """Основная функция запуска"""
    # Проверяем обновления при запуске
    updates_applied = check_updates_on_start()
    
    if updates_applied:
        print("🔄 Please restart the bot to apply updates")
        return
    
    print("🤖 Starting Sons of Garitos Bot...")
    
    # В Replit мы не можем запускать Flask и бота одновременно из-за event loop
    # Давайте спросим пользователя что запускать
    
    print("\n" + "="*50)
    print("Выберите режим запуска:")
    print("1 - Запустить только Telegram бота")
    print("2 - Запустить только Flask сервер (для вебхуков)")
    print("3 - Запустить оба (может вызвать проблемы)")
    print("="*50)
    
    choice = input("Введите номер (1, 2 или 3): ").strip()
    
    if choice == "1":
        # Запускаем только бота
        print("🚀 Starting Telegram Bot only...")
        asyncio.run(run_bot())
    elif choice == "2":
        # Запускаем только Flask
        print("🚀 Starting Flask server only...")
        run_flask()
    elif choice == "3":
        # Пытаемся запустить оба (может не работать)
        print("🚀 Trying to start both services...")
        import threading
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        time.sleep(3)
        asyncio.run(run_bot())
    else:
        print("❌ Неверный выбор. Запускаю только бота...")
        asyncio.run(run_bot())

if __name__ == '__main__':
    main()
