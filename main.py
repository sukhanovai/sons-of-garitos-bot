import os
from bot import setup_bot

async def main():
    # Получаем токен бота из переменных окружения
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment variables")
        return
    
    # Настраиваем и запускаем бота
    application = await setup_bot(BOT_TOKEN)
    
    print("🤖 Bot is starting...")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
