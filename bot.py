import os
import re
import logging
import time
import asyncio
import random
import tempfile
from io import BytesIO
from pathlib import Path
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv
from summarizer import TextSummarizer
from voice_transcriber import VoiceTranscriber
from mind_map_generator import MindMapGenerator
import requests
import traceback
from collections import defaultdict
from typing import List, Dict, Optional

# Создаем директорию для логов если её нет
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Включаем логирование с правильной кодировкой
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8-sig', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Отключаем логи от сторонних библиотек для чистоты логов
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Добавляем обработчик для очистки старых логов
def setup_log_rotation():
    """Настраивает ротацию логов для предотвращения их разрастания"""
    import os
    from datetime import datetime, timedelta
    
    log_file = 'logs/bot.log'
    if os.path.exists(log_file):
        # Проверяем размер файла (если больше 10MB)
        if os.path.getsize(log_file) > 10 * 1024 * 1024:
            # Создаем backup с датой
            backup_name = f'logs/bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            try:
                os.rename(log_file, backup_name)
                logger.info(f"Лог файл переименован в {backup_name}")
            except Exception as e:
                logger.error(f"Ошибка при ротации лога: {e}")

# Вызываем настройку ротации при запуске
setup_log_rotation()

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')  # ID чата администратора для уведомлений об ошибках
ERROR_NOTIFICATIONS_ENABLED = os.getenv('ERROR_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'

# Инициализируем суммаризатор, транскрайбер и mind map генератор
summarizer = TextSummarizer()
voice_transcriber = VoiceTranscriber()

# Инициализируем mind map генератор если есть API ключ
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if OPENROUTER_API_KEY:
    mind_map_generator = MindMapGenerator(OPENROUTER_API_KEY)
    MIND_MAP_AVAILABLE = True
    logger.info("✅ Mind Map Generator инициализирован")
else:
    mind_map_generator = None
    MIND_MAP_AVAILABLE = False
    logger.warning("⚠️ Mind Map Generator недоступен - отсутствует OPENROUTER_API_KEY")

YOUTUBE_REGEX = r"(?:v=|youtu\.be/|youtube\.com/embed/|youtube\.com/watch\?v=)?([\w-]{11})"

def format_transcription_text(text: str) -> str:
    """
    Форматирует текст транскрипции для лучшей читаемости
    
    Args:
        text: исходный текст транскрипции
        
    Returns:
        отформатированный текст
    """
    if not text:
        return text
    
    # Убираем лишние пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Разбиваем на предложения
    sentences = re.split(r'([.!?]+)', text)
    
    # Форматируем предложения
    formatted_sentences = []
    for i in range(0, len(sentences), 2):
        if i + 1 < len(sentences):
            sentence = sentences[i].strip()
            punctuation = sentences[i + 1]
            
            # Делаем первую букву заглавной
            if sentence:
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                formatted_sentences.append(sentence + punctuation)
        else:
            # Последнее предложение без знака препинания
            sentence = sentences[i].strip()
            if sentence:
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                formatted_sentences.append(sentence)
    
    # Объединяем предложения
    formatted_text = ' '.join(formatted_sentences)
    
    # Если нет пунктуации, добавляем точки для лучшего разбиения
    if not re.search(r'[.!?]', formatted_text):
        # Разбиваем на фразы по длине и добавляем точки
        words = formatted_text.split()
        phrases = []
        current_phrase = ""
        
        for word in words:
            if len(current_phrase + " " + word) > 15:  # Фраза не более 15 слов
                if current_phrase:
                    phrases.append(current_phrase.strip() + ".")
                    current_phrase = word
                else:
                    current_phrase = word
            else:
                current_phrase += (" " + word) if current_phrase else word
        
        if current_phrase:
            phrases.append(current_phrase.strip() + ".")
        
        formatted_text = " ".join(phrases)
    
    # Умное разбиение на абзацы
    # Ищем естественные паузы и разбиваем текст
    paragraphs = []
    current_paragraph = ""
    
    # Разбиваем на предложения для лучшего контроля
    sentence_pattern = r'[^.!?]+[.!?]+'
    sentences_list = re.findall(sentence_pattern, formatted_text)
    
    for sentence in sentences_list:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Если текущий абзац станет слишком длинным, начинаем новый
        if len(current_paragraph + " " + sentence) > 120:
            if current_paragraph:
                paragraphs.append(current_paragraph.strip())
                current_paragraph = sentence
            else:
                current_paragraph = sentence
        else:
            current_paragraph += (" " + sentence) if current_paragraph else sentence
    
    # Добавляем последний абзац
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())
    
    # Если абзацы слишком длинные, разбиваем их на строки
    formatted_paragraphs = []
    for paragraph in paragraphs:
        if len(paragraph) > 100:
            # Разбиваем длинный абзац на строки
            words = paragraph.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line + " " + word) <= 80:
                    current_line += (" " + word) if current_line else word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            formatted_paragraphs.append('\n'.join(lines))
        else:
            formatted_paragraphs.append(paragraph)
    
    return '\n\n'.join(formatted_paragraphs)

async def send_error_notification(error_type: str, error_message: str, context: str = "", user_id: int = None, additional_info: dict = None):
    """Отправляет уведомление об ошибке администратору"""
    if not ERROR_NOTIFICATIONS_ENABLED or not ADMIN_CHAT_ID:
        return
    
    # Проверяем cooldown для предотвращения спама
    current_time = time.time()
    error_key = f"{error_type}_{context}"
    
    if error_key in error_notification_cooldown:
        if current_time - error_notification_cooldown[error_key] < ERROR_NOTIFICATION_COOLDOWN:
            return  # Пропускаем уведомление из-за cooldown
    
    error_notification_cooldown[error_key] = current_time
    
    try:
        # Формируем сообщение об ошибке
        message_parts = []
        message_parts.append("🚨 УВЕДОМЛЕНИЕ ОБ ОШИБКЕ")
        message_parts.append("")
        message_parts.append(f"📋 Тип ошибки: {error_type}")
        message_parts.append(f"💬 Сообщение: {error_message}")
        
        if context:
            message_parts.append(f"📍 Контекст: {context}")
        
        if user_id:
            message_parts.append(f"👤 Пользователь: {user_id}")
        
        if additional_info:
            message_parts.append(f"📊 Дополнительная информация:")
            for key, value in additional_info.items():
                message_parts.append(f"   • {key}: {value}")
        
        message_parts.append("")
        message_parts.append(f"⏰ Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        error_message_text = "\n".join(message_parts)
        
        # Отправляем уведомление с безопасной обработкой
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Безопасная отправка без Markdown
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=error_message_text,
            parse_mode=None,  # Отключаем Markdown для избежания ошибок парсинга
            disable_web_page_preview=True
        )
        
        logger.info(f"Отправлено уведомление об ошибке администратору: {error_type}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления об ошибке: {e}")
        # Логируем детали ошибки для отладки
        logger.error(f"📊 Детали ошибки уведомления:")
        logger.error(f"   • Тип: {type(e).__name__}")
        logger.error(f"   • Сообщение: {str(e)}")
        logger.error(f"   • Контекст: отправка уведомления об ошибке")

def log_and_notify_error(error: Exception, context: str = "", user_id: int = None, additional_info: dict = None):
    """Логирует ошибку и отправляет уведомление"""
    try:
        error_type = type(error).__name__
        error_message = str(error)
        
        # Логируем ошибку с деталями
        logger.error(f"Ошибка в {context}: {error_type} - {error_message}")
        
        # Логируем детали ошибки для отладки (без stack trace, так как это может быть не исключение)
        logger.error(f"📊 Детали ошибки:")
        logger.error(f"   • Тип: {error_type}")
        logger.error(f"   • Сообщение: {error_message}")
        logger.error(f"   • Контекст: {context}")
        if user_id:
            logger.error(f"   • Пользователь: {user_id}")
        if additional_info:
            logger.error(f"   • Дополнительная информация: {additional_info}")
        
        # Отправляем уведомление асинхронно
        asyncio.create_task(send_error_notification(
            error_type=error_type,
            error_message=error_message,
            context=context,
            user_id=user_id,
            additional_info=additional_info
        ))
        
    except Exception as log_error:
        # Если произошла ошибка при логировании, записываем в базовый лог
        print(f"Критическая ошибка при логировании: {log_error}")
        print(f"Исходная ошибка: {error}")

# Enhanced rate limiting constants
MIN_REQUEST_INTERVAL = 15  # Increased from 10 to 15 seconds
MAX_RETRIES = 3
BASE_DELAY = 2  # Base delay in seconds
MAX_DELAY = 60  # Maximum delay in seconds

# Global rate limiting state
request_timestamps = {}  # Track last request time per user
global_last_request = 0  # Global rate limiting

# Voice message series grouping system
voice_series_groups = defaultdict(list)  # Group voice messages by user and series
voice_series_timeout = 300  # 5 minutes timeout for grouping voice messages
voice_series_cleanup_interval = 600  # 10 minutes cleanup interval
global_request_lock = asyncio.Lock()  # Prevent concurrent requests

# Multiple message handling system (НОВАЯ ФУНКЦИЯ)
last_text_message_time = {}  # Track last text message time per user
last_youtube_link_time = {}  # Track last YouTube link time per user
MESSAGE_IGNORE_INTERVAL = 5  # Ignore repeated messages within 5 seconds
YOUTUBE_IGNORE_INTERVAL = 10  # Ignore repeated YouTube links within 10 seconds

# Error notification tracking
error_notification_cooldown = {}  # Track last error notification time per error type
ERROR_NOTIFICATION_COOLDOWN = 300  # 5 minutes cooldown between same error notifications

# Track new users for welcome experience
new_users = set()  # Simple set to track new users

# User state tracking system (НОВАЯ ФУНКЦИЯ)
# Отслеживаем состояние пользователя для правильной обработки сообщений
user_states = {}  # Track user states: 'expecting_mind_map_text', 'normal', etc.

