#!/usr/bin/env python3
"""
Быстрый тест - проверяет, что все основные функции работают
Запуск: python quick_test.py
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def quick_check():
    """Быстрая проверка основных функций"""
    print("🔍 Быстрая проверка функций...")
    
    errors = []
    
    # 1. Проверяем импорты
    try:
        import bot
        print("✅ Основные функции бота импортированы")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта bot.py: {e}")
    
    try:
        from summarizer import TextSummarizer
        print("✅ Класс TextSummarizer импортирован")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта summarizer.py: {e}")
    
    # 2. Проверяем извлечение video_id
    try:
        if hasattr(bot, 'extract_video_id'):
            video_id = bot.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            if video_id == "dQw4w9WgXcQ":
                print("✅ Извлечение video_id работает")
            else:
                errors.append(f"❌ Неверный video_id: получен {video_id}")
        else:
            errors.append("❌ Функция extract_video_id не найдена")
    except Exception as e:
        errors.append(f"❌ Ошибка в extract_video_id: {e}")
    
    # 3. Проверяем форматирование субтитров
    try:
        if hasattr(bot, 'format_subtitles'):
            test_transcript = [{'start': 0, 'text': 'Тест'}]
            result = bot.format_subtitles(test_transcript, with_time=False)
            if result == "Тест":
                print("✅ Форматирование субтитров работает")
            else:
                errors.append(f"❌ Неверное форматирование: получено '{result}'")
        else:
            errors.append("❌ Функция format_subtitles не найдена")
    except Exception as e:
        errors.append(f"❌ Ошибка в format_subtitles: {e}")
    
    # 4. Проверяем инициализацию суммаризатора
    try:
        os.environ['OPENROUTER_API_KEY'] = 'test_key'
        summarizer = TextSummarizer()
        if len(summarizer.models) >= 8:
            print("✅ Суммаризатор инициализируется")
        else:
            errors.append(f"❌ Мало моделей в суммаризаторе: {len(summarizer.models)}")
    except Exception as e:
        errors.append(f"❌ Ошибка в TextSummarizer: {e}")
    
    # 5. Проверяем разбивку текста
    try:
        text = "слово " * 200  # 1200+ символов
        chunks = summarizer.split_text(text, max_len=500)
        if len(chunks) > 1:
            print("✅ Разбивка текста работает")
        else:
            errors.append(f"❌ Текст не разбился на части: {len(chunks)} частей")
    except Exception as e:
        errors.append(f"❌ Ошибка в split_text: {e}")
    
    # Итоги
    print("\n" + "="*40)
    if not errors:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("Основные функции работают корректно")
        return True
    else:
        print("💥 НАЙДЕНЫ ОШИБКИ:")
        for error in errors:
            print(f"   {error}")
        return False


if __name__ == "__main__":
    print("⚡ БЫСТРАЯ ПРОВЕРКА ФУНКЦИЙ")
    print("="*40)
    
    success = quick_check()
    
    if success:
        print("\n✨ Можете запускать полные тесты или бота!")
        print("Команды:")
        print("  python tests/simple_tests.py  - простые тесты")
        print("  python tests/test_runner.py   - полные тесты")
        print("  python bot.py                - запуск бота")
    else:
        print("\n🔧 Требуется исправление ошибок")
    
    exit(0 if success else 1) 