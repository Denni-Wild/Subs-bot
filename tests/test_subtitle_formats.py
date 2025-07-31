#!/usr/bin/env python3
"""
Тестовый скрипт для локального тестирования форматирования субтитров.
Тестирует функцию format_subtitles() с разными форматами и сохраняет результаты в файлы.
Поддерживает работу с реальными YouTube видео через YouTube Transcript API.
"""

import os
import sys
import logging
import re
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import format_subtitles, extract_video_id, get_available_transcripts
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Список тестовых YouTube видео
TEST_VIDEOS = [
    "https://www.youtube.com/watch?v=WDKSIQ38wGA",
    "https://www.youtube.com/watch?v=8BtHk-oNlN0", 
    "https://www.youtube.com/watch?v=R0mCFE0bXaE"
]

def create_test_transcript():
    """Создает тестовые данные субтитров, имитирующие реальные YouTube субтитры"""
    return [
        {'start': 0.0, 'text': 'Добро пожаловать в наш видеоурок'},
        {'start': 3.5, 'text': 'Сегодня мы будем изучать основы программирования'},
        {'start': 8.2, 'text': 'Python - это мощный язык программирования'},
        {'start': 12.8, 'text': 'Он прост в изучении и имеет понятный синтаксис'},
        {'start': 18.5, 'text': 'Давайте начнем с установки Python'},
        {'start': 25.3, 'text': 'Скачайте Python с официального сайта python.org'},
        {'start': 32.1, 'text': 'После установки откройте командную строку'},
        {'start': 38.7, 'text': 'Введите python --version для проверки установки'},
        {'start': 45.2, 'text': 'Отлично! Python установлен и готов к работе'},
        {'start': 52.8, 'text': 'Теперь давайте создадим первую программу'},
        {'start': 60.1, 'text': 'Откройте любой текстовый редактор'},
        {'start': 67.4, 'text': 'Создайте файл с расширением .py'},
        {'start': 75.9, 'text': 'Напишите print("Hello, World!")'},
        {'start': 82.3, 'text': 'Сохраните файл и запустите его'},
        {'start': 90.7, 'text': 'Поздравляю! Вы написали первую программу на Python'}
    ]

def get_real_subtitles(video_id, lang_code='ru'):
    """Получает реальные субтитры с YouTube видео"""
    try:
        logger.info(f"Получаем субтитры для видео {video_id}, язык: {lang_code}")
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
        logger.info(f"Получено {len(transcript)} строк субтитров")
        return transcript
    except TranscriptsDisabled:
        logger.error(f"Субтитры отключены для видео {video_id}")
        return None
    except NoTranscriptFound:
        logger.error(f"Субтитры не найдены для видео {video_id}, язык: {lang_code}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении субтитров для {video_id}: {e}")
        # Попробуем получить субтитры без указания языка
        try:
            logger.info(f"Пробуем получить субтитры без указания языка для {video_id}")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            logger.info(f"Получено {len(transcript)} строк субтитров (без указания языка)")
            return transcript
        except Exception as e2:
            logger.error(f"Не удалось получить субтитры даже без указания языка для {video_id}: {e2}")
            return None

def get_available_languages(video_id):
    """Получает список доступных языков субтитров для видео"""
    try:
        list_transcripts = get_available_transcripts(video_id)
        if list_transcripts:
            languages = []
            for transcript in list_transcripts:
                languages.append({
                    'code': transcript.language_code,
                    'name': transcript.language
                })
            logger.info(f"Доступные языки для {video_id}: {languages}")
            return languages
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении списка языков для {video_id}: {e}")
        return []

def save_subtitles_to_file(content, filename):
    """Сохраняет субтитры в файл с обработкой ошибок"""
    try:
        filepath = Path('tests') / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Файл сохранен: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла {filename}: {e}")
        return False