START_MESSAGE = (
    '👋 **Привет! Я YouTube Subtitle Bot**\n\n'
    '🎯 **Я умею:**\n'
    '• 📺 Получать субтитры с YouTube-видео\n'
    '• 🤖 Создавать краткое содержание с помощью ИИ\n'
    '• 🎤 Расшифровывать голосовые сообщения\n\n'
    '🚀 **Начните прямо сейчас:**\n'
    'Отправьте ссылку на YouTube-видео или голосовое сообщение!\n\n'
    '💡 **Нужна помощь?** Нажмите кнопку ниже 👇'
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
    '/about - О боте\n'
    '/reset - Сбросить состояние\n\n'
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

LEARN_MORE_MESSAGE = (
    '📚 **УЗНАЙТЕ БОЛЬШЕ О БОТЕ**\n\n'
    '🎯 **Как это работает:**\n'
    '1️⃣ **Отправьте ссылку** на YouTube-видео\n'
    '2️⃣ **Выберите язык** субтитров\n'
    '3️⃣ **Выберите действие:**\n'
    '   📄 Только субтитры\n'
    '   🤖 Субтитры + ИИ-суммаризация\n'
    '   🔮 Только ИИ-суммаризация\n'
    '4️⃣ **Получите результат!**\n\n'
    '🎤 **Голосовые сообщения:**\n'
    '• Просто отправьте голосовое сообщение\n'
    '• Поддерживаются русский и английский\n'
    '• Максимум 5 минут\n\n'
    '🤖 **ИИ-суммаризация:**\n'
    '• Автоматически создает краткое содержание\n'
    '• Использует современные AI-модели\n'
    '• Время обработки: 2-3 минуты\n\n'
    '⚠️ **Важные ограничения:**\n'
    '• Не чаще 1 запроса в 15 секунд\n'
    '• Субтитры должны быть доступны\n'
    '• Хорошее качество звука для голоса\n\n'
    '💡 **Советы для новичков:**\n'
    '• Начните с короткого видео\n'
    '• Используйте кнопки для навигации\n'
    '• При ошибках подождите 15 секунд\n\n'
    '🚀 **Готовы попробовать?**\n'
    'Отправьте ссылку на YouTube-видео!'
)

QUICK_HELP_MESSAGE = (
    '💡 **БЫСТРАЯ ПОМОЩЬ**\n\n'
    '❓ **Не знаете, что делать?**\n\n'
    '🎬 **Для YouTube-видео:**\n'
    '1. Скопируйте ссылку с YouTube\n'
    '2. Вставьте её в чат\n'
    '3. Выберите нужное действие\n\n'
    '🎤 **Для голосовых сообщений:**\n'
    '1. Нажмите на микрофон\n'
    '2. Запишите сообщение\n'
    '3. Отправьте - бот расшифрует\n\n'
    '🔧 **Проблемы?**\n'
    '• Убедитесь, что ссылка корректная\n'
    '• Проверьте, есть ли субтитры у видео\n'
    '• Подождите 15 секунд между запросами\n\n'
    '🚀 **Попробуйте прямо сейчас!**'
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

async def check_multiple_messages(user_id: int, message_type: str, content: str = None) -> tuple[bool, str]:
    """
    Проверяет, является ли сообщение повторным и должно ли быть проигнорировано
    
    Args:
        user_id: ID пользователя
        message_type: Тип сообщения ('text', 'youtube', 'voice')
        content: Содержимое сообщения (для YouTube ссылок)
        
    Returns:
        tuple: (should_process, warning_message)
    """
    now = time.time()
    
    if message_type == 'voice':
        # Голосовые сообщения проверяем на спам, но не блокируем полностью
        # для возможности пакетной обработки
        last_time = last_text_message_time.get(user_id, 0)
        if now - last_time < MESSAGE_IGNORE_INTERVAL:
            remaining = MESSAGE_IGNORE_INTERVAL - int(now - last_time)
            warning = (
                f'⚠️ **Слишком много голосовых сообщений**\n\n'
                f'🎤 Вы отправили несколько голосовых сообщений подряд\n'
                f'⏱️ Подождите {remaining} секунд\n'
                f'🔄 Сообщения будут обработаны пакетом\n\n'
                f'💡 **Совет:** Голосовые сообщения автоматически группируются'
            )
            return False, warning
        else:
            last_text_message_time[user_id] = now
            return True, ""
    
    elif message_type == 'text':
        last_time = last_text_message_time.get(user_id, 0)
        if now - last_time < MESSAGE_IGNORE_INTERVAL:
            remaining = MESSAGE_IGNORE_INTERVAL - int(now - last_time)
            warning = (
                f'⚠️ **Сообщение проигнорировано**\n\n'
                f'📝 Вы отправили несколько сообщений подряд\n'
                f'⏱️ Подождите {remaining} секунд\n'
                f'🔄 Обрабатывается только первое сообщение\n\n'
                f'💡 **Совет:** Отправляйте сообщения по одному'
            )
            return False, warning
        else:
            last_text_message_time[user_id] = now
            return True, ""
    
    elif message_type == 'youtube':
        last_time = last_youtube_link_time.get(user_id, 0)
        if now - last_time < YOUTUBE_IGNORE_INTERVAL:
            remaining = YOUTUBE_IGNORE_INTERVAL - int(now - last_time)
            warning = (
                f'⚠️ **YouTube ссылка проигнорирована**\n\n'
                f'🎬 Вы отправили несколько ссылок подряд\n'
                f'⏱️ Подождите {remaining} секунд\n'
                f'🔄 Обрабатывается только первая ссылка\n\n'
                f'💡 **Совет:** Отправляйте ссылки по одной'
            )
            return False, warning
        else:
            last_youtube_link_time[user_id] = now
            return True, ""
    
    return True, ""

async def global_rate_limit_check() -> bool:
    """Check global rate limiting to prevent API abuse"""
    global global_last_request
    now = time.time()
    
    async with global_request_lock:
        if now - global_last_request < 2:  # Minimum 2 seconds between any requests
            return False
        global_last_request = now
        return True

async def add_voice_to_series(user_id: int, voice_message: dict) -> str:
    """Добавляет голосовое сообщение в серию и возвращает ID серии"""
    global voice_series_groups
    
    now = time.time()
    series_id = f"series_{user_id}_{int(now // voice_series_timeout)}"
    
    # Добавляем сообщение в серию
    voice_series_groups[series_id].append({
        'voice': voice_message,
        'timestamp': now,
        'user_id': user_id
    })
    
    logger.info(f"🎤 Добавлено голосовое сообщение в серию {series_id} для пользователя {user_id}")
    return series_id

async def get_voice_series(user_id: int, series_id: str) -> List[dict]:
    """Получает все голосовые сообщения из серии"""
    global voice_series_groups
    
    if series_id in voice_series_groups:
        # Фильтруем только сообщения данного пользователя
        user_messages = [msg for msg in voice_series_groups[series_id] if msg['user_id'] == user_id]
        return user_messages
    return []

async def cleanup_expired_voice_series():
    """Очищает устаревшие серии голосовых сообщений"""
    global voice_series_groups
    
    now = time.time()
    expired_series = []
    
    for series_id, messages in voice_series_groups.items():
        if not messages:
            expired_series.append(series_id)
            continue
            
        # Проверяем, есть ли сообщения старше timeout
        oldest_message = min(messages, key=lambda x: x['timestamp'])
        if now - oldest_message['timestamp'] > voice_series_timeout:
            expired_series.append(series_id)
    
    # Удаляем устаревшие серии
    for series_id in expired_series:
        del voice_series_groups[series_id]
        logger.info(f"🗑️ Удалена устаревшая серия голосовых сообщений: {series_id}")
    
    if expired_series:
        logger.info(f"🧹 Очищено {len(expired_series)} устаревших серий голосовых сообщений")

async def cleanup_expired_message_tracking():
    """Очищает устаревшие записи отслеживания сообщений"""
    global last_text_message_time, last_youtube_link_time
    
    now = time.time()
    cleanup_threshold = 3600  # 1 час
    
    # Очищаем старые записи для текстовых сообщений
    expired_text_users = [
        user_id for user_id, timestamp in last_text_message_time.items()
        if now - timestamp > cleanup_threshold
    ]
    for user_id in expired_text_users:
        del last_text_message_time[user_id]
    
    # Очищаем старые записи для YouTube ссылок
    expired_youtube_users = [
        user_id for user_id, timestamp in last_youtube_link_time.items()
        if now - timestamp > cleanup_threshold
    ]
    for user_id in expired_youtube_users:
        del last_youtube_link_time[user_id]
    
    if expired_text_users or expired_youtube_users:
        logger.info(f"🧹 Очищено {len(expired_text_users)} текстовых и {len(expired_youtube_users)} YouTube записей отслеживания")

async def process_voice_series(user_id: int, series_id: str, bot) -> tuple:
    """Обрабатывает серию голосовых сообщений и возвращает объединенный текст"""
    global voice_series_groups
    
    if series_id not in voice_series_groups:
        return False, "Серия голосовых сообщений не найдена", {}
    
    messages = [msg for msg in voice_series_groups[series_id] if msg['user_id'] == user_id]
    if not messages:
        return False, "В серии нет голосовых сообщений", {}
    
    # Сортируем сообщения по времени
    messages.sort(key=lambda x: x['timestamp'])
    
    all_texts = []
    total_duration = 0
    total_tokens = 0
    total_confidence = 0
    successful_transcriptions = 0
    
    logger.info(f"🎤 Обрабатываю серию из {len(messages)} голосовых сообщений для пользователя {user_id}")
    
    for i, msg in enumerate(messages):
        voice = msg['voice']
        logger.info(f"🎤 Обрабатываю сообщение {i+1}/{len(messages)}: длительность {voice.duration} сек")
        
        try:
            # Скачиваем файл
            file = await bot.get_file(voice.file_id)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Скачиваем файл
            await file.download_to_drive(temp_path)
            
            # Транскрибируем
            success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
            
            # Очищаем временный файл
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            
            if success and text:
                all_texts.append(text)
                total_duration += voice.duration
                total_tokens += stats.get('tokens_count', 0)
                total_confidence += stats.get('confidence_avg', 0)
                successful_transcriptions += 1
                logger.info(f"✅ Сообщение {i+1} успешно транскрибировано: {len(text)} символов")
            else:
                logger.warning(f"⚠️ Не удалось транскрибировать сообщение {i+1}: {text}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке сообщения {i+1}: {e}")
    
    if not all_texts:
        return False, "Не удалось транскрибировать ни одного сообщения из серии", {}
    
    # Объединяем все тексты
    combined_text = " ".join(all_texts)
    
    # Формируем статистику
    combined_stats = {
        'messages_count': len(messages),
        'successful_transcriptions': successful_transcriptions,
        'total_duration': total_duration,
        'total_tokens': total_tokens,
        'average_confidence': total_confidence / successful_transcriptions if successful_transcriptions > 0 else 0,
        'text_length': len(combined_text)
    }
    
    logger.info(f"✅ Серия успешно обработана: {len(all_texts)} сообщений, {len(combined_text)} символов")
    
    # Очищаем серию после обработки
    if series_id in voice_series_groups:
        del voice_series_groups[series_id]
    
    return True, combined_text, combined_stats

async def process_single_voice_from_series(update: Update, context: ContextTypes.DEFAULT_TYPE, series_id: str):
    """Обрабатывает одиночное голосовое сообщение из серии"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    try:
        # Получаем серию
        series_messages = await get_voice_series(user_id, series_id)
        if not series_messages:
            await query.edit_message_text('❌ Серия голосовых сообщений не найдена.')
            return
        
        # Берем первое сообщение
        first_message = series_messages[0]
        voice = first_message['voice']
        
        logger.info(f'🎤 Обрабатываю одиночное сообщение из серии {series_id} для пользователя {user_id}')
        
        # Скачиваем файл
        file = await context.bot.get_file(voice.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Скачиваем файл
        await file.download_to_drive(temp_path)
        
        # Транскрибируем
        start_time = time.time()
        success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
        processing_time = time.time() - start_time
        
        # Очищаем временный файл
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        
        if success:
            # Формируем ответ
            response_parts = []
            response_parts.append(f"🎤 **Длительность: {voice.duration} сек ({voice.duration//60} мин {voice.duration%60} сек)**")
            response_parts.append(text)
            
            # Добавляем статистику
            if stats:
                response_parts.append(f"\n📊 **Статистика:**")

                response_parts.append(f"• Символов в тексте: {stats.get('text_length', 0)}")
                response_parts.append(f"• Токенов распознано: {stats.get('tokens_count', 0)}")
                response_parts.append(f"• Средняя уверенность: {stats.get('confidence_avg', 0):.2f}")
                response_parts.append(f"• Время обработки: {processing_time:.2f} сек")
            
            full_response = "\n".join(response_parts)
            
            # Отправляем результат
            if len(full_response) <= 3000:
                await query.edit_message_text(full_response, parse_mode='Markdown')
            else:
                await query.edit_message_text("📄 Расшифровка слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                timestamp = int(time.time())
                file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                await context.bot.send_document(chat_id=user_id, document=InputFile(file))
        else:
            await query.edit_message_text(f'❌ Не удалось расшифровать голосовое сообщение:\n\n{text}')
        
        # Очищаем серию
        if series_id in voice_series_groups:
            del voice_series_groups[series_id]
            
    except Exception as e:
        logger.error(f'❌ Ошибка при обработке одиночного сообщения из серии: {e}', exc_info=True)
        await query.edit_message_text('❌ Произошла ошибка при обработке голосового сообщения.')
        
        # Очищаем серию в случае ошибки
        if series_id in voice_series_groups:
            del voice_series_groups[series_id]

async def process_voice_series_complete(update: Update, context: ContextTypes.DEFAULT_TYPE, series_id: str):
    """Обрабатывает полную серию голосовых сообщений"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    try:
        logger.info(f'🎤 Обрабатываю полную серию {series_id} для пользователя {user_id}')
        
        # Обрабатываем серию
        success, combined_text, combined_stats = await process_voice_series(user_id, series_id, context.bot)
        
        if success:
            # Формируем ответ
            response_parts = []
            response_parts.append("🎤 **РАСШИФРОВКА СЕРИИ ГОЛОСОВЫХ СООБЩЕНИЙ:**")
            response_parts.append(combined_text)
            
            # Добавляем статистику серии
            if combined_stats:
                response_parts.append(f"\n📊 **Статистика серии:**")
                response_parts.append(f"• Сообщений в серии: {combined_stats.get('messages_count', 0)}")
                response_parts.append(f"• Успешно обработано: {combined_stats.get('successful_transcriptions', 0)}")
                response_parts.append(f"• Общая длительность: {combined_stats.get('total_duration', 0)} секунд")
                response_parts.append(f"• Общее количество токенов: {combined_stats.get('total_tokens', 0)}")
                response_parts.append(f"• Средняя уверенность: {combined_stats.get('average_confidence', 0):.2f}")
                response_parts.append(f"• Общая длина текста: {combined_stats.get('text_length', 0)} символов")
            
            full_response = "\n".join(response_parts)
            
            # Отправляем результат
            if len(full_response) <= 3000:
                await query.edit_message_text(full_response, parse_mode='Markdown')
            else:
                await query.edit_message_text("📄 Расшифровка серии слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                timestamp = int(time.time())
                file.name = f'voice_series_transcription_{user_id}_{timestamp}.txt'
                await context.bot.send_document(chat_id=user_id, document=InputFile(file))
        else:
            await query.edit_message_text(f'❌ Не удалось обработать серию голосовых сообщений:\n\n{combined_text}')
            
    except Exception as e:
        logger.error(f'❌ Ошибка при обработке серии голосовых сообщений: {e}', exc_info=True)
        await query.edit_message_text('❌ Произошла ошибка при обработке серии голосовых сообщений.')

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



def build_main_keyboard():
    """Строит главную клавиатуру с учетом доступности mind map"""
    buttons = [
        [InlineKeyboardButton('📺 Получить субтитры', callback_data='get_subs')],
        [InlineKeyboardButton('🎤 Расшифровать голос', callback_data='voice_info')]
    ]
    
    # Добавляем кнопку mind map если доступна
    if MIND_MAP_AVAILABLE:
        buttons.append([InlineKeyboardButton('🧠 Создать Mind Map', callback_data='mind_map_info')])
    
    buttons.extend([
        [InlineKeyboardButton('📚 Узнать подробнее', callback_data='learn_more')],
        [InlineKeyboardButton('💡 Быстрая помощь', callback_data='quick_help')],
        [InlineKeyboardButton('❓ Помощь', callback_data='help')],
        [InlineKeyboardButton('🔄 Начать заново', callback_data='reset')]
    ])
    
    return InlineKeyboardMarkup(buttons)

def format_subtitles(transcript, with_time=False):
    if with_time:
        return '\n'.join([
            f"[{int(item.start)//60:02}:{int(item.start)%60:02}] {item.text}" for item in transcript
        ])
    else:
        return '\n'.join([item.text for item in transcript])

# --- Хендлеры ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_new_user = user_id not in new_users
    
    if is_new_user:
        new_users.add(user_id)
        logger.info(f"👋 Новый пользователь {user_id} присоединился к боту")
        
        # Отправляем основное приветствие
        await update.message.reply_text(START_MESSAGE, reply_markup=build_main_keyboard())
        
        # Через небольшую паузу отправляем дополнительную подсказку
        await asyncio.sleep(1)
        await update.message.reply_text(
            '💡 **Совет для новичка:**\n\n'
            '🎬 **Начните с простого:**\n'
            '• Выберите короткое видео (до 10 минут)\n'
            '• Убедитесь, что у видео есть субтитры\n'
            '• Попробуйте сначала получить только субтитры\n\n'
            '🚀 **Готовы?** Отправьте ссылку на YouTube-видео!'
        )
    else:
        # Для существующих пользователей - обычное приветствие
        await update.message.reply_text(START_MESSAGE, reply_markup=build_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE, reply_markup=build_main_keyboard())

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ABOUT_MESSAGE, reply_markup=build_main_keyboard())

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(INFO_MESSAGE, reply_markup=build_main_keyboard())

async def first_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для новых пользователей - показывает простой пример"""
    await update.message.reply_text(
        '🎯 **ПЕРВЫЙ РАЗ? НЕ БОЙТЕСЬ!**\n\n'
        '🚀 **Вот что нужно сделать:**\n\n'
        '1️⃣ **Найдите интересное видео на YouTube**\n'
        '   (желательно короткое, до 10 минут)\n\n'
        '2️⃣ **Скопируйте ссылку**\n'
        '   (нажмите "Поделиться" → "Копировать ссылку")\n\n'
        '3️⃣ **Вставьте ссылку в чат**\n'
        '   (просто вставьте скопированную ссылку)\n\n'
        '4️⃣ **Выберите действие:**\n'
        '   📄 Сначала попробуйте "Только субтитры"\n'
        '   🤖 Потом "Субтитры + ИИ-суммаризация"\n\n'
        '🎬 **Пример ссылки:**\n'
        'https://youtube.com/watch?v=dQw4w9WgXcQ\n\n'
        '💡 **Совет:** Начните с простого! Выберите видео, которое уже смотрели.\n\n'
        '🚀 **Готовы попробовать?** Отправьте ссылку!',
        reply_markup=build_main_keyboard()
    )

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

async def mind_map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для создания mind map"""
    if not MIND_MAP_AVAILABLE:
        await update.message.reply_text(
            '❌ **Mind Map недоступен**\n\n'
            'Для использования этой функции необходимо настроить OpenRouter API ключ.\n\n'
            '📝 **Как настроить:**\n'
            '1. Получите API ключ на https://openrouter.ai/\n'
            '2. Добавьте OPENROUTER_API_KEY в .env файл\n'
            '3. Перезапустите бота\n\n'
            '💡 **Альтернатива:** Используйте другие функции бота!',
            reply_markup=build_main_keyboard()
        )
        return
    
    await update.message.reply_text(
        '🧠 **СОЗДАНИЕ MIND MAP**\n\n'
        '✅ **Готов к созданию Mind Map!**\n\n'
        '📝 **Теперь отправьте текст:**\n'
        '• Субтитры YouTube\n'
        '• Расшифрованные голосовые сообщения\n'
        '• Любой текстовый контент\n'
        '• Статьи, заметки, документы\n\n'
        '🎯 **Что будет создано:**\n'
        '• Интерактивная карта памяти\n'
        '• PNG изображение\n'
        '• Markdown файл\n'
        '• Автоматическая группировка идей\n\n'
        '🚀 **Отправьте текст прямо сейчас!**\n\n'
        '💡 **Совет:** Чем длиннее текст, тем интереснее получится карта!\n\n'
        '🔄 **Статус:** Ожидаю текст для Mind Map...',
        reply_markup=build_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"🔍 Получено сообщение от пользователя {user_id}")
    
    text = update.message.text.strip()
    logger.info(f"📝 Текст сообщения: {text[:50]}...")
    
    # Проверяем текущее состояние пользователя
    current_state = await get_user_state(user_id)
    logger.info(f"🔄 Текущее состояние пользователя {user_id}: {current_state}")
    
    # Если пользователь ожидает текст для Mind Map
    if current_state == 'expecting_mind_map_text':
        logger.info(f"🧠 Пользователь {user_id} в режиме Mind Map, обрабатываю текст")
        
        # Проверяем, достаточно ли длинный текст для mind map
        if len(text) < 50:
            await update.message.reply_text(
                '❓ **Текст слишком короткий для Mind Map**\n\n'
                '📝 **Минимальная длина:** 50 символов\n'
                '📊 **Ваш текст:** {len(text)} символов\n\n'
                '💡 **Отправьте более длинный текст:**\n'
                '• Субтитры YouTube\n'
                '• Статьи, заметки\n'
                '• Документы, эссе\n'
                '• Расшифрованные голосовые сообщения\n\n'
                '🔄 **Статус:** Ожидаю подходящий текст для Mind Map...',
                reply_markup=build_main_keyboard()
            )
            return
        
        # Создаем mind map
        if MIND_MAP_AVAILABLE:
            await update.message.reply_text(
                f'🧠 **Создаю Mind Map!**\n\n'
                f'📝 **Длина текста:** {len(text)} символов\n'
                f'🎯 **Что будет создано:**\n'
                '• Интерактивная карта памяти\n'
                '• PNG изображение\n'
                '• Markdown файл\n'
                '• Автоматическая группировка идей\n\n'
                '🚀 **Обрабатываю...**',
                reply_markup=build_main_keyboard()
            )
            
            try:
                logger.info(f"🧠 Создаю mind map для пользователя {user_id}, текст: {len(text)} символов")
                
                # Создаем mind map во всех форматах
                results = await mind_map_generator.create_mind_map(text, "all")
                
                logger.info(f"✅ Mind Map создан успешно для пользователя {user_id}")
                
                # Отправляем результаты
                await send_mind_map_results(update, context, results, text)
                
                # Очищаем состояние пользователя
                await clear_user_state(user_id)
                logger.info(f"🔄 Пользователь {user_id} возвращен в нормальное состояние")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при создании mind map для пользователя {user_id}: {e}")
                await update.message.reply_text(
                    f'❌ **Ошибка при создании Mind Map**\n\n'
                    f'🔍 **Детали:** {str(e)}\n\n'
                    '💡 **Попробуйте:**\n'
                    '• Отправить текст заново\n'
                    '• Использовать другой текст\n'
                    '• Обратиться к администратору\n\n'
                    '🔄 **Статус:** Ожидаю новый текст для Mind Map...',
                    reply_markup=build_main_keyboard()
                )
        else:
            await update.message.reply_text(
                '❌ **Mind Map недоступен**\n\n'
                'Для использования этой функции необходимо настроить OpenRouter API ключ.\n\n'
                '💡 **Используйте другие функции бота!**',
                reply_markup=build_main_keyboard()
            )
            # Очищаем состояние пользователя
            await clear_user_state(user_id)
        
        return
    
    # Обычная обработка сообщений (не в режиме Mind Map)
    logger.info(f"📝 Обычная обработка сообщения для пользователя {user_id}")
    
    # Проверяем множественные сообщения (НОВАЯ ЛОГИКА)
    video_id = extract_video_id(text)
    if video_id:
        # Это YouTube ссылка
        should_process, warning = await check_multiple_messages(user_id, 'youtube', text)
        if not should_process:
            logger.info(f"⚠️ YouTube ссылка проигнорирована для пользователя {user_id} (множественное сообщение)")
            await update.message.reply_text(warning)
            return
        logger.info(f"✅ YouTube ссылка принята к обработке для пользователя {user_id}")
    else:
        # Это обычный текст
        should_process, warning = await check_multiple_messages(user_id, 'text', text)
        if not should_process:
            logger.info(f"⚠️ Текстовое сообщение проигнорировано для пользователя {user_id} (множественное сообщение)")
            await update.message.reply_text(warning)
            return
        logger.info(f"✅ Текстовое сообщение принято к обработке для пользователя {user_id}")
    
    # Check user rate limit
    if not await rate_limit_check(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - request_timestamps.get(user_id, 0))
        logger.warning(f"⚠️ Rate limit для пользователя {user_id}, осталось {int(remaining_time)} секунд")
        
        # Показываем сообщение о необходимости подождать
        wait_msg = await update.message.reply_text(
            f'⚠️ **Слишком много запросов**\n\n'
            f'⏱️ Подождите {int(remaining_time)} секунд\n'
            f'🔄 После этого сообщение будет обработано автоматически'
        )
        
        # Ждем истечения времени rate limit
        await asyncio.sleep(remaining_time + 0.5)  # Добавляем небольшой запас
        
        # Обновляем timestamp для следующего запроса
        request_timestamps[user_id] = time.time()
        
        # Показываем, что начинаем обработку
        await wait_msg.edit_text('🔄 Начинаю обработку текстового сообщения...')
        
        # Продолжаем обработку
        logger.info(f'✅ Rate limit истек для пользователя {user_id}, продолжаю обработку')

    logger.info(f"🎬 Извлеченный video_id: {video_id}")
    
    # Обработка YouTube ссылок
    if video_id:
        # Show processing message
        logger.info(f"🔄 Начинаю обработку видео {video_id}")
        processing_msg = await update.message.reply_text('🔄 Получаю информацию о субтитрах...')
        
        # Get available transcripts with retry logic
        logger.info(f"📋 Запрашиваю список доступных субтитров для {video_id}")
        list_transcripts, success, error_msg = await get_available_transcripts_with_retry(video_id)
        
        if not success:
            logger.error(f"❌ Ошибка при получении списка субтитров: {error_msg}")
            log_and_notify_error(
                error=Exception(error_msg),
                context="get_available_transcripts",
                user_id=user_id,
                additional_info={"video_id": video_id}
            )
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
        return
    
    # Если это обычный текст (не YouTube ссылка и не в режиме Mind Map)
    if not video_id:
        logger.info(f"📝 Текст не является YouTube ссылкой, предлагаю создать mind map")
        
        # Проверяем, достаточно ли длинный текст для mind map
        if len(text) < 50:
            await update.message.reply_text(
                '❓ **Не понимаю, что вы хотите**\n\n'
                '🎬 **Для работы с YouTube:**\n'
                '• Скопируйте ссылку с YouTube\n'
                '• Вставьте её в чат\n'
                '• Пример: https://youtube.com/watch?v=...\n\n'
                '🎤 **Для голосовых сообщений:**\n'
                '• Нажмите на микрофон\n'
                '• Запишите сообщение\n'
                '• Отправьте\n\n'
                '🧠 **Для создания Mind Map:**\n'
                '• Отправьте длинный текст (минимум 50 символов)\n'
                '• Субтитры, статьи, заметки\n\n'
                '💡 **Нужна помощь?** Используйте кнопки ниже 👇',
                reply_markup=build_main_keyboard()
            )
            return
        
        # Предлагаем создать mind map
        if MIND_MAP_AVAILABLE:
            await update.message.reply_text(
                f'🧠 **Отличный текст для Mind Map!**\n\n'
                f'📝 **Длина:** {len(text)} символов\n'
                f'🎯 **Что будет создано:**\n'
                '• Интерактивная карта памяти\n'
                '• PNG изображение\n'
                '• Markdown файл\n'
                '• Автоматическая группировка идей\n\n'
                '🚀 **Создаю Mind Map...**',
                reply_markup=build_main_keyboard()
            )
            
            # Создаем mind map
            try:
                logger.info(f"🧠 Создаю mind map для пользователя {user_id}, текст: {len(text)} символов")
                
                # Создаем mind map во всех форматах
                results = await mind_map_generator.create_mind_map(text, "all")
                
                logger.info(f"✅ Mind Map создан успешно для пользователя {user_id}")
                
                # Отправляем результаты
                await send_mind_map_results(update, context, results, text)
                
            except Exception as e:
                logger.error(f"❌ Ошибка при создании mind map для пользователя {user_id}: {e}")
                await update.message.reply_text(
                    f'❌ **Ошибка при создании Mind Map**\n\n'
                    f'🔍 **Детали:** {str(e)}\n\n'
                    '💡 **Попробуйте:**\n'
                    '• Отправить текст заново\n'
                    '• Использовать другой текст\n'
                    '• Обратиться к администратору',
                    reply_markup=build_main_keyboard()
                )
        else:
            await update.message.reply_text(
                '❌ **Mind Map недоступен**\n\n'
                'Для использования этой функции необходимо настроить OpenRouter API ключ.\n\n'
                '💡 **Используйте другие функции бота!**',
                reply_markup=build_main_keyboard()
            )
        return

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает голосовые сообщения"""
    user_id = update.effective_user.id
    
    logger.info(f'🎤 Получено голосовое сообщение от пользователя {user_id}')
    
    # Проверяем множественные сообщения (НОВАЯ ЛОГИКА)
    should_process, warning = await check_multiple_messages(user_id, 'voice')
    if not should_process:
        logger.info(f"⚠️ Голосовое сообщение проигнорировано для пользователя {user_id} (множественное сообщение)")
        await update.message.reply_text(warning)
        return
    logger.info(f"✅ Голосовое сообщение принято к обработке для пользователя {user_id}")
    
    # Check user rate limit
    if not await rate_limit_check(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - request_timestamps.get(user_id, 0))
        logger.warning(f'⚠️ Превышен лимит запросов для пользователя {user_id}, осталось ждать: {int(remaining_time)} сек')
        
        # Показываем сообщение о необходимости подождать
        wait_msg = await update.message.reply_text(
            f'⚠️ **Слишком много запросов**\n\n'
            f'⏱️ Подождите {int(remaining_time)} секунд\n'
            f'🔄 После этого сообщение будет обработано автоматически'
        )
        
        # Ждем истечения времени rate limit
        await asyncio.sleep(remaining_time + 0.5)  # Добавляем небольшой запас
        
        # Обновляем timestamp для следующего запроса
        request_timestamps[user_id] = time.time()
        
        # Показываем, что начинаем обработку
        await wait_msg.edit_text('🔄 Начинаю обработку голосового сообщения...')
        
        # Продолжаем обработку
        logger.info(f'✅ Rate limit истек для пользователя {user_id}, продолжаю обработку')
    
    # Check if voice transcription is available
    if not voice_transcriber.is_available():
        logger.error(f'❌ API транскрипции недоступен для пользователя {user_id} (SONIOX_API_KEY не настроен)')
        await update.message.reply_text(
            '❌ Расшифровка голосовых сообщений недоступна.\n'
            'Необходимо настроить SONIOX_API_KEY в переменных окружения.'
        )
        return
    
    voice = update.message.voice
    if not voice:
        logger.error(f'❌ Не удалось получить объект голосового сообщения для пользователя {user_id}')
        await update.message.reply_text('❌ Не удалось получить голосовое сообщение.')
        return
    
    logger.info(f'📊 Голосовое сообщение: длительность {voice.duration} сек, file_id: {voice.file_id}, размер: {voice.file_size} байт')
    
    # Check voice message duration and offer options for long messages
    if voice.duration > 1200:  # Более 20 минут
        logger.warning(f'⚠️ Пользователь {user_id} отправил слишком длинное голосовое сообщение: {voice.duration} сек (>{voice.duration//60} мин)')
        await update.message.reply_text(
            '⚠️ **Голосовое сообщение слишком длинное**\n\n'
            f'📊 Длительность: {voice.duration} секунд ({voice.duration//60} мин {voice.duration%60} сек)\n'
            '📏 Максимальная поддержка: 20 минут\n\n'
            '💡 **Варианты решения:**\n'
            '• 🎤 Отправьте сообщение короче 20 минут\n'
            '• ✂️ Разделите на несколько частей\n'
            '• 📝 Используйте текстовое сообщение\n'
            '• 🎯 Отправьте только важную часть\n\n'
            '🔄 **Или попробуйте сейчас** (может работать, но без гарантий):',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🎤 Попробовать расшифровать', callback_data='voice_force')],
                [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
        ])
        )
        logger.info(f'📝 Отправлены опции для длинного голосового сообщения пользователю {user_id}')
        return
    elif voice.duration > 600:  # Более 10 минут - предупреждение
        logger.info(f'⚠️ Пользователь {user_id} отправил длинное голосовое сообщение: {voice.duration} сек, требуется подтверждение')
        
        # Сохраняем file_id в контексте пользователя для последующего использования
        context.user_data['pending_voice_file_id'] = voice.file_id
        
        await update.message.reply_text(
            '⚠️ **Длинное голосовое сообщение**\n\n'
            f'📊 Длительность: {voice.duration} секунд ({voice.duration//60} мин {voice.duration%60} сек)\n'
            '⏱️ Обработка может занять 2-3 минуты\n\n'
            '💡 **Рекомендации:**\n'
            '• Для лучшего качества разделите на части\n'
            '• Убедитесь в хорошем качестве звука\n\n'
            '🔄 **Продолжить обработку?**',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('✅ Продолжить', callback_data='voice_continue')],
                [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
            ])
        )
        logger.info(f'📝 Отправлено предупреждение о длинном голосовом сообщении пользователю {user_id}')
        return
    
    # Show processing message
    logger.info(f'🔄 Начинаю прямую обработку голосового сообщения для пользователя {user_id} (длительность: {voice.duration} сек)')
    processing_msg = await update.message.reply_text('🎤 Расшифровываю голосовое сообщение...')
    
    try:
        # Download voice file
        logger.info(f'📥 Загружаю голосовой файл {voice.file_id} для пользователя {user_id}')
        file = await context.bot.get_file(voice.file_id)
        logger.info(f'✅ Файл получен, размер: {file.file_size} байт')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        logger.info(f'💾 Сохраняю файл во временную директорию: {temp_path}')
        
        # Download the file
        await file.download_to_drive(temp_path)
        logger.info(f'✅ Файл успешно загружен в {temp_path}')
        
        # Transcribe voice message
        logger.info(f'🎤 Начинаю транскрипцию голосового сообщения для пользователя {user_id}')
        start_time = time.time()
        success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
        processing_time = time.time() - start_time
        
        logger.info(f'⏱️ Транскрипция завершена за {processing_time:.2f} секунд, успех: {success}')
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
            logger.info(f'🗑️ Временный файл {temp_path} удален')
        except Exception as cleanup_error:
            logger.warning(f'⚠️ Не удалось удалить временный файл {temp_path}: {cleanup_error}')
        
        if success:
            logger.info(f'✅ Транскрипция успешна для пользователя {user_id}, длина текста: {len(text)} символов')
            
            # Format response
            response_parts = []
            response_parts.append(f"🎤 **Длительность: {voice.duration} сек ({voice.duration//60} мин {voice.duration%60} сек)**")
            
            # Форматируем текст для лучшей читаемости
            formatted_text = format_transcription_text(text)
            response_parts.append(f"\n📝 **Текст:**\n{formatted_text}")
            
            # Add statistics
            if stats:
                response_parts.append(f"\n📊 **Статистика:**")

                response_parts.append(f"• Символов в тексте: {stats.get('text_length', 0)}")
                response_parts.append(f"• Токенов распознано: {stats.get('tokens_count', 0)}")
                response_parts.append(f"• Средняя уверенность: {stats.get('confidence_avg', 0):.2f}")
                response_parts.append(f"• Время обработки: {processing_time:.2f} сек")
            
            full_response = "\n".join(response_parts)
            
            # Send response
            if len(full_response) <= 3000:  # Уменьшаем лимит для Markdown
                logger.info(f'📤 Отправляю результат транскрипции пользователю {user_id} (текст)')
                try:
                    await processing_msg.edit_text(full_response, parse_mode='Markdown')
                except Exception as markdown_error:
                    logger.warning(f"Ошибка Markdown разметки в голосовом сообщении, отправляю без разметки: {markdown_error}")
                    # Безопасная отправка без Markdown
                    try:
                        await processing_msg.edit_text(full_response)
                    except Exception as fallback_error:
                        logger.error(f"Ошибка при отправке без Markdown: {fallback_error}")
                        # Последняя попытка - отправляем простой текст
                        safe_text = "📄 Расшифровка готова. Отправляю файлом из-за ошибки форматирования."
                        await processing_msg.edit_text(safe_text)
                        # Отправляем результат файлом
                        file = BytesIO(full_response.encode('utf-8'))
                        timestamp = int(time.time())
                        file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                        await update.message.reply_document(InputFile(file))
            else:
                logger.info(f'📄 Результат слишком длинный, отправляю файлом пользователю {user_id}')
                await processing_msg.edit_text("📄 Расшифровка слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                # Создаем информативное имя файла для голосового сообщения
                timestamp = int(time.time())
                file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                await update.message.reply_document(InputFile(file))
        else:
            logger.error(f'❌ Транскрипция неудачна для пользователя {user_id}: {text}')
            
            # Детальное логирование ошибки (без stack trace, так как это не исключение)
            logger.error(f'📊 Детали ошибки транскрипции:')
            logger.error(f'   • Сообщение: {text}')
            logger.error(f'   • Пользователь: {user_id}')
            logger.error(f'   • Время обработки: {processing_time:.2f} сек')
            
            # Дополнительная диагностика
            try:
                if os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    logger.error(f'📁 Размер временного файла: {file_size} байт')
                else:
                    logger.error('📁 Временный файл не существует')
            except Exception as diag_error:
                logger.error(f'⚠️ Ошибка при диагностике файла: {diag_error}')
            
            log_and_notify_error(
                error=Exception(text),
                context="voice_transcription_failed",
                user_id=user_id,
                additional_info={
                    "duration": voice.duration, 
                    "file_id": voice.file_id,
                    "error_message": text,
                    "processing_time": processing_time
                }
            )
            
            # Отправляем пользователю понятное сообщение об ошибке
            user_error_message = f'❌ Не удалось расшифровать голосовое сообщение:\n\n{text}'
            await processing_msg.edit_text(user_error_message)
            
    except Exception as e:
        logger.error(f'❌ Критическая ошибка при обработке голосового сообщения для пользователя {user_id}: {e}', exc_info=True)
        
        # Детальное логирование
        import traceback
        logger.error(f'Stack trace критической ошибки: {traceback.format_exc()}')
        
        log_and_notify_error(
            error=e,
            context="voice_transcription_exception",
            user_id=user_id,
            additional_info={
                "duration": voice.duration, 
                "file_id": voice.file_id,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        
        try:
            user_error_message = f'❌ Произошла ошибка при обработке голосового сообщения:\n\n{str(e)}'
            await processing_msg.edit_text(user_error_message)
        except Exception as edit_error:
            logger.error(f'❌ Не удалось отправить сообщение об ошибке пользователю {user_id}: {edit_error}')
            # Пытаемся отправить простое сообщение
            try:
                await update.message.reply_text('❌ Произошла ошибка при обработке голосового сообщения. Попробуйте позже.')
            except Exception as simple_error:
                logger.error(f'❌ Не удалось отправить даже простое сообщение об ошибке: {simple_error}')

async def handle_forwarded_voice_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает пересылаемые голосовые сообщения как серию"""
    user_id = update.effective_user.id
    
    logger.info(f'🔄 Получено пересылаемое голосовое сообщение от пользователя {user_id}')
    
    # Проверяем rate limit
    if not await rate_limit_check(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - request_timestamps.get(user_id, 0))
        logger.warning(f'⚠️ Превышен лимит запросов для пользователя {user_id}, осталось ждать: {int(remaining_time)} сек')
        
        # Показываем сообщение о необходимости подождать
        wait_msg = await update.message.reply_text(
            f'⚠️ **Слишком много запросов**\n\n'
            f'⏱️ Подождите {int(remaining_time)} секунд\n'
            f'🔄 После этого сообщение будет обработано автоматически'
        )
        
        # Ждем истечения времени rate limit
        await asyncio.sleep(remaining_time + 0.5)  # Добавляем небольшой запас
        
        # Обновляем timestamp для следующего запроса
        request_timestamps[user_id] = time.time()
        
        # Показываем, что начинаем обработку
        await wait_msg.edit_text('🔄 Начинаю обработку пересылаемого голосового сообщения...')
        
        # Продолжаем обработку
        logger.info(f'✅ Rate limit истек для пользователя {user_id}, продолжаю обработку')
    
    # Проверяем доступность транскрипции
    if not voice_transcriber.is_available():
        logger.error(f'❌ API транскрипции недоступен для пользователя {user_id}')
        await update.message.reply_text(
            '❌ Расшифровка голосовых сообщений недоступна.\n'
            'Необходимо настроить SONIOX_API_KEY в переменных окружения.'
        )
        return
    
    # Получаем голосовое сообщение
    voice = update.message.voice
    if not voice:
        logger.error(f'❌ Не удалось получить объект голосового сообщения для пользователя {user_id}')
        await update.message.reply_text('❌ Не удалось получить голосовое сообщение.')
        return
    
    logger.info(f'📊 Пересылаемое голосовое сообщение: длительность {voice.duration} сек, file_id: {voice.file_id}')
    
    # Проверяем длительность сообщения
    if voice.duration > 1200:  # Более 20 минут
        await update.message.reply_text(
            '⚠️ **Голосовое сообщение слишком длинное**\n\n'
            f'📊 Длительность: {voice.duration} секунд ({voice.duration//60} мин {voice.duration%60} сек)\n'
            '📏 Максимальная поддержка: 20 минут\n\n'
            '💡 **Варианты решения:**\n'
            '• 🎤 Отправьте сообщение короче 20 минут\n'
            '• ✂️ Разделите на несколько частей\n'
            '• 📝 Используйте текстовое сообщение\n'
            '• 🎯 Отправьте только важную часть\n\n'
            '🔄 **Или попробуйте сейчас** (может работать, но без гарантий):',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🎤 Попробовать расшифровать', callback_data='voice_force')],
                [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
            ])
        )
        return
    elif voice.duration > 600:  # Более 10 минут - предупреждение
        # Сохраняем file_id в контексте пользователя для последующего использования
        context.user_data['pending_voice_file_id'] = voice.file_id
        
        await update.message.reply_text(
            '⚠️ **Длинное голосовое сообщение**\n\n'
            f'📊 Длительность: {voice.duration} секунд ({voice.duration//60} мин {voice.duration%60} сек)\n'
            '⏱️ Обработка может занять 2-3 минуты\n\n'
            '💡 **Рекомендации:**\n'
            '• Для лучшего качества разделите на части\n'
            '• Убедитесь в хорошем качестве звука\n\n'
            '🔄 **Продолжить обработку?**',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('✅ Продолжить', callback_data='voice_continue')],
                [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
            ])
        )
        return
    
    # Обрабатываем пересылаемое голосовое сообщение как обычное
    logger.info(f'🔄 Обрабатываю пересылаемое голосовое сообщение для пользователя {user_id}')
    
    # Показываем сообщение о начале обработки
    processing_msg = await update.message.reply_text('🎤 Расшифровываю пересылаемое голосовое сообщение...')
    
    try:
        # Скачиваем голосовой файл
        file = await context.bot.get_file(voice.file_id)
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Скачиваем файл
        await file.download_to_drive(temp_path)
        
        # Транскрибируем голосовое сообщение
        start_time = time.time()
        success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
        processing_time = time.time() - start_time
        
        # Очищаем временный файл
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        
        if success:
            # Формируем ответ
            response_parts = []
            response_parts.append(f"🎤 **Пересылаемое сообщение - Длительность: {voice.duration} сек ({voice.duration//60} мин {voice.duration%60} сек)**")
            
            # Форматируем текст для лучшей читаемости
            formatted_text = format_transcription_text(text)
            response_parts.append(f"\n📝 **Текст:**\n{formatted_text}")
            
            # Добавляем статистику
            if stats:
                response_parts.append(f"\n📊 **Статистика:**")

                response_parts.append(f"• Символов в тексте: {stats.get('text_length', 0)}")
                response_parts.append(f"• Токенов распознано: {stats.get('tokens_count', 0)}")
                response_parts.append(f"• Средняя уверенность: {stats.get('confidence_avg', 0):.2f}")
                response_parts.append(f"• Время обработки: {processing_time:.2f} сек")
            
            full_response = "\n".join(response_parts)
            
            # Отправляем результат
            if len(full_response) <= 3000:
                await processing_msg.edit_text(full_response, parse_mode='Markdown')
            else:
                await processing_msg.edit_text("📄 Расшифровка слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                timestamp = int(time.time())
                file.name = f'forwarded_voice_transcription_{user_id}_{timestamp}.txt'
                await update.message.reply_document(InputFile(file))
        else:
            await processing_msg.edit_text(f'❌ Не удалось расшифровать пересылаемое голосовое сообщение:\n\n{text}')
            
    except Exception as e:
        logger.error(f'❌ Ошибка при обработке пересылаемого голосового сообщения: {e}', exc_info=True)
        await processing_msg.edit_text('❌ Произошла ошибка при обработке пересылаемого голосового сообщения.')

async def handle_multiple_forwarded_voice_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, voice_messages: list):
    """Обрабатывает серию пересылаемых голосовых сообщений"""
    user_id = update.effective_user.id
    
    logger.info(f'🎤 Получена серия из {len(voice_messages)} пересылаемых голосовых сообщений от пользователя {user_id}')
    
    # Проверяем rate limit
    if not await rate_limit_check(user_id):
        remaining_time = MIN_REQUEST_INTERVAL - (time.time() - request_timestamps.get(user_id, 0))
        logger.warning(f'⚠️ Превышен лимит запросов для пользователя {user_id}, осталось ждать: {int(remaining_time)} сек')
        
        # Показываем сообщение о необходимости подождать
        wait_msg = await update.message.reply_text(
            f'⚠️ **Слишком много запросов**\n\n'
            f'⏱️ Подождите {int(remaining_time)} секунд\n'
            f'🔄 После этого серия будет обработана автоматически'
        )
        
        # Ждем истечения времени rate limit
        await asyncio.sleep(remaining_time + 0.5)  # Добавляем небольшой запас
        
        # Обновляем timestamp для следующего запроса
        request_timestamps[user_id] = time.time()
        
        # Показываем, что начинаем обработку
        await wait_msg.edit_text('🔄 Начинаю обработку серии пересылаемых голосовых сообщений...')
        
        # Продолжаем обработку
        logger.info(f'✅ Rate limit истек для пользователя {user_id}, продолжаю обработку серии')
    
    # Проверяем доступность транскрипции
    if not voice_transcriber.is_available():
        logger.error(f'❌ API транскрипции недоступен для пользователя {user_id}')
        await update.message.reply_text(
            '❌ Расшифровка голосовых сообщений недоступна.\n'
            'Необходимо настроить SONIOX_API_KEY в переменных окружения.'
        )
        return
    
    # Проверяем общую длительность серии
    total_duration = sum(voice.duration for voice in voice_messages)
    
    if total_duration > 3600:  # Более 1 часа общей длительности
        await update.message.reply_text(
            '⚠️ **Серия голосовых сообщений слишком длинная**\n\n'
            f'📊 Общая длительность: {total_duration} секунд ({total_duration//60} мин)\n'
            '📏 Максимальная поддержка: 1 час общей длительности\n\n'
            '💡 **Рекомендации:**\n'
            '• Разделите на несколько частей\n'
            '• Обработайте сообщения по группам\n'
            '• Используйте текстовые сообщения для длинных частей'
        )
        return
    
    # Показываем информацию о серии
    await update.message.reply_text(
        f'🎤 **Серия пересылаемых голосовых сообщений**\n\n'
        f'📊 Количество сообщений: {len(voice_messages)}\n'
        f'⏱️ Общая длительность: {total_duration} секунд ({total_duration//60} мин {total_duration%60} сек)\n\n'
        '🔄 **Обработать всю серию?**',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('✅ Обработать серию', callback_data='voice_series_multiple')],
            [InlineKeyboardButton('❌ Отменить', callback_data='voice_cancel')]
        ])
    )
    
    # Сохраняем информацию о серии в контексте пользователя
    context.user_data['pending_voice_series'] = [
        {
            'voice': voice,
            'timestamp': time.time()
        } for voice in voice_messages
    ]

