#!/usr/bin/env python3
"""
Мини-тест за 30 секунд
Проверяет самое необходимое
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🏃‍♂️ МИНИ-ТЕСТ (30 секунд)")

# Тест 1: Импорты основных модулей
try:
    import bot
    print("✅ Bot импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта bot.py: {e}")
    exit(1)

# Тест 2: Проверка функций бота
try:
    # Проверяем, что функция существует
    if hasattr(bot, 'extract_video_id'):
        # Тестируем с правильным форматом URL
        video_id = bot.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        if video_id == "dQw4w9WgXcQ":
            print("✅ Извлечение ID работает")
        else:
            print(f"❌ Проблема с извлечением ID: получили {video_id}")
    else:
        print("❌ Функция extract_video_id не найдена")
except Exception as e:
    print(f"❌ Ошибка при тестировании функций бота: {e}")

# Тест 3: Суммаризатор
try:
    os.environ['OPENROUTER_API_KEY'] = 'test'
    from summarizer import TextSummarizer
    s = TextSummarizer()
    print(f"✅ Суммаризатор: {len(s.models)} моделей")
except Exception as e:
    print(f"❌ Проблема с суммаризатором: {e}")

# Тест 4: Проверка конфигурации
try:
    import json
    with open('enterprise_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"✅ Конфигурация: {len(config.get('servers', {}))} серверов")
except Exception as e:
    print(f"❌ Проблема с конфигурацией: {e}")

# Тест 5: Проверка зависимостей
try:
    import aiofiles
    import aiohttp
    import asyncio
    print("✅ Основные зависимости установлены")
except Exception as e:
    print(f"❌ Проблема с зависимостями: {e}")

print("🎯 Мини-тест завершен!")
print("Запустите 'python tests/quick_test.py' для полной проверки") 