import os
import re
import logging
import time
import asyncio
import random
import tempfile
from io import BytesIO
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv
from summarizer import TextSummarizer
from voice_transcriber import VoiceTranscriber
import requests

# Включаем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализируем суммаризатор и транскрайбер
summarizer = TextSummarizer()
voice_transcriber = VoiceTranscriber()
YOUTUBE_REGEX = r"(?:v=|youtu\.be/|youtube\.com/embed/|youtube\.com/watch\?v=)?([\w-]{11})"

# Enhanced rate limiting constants
MIN_REQUEST_INTERVAL = 15  # Increased from 10 to 15 seconds
MAX_RETRIES = 3
BASE_DELAY = 2  # Base delay in seconds
MAX_DELAY = 60  # Maximum delay in seconds

# Global rate limiting state
request_timestamps = {}  # Track last request time per user
global_last_request = 0  # Global rate limiting
global_request_lock = asyncio.Lock()  # Prevent concurrent requests

START_MESSAGE = (
    '👋 **Добро пожаловать в YouTube Subtitle Bot!**\n\n'
    '🎯 **Основные возможности:**\n'
    '• 📺 Получение субтитров с YouTube-видео\n'
    '• 🎤 Расшифровка голосовых сообщений\n'
    '• 🤖 ИИ-суммаризация субтитров\n'
    '• 🌍 Поддержка множества языков\n\n'
    '📝 **Как использовать:**\n'
    '1. Отправьте ссылку на YouTube-видео\n'
    '2. Выберите язык субтитров\n'
    '3. Выберите действие (субтитры/суммаризация)\n'
    '4. Получите результат!\n\n'
    '🎤 **Голосовые сообщения:**\n'
    'Просто отправьте голосовое сообщение для расшифровки\n'
    'Максимальная длительность: 5 минут\n\n'
    '📚 **Команды:**\n'
    '/start - Начать работу\n'
    '/help - Подробная справка\n'
    '/about - О боте\n'
    '/subs - Получить субтитры\n'
    '/voice - Расшифровать голос\n'
    '/info - Краткая информация\n\n'
    '🚀 **Начните прямо сейчас!**'
)

HELP_MESSAGE = (
    'ℹ️ **ПОДРОБНАЯ СПРАВКА**\n\n'
    '📺 **YouTube субтитры:**\n'
    '1. Отправьте ссылку на YouTube-видео\n'
    '2. Выберите язык субтитров (если доступно несколько)\n'
    '3. Выберите действие:\n'
    '   • 📄 Только субтитры\n'
    '   • 🤖 Субтитры + ИИ-суммаризация\n'
    '   • 🔮 Только ИИ-суммаризация\n'
    '4. При необходимости выберите формат (с/без временных меток)\n'
    '5. Для ИИ-суммаризации выберите модель\n\n'
    '🎤 **Голосовые сообщения:**\n'
    '1. Отправьте голосовое сообщение\n'
    '2. Бот автоматически расшифрует его в текст\n'
    '3. Поддерживаются русский и английский языки\n'
    '4. Максимальная длительность: 5 минут (300 секунд)\n'
    '5. Для длинных сообщений предлагаются варианты действий\n\n'
    '🤖 **ИИ-суммаризация:**\n'
    '• Автоматическое создание краткого содержания\n'
    '• Поддержка различных ИИ-моделей\n'
    '• Время обработки: 2-3 минуты\n\n'
    '⚠️ **Ограничения:**\n'
    '• Не чаще одного запроса в 15 секунд\n'
    '• Субтитры должны быть доступны на видео\n'
    '• ИИ-суммаризация может занять 2-3 минуты\n'
    '• Расшифровка голосовых сообщений до 5 минут\n\n'
    '🔧 **Команды:**\n'
    '/start - Начать работу\n'
    '/help - Показать эту справку\n'
    '/about - О боте\n\n'
    '💡 **Советы:**\n'
    '• Для быстрого доступа используйте кнопки\n'
    '• Длинные результаты отправляются файлами\n'
    '• При ошибках попробуйте повторить через 15 секунд'
)

