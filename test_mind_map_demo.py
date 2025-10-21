#!/usr/bin/env python3
"""
Демонстрация Mind Map Generator для Subs-bot

Этот скрипт показывает работу модуля генерации mind map
"""

import asyncio
import os
from mind_map_generator import MindMapGenerator

async def main():
    """Основная функция демонстрации"""
    print("🧠 Mind Map Generator Demo")
    print("=" * 50)
    
    # Проверяем API ключ
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY не настроен")
        print("Установите переменную окружения или создайте .env файл")
        return
    
    # Создаем генератор
    generator = MindMapGenerator(api_key)
    print("✅ Mind Map Generator инициализирован")
    
    # Тестовый текст
    sample_text = """
    Искусственный интеллект и машинное обучение становятся все более важными в современном мире. 
    Эти технологии используются для анализа больших объемов данных, автоматизации процессов и принятия решений.
    
    В области обработки естественного языка, ИИ помогает создавать чат-ботов, системы перевода и анализа текста. 
    Машинное обучение позволяет компьютерам учиться на примерах и улучшать свою производительность.
    
    YouTube и другие платформы используют ИИ для рекомендаций контента, автоматической генерации субтитров 
    и анализа аудио. Голосовые помощники, такие как Siri и Alexa, также основаны на технологиях ИИ.
    
    В медицине искусственный интеллект помогает диагностировать заболевания, анализировать медицинские изображения 
    и предсказывать результаты лечения. Это значительно улучшает качество медицинской помощи.
    
    Автомобильная промышленность активно развивает автономные транспортные средства, используя ИИ для 
    распознавания объектов, планирования маршрутов и принятия решений в реальном времени.
    """
    
    print(f"\n📝 Анализируем текст ({len(sample_text)} символов)...")
    
    try:
        # Создаем mind map во всех форматах
        results = await generator.create_mind_map(sample_text, "all")
        
        print("\n✅ Mind Map успешно создан!")
        print(f"📊 Главная тема: {results['structure']['main_topic']}")
        print(f"🏷️ Количество подтем: {len(results['structure']['subtopics'])}")
        
        # Показываем структуру
        print("\n📋 Структура идей:")
        for topic, ideas in results['structure']['subtopics'].items():
            print(f"  {topic}: {len(ideas)} идей")
            for idea in ideas[:3]:  # Показываем первые 3 идеи
                print(f"    • {idea}")
            if len(ideas) > 3:
                print(f"    ... и еще {len(ideas) - 3} идей")
        
        # Сохраняем файлы
        print("\n💾 Сохраняем файлы...")
        
        # Markdown
        with open("demo_mindmap.md", "w", encoding="utf-8") as f:
            f.write(results['markdown'])
        print("  ✅ Markdown сохранен: demo_mindmap.md")
        
        # Mermaid
        with open("demo_mindmap.mmd", "w", encoding="utf-8") as f:
            f.write(results['mermaid'])
        print("  ✅ Mermaid сохранен: demo_mindmap.mmd")
        
        # HTML
        with open("demo_mindmap.html", "w", encoding="utf-8") as f:
            f.write(results['html_content'])
        print("  ✅ HTML сохранен: demo_mindmap.html")
        
        # PNG (если доступен)
        if results['png_path']:
            print(f"  ✅ PNG сохранен: {results['png_path']}")
        else:
            print("  ⚠️ PNG не создан (требуется mermaid-cli или доступ к kroki.io)")
        
        print("\n🎉 Демонстрация завершена!")
        print("\n💡 Что дальше:")
        print("  • Откройте demo_mindmap.html в браузере для интерактивной карты")
        print("  • Используйте demo_mindmap.mmd с mermaid-cli для PNG")
        print("  • Изучите demo_mindmap.md для понимания структуры")
        
    except Exception as e:
        print(f"❌ Ошибка при создании mind map: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
