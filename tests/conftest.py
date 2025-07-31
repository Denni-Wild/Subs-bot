import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock


def pytest_configure(config):
    """Конфигурация pytest"""
    # Добавляем пользовательские маркеры
    config.addinivalue_line(
        "markers", "slow: отмечает тесты как медленные (требуют реальных API)"
    )
    config.addinivalue_line(
        "markers", "integration: отмечает интеграционные тесты"
    )


def pytest_collection_modifyitems(config, items):
    """Автоматически пропускаем медленные тесты если не указан флаг"""
    if config.getoption("--run-slow"):
        return
    
    skip_slow = pytest.mark.skip(reason="добавьте --run-slow для запуска медленных тестов")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Добавляем опции командной строки"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="запускать медленные тесты"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для всех асинхронных тестов"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars():
    """Фикстура для мокирования переменных окружения"""
    env_vars = {
        'TELEGRAM_BOT_TOKEN': 'test_telegram_token',
        'OPENROUTER_API_KEY': 'test_openrouter_key'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def sample_transcript():
    """Фикстура с примером субтитров"""
    return [
        {'start': 0.0, 'text': 'Привет всем зрителям!'},
        {'start': 3.5, 'text': 'Сегодня мы поговорим о важной теме.'},
        {'start': 7.2, 'text': 'Это будет интересно и познавательно.'},
        {'start': 11.8, 'text': 'Не забудьте подписаться на канал.'},
        {'start': 15.3, 'text': 'Спасибо за внимание!'}
    ]


@pytest.fixture
def sample_long_transcript():
    """Фикстура с длинными субтитрами (для тестирования разбивки на части)"""
    transcript = []
    for i in range(100):
        transcript.append({
            'start': i * 2.0,
            'text': f'Строка номер {i}. Это довольно длинная строка с множеством слов и деталей, '
                   f'которая поможет протестировать разбивку текста на части. '
                   f'Мы добавляем много информации чтобы превысить лимиты.'
        })
    return transcript


@pytest.fixture
def mock_telegram_objects():
    """Фикстура с mock объектами Telegram"""
    from telegram import Update, Message, User, Chat, CallbackQuery
    
    # Mock User
    user = MagicMock(spec=User)
    user.id = 123456789
    user.first_name = "Test"
    user.username = "testuser"
    
    # Mock Chat
    chat = MagicMock(spec=Chat)
    chat.id = 987654321
    chat.type = "private"
    
    # Mock Message
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.from_user = user
    message.chat = chat
    message.text = "Test message"
    
    # Mock Update
    update = MagicMock(spec=Update)
    update.message = message
    update.effective_user = user
    update.effective_chat = chat
    
    # Mock CallbackQuery
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.id = "test_callback_id"
    callback_query.from_user = user
    callback_query.message = message
    callback_query.data = "test_callback_data"
    
    return {
        'user': user,
        'chat': chat,
        'message': message,
        'update': update,
        'callback_query': callback_query
    }


@pytest.fixture
def mock_youtube_api():
    """Фикстура для мокирования YouTube API"""
    with patch('bot.YouTubeTranscriptApi') as mock_api:
        # Настраиваем mock для list_transcripts
        mock_transcript = MagicMock()
        mock_transcript.language_code = 'ru'
        mock_transcript.language = 'Russian'
        
        mock_api.list_transcripts.return_value = [mock_transcript]
        
        # Настраиваем mock для get_transcript
        sample_transcript = [
            {'start': 0.0, 'text': 'Тестовые субтитры'},
            {'start': 3.0, 'text': 'Для проверки функционала'}
        ]
        mock_api.get_transcript.return_value = sample_transcript
        
        yield mock_api


@pytest.fixture
def mock_openrouter_api():
    """Фикстура для мокирования OpenRouter API"""
    import responses
    
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": "Тестовая суммаризация от ИИ модели"
                        }
                    }
                ]
            },
            status=200
        )
        yield rsps


@pytest.fixture
def clean_user_data():
    """Фикстура для чистого пользовательского контекста"""
    from telegram.ext import ContextTypes
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context


# Хелперы для тестов
class AsyncMockHelper:
    """Помощник для создания асинхронных моков"""
    
    @staticmethod
    def create_async_mock(*args, **kwargs):
        """Создает асинхронный mock"""
        mock = MagicMock(*args, **kwargs)
        
        async def async_side_effect(*args, **kwargs):
            return mock.return_value
        
        mock.side_effect = async_side_effect
        return mock


# Настройки для запуска тестов
pytest_plugins = ['pytest_asyncio'] 