import os
import re
import logging
import time
from io import BytesIO
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv

# Включаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

YOUTUBE_REGEX = r"(?:v=|youtu\\.be/|youtube\\.com/embed/|youtube\\.com/watch\\?v=)?([\w-]{11})"

START_MESSAGE = (
    '👋 Привет! Я бот для получения субтитров с YouTube-видео.\n\n'
    'Просто пришлите мне ссылку на видео или его ID, и я отправлю вам субтитры (если они доступны).\n\n'
    'Поддерживаемые языки: русский, английский и другие, если есть.\n'
    'Можно выбрать формат: с временными метками или без.\n\n'
    'Для справки используйте /help.'
)

HELP_MESSAGE = (
    'ℹ️ Как пользоваться ботом:\n'
    '1. Пришлите ссылку на YouTube-видео или его ID (11 символов).\n'
    '2. Если у видео есть субтитры, выберите язык и формат.\n'
    '3. Если субтитры длинные, получите их в виде файла.\n\n'
    'Пример ссылки: https://youtu.be/dQw4w9WgXcQ\n'
    'Пример ID: dQw4w9WgXcQ'
)

# Антиспам: минимальный интервал между запросами (сек)
MIN_REQUEST_INTERVAL = 10

# --- Вспомогательные функции ---
def extract_video_id(text):
    match = re.search(YOUTUBE_REGEX, text)
    if match:
        return match.group(1)
    return None

def get_available_transcripts(video_id):
    try:
        list_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        return list_transcripts
    except Exception as e:
        logger.error(f'Ошибка при получении списка субтитров: {e}')
        return None

def build_language_keyboard(list_transcripts):
    buttons = []
    for transcript in list_transcripts:
        lang_code = transcript.language_code
        lang_name = transcript.language
        buttons.append([InlineKeyboardButton(f'{lang_name} ({lang_code})', callback_data=f'lang_{lang_code}')])
    return InlineKeyboardMarkup(buttons)

def build_format_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('С временными метками', callback_data='format_with_time')],
        [InlineKeyboardButton('Без временных меток', callback_data='format_plain')]
    ])

def build_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('Помощь', callback_data='help')],
        [InlineKeyboardButton('Получить субтитры', callback_data='get_subs')]
    ])

def format_subtitles(transcript, with_time=False):
    if with_time:
        return '\n'.join([
            f"[{int(item['start'])//60:02}:{int(item['start'])%60:02}] {item['text']}" for item in transcript
        ])
    else:
        return '\n'.join([item['text'] for item in transcript])

# --- Хендлеры ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(START_MESSAGE, reply_markup=build_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE, reply_markup=build_main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()
    last_time = context.user_data.get('last_request_time', 0)
    if now - last_time < MIN_REQUEST_INTERVAL:
        await update.message.reply_text(f'Пожалуйста, не чаще одного запроса в {MIN_REQUEST_INTERVAL} секунд.')
        return
    context.user_data['last_request_time'] = now

    text = update.message.text.strip()
    video_id = extract_video_id(text)
    if not video_id:
        await update.message.reply_text('Пожалуйста, пришлите корректную ссылку на YouTube-видео или его ID.')
        return
    list_transcripts = get_available_transcripts(video_id)
    if not list_transcripts:
        await update.message.reply_text('Не удалось получить список субтитров или субтитры отсутствуют.')
        return
    list_transcripts = list(list_transcripts)  # Исправление: приводим к списку
    # Сохраняем видео для пользователя
    context.user_data['video_id'] = video_id
    context.user_data['list_transcripts'] = list_transcripts
    # Если только один язык — сразу предлагаем формат
    if len(list_transcripts) == 1:
        lang_code = list_transcripts[0].language_code
        context.user_data['lang_code'] = lang_code
        await update.message.reply_text(
            f'Выбран язык: {list_transcripts[0].language} ({lang_code}). Теперь выберите формат:',
            reply_markup=build_format_keyboard()
        )
    else:
        await update.message.reply_text('Выберите язык субтитров:', reply_markup=build_language_keyboard(list_transcripts))

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = query.data.replace('lang_', '')
    context.user_data['lang_code'] = lang_code
    await query.edit_message_text(f'Выбран язык: {lang_code}. Теперь выберите формат:', reply_markup=build_format_keyboard())

async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with_time = query.data == 'format_with_time'
    context.user_data['with_time'] = with_time
    video_id = context.user_data.get('video_id')
    lang_code = context.user_data.get('lang_code')
    if not video_id or not lang_code:
        await query.edit_message_text('Ошибка: не найдено видео или язык. Начните заново.')
        return
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
        subtitles = format_subtitles(transcript, with_time=with_time)
        format_str = 'с метками' if with_time else 'без меток'
        stat_msg = f'Язык: {lang_code}\nСтрок: {len(transcript)}\nФормат: {format_str}'
        if len(subtitles) <= 4000:
            await query.edit_message_text(subtitles)
            await query.message.reply_text(stat_msg)
        else:
            file = BytesIO(subtitles.encode('utf-8'))
            file.name = f'subtitles_{video_id}_{lang_code}.txt'
            await query.edit_message_text('Субтитры слишком длинные, отправляю файлом.')
            await query.message.reply_document(InputFile(file), caption=stat_msg)
    except TranscriptsDisabled:
        await query.edit_message_text('У этого видео субтитры отключены.')
    except NoTranscriptFound:
        await query.edit_message_text('Субтитры не найдены.')
    except Exception as e:
        logger.error(f'Ошибка при получении субтитров: {e}')
        await query.edit_message_text(f'Ошибка: {e}')

async def main_keyboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'help':
        await query.edit_message_text(HELP_MESSAGE, reply_markup=build_main_keyboard())
    elif query.data == 'get_subs':
        await query.edit_message_text('Пришлите ссылку на YouTube-видео или его ID.')

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Неизвестная команда. Для справки используйте /help.', reply_markup=build_main_keyboard())

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r'^lang_'))
    app.add_handler(CallbackQueryHandler(format_callback, pattern=r'^format_'))
    app.add_handler(CallbackQueryHandler(main_keyboard_callback, pattern=r'^(help|get_subs)$'))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    print('Бот запущен!')
    app.run_polling() 