async def process_multiple_forwarded_voice_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает серию пересылаемых голосовых сообщений"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    try:
        # Получаем сохраненную серию из контекста
        voice_series = context.user_data.get('pending_voice_series', [])
        if not voice_series:
            await query.edit_message_text('❌ Серия голосовых сообщений не найдена.')
            return
        
        logger.info(f'🎤 Обрабатываю серию из {len(voice_series)} пересылаемых голосовых сообщений для пользователя {user_id}')
        
        all_texts = []
        total_duration = 0
        total_tokens = 0
        total_confidence = 0
        successful_transcriptions = 0
        
        for i, voice_data in enumerate(voice_series):
            voice = voice_data['voice']
            logger.info(f'🎤 Обрабатываю сообщение {i+1}/{len(voice_series)}: длительность {voice.duration} сек')
            
            try:
                # Скачиваем файл
                file = await context.bot.get_file(voice.file_id)
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # Скачиваем файл
                await file.download_to_drive(temp_path)
                
                # Транскрибируем
                success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
                
                # Очищаем временный файл
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                
                if success and text:
                    all_texts.append(text)
                    total_duration += voice.duration
                    total_tokens += stats.get('tokens_count', 0)
                    total_confidence += stats.get('confidence_avg', 0)
                    successful_transcriptions += 1
                    logger.info(f'✅ Сообщение {i+1} успешно транскрибировано: {len(text)} символов')
                else:
                    logger.warning(f'⚠️ Не удалось транскрибировать сообщение {i+1}: {text}')
                    
            except Exception as e:
                logger.error(f'❌ Ошибка при обработке сообщения {i+1}: {e}')
        
        if not all_texts:
            await query.edit_message_text('❌ Не удалось транскрибировать ни одного сообщения из серии.')
            # Очищаем контекст
            context.user_data.pop('pending_voice_series', None)
            return
        
        # Объединяем все тексты
        combined_text = " ".join(all_texts)
        
        # Формируем статистику серии
        combined_stats = {
            'messages_count': len(voice_series),
            'successful_transcriptions': successful_transcriptions,
            'total_duration': total_duration,
            'total_tokens': total_tokens,
            'average_confidence': total_confidence / successful_transcriptions if successful_transcriptions > 0 else 0,
            'text_length': len(combined_text)
        }
        
        logger.info(f'✅ Серия пересылаемых сообщений успешно обработана: {len(all_texts)} сообщений, {len(combined_text)} символов')
        
        # Формируем ответ
        response_parts = []
        response_parts.append("🎤 **РАСШИФРОВКА СЕРИИ ПЕРЕСЫЛАЕМЫХ ГОЛОСОВЫХ СООБЩЕНИЙ:**")
        response_parts.append(combined_text)
        
        # Добавляем статистику серии
        if combined_stats:
            response_parts.append(f"\n📊 **Статистика серии:**")
            response_parts.append(f"• Сообщений в серии: {combined_stats.get('messages_count', 0)}")
            response_parts.append(f"• Успешно обработано: {combined_stats.get('successful_transcriptions', 0)}")
            response_parts.append(f"• Общая длительность: {combined_stats.get('total_duration', 0)} секунд")
            response_parts.append(f"• Общее количество токенов: {combined_stats.get('total_tokens', 0)}")
            response_parts.append(f"• Средняя уверенность: {combined_stats.get('average_confidence', 0):.2f}")
            response_parts.append(f"• Общая длина текста: {combined_stats.get('text_length', 0)} символов")
        
        full_response = "\n".join(response_parts)
        
        # Отправляем результат
        if len(full_response) <= 3000:
            await query.edit_message_text(full_response, parse_mode='Markdown')
        else:
            await query.edit_message_text("📄 Расшифровка серии слишком длинная, отправляю файлом.")
            file = BytesIO(full_response.encode('utf-8'))
            timestamp = int(time.time())
            file.name = f'multiple_forwarded_voice_series_{user_id}_{timestamp}.txt'
            await context.bot.send_document(chat_id=user_id, document=InputFile(file))
        
        # Очищаем контекст
        context.user_data.pop('pending_voice_series', None)
        
    except Exception as e:
        logger.error(f'❌ Ошибка при обработке серии пересылаемых голосовых сообщений: {e}', exc_info=True)
        await query.edit_message_text('❌ Произошла ошибка при обработке серии пересылаемых голосовых сообщений.')
        # Очищаем контекст в случае ошибки
        context.user_data.pop('pending_voice_series', None)



