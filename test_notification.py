#!/usr/bin/env python3
"""
Тест уведомлений об ошибках
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')

async def test_notification():
    """Отправляет тестовое уведомление об ошибке"""
    
    print("🧪 Отправка тестового уведомления об ошибке...")
    
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("❌ Необходимо настроить TELEGRAM_BOT_TOKEN и ADMIN_CHAT_ID")
        return
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Отправляем уведомление об ошибке
        message = await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="""🚨 ТЕСТОВОЕ УВЕДОМЛЕНИЕ ОБ ОШИБКЕ

🤖 Бот: @ssubs_dl_bot
⏰ Время: Система запущена и работает
🔧 Тип: SystemStartupTest
📋 Статус: ✅ ВСЕ РАБОТАЕТ!

💡 Если вы видите это сообщение, значит уведомления об ошибках настроены правильно!

🎉 Система готова к работе!"""
        )
        
        print(f"✅ Тестовое уведомление отправлено!")
        print(f"Message ID: {message.message_id}")
        print(f"Chat ID: {message.chat_id}")
        
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления: {e}")

if __name__ == "__main__":
    asyncio.run(test_notification())