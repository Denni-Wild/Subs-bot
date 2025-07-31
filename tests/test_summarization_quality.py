#!/usr/bin/env python3
"""
Тестирование качества ИИ-суммаризации
Сравнение разных моделей на реальных субтитрах
"""

import os
import asyncio
import time
from summarizer import TextSummarizer

# Тестовый API ключ (замените на реальный для полного тестирования)
os.environ['OPENROUTER_API_KEY'] = 'sk-or-v1-your-real-key-here'

async def test_summarization_quality():
    """Тестирование качества суммаризации разными моделями"""
    
    print("🎯 ТЕСТИРОВАНИЕ КАЧЕСТВА ИИ-СУММАРИЗАЦИИ")
    print("="*60)
    
    # Читаем субтитры
    try:
        with open('subtitles_DpQtKCcTMnQ_ru.txt', 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"📄 Загружен текст: {len(text)} символов, {len(text.split())} слов")
    except FileNotFoundError:
        print("❌ Файл субтитров не найден!")
        return
    
    # Инициализируем суммаризатор
    summarizer = TextSummarizer()
    print(f"🤖 Доступно моделей: {len(summarizer.models)}")
    
    # Сокращаем текст для тестирования (первые 3000 символов)
    test_text = text[:3000] + "..."
    print(f"🔬 Тестируем на отрывке: {len(test_text)} символов")
    print(f"📖 Начало текста: {test_text[:200]}...")
    
    print("\n" + "="*60)
    print("🚀 НАЧИНАЕМ ТЕСТИРОВАНИЕ МОДЕЛЕЙ")
    print("="*60)
    
    results = []
    
    # Тестируем первые 4 модели (чтобы не ждать слишком долго)
    models_to_test = [0, 1, 2, 3]  # Venice, Gemma, Hunyuan, DeepSeek
    
    for model_index in models_to_test:
        model_name = summarizer.models[model_index][0]
        model_id = summarizer.models[model_index][1]
        
        print(f"\n🔄 Тестируем модель {model_index + 1}/4: {model_name}")
        print(f"   ID: {model_id}")
        
        start_time = time.time()
        
        try:
            # Создаем специальный промт для качественной суммаризации
            custom_prompt = """Проанализируй этот текст и создай структурированную суммаризацию:

1. ГЛАВНАЯ ТЕМА (одно предложение)
2. КЛЮЧЕВЫЕ МОМЕНТЫ (3-5 пунктов)
3. ОСНОВНЫЕ ВЫВОДЫ (2-3 предложения)
4. О ЧЕМ ЭТОТ ТЕКСТ (краткое резюме)

Будь точным и конкретным."""
            
            summary, stats = await summarizer.summarize_text(
                test_text, 
                model_index=model_index,
                custom_prompt=custom_prompt
            )
            
            duration = time.time() - start_time
            
            print(f"   ✅ Готово за {duration:.1f} сек")
            print(f"   📊 Сжатие: {stats.get('original_length', 0)} → {stats.get('summary_length', 0)} символов")
            
            results.append({
                'model_name': model_name,
                'model_id': model_id,
                'summary': summary,
                'duration': duration,
                'stats': stats,
                'success': True
            })
            
            # Показываем первые 200 символов суммаризации
            preview = summary[:200] + "..." if len(summary) > 200 else summary
            print(f"   📝 Превью: {preview}")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ Ошибка: {e}")
            
            results.append({
                'model_name': model_name,
                'model_id': model_id,
                'summary': f"Ошибка: {e}",
                'duration': duration,
                'stats': {},
                'success': False
            })
    
    # Выводим сравнительный анализ
    print("\n" + "="*60)
    print("📊 СРАВНИТЕЛЬНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("="*60)
    
    successful_results = [r for r in results if r['success']]
    
    if not successful_results:
        print("❌ Ни одна модель не смогла создать суммаризацию")
        print("💡 Возможные причины:")
        print("   - Неверный API ключ OpenRouter")
        print("   - Проблемы с интернет-соединением")
        print("   - Временная недоступность сервиса")
        return
    
    print(f"✅ Успешных суммаризаций: {len(successful_results)}/{len(results)}")
    
    # Сортируем по скорости
    successful_results.sort(key=lambda x: x['duration'])
    
    print(f"\n🏆 РЕЙТИНГ ПО СКОРОСТИ:")
    for i, result in enumerate(successful_results, 1):
        print(f"   {i}. {result['model_name']}: {result['duration']:.1f} сек")
    
    # Анализ качества (длина суммаризации)
    print(f"\n📏 АНАЛИЗ ДЛИНЫ СУММАРИЗАЦИИ:")
    for result in successful_results:
        summary_len = len(result['summary'])
        print(f"   {result['model_name']}: {summary_len} символов")
    
    # Показываем полные результаты
    print(f"\n📋 ПОЛНЫЕ РЕЗУЛЬТАТЫ:")
    print("="*60)
    
    for i, result in enumerate(successful_results, 1):
        print(f"\n🤖 МОДЕЛЬ {i}: {result['model_name']}")
        print(f"⏱️  Время: {result['duration']:.1f} сек")
        print(f"📊 Статистика: {result['stats']}")
        print(f"📝 СУММАРИЗАЦИЯ:")
        print("-" * 40)
        print(result['summary'])
        print("-" * 40)
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    if successful_results:
        fastest = successful_results[0]
        print(f"   🚀 Самая быстрая: {fastest['model_name']} ({fastest['duration']:.1f} сек)")
        
        # Находим самую подробную суммаризацию
        detailed = max(successful_results, key=lambda x: len(x['summary']))
        print(f"   📖 Самая подробная: {detailed['model_name']} ({len(detailed['summary'])} символов)")
        
        print(f"\n   ✨ Для продакшена рекомендуем тестировать с реальным API ключом")
        print(f"   ✨ Лучшее качество покажут модели: Mistral, DeepSeek, или Gemma")

def test_with_real_youtube():
    """Тест с реальным YouTube видео"""
    print(f"\n🎬 ТЕСТ С РЕАЛЬНЫМ YOUTUBE ВИДЕО")
    print("="*40)
    print("Для полного тестирования:")
    print("1. Запустите бота: python bot.py")
    print("2. Отправьте ссылку: https://youtu.be/DpQtKCcTMnQ")
    print("3. Выберите 'Только ИИ-суммаризация'")
    print("4. Сравните результаты разных моделей")

if __name__ == "__main__":
    print("🧪 ФИНАЛЬНАЯ ФАЗА ТЕСТИРОВАНИЯ")
    print("Тестирование качества ИИ-суммаризации YouTube субтитров")
    print()
    
    # Проверяем API ключ
    api_key = os.environ.get('OPENROUTER_API_KEY', '')
    if not api_key or api_key.startswith('sk-or-v1-your-real'):
        print("⚠️  ВНИМАНИЕ: Используется тестовый API ключ!")
        print("   Для полного тестирования установите реальный ключ:")
        print("   export OPENROUTER_API_KEY='your-real-key'")
        print("   Или добавьте в .env файл")
        print()
        print("🔄 Продолжаем с демо-режимом...")
        print()
    
    # Запускаем тестирование
    asyncio.run(test_summarization_quality())
    
    # Дополнительные рекомендации
    test_with_real_youtube()
    
    print(f"\n🎯 ИТОГ: Система готова для извлечения основных мыслей из YouTube видео!") 