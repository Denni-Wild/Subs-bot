#!/usr/bin/env python3
"""
Скрипт для настройки команд бота через BotFather API
Запустите этот скрипт один раз для настройки команд в интерфейсе Telegram
"""

import os
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    exit(1)

# Команды для настройки
commands = [
    {"command": "start", "description": "🚀 Начать работу с ботом"},
    {"command": "help", "description": "📚 Подробная справка по использованию"},
    {"command": "about", "description": "🤖 Информация о боте"},
    {"command": "subs", "description": "📺 Получить субтитры с YouTube"},
    {"command": "voice", "description": "🎤 Расшифровать голосовое сообщение"},
    {"command": "info", "description": "ℹ️ Краткая информация о возможностях"}
]

def set_bot_commands():
    """Устанавливает команды бота через BotFather API"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    
    try:
        response = requests.post(url, json={"commands": commands})
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            print("✅ Команды бота успешно настроены!")
            print("\n📋 Настроенные команды:")
            for cmd in commands:
                print(f"  /{cmd['command']} - {cmd['description']}")
            print("\n🎉 Теперь команды будут видны в интерфейсе Telegram!")
        else:
            print(f"❌ Ошибка при настройке команд: {result.get('description', 'Неизвестная ошибка')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

def get_bot_info():
    """Получает информацию о боте"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        result = response.json()
        if result.get("ok"):
            bot_info = result["result"]
            print(f"🤖 Информация о боте:")
            print(f"  Имя: {bot_info.get('first_name', 'Неизвестно')}")
            print(f"  Username: @{bot_info.get('username', 'Неизвестно')}")
            print(f"  ID: {bot_info.get('id', 'Неизвестно')}")
            return True
        else:
            print(f"❌ Ошибка при получении информации о боте: {result.get('description', 'Неизвестная ошибка')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Настройка команд бота...")
    print("=" * 50)
    
    # Проверяем информацию о боте
    if get_bot_info():
        print("\n" + "=" * 50)
        # Настраиваем команды
        set_bot_commands()
    else:
        print("❌ Не удалось получить информацию о боте. Проверьте токен.") 