def test_subtitle_formatting():
    """Основная функция тестирования форматирования субтитров с демо-данными"""
    logger.info("Начинаем тестирование форматирования субтитров с демо-данными...")
    
    # Создаем тестовые данные
    test_transcript = create_test_transcript()
    logger.info(f"Создано {len(test_transcript)} тестовых строк субтитров")
    
    # Тестируем форматирование с временными метками
    logger.info("Тестируем форматирование с временными метками...")
    subtitles_with_time = format_subtitles(test_transcript, with_time=True)
    
    # Тестируем форматирование без временных меток
    logger.info("Тестируем форматирование без временных меток...")
    subtitles_plain = format_subtitles(test_transcript, with_time=False)
    
    # Сохраняем результаты в файлы
    logger.info("Сохраняем результаты в файлы...")
    
    success_with_time = save_subtitles_to_file(
        subtitles_with_time, 
        'subtitles_test_with_time.txt'
    )
    
    success_plain = save_subtitles_to_file(
        subtitles_plain, 
        'subtitles_test_plain.txt'
    )
    
    # Выводим статистику
    logger.info("=== СТАТИСТИКА ТЕСТИРОВАНИЯ (ДЕМО) ===")
    logger.info(f"Строк субтитров: {len(test_transcript)}")
    logger.info(f"Размер с тайм-кодами: {len(subtitles_with_time)} символов")
    logger.info(f"Размер без тайм-кодов: {len(subtitles_plain)} символов")
    logger.info(f"Файл с тайм-кодами: {'✅' if success_with_time else '❌'}")
    logger.info(f"Файл без тайм-кодов: {'✅' if success_plain else '❌'}")
    
    # Проверяем корректность форматирования
    logger.info("=== ПРОВЕРКА ФОРМАТИРОВАНИЯ ===")
    
    # Проверяем наличие тайм-кодов в первом файле
    if '[00:00]' in subtitles_with_time and '[01:00]' in subtitles_with_time:
        logger.info("✅ Тайм-коды корректно добавлены")
    else:
        logger.error("❌ Ошибка в форматировании тайм-кодов")
    
    # Проверяем отсутствие тайм-кодов во втором файле
    if '[00:00]' not in subtitles_plain and '[01:00]' not in subtitles_plain:
        logger.info("✅ Тайм-коды корректно удалены")
    else:
        logger.error("❌ Ошибка: тайм-коды присутствуют в файле без меток")
    
    # Проверяем наличие текста в обоих файлах
    if 'Python' in subtitles_with_time and 'Python' in subtitles_plain:
        logger.info("✅ Текст корректно сохранен в обоих форматах")
    else:
        logger.error("❌ Ошибка: текст не сохранен корректно")
    
    return success_with_time and success_plain

def test_real_youtube_videos():
    """Тестирование с реальными YouTube видео"""
    logger.info("=== ТЕСТИРОВАНИЕ С РЕАЛЬНЫМИ YOUTUBE ВИДЕО ===")
    
    total_success = 0
    total_videos = len(TEST_VIDEOS)
    
    for video_url in TEST_VIDEOS:
        logger.info(f"\n--- Обработка видео: {video_url} ---")
        
        # Извлекаем ID видео
        video_id = extract_video_id(video_url)
        if not video_id:
            logger.error(f"Не удалось извлечь ID из ссылки: {video_url}")
            continue
        
        logger.info(f"ID видео: {video_id}")
        
        # Получаем доступные языки
        languages = get_available_languages(video_id)
        if not languages:
            logger.warning(f"Не удалось получить список языков для {video_id}")
            # Попробуем стандартные языки
            languages = [
                {'code': 'ru', 'name': 'Russian'},
                {'code': 'en', 'name': 'English'},
                {'code': 'auto', 'name': 'Auto'}
            ]
        
        # Пытаемся получить субтитры для каждого языка
        transcript = None
        used_lang = None
        
        for lang_info in languages:
            lang_code = lang_info['code']
            lang_name = lang_info['name']
            
            logger.info(f"Пробуем язык: {lang_name} ({lang_code})")
            
            # Получаем субтитры
            transcript = get_real_subtitles(video_id, lang_code)
            if transcript:
                used_lang = lang_code
                logger.info(f"✅ Успешно получили субтитры для {video_id}, язык: {lang_code}")
                break
            else:
                logger.warning(f"Не удалось получить субтитры для {video_id}, язык: {lang_code}")
        
        if not transcript:
            logger.error(f"❌ Не удалось получить субтитры для видео {video_id} ни на одном языке")
            continue
        
        # Форматируем субтитры в двух форматах
        subtitles_with_time = format_subtitles(transcript, with_time=True)
        subtitles_plain = format_subtitles(transcript, with_time=False)
        
        # Сохраняем файлы
        filename_with_time = f'subtitles_{video_id}_with_time_{used_lang}.txt'
        filename_plain = f'subtitles_{video_id}_plain_{used_lang}.txt'
        
        success_with_time = save_subtitles_to_file(subtitles_with_time, filename_with_time)
        success_plain = save_subtitles_to_file(subtitles_plain, filename_plain)
        
        if success_with_time and success_plain:
            logger.info(f"✅ Успешно обработано видео {video_id}, язык: {used_lang}")
            logger.info(f"   Строк: {len(transcript)}")
            logger.info(f"   Размер с тайм-кодами: {len(subtitles_with_time)} символов")
            logger.info(f"   Размер без тайм-кодов: {len(subtitles_plain)} символов")
            total_success += 1
        else:
            logger.error(f"❌ Ошибка при сохранении файлов для {video_id}, язык: {used_lang}")
    
    logger.info(f"\n=== ИТОГИ ТЕСТИРОВАНИЯ РЕАЛЬНЫХ ВИДЕО ===")
    logger.info(f"Всего видео: {total_videos}")
    logger.info(f"Успешно обработано: {total_success}")
    logger.info(f"Процент успеха: {(total_success/total_videos)*100:.1f}%")
    
    return total_success > 0

