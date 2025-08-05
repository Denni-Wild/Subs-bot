#!/usr/bin/env python3
"""
Демонстрационный скрипт работы бота с выбором формата субтитров.
Показывает, как бот обрабатывает запросы пользователей и форматирует субтитры.
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot import (
    extract_video_id, 
    get_available_transcripts, 
    format_subtitles,
    build_format_keyboard,
    build_action_keyboard
)

def demo_format_selection():
    """Демонстрация выбора формата субтитров"""
    print("🤖 ДЕМОНСТРАЦИЯ РАБОТЫ БОТА С ВЫБОРОМ ФОРМАТА СУБТИТРОВ")
    print("=" * 60)
    
    # Тестовые данные (имитируем субтитры)
    test_transcript = [
        {'start': 0.0, 'text': 'Добро пожаловать в наш видеоурок'},
        {'start': 3.5, 'text': 'Сегодня мы будем изучать основы программирования'},
        {'start': 8.2, 'text': 'Python - это мощный язык программирования'},
        {'start': 12.8, 'text': 'Он прост в изучении и имеет понятный синтаксис'},
        {'start': 18.5, 'text': 'Давайте начнем с установки Python'},
        {'start': 25.3, 'text': 'Скачайте Python с официального сайта python.org'},
        {'start': 32.1, 'text': 'После установки откройте командную строку'},
        {'start': 38.7, 'text': 'Введите python --version для проверки установки'},
        {'start': 45.2, 'text': 'Отлично! Python установлен и готов к работе'},
        {'start': 52.8, 'text': 'Теперь давайте создадим первую программу'}
    ]
    
    print("📋 Шаг 1: Пользователь отправляет ссылку на YouTube видео")
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"   Ссылка: {video_url}")
    
    # Извлекаем ID видео
    video_id = extract_video_id(video_url)
    print(f"   Извлеченный ID: {video_id}")
    
    print("\n📋 Шаг 2: Бот проверяет доступные субтитры")
    print("   (В демо используем тестовые данные)")
    print(f"   Найдено строк субтитров: {len(test_transcript)}")
    
    print("\n📋 Шаг 3: Бот предлагает выбрать действие")
    action_keyboard = build_action_keyboard()
    print("   Доступные действия:")
    for row in action_keyboard.inline_keyboard:
        for button in row:
            print(f"   - {button.text} (callback: {button.callback_data})")
    
    print("\n📋 Шаг 4: Пользователь выбирает 'Только субтитры'")
    selected_action = 'action_subtitles'
    print(f"   Выбрано: {selected_action}")
    
    print("\n📋 Шаг 5: Бот предлагает выбрать формат субтитров")
    format_keyboard = build_format_keyboard()
    print("   Доступные форматы:")
    for row in format_keyboard.inline_keyboard:
        for button in row:
            print(f"   - {button.text} (callback: {button.callback_data})")
    
    print("\n📋 Шаг 6: Демонстрация форматирования")
    print("   Формат 1: С временными метками")
    subtitles_with_time = format_subtitles(test_transcript, with_time=True)
    print("   Результат:")
    for line in subtitles_with_time.split('\n')[:5]:  # Показываем первые 5 строк
        print(f"   {line}")
    print("   ...")
    
    print("\n   Формат 2: Без временных меток")
    subtitles_plain = format_subtitles(test_transcript, with_time=False)
    print("   Результат:")
    for line in subtitles_plain.split('\n')[:5]:  # Показываем первые 5 строк
        print(f"   {line}")
    print("   ...")
    
    print("\n📊 СТАТИСТИКА:")
    print(f"   Строк субтитров: {len(test_transcript)}")
    print(f"   Размер с тайм-кодами: {len(subtitles_with_time)} символов")
    print(f"   Размер без тайм-кодов: {len(subtitles_plain)} символов")
    
    return test_transcript, subtitles_with_time, subtitles_plain

def demo_real_subtitles():
    """Демонстрация с реальными субтитрами"""
    print("\n" + "=" * 60)
    print("🎬 ДЕМОНСТРАЦИЯ С РЕАЛЬНЫМИ СУБТИТРАМИ")
    print("=" * 60)
    
    # Загружаем реальные субтитры
    subtitle_file = Path('subtitles_DpQtKCcTMnQ_ru.txt')
    if not subtitle_file.exists():
        print("❌ Файл с реальными субтитрами не найден")
        return
    
    print(f"📁 Загружаем реальные субтитры из: {subtitle_file}")
    
    try:
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим субтитры в формат для тестирования
        lines = content.strip().split('\n')
        transcript = []
        current_time = 0
        
        for line in lines[:50]:  # Берем первые 50 строк для демо
            if line.strip():
                transcript.append({
                    'start': current_time,
                    'text': line.strip()
                })
                current_time += 3
        
        print(f"✅ Загружено {len(transcript)} строк реальных субтитров")
        
        print("\n📋 Форматирование реальных субтитров:")
        
        # Форматируем с тайм-кодами
        subtitles_with_time = format_subtitles(transcript, with_time=True)
        print("\n   🔹 С временными метками (первые 3 строки):")
        for line in subtitles_with_time.split('\n')[:3]:
            print(f"   {line}")
        
        # Форматируем без тайм-кодов
        subtitles_plain = format_subtitles(transcript, with_time=False)
        print("\n   🔹 Без временных меток (первые 3 строки):")
        for line in subtitles_plain.split('\n')[:3]:
            print(f"   {line}")
        
        print(f"\n📊 Статистика реальных субтитров:")
        print(f"   Строк: {len(transcript)}")
        print(f"   Размер с тайм-кодами: {len(subtitles_with_time)} символов")
        print(f"   Размер без тайм-кодов: {len(subtitles_plain)} символов")
        
        # Сохраняем демо-файлы
        demo_dir = Path('demo_output')
        demo_dir.mkdir(exist_ok=True)
        
        with open(demo_dir / 'demo_with_time.txt', 'w', encoding='utf-8') as f:
            f.write(subtitles_with_time)
        
        with open(demo_dir / 'demo_plain.txt', 'w', encoding='utf-8') as f:
            f.write(subtitles_plain)
        
        print(f"\n💾 Демо-файлы сохранены в папке: {demo_dir}")
        
    except Exception as e:
        print(f"❌ Ошибка при обработке реальных субтитров: {e}")

def main():
    """Главная функция демонстрации"""
    print("🚀 ЗАПУСК ДЕМОНСТРАЦИИ РАБОТЫ БОТА")
    print("=" * 60)
    
    try:
        # Демонстрация с тестовыми данными
        demo_format_selection()
        
        # Демонстрация с реальными субтитрами
        demo_real_subtitles()
        
        print("\n" + "=" * 60)
        print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 60)
        print("\n📝 Что было продемонстрировано:")
        print("   • Извлечение ID видео из ссылки")
        print("   • Создание клавиатур для выбора формата")
        print("   • Форматирование субтитров с тайм-кодами")
        print("   • Форматирование субтитров без тайм-кодов")
        print("   • Работа с реальными данными")
        print("   • Сохранение результатов в файлы")
        
        print("\n🤖 Для запуска реального бота:")
        print("   1. Создайте файл .env с токеном TELEGRAM_BOT_TOKEN")
        print("   2. Запустите: python bot.py")
        print("   3. Отправьте боту ссылку на YouTube видео")
        print("   4. Выберите формат субтитров")
        
    except Exception as e:
        print(f"\n❌ Ошибка в демонстрации: {e}")

if __name__ == "__main__":
    main() 