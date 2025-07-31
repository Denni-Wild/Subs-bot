import logging
import asyncio
from bot import extract_video_id, get_available_transcripts_with_retry

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_video_processing():
    """Тестируем обработку видео"""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    logger.info("🧪 Начинаю тестирование обработки видео")
    
    # Тестируем извлечение video_id
    video_id = extract_video_id(test_url)
    logger.info(f"🎬 Извлеченный video_id: {video_id}")
    
    if video_id:
        # Тестируем получение субтитров
        logger.info(f"🔄 Тестирую получение субтитров для {video_id}")
        try:
            list_transcripts, success, error_msg = await get_available_transcripts_with_retry(video_id)
            
            if success:
                logger.info(f"✅ Успешно получены субтитры: {len(list_transcripts)} языков")
                for transcript in list_transcripts:
                    logger.info(f"  - {transcript.language} ({transcript.language_code})")
            else:
                logger.error(f"❌ Ошибка: {error_msg}")
        except Exception as e:
            logger.error(f"❌ Исключение при получении субтитров: {e}")
    else:
        logger.error("❌ Не удалось извлечь video_id")

if __name__ == "__main__":
    asyncio.run(test_video_processing()) 