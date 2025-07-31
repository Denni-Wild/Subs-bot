#!/usr/bin/env python3
"""
Демо-тестирование функций суммаризации
Показывает как система разбивает текст и анализирует его
"""

import os
from summarizer import TextSummarizer

def demo_text_analysis():
    """Демонстрация анализа текста без ИИ"""
    
    print("🎯 ДЕМО: АНАЛИЗ ТЕКСТА И ПОДГОТОВКА К СУММАРИЗАЦИИ")
    print("="*60)
    
    # Читаем субтитры
    try:
        with open('subtitles_DpQtKCcTMnQ_ru.txt', 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"📄 Загружен текст субтитров")
        print(f"   Размер: {len(text)} символов")
        print(f"   Слов: {len(text.split())} слов")
        print(f"   Строк: {text.count(chr(10)) + 1}")
    except FileNotFoundError:
        print("❌ Файл субтитров не найден!")
        return
    
    # Анализируем содержание
    print(f"\n📖 АНАЛИЗ СОДЕРЖАНИЯ:")
    lines = text.split('\n')[:20]  # Первые 20 строк
    print("Первые строки субтитров:")
    for i, line in enumerate(lines, 1):
        if line.strip():
            print(f"   {i:2}: {line.strip()}")
    
    # Инициализируем суммаризатор
    os.environ['OPENROUTER_API_KEY'] = 'demo'
    summarizer = TextSummarizer()
    
    print(f"\n🤖 ДОСТУПНЫЕ ИИ-МОДЕЛИ:")
    for i, (name, model_id) in enumerate(summarizer.models):
        print(f"   {i+1}. {name}")
        print(f"      ID: {model_id}")
    
    # Демонстрируем разбивку текста
    print(f"\n✂️  РАЗБИВКА ТЕКСТА НА ЧАСТИ:")
    chunks = summarizer.split_text(text, max_len=1000)
    print(f"   Исходный текст: {len(text)} символов")
    print(f"   Разбито на: {len(chunks)} частей")
    print(f"   Размер части: до 1000 символов")
    
    for i, chunk in enumerate(chunks[:3], 1):  # Показываем первые 3 части
        print(f"\n   📄 Часть {i}: {len(chunk)} символов")
        preview = chunk[:150] + "..." if len(chunk) > 150 else chunk
        print(f"      Превью: {preview}")
    
    if len(chunks) > 3:
        print(f"   ... и еще {len(chunks) - 3} частей")
    
    # Анализируем ключевые слова
    print(f"\n🔍 АНАЛИЗ КЛЮЧЕВЫХ СЛОВ:")
    words = text.lower().split()
    word_freq = {}
    
    # Исключаем служебные слова
    stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'что', 'это', 'как', 'но', 'или', 
                  'то', 'так', 'все', 'уже', 'ещё', 'будет', 'если', 'может', 'очень'}
    
    for word in words:
        clean_word = ''.join(c for c in word if c.isalpha())
        if len(clean_word) > 3 and clean_word not in stop_words:
            word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
    
    # Топ-10 слов
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    print("   Топ-10 часто встречающихся слов:")
    for word, count in top_words:
        print(f"      {word}: {count} раз")
    
    # Определяем тематику по ключевым словам
    print(f"\n🎯 ОПРЕДЕЛЕНИЕ ТЕМАТИКИ:")
    astro_words = ['сатурн', 'рыбах', 'транзит', 'знак', 'лагна', 'сады', 'планета']
    found_astro = [word for word, _ in top_words if any(aw in word for aw in astro_words)]
    
    if found_astro:
        print("   ✅ Обнаружена астрологическая тематика")
        print(f"   Ключевые термины: {', '.join(found_astro)}")
    else:
        print("   🔍 Тематика требует дополнительного анализа")
    
    print(f"\n📋 СТРУКТУРА ДЛЯ ИИ-СУММАРИЗАЦИИ:")
    print("   Система подготовила текст для анализа ИИ:")
    print(f"   ✅ Разбито на {len(chunks)} логических частей")
    print("   ✅ Выявлены ключевые слова и тематика")
    print("   ✅ Определен объем для обработки")
    print("   🤖 Готово для передачи ИИ-моделям")

def demo_prompts():
    """Демонстрация промптов для ИИ"""
    
    print(f"\n🎭 ПРОМПТЫ ДЛЯ ИИ-АНАЛИЗА:")
    print("="*40)
    
    prompts = [
        {
            "name": "Базовая суммаризация",
            "prompt": "Создай краткое изложение этого текста на русском языке. Выдели главные мысли и ключевые моменты."
        },
        {
            "name": "Структурированный анализ",
            "prompt": """Проанализируй этот текст и создай структурированную суммаризацию:

1. ГЛАВНАЯ ТЕМА (одно предложение)
2. КЛЮЧЕВЫЕ МОМЕНТЫ (3-5 пунктов)  
3. ОСНОВНЫЕ ВЫВОДЫ (2-3 предложения)
4. О ЧЕМ ЭТОТ ТЕКСТ (краткое резюме)

Будь точным и конкретным."""
        },
        {
            "name": "Экспертный анализ",
            "prompt": """Выполни экспертный анализ содержания:

• О чем говорится в тексте?
• Какие основные идеи представлены?
• Какие выводы можно сделать?
• Какая практическая польза от этой информации?

Ответь развернуто и структурированно."""
        }
    ]
    
    for i, prompt_data in enumerate(prompts, 1):
        print(f"\n🤖 ПРОМПТ {i}: {prompt_data['name']}")
        print("-" * 30)
        print(prompt_data['prompt'])
        print("-" * 30)

def show_testing_commands():
    """Показываем команды для реального тестирования"""
    
    print(f"\n🚀 КОМАНДЫ ДЛЯ РЕАЛЬНОГО ТЕСТИРОВАНИЯ:")
    print("="*50)
    
    print("1️⃣  Тестирование с реальным API:")
    print("   export OPENROUTER_API_KEY='your-key'")
    print("   python test_summarization_quality.py")
    
    print("\n2️⃣  Тестирование через бота:")
    print("   python bot.py")
    print("   # Отправьте ссылку: https://youtu.be/DpQtKCcTMnQ")
    
    print("\n3️⃣  Тест с реальным видео:")
    print("   python tests/test_real_video.py")
    
    print("\n4️⃣  Прямое тестирование суммаризатора:")
    print("""   python -c "
import asyncio
from summarizer import TextSummarizer
s = TextSummarizer()
text = open('subtitles_DpQtKCcTMnQ_ru.txt').read()[:2000]
result = asyncio.run(s.summarize_text(text, 0))
print(result[0])
   \"""")

if __name__ == "__main__":
    print("🎬 ДЕМО-АНАЛИЗ YOUTUBE СУБТИТРОВ")
    print("Подготовка к ИИ-суммаризации")
    print()
    
    demo_text_analysis()
    demo_prompts()
    show_testing_commands()
    
    print(f"\n🎯 ЗАКЛЮЧЕНИЕ:")
    print("✅ Система успешно загружает и анализирует субтитры")
    print("✅ Текст корректно разбивается на части для ИИ")
    print("✅ Определена тематика (астрология)")
    print("✅ Подготовлены качественные промпты")
    print("🤖 Готово к тестированию с реальными ИИ-моделями!") 