ABOUT_MESSAGE = (
    '🤖 **О БОТЕ**\n\n'
    '**YouTube Subtitle Bot** - это умный помощник для работы с YouTube-контентом.\n\n'
    '🎯 **Наша миссия:**\n'
    'Сделать YouTube-контент более доступным и удобным для изучения.\n\n'
    '✨ **Возможности:**\n'
    '• 📺 Извлечение субтитров с любого YouTube-видео\n'
    '• 🌍 Поддержка множества языков\n'
    '• 🤖 ИИ-суммаризация для быстрого понимания\n'
    '• 🎤 Расшифровка голосовых сообщений\n'
    '• 📊 Статистика и аналитика\n\n'
    '🛠 **Технологии:**\n'
    '• YouTube Transcript API\n'
    '• ИИ-модели для суммаризации\n'
    '• Голосовое распознавание\n'
    '• Telegram Bot API\n\n'
    '📈 **Статистика:**\n'
    '• Поддержка 100+ языков\n'
    '• Быстрая обработка\n'
    '• Надежная работа\n\n'
    '💬 **Поддержка:**\n'
    'При возникновении проблем используйте /help\n\n'
    '🚀 **Версия:** 2.0\n'
    '📅 **Обновлено:** 2024'
)

INFO_MESSAGE = (
    'ℹ️ **КРАТКАЯ ИНФОРМАЦИЯ**\n\n'
    '🎯 **Что умеет бот:**\n'
    '• 📺 Получать субтитры с YouTube-видео\n'
    '• 🤖 Создавать ИИ-суммаризацию\n'
    '• 🎤 Расшифровывать голосовые сообщения\n'
    '• 🌍 Поддерживать множество языков\n\n'
    '⚡ **Быстрый старт:**\n'
    '1. Отправьте ссылку на YouTube-видео\n'
    '2. Выберите язык и действие\n'
    '3. Получите результат!\n\n'
    '🎤 **Голосовые сообщения:**\n'
    'Просто отправьте голосовое сообщение\n'
    'Максимум: 5 минут\n\n'
    '⏱️ **Ограничения:**\n'
    '• Не чаще 1 запроса в 15 секунд\n'
    '• ИИ-суммаризация: 2-3 минуты\n'
    '• Голос: до 5 минут\n\n'
    '💡 **Советы:**\n'
    '• Используйте кнопки для удобства\n'
    '• Длинные результаты отправляются файлами\n'
    '• При ошибках ждите 15 секунд\n\n'
    '📚 **Подробнее:** /help'
)

# --- Вспомогательные функции ---
def extract_video_id(text):
    match = re.search(YOUTUBE_REGEX, text)
    return match.group(1) if match else None

def sanitize_filename(filename):
    """Создает безопасное имя файла, убирая недопустимые символы"""
    # Убираем недопустимые символы для имен файлов
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    
    # Заменяем множественные пробелы и дефисы
    filename = re.sub(r'\s+', ' ', filename)
    filename = re.sub(r'-+', '-', filename)
    
    # Ограничиваем длину имени файла
    if len(filename) > 100:
        filename = filename[:97] + '...'
    
    return filename.strip()

async def get_video_title(video_id: str) -> str:
    """Получает название видео с YouTube"""
    try:
        # Используем oEmbed API для получения информации о видео
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        
        async with asyncio.Lock():  # Предотвращаем одновременные запросы
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            title = data.get('title', 'Unknown Video')
            logger.info(f"✅ Получено название видео: {title}")
            return title
            
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить название видео {video_id}: {e}")
        return f"Video_{video_id}"

async def create_filename(video_id: str, file_type: str, lang_code: str = None, format_str: str = None) -> str:
    """Создает информативное имя файла"""
    try:
        # Получаем название видео
        video_title = await get_video_title(video_id)
        safe_title = sanitize_filename(video_title)
        
        # Формируем имя файла
        filename_parts = [safe_title]
        
        if lang_code:
            filename_parts.append(f"[{lang_code}]")
        
        if format_str:
            format_short = "time" if "метками" in format_str else "plain"
            filename_parts.append(f"[{format_short}]")
        
        filename_parts.append(f"[{file_type}]")
        
        filename = " - ".join(filename_parts) + ".txt"
        
        logger.info(f"📝 Создано имя файла: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания имени файла: {e}")
        # Fallback к старому формату
        fallback_parts = [file_type, video_id]
        if lang_code:
            fallback_parts.append(lang_code)
        return f"{'_'.join(fallback_parts)}.txt"

async def rate_limit_check(user_id: int) -> bool:
    """Check if user is within rate limits"""
    now = time.time()
    last_time = request_timestamps.get(user_id, 0)
    
    if now - last_time < MIN_REQUEST_INTERVAL:
        return False
    
    request_timestamps[user_id] = now
    return True

async def global_rate_limit_check() -> bool:
    """Check global rate limiting to prevent API abuse"""
    global global_last_request
    now = time.time()
    
    async with global_request_lock:
        if now - global_last_request < 2:  # Minimum 2 seconds between any requests
            return False
        global_last_request = now
        return True