async def process_forwarded_voice_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает серию пересылаемых голосовых сообщений"""
    user_id = update.effective_user.id
    query = update.callback_query
    
    try:
        # Получаем серию из контекста
        series_key = f"forwarded_series_{user_id}"
        series_data = context.user_data.get(series_key, {})
        messages = series_data.get('messages', [])
        
        if not messages:
            await query.edit_message_text('❌ Серия пересылаемых голосовых сообщений не найдена.')
            return
        
        logger.info(f'🎤 Обрабатываю серию из {len(messages)} пересылаемых голосовых сообщений для пользователя {user_id}')
        
        all_texts = []
        total_duration = 0
        total_tokens = 0
        total_confidence = 0
        successful_transcriptions = 0
        
        for i, msg in enumerate(messages):
            voice = msg['voice']
            logger.info(f'🎤 Обрабатываю сообщение {i+1}/{len(messages)}: длительность {voice.duration} сек')
            
            try:
                # Скачиваем файл
                file = await context.bot.get_file(voice.file_id)
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # Скачиваем файл
                await file.download_to_drive(temp_path)
                
                # Транскрибируем
                success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
                
                # Очищаем временный файл
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                
                if success and text:
                    all_texts.append(text)
                    total_duration += voice.duration
                    total_tokens += stats.get('tokens_count', 0)
                    total_confidence += stats.get('confidence_avg', 0)
                    successful_transcriptions += 1
                    logger.info(f'✅ Сообщение {i+1} успешно транскрибировано: {len(text)} символов')
                else:
                    logger.warning(f'⚠️ Не удалось транскрибировать сообщение {i+1}: {text}')
                    
            except Exception as e:
                logger.error(f'❌ Ошибка при обработке сообщения {i+1}: {e}')
        
        if not all_texts:
            await query.edit_message_text('❌ Не удалось транскрибировать ни одного сообщения из серии.')
            # Очищаем контекст
            context.user_data.pop(series_key, None)
            return
        
        # Объединяем все тексты
        combined_text = " ".join(all_texts)
        
        # Формируем статистику серии
        combined_stats = {
            'messages_count': len(messages),
            'successful_transcriptions': successful_transcriptions,
            'total_duration': total_duration,
            'total_tokens': total_tokens,
            'average_confidence': total_confidence / successful_transcriptions if successful_transcriptions > 0 else 0,
            'text_length': len(combined_text)
        }
        
        logger.info(f'✅ Серия пересылаемых сообщений успешно обработана: {len(all_texts)} сообщений, {len(combined_text)} символов')
        
        # Формируем ответ
        response_parts = []
        response_parts.append("🎤 **РАСШИФРОВКА СЕРИИ ПЕРЕСЫЛАЕМЫХ ГОЛОСОВЫХ СООБЩЕНИЙ:**")
        response_parts.append(combined_text)
        
        # Добавляем статистику серии
        if combined_stats:
            response_parts.append(f"\n📊 **Статистика серии:**")
            response_parts.append(f"• Сообщений в серии: {combined_stats.get('messages_count', 0)}")
            response_parts.append(f"• Успешно обработано: {combined_stats.get('successful_transcriptions', 0)}")
            response_parts.append(f"• Общая длительность: {combined_stats.get('total_duration', 0)} секунд")
            response_parts.append(f"• Общее количество токенов: {combined_stats.get('total_tokens', 0)}")
            response_parts.append(f"• Средняя уверенность: {combined_stats.get('average_confidence', 0):.2f}")
            response_parts.append(f"• Общая длина текста: {combined_stats.get('text_length', 0)} символов")
        
        full_response = "\n".join(response_parts)
        
        # Отправляем результат
        if len(full_response) <= 3000:
            await query.edit_message_text(full_response, parse_mode='Markdown')
        else:
            await query.edit_message_text("📄 Расшифровка серии слишком длинная, отправляю файлом.")
            file = BytesIO(full_response.encode('utf-8'))
            timestamp = int(time.time())
            file.name = f'forwarded_voice_series_{user_id}_{timestamp}.txt'
            await context.bot.send_document(chat_id=user_id, document=InputFile(file))
        
        # Очищаем контекст
        context.user_data.pop(series_key, None)
        
    except Exception as e:
        logger.error(f'❌ Ошибка при обработке серии пересылаемых голосовых сообщений: {e}', exc_info=True)
        await query.edit_message_text('❌ Произошла ошибка при обработке серии пересылаемых голосовых сообщений.')
        # Очищаем контекст в случае ошибки
        series_key = f"forwarded_series_{user_id}"
        context.user_data.pop(series_key, None)

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
    
    # Логируем текущее состояние пользователя
    user_id = query.from_user.id
    current_state = {
        'video_id': context.user_data.get('video_id'),
        'lang_code': context.user_data.get('lang_code'),
        'action': action,
        'model_index': context.user_data.get('model_index'),
        'with_time': context.user_data.get('with_time')
    }
    logger.info(f"👤 Пользователь {user_id} выбрал действие '{action}'. Текущее состояние: {current_state}")
    
    if action == 'subtitles':
        # Только субтитры - сразу выбираем формат
        await query.edit_message_text('Выберите формат субтитров:', reply_markup=build_format_keyboard())
    elif action in ['ai_summary', 'only_summary']:
        # Автоматически выбираем модель, сразу переходим к выбору формата
        logger.info(f"🤖 Автоматически выбираем модель для действия '{action}'")
        await query.edit_message_text('Выберите формат субтитров:', reply_markup=build_format_keyboard())



async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with_time = query.data == 'format_with_time'
    context.user_data['with_time'] = with_time
    
    # Логируем выбор формата
    user_id = query.from_user.id
    action = context.user_data.get('action')
    logger.info(f"📝 Пользователь {user_id} выбрал формат {'с метками' if with_time else 'без меток'} для действия '{action}'")
    
    await process_request(query, context)

async def process_request(query, context):
    """Обрабатывает запрос пользователя: получает субтитры и/или создает суммаризацию"""
    video_id = context.user_data.get('video_id')
    lang_code = context.user_data.get('lang_code')
    action = context.user_data.get('action')
    with_time = context.user_data.get('with_time', False)
    
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
        log_and_notify_error(
            error=Exception(error_msg),
            context="get_transcript",
            user_id=query.from_user.id,
            additional_info={"video_id": video_id, "lang_code": lang_code}
        )
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
        
        # Проверяем длину текста перед началом
        text_check = summarizer.check_text_length(raw_subtitles)
        
        if not text_check["can_process"]:
            # Текст слишком длинный - отказываем в обработке
            await query.edit_message_text(
                f"❌ **Текст слишком длинный для обработки**\n\n"
                f"📏 Размер: {text_check['length']:,} символов\n"
                f"🔢 Частей: {text_check['chunks']}\n\n"
                f"⚠️ Максимальная длина: {summarizer.max_text_length:,} символов\n\n"
                f"💡 **Рекомендации:**\n"
                f"• Разделите видео на части\n"
                f"• Используйте более короткие видео\n"
                f"• Обработайте только субтитры"
            )
            return
        
        # Показываем предупреждение для длинных текстов
        if text_check["warning"]:
            await query.edit_message_text(
                f"🤖 **Начинаю ИИ-суммаризацию**\n\n"
                f"{text_check['warning']}\n\n"
                f"⏳ Пожалуйста, подождите..."
            )
        else:
            await query.edit_message_text('🤖 Создаю ИИ-суммаризацию... Это может занять до 2-3 минут.')
        
        try:
            # Автоматически выбираем модель для суммаризации
            summary, stats = await summarizer.summarize_text(raw_subtitles)
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
            
            # Если язык не русский, добавляем перевод
            source_language = stats.get('source_language', 'unknown')
            if source_language != 'ru':
                logger.info(f"🌍 Язык не русский ({source_language}), создаю перевод...")
                await query.edit_message_text('🌍 Создаю перевод на русский язык...')
                
                try:
                    # Автоматически выбираем модель для перевода
                    translation = await summarizer.translate_to_russian(summary, source_language)
                    response_parts.append("\n🇷🇺 **ПЕРЕВОД НА РУССКИЙ:**")
                    response_parts.append(translation)
                    logger.info(f"✅ Перевод завершен успешно")
                except Exception as translation_error:
                    logger.error(f"❌ Ошибка перевода: {translation_error}")
                    response_parts.append("\n❌ Не удалось создать перевод на русский язык")
            
            # Статистика
            response_parts.append(f"\n📊 **Статистика:**")
            response_parts.append(f"• Модель: {stats.get('model', 'неизвестно')}")
            response_parts.append(f"• Строк субтитров: {len(transcript)}")
            response_parts.append(f"• Обработано частей: {stats.get('chunks', 0)}")
            response_parts.append(f"• Исходный размер: {stats.get('original_length', 0)} символов")
            response_parts.append(f"• Размер суммаризации: {stats.get('summary_length', 0)} символов")
            response_parts.append(f"• Исходный язык: {source_language}")
            
            # Информация о fallback механизме
            if stats.get('fallback_used'):
                response_parts.append(f"• ⚠️ Fallback: использованы промежуточные результаты")
            if stats.get('final_summary_failed'):
                response_parts.append(f"• ⚠️ Итоговая суммаризация: не удалась")
            
            # Дополнительная информация от API
            if 'prompt_tokens' in stats:
                response_parts.append(f"• Токенов промпта: {stats.get('prompt_tokens', 0)}")
                response_parts.append(f"• Токенов ответа: {stats.get('completion_tokens', 0)}")
                response_parts.append(f"• Всего токенов: {stats.get('total_tokens', 0)}")
                response_parts.append(f"• Причина завершения: {stats.get('finish_reason', 'unknown')}")
            
            full_response = "\n".join(response_parts)
            
            # Отправляем ответ
            if len(full_response) <= 3000:  # Уменьшаем лимит для Markdown
                try:
                    await query.edit_message_text(full_response, parse_mode='Markdown')
                except Exception as markdown_error:
                    logger.warning(f"Ошибка Markdown разметки, отправляю без разметки: {markdown_error}")
                    # Безопасная отправка без Markdown
                    try:
                        await query.edit_message_text(full_response)
                    except Exception as fallback_error:
                        logger.error(f"Ошибка при отправке без Markdown: {fallback_error}")
                        # Последняя попытка - отправляем простой текст
                        safe_text = "📄 Результат обработки готов. Отправляю файлом из-за ошибки форматирования."
                        await query.edit_message_text(safe_text)
                        # Отправляем результат файлом
                        file = BytesIO(full_response.encode('utf-8'))
                        filename = await create_filename(video_id, "summary", lang_code)
                        file.name = filename
                        await query.message.reply_document(InputFile(file))
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
            
            # Запрашиваем удовлетворенность результатом
            await ask_user_satisfaction(query, context, summary, stats, raw_subtitles, action, subtitles, video_id, lang_code, format_str)
            
        except Exception as ai_error:
            logger.error(f'Ошибка ИИ-суммаризации: {ai_error}')
            log_and_notify_error(
                error=ai_error,
                context="ai_summarization",
                user_id=query.from_user.id,
                additional_info={
                    "video_id": video_id,
                    "lang_code": lang_code,
                    "action": action
                }
            )
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
    elif query.data == 'learn_more':
        await query.edit_message_text(LEARN_MORE_MESSAGE, reply_markup=build_main_keyboard())
    elif query.data == 'quick_help':
        await query.edit_message_text(QUICK_HELP_MESSAGE, reply_markup=build_main_keyboard())
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
    elif query.data == 'mind_map_info':
        if not MIND_MAP_AVAILABLE:
            await query.edit_message_text(
                '❌ **Mind Map недоступен**\n\n'
                'Для использования этой функции необходимо настроить OpenRouter API ключ.\n\n'
                '📝 **Как настроить:**\n'
                '1. Получите API ключ на https://openrouter.ai/\n'
                '2. Добавьте OPENROUTER_API_KEY в .env файл\n'
                '3. Перезапустите бота\n\n'
                '💡 **Альтернатива:** Используйте другие функции бота!',
                reply_markup=build_main_keyboard()
            )
            return
        
        # Устанавливаем состояние ожидания текста для Mind Map
        user_id = query.from_user.id
        await set_user_state(user_id, 'expecting_mind_map_text')
        
        await query.edit_message_text(
            '🧠 **СОЗДАНИЕ MIND MAP**\n\n'
            '✅ **Готов к созданию Mind Map!**\n\n'
            '📝 **Теперь отправьте текст:**\n'
            '• Субтитры YouTube\n'
            '• Расшифрованные голосовые сообщения\n'
            '• Любой текстовый контент\n'
            '• Статьи, заметки, документы\n\n'
            '🎯 **Что будет создано:**\n'
            '• Интерактивная карта памяти\n'
            '• PNG изображение\n'
            '• Markdown файл\n'
            '• Автоматическая группировка идей\n\n'
            '🚀 **Отправьте текст прямо сейчас!**\n\n'
            '💡 **Совет:** Чем длиннее текст, тем интереснее получится карта!\n\n'
            '🔄 **Статус:** Ожидаю текст для Mind Map...',
            reply_markup=build_main_keyboard()
        )
    elif query.data == 'reset':
        # Сбрасываем состояние пользователя
        user_id = query.from_user.id
        context.user_data.clear()
        # Очищаем состояние пользователя
        await clear_user_state(user_id)
        logger.info(f"🔄 Пользователь {user_id} сбросил состояние через кнопку")
        await query.edit_message_text(
            '🔄 Состояние сброшено! Отправьте новую ссылку на YouTube-видео.',
            reply_markup=build_main_keyboard()
        )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Неизвестная команда. Для справки используйте /help.', reply_markup=build_main_keyboard())

async def voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает callback'и для голосовых сообщений"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    logger.info(f'📞 Получен callback для голосового сообщения: {query.data} от пользователя {user_id}')
    
    try:
        await query.answer()
        
        if query.data == 'voice_cancel':
            logger.info(f'❌ Пользователь {user_id} отменил обработку голосового сообщения')
            # Очищаем сохраненный file_id
            context.user_data.pop('pending_voice_file_id', None)
            await query.edit_message_text('❌ Обработка голосового сообщения отменена.')
            return
        
        elif query.data == 'voice_continue':
            # Получаем file_id из контекста пользователя
            file_id = context.user_data.get('pending_voice_file_id')
            if not file_id:
                logger.error(f'❌ Не найден file_id для пользователя {user_id}')
                await query.edit_message_text('❌ Ошибка: не найден файл голосового сообщения. Отправьте сообщение заново.')
                return
            
            logger.info(f'✅ Пользователь {user_id} подтвердил обработку длинного голосового сообщения: {file_id}')
            logger.info(f'🔄 Начинаю обработку длинного голосового сообщения для пользователя {user_id}')
            await query.edit_message_text('🔄 Обрабатываю длинное голосовое сообщение...')
            
            # Очищаем сохраненный file_id
            context.user_data.pop('pending_voice_file_id', None)
            
            await process_voice_message_by_file_id(update, context, file_id, force=False)
        
        elif query.data.startswith('voice_force_'):
            file_id = query.data.replace('voice_force_', '')
            logger.info(f'⚠️ Пользователь {user_id} запросил принудительную обработку голосового сообщения: {file_id}')
            logger.info(f'🔄 Начинаю принудительную обработку длинного голосового сообщения для пользователя {user_id}')
            await query.edit_message_text('⚠️ **Попытка обработки длинного сообщения**\n\n🔄 Обрабатываю... Это может занять до 5 минут.')
            await process_voice_message_by_file_id(update, context, file_id, force=True)
        
        elif query.data.startswith('voice_continue_'):
            file_id = query.data.replace('voice_continue_', '')
            logger.info(f'✅ Пользователь {user_id} подтвердил обработку длинного голосового сообщения: {file_id}')
            logger.info(f'🔄 Начинаю обработку длинного голосового сообщения для пользователя {user_id}')
            await query.edit_message_text('🔄 Обрабатываю длинное голосовое сообщение...')
            await process_voice_message_by_file_id(update, context, file_id, force=False)
        
        elif query.data.startswith('voice_single_'):
            series_id = query.data.replace('voice_single_', '')
            logger.info(f'🎤 Пользователь {user_id} запросил обработку одиночного сообщения из серии: {series_id}')
            await query.edit_message_text('🔄 Обрабатываю одиночное голосовое сообщение...')
            await process_single_voice_from_series(update, context, series_id)
        
        elif query.data.startswith('voice_series_'):
            series_id = query.data.replace('voice_series_', '')
            logger.info(f'🎤 Пользователь {user_id} запросил обработку серии голосовых сообщений: {series_id}')
            await query.edit_message_text('🔄 Обрабатываю серию голосовых сообщений...')
            await process_voice_series_complete(update, context, series_id)
        
        elif query.data.startswith('voice_wait_'):
            series_id = query.data.replace('voice_wait_', '')
            logger.info(f'⏳ Пользователь {user_id} решил подождать добавления сообщений в серию: {series_id}')
            await query.edit_message_text(
                '⏳ **Ожидание добавления сообщений в серию**\n\n'
                '💡 Отправьте еще голосовые сообщения для создания серии\n'
                '⏱️ Или подождите 5 минут для автоматической обработки\n\n'
                '🔄 **Когда будете готовы, нажмите кнопку ниже:**',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('✅ Обработать серию', callback_data=f'voice_series_{series_id}')],
                    [InlineKeyboardButton('🎤 Обработать сейчас', callback_data=f'voice_single_{series_id}')]
                ])
            )
        
        elif query.data == 'voice_series_multiple':
            logger.info(f'🎤 Пользователь {user_id} запросил обработку серии пересылаемых голосовых сообщений')
            await query.edit_message_text('🔄 Обрабатываю серию пересылаемых голосовых сообщений...')
            await process_multiple_forwarded_voice_series(update, context)
        
        else:
            logger.warning(f'⚠️ Неизвестный callback для голосового сообщения: {query.data} от пользователя {user_id}')
            await query.edit_message_text('❌ Неизвестная команда.')
            
    except Exception as e:
        logger.error(f'❌ Ошибка в voice_callback для пользователя {user_id}: {e}', exc_info=True)
        try:
            await query.edit_message_text('❌ Произошла ошибка при обработке команды.')
        except:
            pass


async def process_voice_message_by_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str, force: bool = False):
    """Обрабатывает голосовое сообщение по file_id"""
    user_id = update.effective_user.id
    
    logger.info(f'🎬 Начинаю обработку голосового сообщения для пользователя {user_id}, file_id: {file_id}, force: {force}')
    try:
        # Download voice file
        logger.info(f'📥 Загружаю голосовой файл {file_id} для пользователя {user_id}')
        file = await context.bot.get_file(file_id)
        logger.info(f'✅ Файл получен, размер: {file.file_size} байт')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            temp_path = temp_file.name
        
        logger.info(f'💾 Сохраняю файл во временную директорию: {temp_path}')
        
        # Download the file
        await file.download_to_drive(temp_path)
        logger.info(f'✅ Файл успешно загружен в {temp_path}')
        
        # Create a mock voice object for the transcriber
        class MockVoice:
            def __init__(self, file_id, duration=300):
                self.file_id = file_id
                self.duration = duration
        
        voice = MockVoice(file_id, duration=1200 if force else 600)
        logger.info(f'🎤 Начинаю транскрипцию голосового сообщения (длительность: {voice.duration} сек)')
        
        # Transcribe voice message
        start_time = time.time()
        success, text, stats = await voice_transcriber.transcribe_voice_message(temp_path)
        processing_time = time.time() - start_time
        
        logger.info(f'⏱️ Транскрипция завершена за {processing_time:.2f} секунд, успех: {success}')
        
        # Clean up temporary file
        try:
            os.unlink(temp_path)
            logger.info(f'🗑️ Временный файл {temp_path} удален')
        except Exception as cleanup_error:
            logger.warning(f'⚠️ Не удалось удалить временный файл {temp_path}: {cleanup_error}')
        
        if success:
            logger.info(f'✅ Транскрипция успешна для пользователя {user_id}, длина текста: {len(text)} символов')
            
            # Format response
            response_parts = []
            response_parts.append(f"🎤 **Длительность: {voice.duration} сек ({voice.duration//60} мин {voice.duration%60} сек)**")
            if force:
                response_parts.append("⚠️ *Обработано в экспериментальном режиме*")
            
            # Форматируем текст для лучшей читаемости
            formatted_text = format_transcription_text(text)
            response_parts.append(f"\n📝 **Текст:**\n{formatted_text}")
            
            # Add statistics
            if stats:
                response_parts.append(f"\n📊 **Статистика:**")

                response_parts.append(f"• Символов в тексте: {stats.get('text_length', 0)}")
                response_parts.append(f"• Токенов распознано: {stats.get('tokens_count', 0)}")
                response_parts.append(f"• Средняя уверенность: {stats.get('confidence_avg', 0):.2f}")
                response_parts.append(f"• Время обработки: {processing_time:.2f} сек")
            
            full_response = "\n".join(response_parts)
            
            # Send response
            if len(full_response) <= 3000:  # Уменьшаем лимит для Markdown
                logger.info(f'📤 Отправляю результат транскрипции пользователю {user_id} (текст)')
                try:
                    await update.callback_query.edit_message_text(full_response, parse_mode='Markdown')
                except Exception as markdown_error:
                    logger.warning(f"Ошибка Markdown разметки в голосовом сообщении, отправляю без разметки: {markdown_error}")
                    # Безопасная отправка без Markdown
                    try:
                        await update.callback_query.edit_message_text(full_response)
                    except Exception as fallback_error:
                        logger.error(f"Ошибка при отправке без Markdown: {fallback_error}")
                        # Последняя попытка - отправляем простой текст
                        safe_text = "📄 Расшифровка готова. Отправляю файлом из-за ошибки форматирования."
                        await update.callback_query.edit_message_text(safe_text)
                        # Отправляем результат файлом
                        file = BytesIO(full_response.encode('utf-8'))
                        timestamp = int(time.time())
                        file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                        await update.callback_query.message.reply_document(InputFile(file))
            else:
                logger.info(f'📄 Результат слишком длинный, отправляю файлом пользователю {user_id}')
                await update.callback_query.edit_message_text("📄 Расшифровка слишком длинная, отправляю файлом.")
                file = BytesIO(full_response.encode('utf-8'))
                # Создаем информативное имя файла для голосового сообщения
                timestamp = int(time.time())
                file.name = f'voice_transcription_{user_id}_{timestamp}.txt'
                await update.callback_query.message.reply_document(InputFile(file))
        else:
            logger.error(f'❌ Транскрипция неудачна для пользователя {user_id}: {text}')
            
            # Детальное логирование ошибки (без stack trace, так как это не исключение)
            logger.error(f'📊 Детали ошибки транскрипции:')
            logger.error(f'   • Сообщение: {text}')
            logger.error(f'   • Пользователь: {user_id}')
            logger.error(f'   • Время обработки: {processing_time:.2f} сек')
            
            # Дополнительная диагностика
            try:
                if os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    logger.error(f'📁 Размер временного файла: {file_size} байт')
                else:
                    logger.error('📁 Временный файл не существует')
            except Exception as diag_error:
                logger.error(f'⚠️ Ошибка при диагностике файла: {diag_error}')
            
            log_and_notify_error(
                error=Exception(text),
                context="voice_transcription_by_file_id_failed",
                user_id=user_id,
                additional_info={
                    "file_id": file_id, 
                    "force": force,
                    "error_message": text,
                    "processing_time": processing_time
                }
            )
            
            # Отправляем пользователю понятное сообщение об ошибке
            user_error_message = f'❌ Не удалось расшифровать голосовое сообщение:\n\n{text}'
            await update.callback_query.edit_message_text(user_error_message)
            
    except Exception as e:
        logger.error(f'❌ Критическая ошибка при обработке голосового сообщения по file_id {file_id} для пользователя {user_id}: {e}', exc_info=True)
        
        # Детальное логирование
        import traceback
        logger.error(f'Stack trace критической ошибки: {traceback.format_exc()}')
        
        log_and_notify_error(
            error=e,
            context="voice_transcription_by_file_id_exception",
            user_id=user_id,
            additional_info={
                "file_id": file_id, 
                "force": force,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        
        try:
            user_error_message = f'❌ Произошла ошибка при обработке голосового сообщения:\n\n{str(e)}'
            await update.callback_query.edit_message_text(user_error_message)
        except Exception as edit_error:
            logger.error(f'❌ Не удалось отправить сообщение об ошибке пользователю {user_id}: {edit_error}')
            # Пытаемся отправить простое сообщение
            try:
                await update.callback_query.message.reply_text('❌ Произошла ошибка при обработке голосового сообщения. Попробуйте позже.')
            except Exception as simple_error:
                logger.error(f'❌ Не удалось отправить даже простое сообщение об ошибке: {simple_error}')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает состояние пользователя"""
    user_id = update.effective_user.id
    
    # Очищаем все данные пользователя
    context.user_data.clear()
    
    logger.info(f"🔄 Пользователь {user_id} сбросил состояние")
    
    await update.message.reply_text(
        '🔄 Состояние сброшено! Отправьте новую ссылку на YouTube-видео.',
        reply_markup=build_main_keyboard()
    )

