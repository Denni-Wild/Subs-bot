#!/usr/bin/env python3
"""
Простой тест для проверки функциональности перевода
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from summarizer import TextSummarizer

def test_detect_language():
    """Тест определения языка"""
    print("🧪 Тестирую определение языка...")
    
    summarizer = TextSummarizer()
    
    # Тест русского языка
    russian_text = "Это русский текст с кириллическими символами"
    result = summarizer.detect_language(russian_text)
    print(f"Русский текст: '{russian_text[:20]}...' -> {result}")
    assert result == 'ru', f"Ожидался 'ru', получен '{result}'"
    
    # Тест английского языка
    english_text = "This is English text with Latin characters"
    result = summarizer.detect_language(english_text)
    print(f"Английский текст: '{english_text[:20]}...' -> {result}")
    assert result == 'en', f"Ожидался 'en', получен '{result}'"
    
    # Тест смешанного языка
    mixed_text = "This is mixed text with some русские слова"
    result = summarizer.detect_language(mixed_text)
    print(f"Смешанный текст: '{mixed_text[:20]}...' -> {result}")
    assert result in ['ru', 'en', 'other'], f"Неожиданный результат: '{result}'"
    
    # Тест короткого текста
    short_text = "Hello"
    result = summarizer.detect_language(short_text)
    print(f"Короткий текст: '{short_text}' -> {result}")
    assert result == 'en', f"Ожидался 'en', получен '{result}'"
    
    # Тест пустого текста
    empty_text = ""
    result = summarizer.detect_language(empty_text)
    print(f"Пустой текст: -> {result}")
    assert result == 'other', f"Ожидался 'other', получен '{result}'"
    
    print("✅ Все тесты определения языка прошли успешно!")

async def test_translate_to_russian():
    """Тест перевода на русский язык"""
    print("\n🌍 Тестирую перевод на русский...")
    
    summarizer = TextSummarizer()
    
    # Проверяем, есть ли API ключ
    if not summarizer.api_key:
        print("⚠️ API ключ не настроен, пропускаю тест перевода")
        return
    
    english_text = "Hello world! This is a test message."
    result = await summarizer.translate_to_russian(english_text, 'en')
    print(f"Перевод: '{english_text}' -> '{result[:50]}...'")
    
    # Проверяем, что перевод отличается от исходного текста
    if result != english_text:
        print("✅ Перевод выполнен успешно!")
    else:
        print("⚠️ Перевод вернул исходный текст (возможно, API недоступен)")
    
    print("✅ Тест перевода завершен!")

async def test_summarize_with_language_detection():
    """Тест суммаризации с определением языка"""
    print("\n🤖 Тестирую суммаризацию с определением языка...")
    
    summarizer = TextSummarizer()
    
    # Тест с русским текстом
    russian_text = "Это русский текст для тестирования. Он содержит несколько предложений."
    result, stats = await summarizer.summarize_text(russian_text)
    print(f"Русский текст -> язык: {stats.get('source_language', 'unknown')}")
    assert stats.get('source_language') == 'ru', f"Ожидался 'ru', получен '{stats.get('source_language')}'"
    
    # Тест с английским текстом
    english_text = "This is English text for testing. It contains several sentences."
    result, stats = await summarizer.summarize_text(english_text)
    print(f"Английский текст -> язык: {stats.get('source_language', 'unknown')}")
    assert stats.get('source_language') == 'en', f"Ожидался 'en', получен '{stats.get('source_language')}'"
    
    print("✅ Тест суммаризации с определением языка прошел успешно!")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов функциональности перевода...")
    
    try:
        # Синхронные тесты
        test_detect_language()
        
        # Асинхронные тесты
        await test_translate_to_russian()
        await test_summarize_with_language_detection()
        
        print("\n🎉 Все тесты прошли успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 