#!/usr/bin/env python3
"""
Офлайн тест Mind Map Generator для Subs-bot

Этот скрипт тестирует функциональность без API ключей
"""

import asyncio
import json
from mind_map_generator import MindMapGenerator

class MockMindMapGenerator(MindMapGenerator):
    """Мок-версия генератора для тестирования без API"""
    
    async def _analyze_chunk_with_llm(self, chunk: str):
        """Мок-анализ чанка текста"""
        # Имитируем анализ LLM на основе ключевых слов
        ideas = []
        
        # Простой анализ по ключевым словам
        if 'искусственный интеллект' in chunk.lower() or 'ии' in chunk.lower():
            ideas.extend([
                "Искусственный интеллект и машинное обучение",
                "Автоматизация процессов",
                "Анализ больших данных"
            ])
        
        if 'youtube' in chunk.lower() or 'субтитры' in chunk.lower():
            ideas.extend([
                "YouTube платформа",
                "Автоматическая генерация субтитров",
                "Анализ аудио контента"
            ])
        
        if 'голос' in chunk.lower() or 'аудио' in chunk.lower():
            ideas.extend([
                "Голосовые помощники",
                "Распознавание речи",
                "Обработка аудио"
            ])
        
        if 'медицина' in chunk.lower() or 'здоровье' in chunk.lower():
            ideas.extend([
                "Медицинская диагностика",
                "Анализ медицинских изображений",
                "Предсказание результатов лечения"
            ])
        
        if 'автомобиль' in chunk.lower() or 'транспорт' in chunk.lower():
            ideas.extend([
                "Автономные транспортные средства",
                "Распознавание объектов",
                "Планирование маршрутов"
            ])
        
        # Добавляем общие идеи если ничего не найдено
        if not ideas:
            ideas = [
                "Технологические инновации",
                "Цифровая трансформация",
                "Автоматизация процессов"
            ]
        
        return ideas

async def main():
    """Основная функция тестирования"""
    print("🧠 Mind Map Generator - Офлайн тест")
    print("=" * 50)
    
    # Создаем мок-генератор
    generator = MockMindMapGenerator("mock_api_key")
    print("✅ Mock Mind Map Generator инициализирован")
    
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
        with open("test_mindmap.md", "w", encoding="utf-8") as f:
            f.write(results['markdown'])
        print("  ✅ Markdown сохранен: test_mindmap.md")
        
        # Mermaid
        with open("test_mindmap.mmd", "w", encoding="utf-8") as f:
            f.write(results['mermaid'])
        print("  ✅ Mermaid сохранен: test_mindmap.mmd")
        
        # HTML
        with open("test_mindmap.html", "w", encoding="utf-8") as f:
            f.write(results['html_content'])
        print("  ✅ HTML сохранен: test_mindmap.html")
        
        # PNG (если доступен)
        if results['png_path']:
            print(f"  ✅ PNG сохранен: {results['png_path']}")
        else:
            print("  ⚠️ PNG не создан (требуется mermaid-cli или доступ к kroki.io)")
        
        print("\n🎉 Тестирование завершено!")
        print("\n💡 Что дальше:")
        print("  • Откройте test_mindmap.html в браузере для интерактивной карты")
        print("  • Изучите test_mindmap.md для понимания структуры")
        print("  • Проверьте test_mindmap.mmd для Mermaid диаграммы")
        
        # Показываем краткий пример Markdown
        print("\n📝 Пример сгенерированного Markdown:")
        print("-" * 40)
        lines = results['markdown'].split('\n')[:15]  # Первые 15 строк
        for line in lines:
            print(line)
        if len(results['markdown'].split('\n')) > 15:
            print("...")
        
    except Exception as e:
        print(f"❌ Ошибка при создании mind map: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