async def get_transcript_with_retry(video_id: str, languages: list, max_retries: int = MAX_RETRIES) -> tuple:
    """
    Get transcript with exponential backoff retry logic and fallback methods
    Returns: (transcript_data, success, error_message)
    """
    logger.info(f"🔄 Начинаю получение субтитров для {video_id}, языки: {languages}, попытка 1/{max_retries}")
    
    # Сначала попробуем получить список всех доступных субтитров
    try:
        logger.info(f"📋 Получаю полный список субтитров для анализа")
        ytt_api = YouTubeTranscriptApi()
        list_transcripts = ytt_api.list(video_id)
        available_languages = [t.language_code for t in list_transcripts]
        logger.info(f"🌍 Доступные языки: {available_languages}")
        
        # Если запрошенный язык недоступен, попробуем альтернативы
        if languages[0] not in available_languages:
            fallback_languages = ['en', 'ru', 'auto']  # Приоритетные языки для fallback
            for fallback_lang in fallback_languages:
                if fallback_lang in available_languages:
                    logger.info(f"🔄 Запрошенный язык {languages[0]} недоступен, использую fallback: {fallback_lang}")
                    languages = [fallback_lang]
                    break
            else:
                # Если нет подходящих fallback, используем первый доступный
                if available_languages:
                    logger.info(f"🔄 Использую первый доступный язык: {available_languages[0]}")
                    languages = [available_languages[0]]
                else:
                    return None, False, "Субтитры недоступны для этого видео."
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить список субтитров: {e}")
        # Продолжаем с исходными языками
    
    for attempt in range(max_retries):
        try:
            logger.info(f"📡 Попытка {attempt + 1}/{max_retries}: проверка глобального rate limit")
            # Check global rate limit
            if not await global_rate_limit_check():
                logger.info(f"⏳ Глобальный rate limit активен, жду 2 секунды")
                await asyncio.sleep(2)
                continue
                
            logger.info(f"🌐 Выполняю запрос к YouTube API для получения субтитров")
            
            # Попробуем разные методы получения субтитров
            transcript = None
            
            # Метод 1: Прямой запрос
            try:
                ytt_api = YouTubeTranscriptApi()
                transcript = ytt_api.fetch(video_id, languages=languages)
                logger.info(f"✅ Успешно получены субтитры методом 1: {len(transcript)} строк")
            except Exception as e1:
                logger.warning(f"⚠️ Метод 1 не сработал: {e1}")
                
                # Метод 2: Попробуем получить через list_transcripts
                try:
                    ytt_api = YouTubeTranscriptApi()
                    list_transcripts = ytt_api.list(video_id)
                    for lang in languages:
                        try:
                            transcript_obj = list_transcripts.find_transcript([lang])
                            transcript = transcript_obj.fetch()
                            logger.info(f"✅ Успешно получены субтитры методом 2: {len(transcript)} строк")
                            break
                        except:
                            continue
                except Exception as e2:
                    logger.warning(f"⚠️ Метод 2 не сработал: {e2}")
                    
                    # Метод 3: Попробуем автоматически сгенерированные субтитры
                    try:
                        ytt_api = YouTubeTranscriptApi()
                        transcript = ytt_api.fetch(video_id, languages=['auto'])
                        logger.info(f"✅ Успешно получены автоматические субтитры: {len(transcript)} строк")
                    except Exception as e3:
                        logger.warning(f"⚠️ Метод 3 не сработал: {e3}")
            
            if transcript:
                return transcript, True, None
            else:
                raise Exception("Все методы получения субтитров не сработали")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ошибка при получении субтитров (попытка {attempt + 1}/{max_retries}): {error_msg}")
            
            # Handle specific error types
            if "Too Many Requests" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Rate limit hit for video {video_id}, attempt {attempt + 1}/{max_retries}, waiting {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None, False, f"Превышен лимит запросов к YouTube. Попробуйте позже (через 5-10 минут)."
            
            elif "TranscriptsDisabled" in error_msg:
                return None, False, "У этого видео субтитры отключены."
            
            elif "NoTranscriptFound" in error_msg:
                return None, False, "Субтитры не найдены для этого видео."
            
            elif "Video unavailable" in error_msg:
                return None, False, "Видео недоступно или удалено."
            
            elif "no element found" in error_msg:
                if attempt < max_retries - 1:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(f"XML parsing error for {video_id}, attempt {attempt + 1}/{max_retries}: {error_msg}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None, False, "Проблема с получением субтитров. Возможно, субтитры автоматически сгенерированы и временно недоступны."
            
            else:
                if attempt < max_retries - 1:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Error getting transcript for {video_id}, attempt {attempt + 1}/{max_retries}: {error_msg}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None, False, f"Ошибка при получении субтитров: {error_msg}"
    
    return None, False, "Неизвестная ошибка при получении субтитров."

async def get_available_transcripts_with_retry(video_id: str, max_retries: int = MAX_RETRIES) -> tuple:
    """
    Get available transcripts list with retry logic
    Returns: (transcripts_list, success, error_message)
    """
    logger.info(f"🔄 Начинаю получение списка субтитров для {video_id}, попытка 1/{max_retries}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"📡 Попытка {attempt + 1}/{max_retries}: проверка глобального rate limit")
            # Check global rate limit
            if not await global_rate_limit_check():
                logger.info(f"⏳ Глобальный rate limit активен, жду 2 секунды")
                await asyncio.sleep(2)
                continue
                
            logger.info(f"🌐 Выполняю запрос к YouTube API для получения списка субтитров")
            ytt_api = YouTubeTranscriptApi()
            list_transcripts = ytt_api.list(video_id)
            logger.info(f"✅ Успешно получен список субтитров от YouTube API")
            return list(list_transcripts), True, None
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ошибка при получении списка субтитров (попытка {attempt + 1}/{max_retries}): {error_msg}")
            
            if "Too Many Requests" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    logger.warning(f"Rate limit hit for video {video_id} (list), attempt {attempt + 1}/{max_retries}, waiting {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None, False, f"Превышен лимит запросов к YouTube. Попробуйте позже (через 5-10 минут)."
            
            elif "Video unavailable" in error_msg:
                return None, False, "Видео недоступно или удалено."
            
            else:
                if attempt < max_retries - 1:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Error listing transcripts for {video_id}, attempt {attempt + 1}/{max_retries}: {error_msg}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None, False, f"Ошибка при получении списка субтитров: {error_msg}"
    
    return None, False, "Неизвестная ошибка при получении списка субтитров."

def build_language_keyboard(list_transcripts):
    buttons = []
    for transcript in list_transcripts:
        lang_code = transcript.language_code
        lang_name = transcript.language
        buttons.append([InlineKeyboardButton(f'{lang_name} ({lang_code})', callback_data=f'lang_{lang_code}')])
    return InlineKeyboardMarkup(buttons)

def build_action_keyboard():
    """Выбор действия: только субтитры или с ИИ-суммаризацией"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📄 Только субтитры', callback_data='action_subtitles')],
        [InlineKeyboardButton('🤖 Субтитры + ИИ-суммаризация', callback_data='action_ai_summary')],
        [InlineKeyboardButton('🔮 Только ИИ-суммаризация', callback_data='action_only_summary')]
    ])

def build_format_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('С временными метками', callback_data='format_with_time')],
        [InlineKeyboardButton('Без временных меток', callback_data='format_plain')]
    ])

def build_model_keyboard():
    """Выбор ИИ-модели для суммаризации"""
    models = summarizer.get_available_models()
    buttons = []
    for i, model in enumerate(models[:6]):  # Показываем первые 6 моделей
        buttons.append([InlineKeyboardButton(f'🤖 {model}', callback_data=f'model_{i}')])
    buttons.append([InlineKeyboardButton('⚡ Быстрый выбор (первая доступная)', callback_data='model_auto')])
    return InlineKeyboardMarkup(buttons)

def build_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📺 Получить субтитры', callback_data='get_subs')],
        [InlineKeyboardButton('🎤 Расшифровать голос', callback_data='voice_info')],
        [InlineKeyboardButton('📚 Помощь', callback_data='help')],
        [InlineKeyboardButton('ℹ️ Информация', callback_data='info')],
        [InlineKeyboardButton('🤖 О боте', callback_data='about')]
    ])

def format_subtitles(transcript, with_time=False):
    if with_time:
        return '\n'.join([
            f"[{int(item.start)//60:02}:{int(item.start)%60:02}] {item.text}" for item in transcript
        ])
    else:
        return '\n'.join([item.text for item in transcript])

# --- Хендлеры ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(START_MESSAGE, reply_markup=build_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE, reply_markup=build_main_keyboard())

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_MESSAGE, reply_markup=build_main_keyboard())

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(INFO_MESSAGE, reply_markup=build_main_keyboard())

async def subs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '📺 **ПОЛУЧЕНИЕ СУБТИТРОВ**\n\n'
        'Отправьте ссылку на YouTube-видео, и я помогу вам получить субтитры!\n\n'
        '🎯 **Что можно сделать:**\n'
        '• 📄 Получить только субтитры\n'
        '• 🤖 Субтитры + ИИ-суммаризация\n'
        '• 🔮 Только ИИ-суммаризация\n\n'
        '📝 **Форматы:**\n'
        '• С временными метками\n'
        '• Без временных меток\n\n'
        '🚀 **Отправьте ссылку прямо сейчас!**'
    )

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🎤 **РАСШИФРОВКА ГОЛОСОВЫХ СООБЩЕНИЙ**\n\n'
        'Отправьте голосовое сообщение, и я расшифрую его в текст!\n\n'
        '✅ **Поддерживается:**\n'
        '• Русский язык\n'
        '• Английский язык\n'
        '• Длительность до 5 минут\n\n'
        '⚠️ **Ограничения:**\n'
        '• Максимум 5 минут (300 секунд)\n'
        '• Хорошее качество звука\n'
        '• Четкая речь\n\n'
        '🚀 **Отправьте голосовое сообщение прямо сейчас!**'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🔍 Получено сообщение от пользователя {user_id}")
    
    # Check user rate limit
    if not await rate_limit_check(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - request_timestamps.get(user_id, 0))
        logger.warning(f"⚠️ Rate limit для пользователя {user_id}, осталось {int(remaining_time)} секунд")
        await update.message.reply_text(f'⚠️ Слишком много запросов. Подождите {int(remaining_time)} секунд.')
        return

    text = update.message.text.strip()
    logger.info(f"📝 Текст сообщения: {text[:50]}...")
    
    video_id = extract_video_id(text)
    logger.info(f"🎬 Извлеченный video_id: {video_id}")
    
    if not video_id:
        logger.warning(f"❌ Не удалось извлечь video_id из текста: {text}")
        await update.message.reply_text('Пожалуйста, пришлите корректную ссылку на YouTube-видео или его ID.')
        return
    
    # Show processing message
    logger.info(f"🔄 Начинаю обработку видео {video_id}")
    processing_msg = await update.message.reply_text('🔄 Получаю информацию о субтитрах...')
    
    # Get available transcripts with retry logic
    logger.info(f"📋 Запрашиваю список доступных субтитров для {video_id}")
    list_transcripts, success, error_msg = await get_available_transcripts_with_retry(video_id)
    
    if not success:
        logger.error(f"❌ Ошибка при получении списка субтитров: {error_msg}")
        await processing_msg.edit_text(f'❌ {error_msg}')
        return
    
    logger.info(f"✅ Получен список субтитров: {len(list_transcripts)} языков")
    
    if not list_transcripts:
        logger.warning(f"❌ Субтитры не найдены для видео {video_id}")
        await processing_msg.edit_text('❌ Субтитры не найдены для этого видео.')
        return
    
    # Save video info for user
    context.user_data['video_id'] = video_id
    context.user_data['list_transcripts'] = list_transcripts
    
    # If only one language - offer action directly
    if len(list_transcripts) == 1:
        lang_code = list_transcripts[0].language_code
        context.user_data['lang_code'] = lang_code
        logger.info(f"🎯 Один язык найден: {lang_code}")
        await processing_msg.edit_text(
            f'✅ Выбран язык: {list_transcripts[0].language} ({lang_code}). Что хотите получить?',
            reply_markup=build_action_keyboard()
        )
    else:
        logger.info(f"🌍 Найдено {len(list_transcripts)} языков, предлагаю выбор")
        await processing_msg.edit_text('✅ Выберите язык субтитров:', reply_markup=build_language_keyboard(list_transcripts))

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает голосовые сообщения"""
    user_id = update.effective_user.id
    
    # Check user rate limit
    if not await rate_limit_check(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - request_timestamps.get(user_id, 0))
        await update.message.reply_text(f'⚠️ Слишком много запросов. Подождите {int(remaining_time)} секунд.')
        return
    
    # Check if voice transcription is available
    if not voice_transcriber.is_available():
        await update.message.reply_text(
            '❌ Расшифровка голосовых сообщений недоступна.\n'
            'Необходимо настроить SONIOX_API_KEY в переменных окружения.'
        )
        return
    
    voice = update.message.voice
    if not voice:
        await update.message.reply_text('❌ Не удалось получить голосовое сообщение.')
        return
    
    # Check voice message duration and offer options for long messages
    if voice.duration > 300:  # Более 5 минут
        await update.message.reply_text(
            '⚠️ **Голосовое сообщение слишком длинное**\n\n'
            f'📊 Длительность: {voice.duration} секунд ({voice.duration//60} мин {voice.duration%60} сек)\n'
            '📏 Максимальная поддержка: 5 минут\n\n'
            '💡 **Варианты решения:**\n'
            '• 🎤 Отправьте сообщение короче 5 минут\n'
            '• ✂️ Разделите на несколько частей\n'
            '• 📝 Используйте текстовое сообщение\n'
            '• 🎯 Отправьте только важную часть\n\n'
            '🔄 **Или попробуйте сейчас** (может работать, но без гарантий):',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🎤 Попробовать расшифровать', callback_data=f'voice_force_{voice.file_id}')],
                [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
            ])
        )
        return
    elif voice.duration > 180:  # Более 3 минут - предупреждение
        await update.message.reply_text(
            '⚠️ **Длинное голосовое сообщение**\n\n'
            f'📊 Длительность: {voice.duration} секунд ({voice.duration//60} мин {voice.duration%60} сек)\n'
            '⏱️ Обработка может занять 2-3 минуты\n\n'
            '💡 **Рекомендации:**\n'
            '• Для лучшего качества разделите на части\n'
            '• Убедитесь в хорошем качестве звука\n\n'
            '🔄 **Продолжить обработку?**',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('✅ Продолжить', callback_data=f'voice_continue_{voice.file_id}')],
                [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
            ])
        )
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text('🎤 Расшифровываю голосовое сообщение...')
    
    try:
        # Download voice file
        file = await context.bot.get_file(voice.file_id)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download the file
        await file.download_to_drive(temp_path)
        
        # Transcribe voice message
        success, text, stats = await voice_transcriber.transcribe_voice_message(voice, temp_path)
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if success:
            # Format response
            response_parts = []
            response_parts.append("🎤 **РАСШИФРОВКА ГОЛОСОВОГО СООБЩЕНИЯ:**")
            response_parts.append(text)
            
            # Add statistics
            if stats:
                response_parts.append(f"\n📊 **Статистика:**")
                response_parts.append(f"• Длительность: {voice.duration} секунд")
                response_parts.append(f"• Символов в тексте: {stats.get('text_length', 0)}")
                response_parts.append(f"• Токенов распознано: {stats.get('tokens_count', 0)}")
                response_parts.append(f"• Средняя уверенность: {stats.get('confidence_avg', 0):.2f}")
            
            full_response = "\n".join(response_parts)
            
            # Send response
            if len(full_response) <= 4000:
                await processing_msg.edit_text(full_response, parse_mode='Markdown')
            else:
                await processing_msg.edit_text("📄 Расшифровка слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                # Создаем информативное имя файла для голосового сообщения
                timestamp = int(time.time())
                file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                await update.message.reply_document(InputFile(file))
        else:
            await processing_msg.edit_text(f'❌ {text}')
            
    except Exception as e:
        logger.error(f'Ошибка при обработке голосового сообщения: {e}')
        await processing_msg.edit_text(f'❌ Ошибка при обработке голосового сообщения: {str(e)}')

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.replace('lang_', '')
    context.user_data['lang_code'] = lang_code
    await query.edit_message_text(f'Выбран язык: {lang_code}. Что хотите получить?', reply_markup=build_action_keyboard())

async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace('action_', '')
    context.user_data['action'] = action
    
    if action == 'subtitles':
        # Только субтитры - сразу выбираем формат
        await query.edit_message_text('Выберите формат субтитров:', reply_markup=build_format_keyboard())
    elif action in ['ai_summary', 'only_summary']:
        # Нужна ИИ-суммаризация - выбираем модель
        await query.edit_message_text('Выберите ИИ-модель для суммаризации:', reply_markup=build_model_keyboard())

async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'model_auto':
        model_index = 0  # Первая модель по умолчанию
    else:
        model_index = int(query.data.replace('model_', ''))
    
    context.user_data['model_index'] = model_index
    
    action = context.user_data.get('action')
    if action == 'ai_summary':
        # Субтитры + ИИ: нужен формат субтитров
        await query.edit_message_text('Выберите формат субтитров:', reply_markup=build_format_keyboard())
    else:
        # Только ИИ-суммаризация: обрабатываем сразу
        context.user_data['with_time'] = False  # Для суммаризации формат не важен
        await process_request(query, context)

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with_time = query.data == 'format_with_time'
    context.user_data['with_time'] = with_time
    await process_request(query, context)

async def process_request(query, context):
    """Обрабатывает запрос пользователя: получает субтитры и/или создает суммаризацию"""
    video_id = context.user_data.get('video_id')
    lang_code = context.user_data.get('lang_code')
    action = context.user_data.get('action')
    with_time = context.user_data.get('with_time', False)
    model_index = context.user_data.get('model_index', 0)
    
    logger.info(f"🔄 Обрабатываю запрос: video_id={video_id}, lang_code={lang_code}, action={action}, with_time={with_time}")
    
    if not video_id or not lang_code:
        logger.error(f"❌ Отсутствуют video_id или lang_code: video_id={video_id}, lang_code={lang_code}")
        await query.edit_message_text('❌ Ошибка: не найдено видео или язык. Начните заново.')
        return
    
    # Show processing message
    logger.info(f"📝 Показываю сообщение о получении субтитров")
    await query.edit_message_text('🔄 Получаю субтитры...')
    
    # Get transcript with retry logic
    logger.info(f"🎬 Запрашиваю субтитры для {video_id} на языке {lang_code}")
    transcript, success, error_msg = await get_transcript_with_retry(video_id, [lang_code])
    
    if not success:
        logger.error(f"❌ Не удалось получить субтитры: {error_msg}")
        await query.edit_message_text(f'❌ {error_msg}')
        return
    
    logger.info(f"✅ Субтитры получены успешно: {len(transcript)} строк")
    subtitles = format_subtitles(transcript, with_time=with_time)
    raw_subtitles = format_subtitles(transcript, with_time=False)  # Для ИИ без меток времени
    
    format_str = 'с метками' if with_time else 'без меток'
    
    if action == 'subtitles':
        # Только субтитры
        logger.info(f"📄 Отправляю только субтитры")
        await send_subtitles(query, subtitles, video_id, lang_code, format_str, len(transcript))
    
    elif action in ['ai_summary', 'only_summary']:
        # ИИ-суммаризация
        logger.info(f"🤖 Начинаю ИИ-суммаризацию")
        await query.edit_message_text('🤖 Создаю ИИ-суммаризацию... Это может занять до 2-3 минут.')
        
        try:
            summary, stats = await summarizer.summarize_text(raw_subtitles, model_index)
            logger.info(f"✅ ИИ-суммаризация завершена успешно")
            
            # Формируем ответ
            response_parts = []
            
            if action == 'ai_summary':
                # Субтитры + суммаризация
                response_parts.append("📄 **СУБТИТРЫ:**")
                if len(subtitles) <= 2000:
                    response_parts.append(subtitles[:2000])
                    if len(subtitles) > 2000:
                        response_parts.append("... (слишком длинные, полная версия в файле)")
                else:
                    response_parts.append("(Субтитры слишком длинные, отправлены файлом)")
            
            response_parts.append("\n🤖 **ИИ-СУММАРИЗАЦИЯ:**")
            response_parts.append(summary)
            
            # Статистика
            response_parts.append(f"\n📊 **Статистика:**")
            response_parts.append(f"• Модель: {stats.get('model', 'неизвестно')}")
            response_parts.append(f"• Строк субтитров: {len(transcript)}")
            response_parts.append(f"• Обработано частей: {stats.get('chunks', 0)}")
            response_parts.append(f"• Исходный размер: {stats.get('original_length', 0)} символов")
            response_parts.append(f"• Размер суммаризации: {stats.get('summary_length', 0)} символов")
            
            full_response = "\n".join(response_parts)
            
            # Отправляем ответ
            if len(full_response) <= 4000:
                await query.edit_message_text(full_response, parse_mode='Markdown')
            else:
                await query.edit_message_text("📄 Результат слишком длинный, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                # Создаем информативное имя файла для суммаризации
                filename = await create_filename(video_id, "summary", lang_code)
                file.name = filename
                await query.message.reply_document(InputFile(file))
            
            # Если нужны субтитры файлом
            if action == 'ai_summary' and len(subtitles) > 2000:
                subs_file = BytesIO(subtitles.encode('utf-8'))
                # Создаем информативное имя файла для субтитров
                subs_filename = await create_filename(video_id, "subtitles", lang_code, format_str)
                subs_file.name = subs_filename
                await query.message.reply_document(
                    InputFile(subs_file), 
                    caption=f'Полные субтитры\nФормат: {format_str}'
                )
            
        except Exception as ai_error:
            logger.error(f'Ошибка ИИ-суммаризации: {ai_error}')
            await query.edit_message_text(f'❌ Ошибка при создании ИИ-суммаризации: {ai_error}')

async def send_subtitles(query, subtitles, video_id, lang_code, format_str, transcript_count):
    """Отправляет только субтитры"""
    stat_msg = f'Язык: {lang_code}\nСтрок: {transcript_count}\nФормат: {format_str}'
    
    if len(subtitles) <= 4000:
        await query.edit_message_text(subtitles)
        await query.message.reply_text(stat_msg)
    else:
        file = BytesIO(subtitles.encode('utf-8'))
        # Создаем информативное имя файла
        filename = await create_filename(video_id, "subtitles", lang_code, format_str)
        file.name = filename
        await query.edit_message_text('Субтитры слишком длинные, отправляю файлом.')
        await query.message.reply_document(InputFile(file), caption=stat_msg)

async def main_keyboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'help':
        await query.edit_message_text(HELP_MESSAGE, reply_markup=build_main_keyboard())
    elif query.data == 'get_subs':
        await query.edit_message_text('Пришлите ссылку на YouTube-видео или его ID.')
    elif query.data == 'about':
        await query.edit_message_text(ABOUT_MESSAGE, reply_markup=build_main_keyboard())
    elif query.data == 'info':
        await query.edit_message_text(INFO_MESSAGE, reply_markup=build_main_keyboard())
    elif query.data == 'voice_info':
        await query.edit_message_text(
            '🎤 **РАСШИФРОВКА ГОЛОСОВЫХ СООБЩЕНИЙ**\n\n'
            'Отправьте голосовое сообщение, и я расшифрую его в текст!\n\n'
            '✅ **Поддерживается:**\n'
            '• Русский язык\n'
            '• Английский язык\n'
            '• Длительность до 5 минут\n\n'
            '⚠️ **Ограничения:**\n'
            '• Максимум 5 минут (300 секунд)\n'
            '• Хорошее качество звука\n'
            '• Четкая речь\n\n'
            '🚀 **Отправьте голосовое сообщение прямо сейчас!**',
            reply_markup=build_main_keyboard()
        )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Неизвестная команда. Для справки используйте /help.', reply_markup=build_main_keyboard())

async def voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает callback'и для голосовых сообщений"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'voice_cancel':
        await query.edit_message_text('❌ Обработка голосового сообщения отменена.')
        return
    
    elif query.data.startswith('voice_force_'):
        file_id = query.data.replace('voice_force_', '')
        await query.edit_message_text('⚠️ **Попытка обработки длинного сообщения**\n\n🔄 Обрабатываю... Это может занять до 5 минут.')
        await process_voice_message_by_file_id(update, context, file_id, force=True)
    
    elif query.data.startswith('voice_continue_'):
        file_id = query.data.replace('voice_continue_', '')
        await query.edit_message_text('🔄 Обрабатываю длинное голосовое сообщение...')
        await process_voice_message_by_file_id(update, context, file_id, force=False)

async def process_voice_message_by_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str, force: bool = False):
    """Обрабатывает голосовое сообщение по file_id"""
    user_id = update.effective_user.id
    
    try:
        # Download voice file
        file = await context.bot.get_file(file_id)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download the file
        await file.download_to_drive(temp_path)
        
        # Create a mock voice object for the transcriber
        class MockVoice:
            def __init__(self, file_id, duration=300):
                self.file_id = file_id
                self.duration = duration
        
        voice = MockVoice(file_id, duration=300 if force else 180)
        
        # Transcribe voice message
        success, text, stats = await voice_transcriber.transcribe_voice_message(voice, temp_path)
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if success:
            # Format response
            response_parts = []
            response_parts.append("🎤 **РАСШИФРОВКА ГОЛОСОВОГО СООБЩЕНИЯ:**")
            if force:
                response_parts.append("⚠️ *Обработано в экспериментальном режиме*")
            response_parts.append(text)
            
            # Add statistics
            if stats:
                response_parts.append(f"\n📊 **Статистика:**")
                response_parts.append(f"• Длительность: {voice.duration} секунд")
                response_parts.append(f"• Символов в тексте: {stats.get('text_length', 0)}")
                response_parts.append(f"• Токенов распознано: {stats.get('tokens_count', 0)}")
                response_parts.append(f"• Средняя уверенность: {stats.get('confidence_avg', 0):.2f}")
            
            full_response = "\n".join(response_parts)
            
            # Send response
            if len(full_response) <= 4000:
                await update.callback_query.edit_message_text(full_response, parse_mode='Markdown')
            else:
                await update.callback_query.edit_message_text("📄 Расшифровка слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                # Создаем информативное имя файла для голосового сообщения
                timestamp = int(time.time())
                file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                await update.callback_query.message.reply_document(InputFile(file))
        else:
            await update.callback_query.edit_message_text(f'❌ {text}')
            
    except Exception as e:
        logger.error(f'Ошибка при обработке голосового сообщения по file_id: {e}')
        await update.callback_query.edit_message_text(f'❌ Ошибка при обработке голосового сообщения: {str(e)}')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('about', about_command))
    app.add_handler(CommandHandler('info', info_command))
    app.add_handler(CommandHandler('subs', subs_command))
    app.add_handler(CommandHandler('voice', voice_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r'^lang_'))
    app.add_handler(CallbackQueryHandler(action_callback, pattern=r'^action_'))
    app.add_handler(CallbackQueryHandler(model_callback, pattern=r'^model_'))
    app.add_handler(CallbackQueryHandler(format_callback, pattern=r'^format_'))
    app.add_handler(CallbackQueryHandler(main_keyboard_callback, pattern=r'^(help|get_subs|about|info|voice_info)$'))
    app.add_handler(CallbackQueryHandler(voice_callback, pattern=r'^(voice_force_|voice_continue_|voice_cancel)$'))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    print('Бот запущен!')
    app.run_polling() 