async def ask_user_satisfaction(query, context, summary, stats, raw_subtitles, action, subtitles, video_id, lang_code, format_str):
    """Запрашивает у пользователя удовлетворенность результатом суммаризации"""
    user_id = query.from_user.id
    
    # Сохраняем данные для возможной повторной попытки
    context.user_data['pending_summary_data'] = {
        'summary': summary,
        'stats': stats,
        'raw_subtitles': raw_subtitles,
        'action': action,
        'subtitles': subtitles,
        'video_id': video_id,
        'lang_code': lang_code,
        'format_str': format_str
    }
    
    # Создаем клавиатуру для оценки результата
    satisfaction_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('👍 Доволен результатом', callback_data='satisfaction_good')],
        [InlineKeyboardButton('👎 Не доволен, попробовать другую модель', callback_data='satisfaction_bad')],
        [InlineKeyboardButton('❌ Отмена', callback_data='satisfaction_cancel')]
    ])
    
    # Отправляем запрос удовлетворенности
    await query.message.reply_text(
        '🤖 **Как вам результат суммаризации?**\n\n'
        'Если вы довольны - можете сохранить результат.\n'
        'Если нет - я попробую использовать другую модель.',
        reply_markup=satisfaction_keyboard
    )
    
    logger.info(f"👤 Запрошена удовлетворенность у пользователя {user_id} для видео {video_id}")

