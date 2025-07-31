import asyncio
import logging
from youtube_transcript_api import YouTubeTranscriptApi

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_working_video():
    """Тестируем рабочее видео для сравнения"""
    video_id = "dQw4w9WgXcQ"  # Rick Roll - должно работать
    
    logger.info(f"🧪 Тестирую рабочее видео: {video_id}")
    
    try:
        # 1. Получаем список всех субтитров
        logger.info("📋 Получаю список всех субтитров...")
        list_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        available_languages = [t.language_code for t in list_transcripts]
        logger.info(f"🌍 Доступные языки: {available_languages}")
        
        # 2. Пробуем получить субтитры для английского
        logger.info("🎬 Тестирую английский язык...")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            logger.info(f"✅ Успешно получены субтитры для en: {len(transcript)} строк")
            logger.info(f"📝 Первые 3 строки: {transcript[:3]}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка для языка en: {e}")
        
        # 3. Пробуем через list_transcripts
        logger.info("🔍 Пробую через list_transcripts...")
        try:
            for transcript_obj in list_transcripts:
                if transcript_obj.language_code == 'en':
                    transcript = transcript_obj.fetch()
                    logger.info(f"✅ Успешно через list_transcripts: {len(transcript)} строк")
                    return True
        except Exception as e:
            logger.error(f"❌ Ошибка через list_transcripts: {e}")
            
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
    
    return False

if __name__ == "__main__":
    asyncio.run(test_working_video()) 