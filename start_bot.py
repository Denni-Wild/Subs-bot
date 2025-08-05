#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота с улучшенным логированием
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
def setup_logging():
    """Настройка логирования для бота"""
    # Создаем директорию для логов если её нет
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Отключаем логи от сторонних библиотек
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def check_environment():
    """Проверка переменных окружения"""
    required_vars = ['TELEGRAM_BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        print("Создайте файл .env с необходимыми переменными")
        return False
    
    return True

def main():
    """Основная функция запуска бота"""
    print("🚀 Запуск Telegram бота...")
    
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Проверка переменных окружения
    if not check_environment():
        sys.exit(1)
    
    try:
        # Импортируем и запускаем бота
        from bot import app
        
        logger.info("Бот успешно инициализирован")
        print("✅ Бот запущен и готов к работе!")
        print("📝 Логи сохраняются в файл: logs/bot.log")
        print("🛑 Для остановки нажмите Ctrl+C")
        
        # Запускаем бота
        app.run_polling()
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки, завершаем работу бота")
        print("\n🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        print(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()