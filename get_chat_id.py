#!/usr/bin/env python3
"""
Скрипт для получения Chat ID пользователя
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def get_bot_info():
    """Получает информацию о боте"""
    
    print("🤖 Получение информации о боте...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не найден")
        return
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        
        print(f"✅ Информация о боте:")
        print(f"   Имя: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
        print(f"   Может присоединяться к группам: {bot_info.can_join_groups}")
        print(f"   Может читать все групповые сообщения: {bot_info.can_read_all_group_messages}")
        print(f"   Поддерживает inline режим: {bot_info.supports_inline_queries}")
        
        print(f"\n📱 Для получения вашего Chat ID:")
        print(f"1. Найдите бота @{bot_info.username} в Telegram")
        print(f"2. Отправьте команду /start")
        print(f"3. Затем отправьте любое сообщение")
        print(f"4. Запустите этот скрипт снова для получения обновлений")
        
    except Exception as e:
        print(f"❌ Ошибка при получении информации о боте: {e}")

async def get_updates():
    """Получает последние обновления"""
    
    print("\n📨 Получение последних обновлений...")
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не найден")
        return
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Получаем обновления
        updates = await bot.get_updates()
        
        if not updates:
            print("📭 Нет новых обновлений")
            print("💡 Отправьте сообщение боту и попробуйте снова")
            return
        
        print(f"📨 Найдено {len(updates)} обновлений:")
        
        for i, update in enumerate(updates[-5:], 1):  # Показываем последние 5
            if update.message:
                user = update.message.from_user
                chat = update.message.chat
                print(f"\n{i}. Сообщение от пользователя:")
                print(f"   Пользователь ID: {user.id}")
                print(f"   Имя: {user.first_name} {user.last_name or ''}")
                print(f"   Username: @{user.username or 'нет'}")
                print(f"   Chat ID: {chat.id}")
                print(f"   Тип чата: {chat.type}")
                print(f"   Текст: {update.message.text[:50]}...")
                
                if chat.type == 'private':
                    print(f"   ✅ Это ваш Chat ID для уведомлений: {chat.id}")
        
    except Exception as e:
        print(f"❌ Ошибка при получении обновлений: {e}")

if __name__ == "__main__":
    asyncio.run(get_bot_info())
    asyncio.run(get_updates()) 