async def satisfaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает callback'и для оценки удовлетворенности"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.answer()
    
    if query.data == 'satisfaction_good':
        # Пользователь доволен результатом
        await handle_satisfaction_good(query, context)
    elif query.data == 'satisfaction_bad':
        # Пользователь не доволен, пробуем другую модель
        await handle_satisfaction_bad(query, context)
    elif query.data == 'satisfaction_cancel':
        # Пользователь отменяет
        await handle_satisfaction_cancel(query, context)

async def handle_satisfaction_good(query, context):
    """Обрабатывает положительную оценку результата"""
    user_id = query.from_user.id
    pending_data = context.user_data.get('pending_summary_data', {})
    
    if not pending_data:
        await query.edit_message_text('❌ Ошибка: данные о суммаризации не найдены')
        return
    
    # Логируем положительную обратную связь
    stats = pending_data.get('stats', {})
    model_name = stats.get('model', 'неизвестно')
    text_length = stats.get('original_length', 0)
    summary_length = stats.get('summary_length', 0)
    
    summarizer.log_user_feedback(
        model_name=model_name,
        text_length=text_length,
        summary_length=summary_length,
        user_satisfied=True
    )
    
    # Очищаем данные
    context.user_data.pop('pending_summary_data', None)
    
    await query.edit_message_text(
        '✅ **Отлично!** Результат сохранен.\n\n'
        f'🤖 Использованная модель: {model_name}\n'
        f'📊 Размер суммаризации: {summary_length} символов\n\n'
        'Спасибо за обратную связь! 🙏'
    )
    
    logger.info(f"✅ Пользователь {user_id} доволен результатом суммаризации с моделью {model_name}")