def load_existing_subtitles():
    """Загружает существующие субтитры из файла для тестирования"""
    try:
        # Пробуем разные пути к файлу субтитров
        possible_paths = [
            Path('../subtitles_DpQtKCcTMnQ_ru.txt'),
            Path('../../subtitles_DpQtKCcTMnQ_ru.txt'),
            Path('subtitles_DpQtKCcTMnQ_ru.txt'),
            Path('../tests/subtitles_DpQtKCcTMnQ_ru.txt')
        ]
        
        subtitle_file = None
        for path in possible_paths:
            if path.exists():
                subtitle_file = path
                break
        
        if not subtitle_file:
            logger.warning("Файл субтитров не найден по путям:")
            for path in possible_paths:
                logger.warning(f"  - {path.absolute()}")
            return None
        
        logger.info(f"Найден файл субтитров: {subtitle_file.absolute()}")
        
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим субтитры в формат для тестирования
        lines = content.strip().split('\n')
        transcript = []
        current_time = 0
        
        for line in lines:
            if line.strip():
                transcript.append({
                    'start': current_time,
                    'text': line.strip()
                })
                current_time += 3  # Примерное время между строками
        
        logger.info(f"Загружено {len(transcript)} строк из существующего файла субтитров")
        return transcript
    except Exception as e:
        logger.error(f"Ошибка при загрузке существующих субтитров: {e}")
        return None

def test_existing_subtitles():
    """Тестирование форматирования на существующих субтитрах"""
    logger.info("=== ТЕСТИРОВАНИЕ НА СУЩЕСТВУЮЩИХ СУБТИТРАХ ===")
    
    # Загружаем существующие субтитры
    transcript = load_existing_subtitles()
    if not transcript:
        logger.warning("Не удалось загрузить существующие субтитры, пропускаем тест")
        return False
    
    # Форматируем субтитры в двух форматах
    subtitles_with_time = format_subtitles(transcript, with_time=True)
    subtitles_plain = format_subtitles(transcript, with_time=False)
    
    # Сохраняем файлы
    filename_with_time = 'subtitles_existing_with_time.txt'
    filename_plain = 'subtitles_existing_plain.txt'
    
    success_with_time = save_subtitles_to_file(subtitles_with_time, filename_with_time)
    success_plain = save_subtitles_to_file(subtitles_plain, filename_plain)
    
    if success_with_time and success_plain:
        logger.info(f"✅ Успешно обработаны существующие субтитры")
        logger.info(f"   Строк: {len(transcript)}")
        logger.info(f"   Размер с тайм-кодами: {len(subtitles_with_time)} символов")
        logger.info(f"   Размер без тайм-кодов: {len(subtitles_plain)} символов")
        
        # Проверяем корректность форматирования
        if '[00:00]' in subtitles_with_time:
            logger.info("✅ Тайм-коды корректно добавлены")
        else:
            logger.error("❌ Ошибка в форматировании тайм-кодов")
        
        if '[00:00]' not in subtitles_plain:
            logger.info("✅ Тайм-коды корректно удалены")
        else:
            logger.error("❌ Ошибка: тайм-коды присутствуют в файле без меток")
        
        return True
    else:
        logger.error("❌ Ошибка при сохранении файлов с существующими субтитрами")
        return False

def main():
    """Главная функция"""
    logger.info("=== ТЕСТИРОВАНИЕ ФОРМАТИРОВАНИЯ СУБТИТРОВ ===")
    
    try:
        # Тестируем с демо-данными
        demo_success = test_subtitle_formatting()
        
        # Тестируем с существующими субтитрами
        existing_success = test_existing_subtitles()
        
        # Тестируем с реальными YouTube видео
        real_success = test_real_youtube_videos()
        
        if demo_success and existing_success:
            logger.info("✅ Основные тесты завершены успешно!")
            print("\n" + "="*60)
            print("✅ ОСНОВНЫЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
            print("📁 Файлы сохранены в папке tests/")
            print("   - Демо-файлы: subtitles_test_*.txt")
            print("   - Существующие субтитры: subtitles_existing_*.txt")
            if real_success:
                print("   - Реальные видео: subtitles_{video_id}_*.txt")
            print("="*60)
        elif demo_success:
            logger.warning("⚠️ Демо-тесты прошли, но есть проблемы с другими тестами")
            print("\n" + "="*60)
            print("⚠️ ДЕМО-ТЕСТЫ ПРОШЛИ, НО ЕСТЬ ПРОБЛЕМЫ С ДРУГИМИ ТЕСТАМИ")
            print("Проверьте логи выше для деталей")
            print("="*60)
        else:
            logger.error("❌ Тестирование завершено с ошибками!")
            print("\n" + "="*60)
            print("❌ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО С ОШИБКАМИ!")
            print("Проверьте логи выше для деталей")
            print("="*60)
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    main() 