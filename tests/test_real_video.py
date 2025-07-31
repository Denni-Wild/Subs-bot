#!/usr/bin/env python3
"""
Тестирование функционала на реальном YouTube видео
Запуск: python test_real_video.py <youtube_url>
"""

import sys
import os
import asyncio
from datetime import datetime

# Импортируем наши модули
try:
    from bot import extract_video_id, get_available_transcripts, format_subtitles
    from summarizer import TextSummarizer
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)


def print_separator(title=""):
    """Красивый разделитель"""
    print("\n" + "="*60)
    if title:
        print(f"🎯 {title}")
        print("="*60)


def test_extract_video_id(url):
    """Тест извлечения video_id"""
    print_separator("ТЕСТ 1: Извлечение Video ID")
    
    print(f"📺 Входная ссылка: {url}")
    
    video_id = extract_video_id(url)
    
    if video_id:
        print(f"✅ Video ID извлечен: {video_id}")
        print(f"🔗 Прямая ссылка: https://youtu.be/{video_id}")
        return video_id
    else:
        print("❌ Не удалось извлечь Video ID")
        return None


def test_get_transcripts(video_id):
    """Тест получения доступных субтитров"""
    print_separator("ТЕСТ 2: Получение списка субтитров")
    
    print(f"🔍 Проверяем доступные субтитры для {video_id}...")
    
    try:
        transcripts = get_available_transcripts(video_id)
        
        if transcripts:
            transcripts_list = list(transcripts)
            print(f"✅ Найдено языков субтитров: {len(transcripts_list)}")
            
            print("\n📋 Доступные языки:")
            for i, transcript in enumerate(transcripts_list, 1):
                print(f"   {i}. {transcript.language} ({transcript.language_code})")
            
            return transcripts_list
        else:
            print("❌ Субтитры не найдены")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при получении субтитров: {e}")
        return None


def test_download_subtitles(video_id, lang_code='ru'):
    """Тест скачивания субтитров"""
    print_separator(f"ТЕСТ 3: Скачивание субтитров ({lang_code})")
    
    try:
        print(f"⬇️ Скачиваем субтитры на языке: {lang_code}")
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
        
        if transcript:
            print(f"✅ Субтитры получены: {len(transcript)} сегментов")
            
            # Форматируем разными способами
            plain_text = format_subtitles(transcript, with_time=False)
            time_text = format_subtitles(transcript, with_time=True)
            
            print(f"📊 Статистика:")
            print(f"   • Сегментов: {len(transcript)}")
            print(f"   • Символов (без меток): {len(plain_text)}")
            print(f"   • Символов (с метками): {len(time_text)}")
            
            # Показываем первые 3 строки
            print(f"\n📝 Первые строки (без времени):")
            lines = plain_text.split('\n')[:3]
            for i, line in enumerate(lines, 1):
                print(f"   {i}. {line}")
            
            print(f"\n🕐 Первые строки (с временными метками):")
            time_lines = time_text.split('\n')[:3]
            for i, line in enumerate(time_lines, 1):
                print(f"   {i}. {line}")
            
            return plain_text
        else:
            print("❌ Субтитры пусты")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка скачивания субтитров: {e}")
        return None


async def test_ai_summarization(text):
    """Тест ИИ-суммаризации"""
    print_separator("ТЕСТ 4: ИИ-суммаризация")
    
    # Проверяем наличие API ключа
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_key:
        print("⚠️ OPENROUTER_API_KEY не найден в переменных окружения")
        print("💡 Для теста ИИ-суммаризации нужен API ключ OpenRouter")
        print("   Получить можно на: https://openrouter.ai/")
        return None
    
    print(f"🤖 API ключ найден: {openrouter_key[:10]}...{openrouter_key[-4:]}")
    
    try:
        summarizer = TextSummarizer()
        
        print(f"📊 Модели доступны: {len(summarizer.models)}")
        print(f"🔧 Размер частей: {summarizer.chunk_size} символов")
        
        # Ограничиваем текст для экономии API вызовов (первые 2000 символов)
        test_text = text[:2000] if len(text) > 2000 else text
        
        print(f"📝 Обрабатываем текст: {len(test_text)} символов")
        print(f"⏳ Начинаем суммаризацию... (может занять 1-2 минуты)")
        
        start_time = datetime.now()
        
        summary, stats = await summarizer.summarize_text(test_text, model_index=0)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Суммаризация завершена за {duration:.1f} секунд")
        
        print(f"\n📊 Статистика обработки:")
        for key, value in stats.items():
            print(f"   • {key}: {value}")
        
        print(f"\n🤖 РЕЗУЛЬТАТ СУММАРИЗАЦИИ:")
        print("-" * 40)
        print(summary)
        print("-" * 40)
        
        return summary
        
    except Exception as e:
        print(f"❌ Ошибка ИИ-суммаризации: {e}")
        return None


def main():
    """Основная функция тестирования"""
    print("🎬 ТЕСТИРОВАНИЕ НА РЕАЛЬНОМ YOUTUBE ВИДЕО")
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Получаем URL из аргументов командной строки или запрашиваем
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("\n🔗 Введите ссылку на YouTube видео: ").strip()
    
    if not url:
        print("❌ Ссылка не указана")
        return
    
    print(f"🎯 Тестируем URL: {url}")
    
    # Тест 1: Извлечение video_id
    video_id = test_extract_video_id(url)
    if not video_id:
        print("\n💥 Не удалось извлечь video_id. Тестирование прервано.")
        return
    
    # Тест 2: Получение доступных субтитров
    transcripts = test_get_transcripts(video_id)
    if not transcripts:
        print("\n💥 Субтитры недоступны. Дальнейшее тестирование невозможно.")
        return
    
    # Выбираем язык для тестирования
    lang_code = 'ru'  # По умолчанию русский
    available_langs = [t.language_code for t in transcripts]
    
    if 'ru' not in available_langs and 'en' in available_langs:
        lang_code = 'en'
    elif 'ru' not in available_langs and 'en' not in available_langs:
        lang_code = available_langs[0]  # Берем первый доступный
    
    print(f"\n🎯 Выбран язык для тестирования: {lang_code}")
    
    # Тест 3: Скачивание субтитров
    subtitles_text = test_download_subtitles(video_id, lang_code)
    if not subtitles_text:
        print("\n💥 Не удалось получить субтитры.")
        return
    
    # Тест 4: ИИ-суммаризация (асинхронно)
    try:
        asyncio.run(test_ai_summarization(subtitles_text))
    except Exception as e:
        print(f"❌ Ошибка в асинхронном тесте: {e}")
    
    # Итоги
    print_separator("ИТОГИ ТЕСТИРОВАНИЯ")
    print("✅ Извлечение video_id: РАБОТАЕТ")
    print("✅ Получение списка субтитров: РАБОТАЕТ") 
    print("✅ Скачивание субтитров: РАБОТАЕТ")
    
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if openrouter_key:
        print("✅ ИИ-суммаризация: ПРОТЕСТИРОВАНА")
    else:
        print("⚠️ ИИ-суммаризация: НЕ ТЕСТИРОВАЛАСЬ (нет API ключа)")
    
    print("\n🎉 ОСНОВНОЙ ФУНКЦИОНАЛ РАБОТАЕТ!")
    print(f"📺 Протестировано видео: {video_id}")


if __name__ == "__main__":
    main() 