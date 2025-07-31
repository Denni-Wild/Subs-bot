import asyncio
import logging
from youtube_transcript_api import YouTubeTranscriptApi

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_specific_video():
    """Тестируем конкретное проблемное видео"""
    video_id = "WDKSIQ38wGA"
    
    logger.info(f"🧪 Тестирую проблемное видео: {video_id}")
    
    try:
        # 1. Получаем список всех субтитров
        logger.info("📋 Получаю список всех субтитров...")
        list_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        available_languages = [t.language_code for t in list_transcripts]
        logger.info(f"🌍 Доступные языки: {available_languages}")
        
        # 2. Пробуем получить субтитры для каждого языка
        for lang in available_languages:
            logger.info(f"🎬 Тестирую язык: {lang}")
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                logger.info(f"✅ Успешно получены субтитры для {lang}: {len(transcript)} строк")
                logger.info(f"📝 Первые 3 строки: {transcript[:3]}")
                return
            except Exception as e:
                logger.error(f"❌ Ошибка для языка {lang}: {e}")
        
        # 3. Пробуем автоматически сгенерированные субтитры
        logger.info("🤖 Пробую автоматически сгенерированные субтитры...")
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['auto'])
            logger.info(f"✅ Успешно получены автоматические субтитры: {len(transcript)} строк")
        except Exception as e:
            logger.error(f"❌ Ошибка с автоматическими субтитрами: {e}")
        
        # 4. Пробуем через list_transcripts с переводом
        logger.info("🔍 Пробую через list_transcripts с переводом...")
        try:
            for transcript_obj in list_transcripts:
                try:
                    # Пробуем получить оригинальные субтитры
                    transcript = transcript_obj.fetch()
                    logger.info(f"✅ Успешно через list_transcripts: {len(transcript)} строк")
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка через list_transcripts: {e}")
                    
                    # Пробуем перевести на английский
                    try:
                        logger.info(f"🔄 Пробую перевести {transcript_obj.language_code} на английский...")
                        transcript = transcript_obj.translate('en').fetch()
                        logger.info(f"✅ Успешно переведены на английский: {len(transcript)} строк")
                        logger.info(f"📝 Первые 3 строки: {transcript[:3]}")
                        break
                    except Exception as e2:
                        logger.error(f"❌ Ошибка перевода: {e2}")
                        
                        # Пробуем другие языки перевода
                        for target_lang in ['en', 'ru', 'es', 'fr']:
                            if target_lang != transcript_obj.language_code:
                                try:
                                    logger.info(f"🔄 Пробую перевести на {target_lang}...")
                                    transcript = transcript_obj.translate(target_lang).fetch()
                                    logger.info(f"✅ Успешно переведены на {target_lang}: {len(transcript)} строк")
                                    break
                                except:
                                    continue
                        else:
                            logger.error(f"❌ Не удалось перевести субтитры")
                            
        except Exception as e:
            logger.error(f"❌ Общая ошибка list_transcripts: {e}")
            
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_specific_video()) 