async def handle_satisfaction_bad(query, context):
    """Обрабатывает отрицательную оценку результата и пробует другую модель"""
    user_id = query.from_user.id
    pending_data = context.user_data.get('pending_summary_data', {})
    
    if not pending_data:
        await query.edit_message_text('❌ Ошибка: данные о суммаризации не найдены')
        return
    
    # Логируем отрицательную обратную связь
    stats = pending_data.get('stats', {})
    model_name = stats.get('model', 'неизвестно')
    text_length = stats.get('original_length', 0)
    summary_length = stats.get('summary_length', 0)
    
    summarizer.log_user_feedback(
        model_name=model_name,
        text_length=text_length,
        summary_length=summary_length,
        user_satisfied=False,
        feedback_reason="Пользователь не доволен качеством"
    )
    
    # Пробуем другую модель
    await query.edit_message_text('🔄 Пробую другую модель для улучшения результата...')
    
    try:
        raw_subtitles = pending_data.get('raw_subtitles', '')
        action = pending_data.get('action', '')
        subtitles = pending_data.get('subtitles', '')
        video_id = pending_data.get('video_id', '')
        lang_code = pending_data.get('lang_code', '')
        format_str = pending_data.get('format_str', '')
        
        # Используем функцию с повторными попытками
        new_summary, new_stats, success = await summarizer.summarize_with_retry(raw_subtitles, max_retries=2)
        
        if success:
            # Обновляем данные
            pending_data.update({
                'summary': new_summary,
                'stats': new_stats
            })
            context.user_data['pending_summary_data'] = pending_data
            
            # Показываем новый результат
            new_model = new_stats.get('model', 'неизвестно')
            await query.edit_message_text(
                f'🤖 **Новая попытка с моделью {new_model}**\n\n'
                f'{new_summary[:1000]}{"..." if len(new_summary) > 1000 else ""}\n\n'
                'Как вам новый результат?',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('👍 Доволен', callback_data='satisfaction_good')],
                    [InlineKeyboardButton('👎 Все еще не доволен', callback_data='satisfaction_bad')],
                    [InlineKeyboardButton('❌ Отмена', callback_data='satisfaction_cancel')]
                ])
            )
            
            logger.info(f"🔄 Повторная попытка суммаризации для пользователя {user_id} с моделью {new_model}")
        else:
            # Все попытки исчерпаны
            await query.edit_message_text(
                '❌ **К сожалению, не удалось улучшить результат**\n\n'
                'Я попробовал несколько разных моделей, но результат не улучшился.\n\n'
                'Возможные причины:\n'
                '• Сложность исходного текста\n'
                '• Ограничения бесплатных моделей\n'
                '• Технические проблемы\n\n'
                'Попробуйте позже или обратитесь к администратору.'
            )
            
            # Очищаем данные
            context.user_data.pop('pending_summary_data', None)
            
            logger.warning(f"⚠️ Все попытки суммаризации исчерпаны для пользователя {user_id}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при повторной попытке суммаризации для пользователя {user_id}: {e}")
        await query.edit_message_text(
            '❌ Произошла ошибка при попытке улучшить результат.\n'
            'Попробуйте позже или обратитесь к администратору.'
        )

async def handle_satisfaction_cancel(query, context):
    """Обрабатывает отмену оценки"""
    user_id = query.from_user.id
    
    # Очищаем данные
    context.user_data.pop('pending_summary_data', None)
    
    await query.edit_message_text('❌ Оценка отменена.')
    
    logger.info(f"❌ Пользователь {user_id} отменил оценку результата")

async def send_mind_map_results(update: Update, context: ContextTypes.DEFAULT_TYPE, results: dict, original_text: str):
    """Отправляет результаты создания mind map пользователю"""
    user_id = update.effective_user.id
    logger.info(f"📤 Отправляю результаты mind map пользователю {user_id}")
    
    try:
        # Отправляем основную информацию
        structure = results['structure']
        main_topic = structure['main_topic']
        subtopics_count = len(structure['subtopics'])
        total_ideas = sum(len(items) for items in structure['subtopics'].values())
        
        info_message = (
            f'🧠 **Mind Map создан успешно!**\n\n'
            f'📊 **Статистика:**\n'
            f'• 🎯 Главная тема: {main_topic}\n'
            f'• 🏷️ Количество подтем: {subtopics_count}\n'
            f'• 💡 Всего идей: {total_ideas}\n'
            f'• 📝 Анализировано символов: {len(original_text)}\n\n'
            f'📋 **Структура идей:**\n'
        )
        
        # Добавляем информацию о подтемах
        for topic, ideas in structure['subtopics'].items():
            info_message += f'• **{topic}**: {len(ideas)} идей\n'
        
        info_message += '\n📁 **Файлы готовы к скачиванию ниже**'
        
        await update.message.reply_text(info_message)
        
        # Отправляем Markdown файл
        if results['markdown']:
            markdown_file = BytesIO(results['markdown'].encode('utf-8'))
            markdown_file.name = f'mindmap_{hash(original_text) % 10000}.md'
            await update.message.reply_document(
                document=InputFile(markdown_file, filename=markdown_file.name),
                caption='📄 **Markdown файл**\nИспользуйте для создания mind map в других инструментах'
            )
        
        # Отправляем Mermaid файл
        if results['mermaid']:
            mermaid_file = BytesIO(results['mermaid'].encode('utf-8'))
            mermaid_file.name = f'mindmap_{hash(original_text) % 10000}.mmd'
            await update.message.reply_document(
                document=InputFile(mermaid_file, filename=mermaid_file.name),
                caption='🎨 **Mermaid диаграмма**\nИспользуйте в Mermaid Live Editor или других инструментах'
            )
        
        # Отправляем HTML файл
        if results['html_content']:
            html_file = BytesIO(results['html_content'].encode('utf-8'))
            html_file.name = f'mindmap_{hash(original_text) % 10000}.html'
            await update.message.reply_document(
                document=InputFile(html_file, filename=html_file.name),
                caption='🌐 **Интерактивная HTML карта**\nОткройте в браузере для интерактивного просмотра'
            )
        
        # Отправляем PNG изображение если доступно
        if results['png_path'] and os.path.exists(results['png_path']):
            try:
                with open(results['png_path'], 'rb') as png_file:
                    await update.message.reply_photo(
                        photo=png_file,
                        caption='🖼️ **PNG изображение**\nСтатичная версия mind map'
                    )
                # Удаляем временный файл
                os.remove(results['png_path'])
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить PNG для пользователя {user_id}: {e}")
        
        # Отправляем финальное сообщение с инструкциями
        await update.message.reply_text(
            '🎉 **Mind Map готов!**\n\n'
            '💡 **Как использовать:**\n'
            '• 📄 **Markdown**: Откройте в любом редакторе\n'
            '• 🎨 **Mermaid**: Вставьте в Mermaid Live Editor\n'
            '• 🌐 **HTML**: Откройте в браузере\n'
            '• 🖼️ **PNG**: Используйте в презентациях\n\n'
            '🚀 **Попробуйте снова:**\n'
            '• Отправьте другой текст\n'
            '• YouTube субтитры\n'
            '• Голосовые сообщения\n\n'
            '💭 **Нужна помощь?** Используйте кнопки ниже 👇',
            reply_markup=build_main_keyboard()
        )
        
        logger.info(f"✅ Результаты mind map успешно отправлены пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке результатов mind map пользователю {user_id}: {e}")
        await update.message.reply_text(
            '❌ **Ошибка при отправке файлов**\n\n'
            'Mind Map был создан, но не удалось отправить файлы.\n\n'
            '💡 **Попробуйте:**\n'
            '• Отправить текст заново\n'
            '• Использовать другие функции бота\n\n'
            '📝 **Техническая информация:**\n'
            f'`{str(e)[:100]}...`',
            reply_markup=build_main_keyboard()
        )

async def start_background_tasks():
    """Запускает фоновые задачи для очистки"""
    while True:
        try:
            # Очистка устаревших серий голосовых сообщений
            await cleanup_expired_voice_series()
            
            # Очистка устаревших записей отслеживания сообщений
            await cleanup_expired_message_tracking()
            
            # Очистка устаревших состояний пользователей
            await cleanup_expired_user_states()
            
            # Ждем 10 минут перед следующей очисткой
            await asyncio.sleep(600)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновой задаче очистки: {e}")
            await asyncio.sleep(60)  # При ошибке ждем 1 минуту

async def set_user_state(user_id: int, state: str):
    """Устанавливает состояние пользователя"""
    global user_states
    user_states[user_id] = state
    logger.info(f"🔄 Пользователь {user_id} переведен в состояние: {state}")

async def get_user_state(user_id: int) -> str:
    """Получает текущее состояние пользователя"""
    global user_states
    return user_states.get(user_id, 'normal')

async def clear_user_state(user_id: int):
    """Очищает состояние пользователя"""
    global user_states
    if user_id in user_states:
        del user_states[user_id]
        logger.info(f"🔄 Состояние пользователя {user_id} очищено")

async def cleanup_expired_user_states():
    """Очищает устаревшие состояния пользователей"""
    global user_states
    
    now = time.time()
    cleanup_threshold = 3600  # 1 час
    
    # Очищаем состояния пользователей, которые неактивны более часа
    # Для простых состояний (строки) используем время последнего сообщения
    expired_users = []
    
    for user_id, state in user_states.items():
        # Если состояние - строка, проверяем время последнего сообщения
        if isinstance(state, str):
            last_message_time = last_text_message_time.get(user_id, 0)
            if now - last_message_time > cleanup_threshold:
                expired_users.append(user_id)
    
    for user_id in expired_users:
        del user_states[user_id]
    
    if expired_users:
        logger.info(f"🧹 Очищено {len(expired_users)} устаревших состояний пользователей")

if __name__ == '__main__':
    try:
        # Проверяем наличие токена
        if not TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения")
            print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден. Проверьте файл .env")
            exit(1)
        
        # Создаем приложение с улучшенными настройками
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('about', about_command))
        app.add_handler(CommandHandler('info', info_command))
        app.add_handler(CommandHandler('first_time', first_time_command))
        app.add_handler(CommandHandler('subs', subs_command))
        app.add_handler(CommandHandler('voice', voice_command))
        app.add_handler(CommandHandler('mindmap', mind_map_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        app.add_handler(MessageHandler(filters.VOICE & filters.FORWARDED, handle_forwarded_voice_series))
        app.add_handler(CallbackQueryHandler(language_callback, pattern=r'^lang_'))
        app.add_handler(CallbackQueryHandler(action_callback, pattern=r'^action_'))

        app.add_handler(CallbackQueryHandler(format_callback, pattern=r'^format_'))
        app.add_handler(CallbackQueryHandler(satisfaction_callback, pattern=r'^satisfaction_'))
        app.add_handler(CallbackQueryHandler(main_keyboard_callback, pattern=r'^(help|learn_more|quick_help|get_subs|about|info|voice_info|mind_map_info|reset)$'))
        app.add_handler(CallbackQueryHandler(voice_callback, pattern=r'^(voice_force_|voice_continue_|voice_continue|voice_cancel|voice_single_|voice_series_|voice_wait_|voice_series_multiple)$'))
        app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
        app.add_handler(CommandHandler('reset', reset_command))
        
        # Добавляем глобальный обработчик ошибок
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Глобальный обработчик ошибок"""
            logger.error(f"❌ Необработанная ошибка: {context.error}", exc_info=context.error)
            
            # Отправляем уведомление администратору
            if update and hasattr(update, 'effective_user'):
                user_id = update.effective_user.id if update.effective_user else None
                log_and_notify_error(
                    error=context.error,
                    context="unhandled_exception",
                    user_id=user_id,
                    additional_info={"update_type": type(update).__name__}
                )
        
        app.add_error_handler(error_handler)
        
        logger.info("🚀 Бот инициализирован успешно")
        print('🚀 Бот запущен!')
        
        # Запускаем фоновые задачи очистки в отдельном потоке
        import threading
        def run_background_tasks():
            asyncio.run(start_background_tasks())
        
        background_thread = threading.Thread(target=run_background_tasks, daemon=True)
        background_thread.start()
        logger.info("🔄 Фоновые задачи очистки запущены")
        
        # Запускаем бота
        try:
            logger.info("🚀 Запускаю бота...")
            app.run_polling(
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
                close_loop=False
            )
        except Exception as startup_error:
            logger.error(f"❌ Критическая ошибка при запуске бота: {startup_error}")
            print(f"❌ Критическая ошибка при запуске: {startup_error}")
            
    except Exception as init_error:
        logger.error(f"❌ Ошибка инициализации бота: {init_error}")
        print(f"❌ Ошибка инициализации: {init_error}")
        import traceback
        traceback.print_exc()