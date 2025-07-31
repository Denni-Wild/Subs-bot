import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import Update, Message, User, Chat, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import bot
from summarizer import TextSummarizer


class TestBotUtilityFunctions:
    """Тесты вспомогательных функций бота"""
    
    def test_extract_video_id_youtube_watch(self):
        """Тест извлечения ID из ссылки youtube.com/watch"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = bot.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_youtu_be(self):
        """Тест извлечения ID из короткой ссылки youtu.be"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = bot.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_embed(self):
        """Тест извлечения ID из embed ссылки"""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = bot.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_direct(self):
        """Тест извлечения ID из прямого ID"""
        video_id = bot.extract_video_id("dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"
    
    def test_extract_video_id_invalid(self):
        """Тест с невалидными ссылками"""
        invalid_urls = [
            "https://www.google.com",
            "not a url",
            "https://youtube.com/invalid",
            "shortid"
        ]
        
        for url in invalid_urls:
            video_id = bot.extract_video_id(url)
            assert video_id is None
    
    @patch('bot.YouTubeTranscriptApi.list_transcripts')
    def test_get_available_transcripts_success(self, mock_list):
        """Тест успешного получения списка субтитров"""
        mock_transcript = MagicMock()
        mock_transcript.language_code = 'ru'
        mock_transcript.language = 'Russian'
        mock_list.return_value = [mock_transcript]
        
        result = bot.get_available_transcripts("test_video_id")
        
        assert result is not None
        mock_list.assert_called_once_with("test_video_id")
    
    @patch('bot.YouTubeTranscriptApi.list_transcripts')
    def test_get_available_transcripts_error(self, mock_list):
        """Тест обработки ошибки при получении субтитров"""
        mock_list.side_effect = Exception("API Error")
        
        result = bot.get_available_transcripts("test_video_id")
        
        assert result is None
    
    def test_format_subtitles_with_time(self):
        """Тест форматирования субтитров с временными метками"""
        transcript = [
            {'start': 0.0, 'text': 'Первая строка'},
            {'start': 65.5, 'text': 'Вторая строка'}
        ]
        
        result = bot.format_subtitles(transcript, with_time=True)
        
        expected = "[00:00] Первая строка\n[01:05] Вторая строка"
        assert result == expected
    
    def test_format_subtitles_plain(self):
        """Тест форматирования субтитров без временных меток"""
        transcript = [
            {'start': 0.0, 'text': 'Первая строка'},
            {'start': 65.5, 'text': 'Вторая строка'}
        ]
        
        result = bot.format_subtitles(transcript, with_time=False)
        
        expected = "Первая строка\nВторая строка"
        assert result == expected


class TestBotKeyboards:
    """Тесты создания клавиатур"""
    
    def test_build_language_keyboard(self):
        """Тест создания клавиатуры выбора языка"""
        mock_transcripts = []
        for lang_code, lang_name in [('ru', 'Russian'), ('en', 'English')]:
            transcript = MagicMock()
            transcript.language_code = lang_code
            transcript.language = lang_name
            mock_transcripts.append(transcript)
        
        keyboard = bot.build_language_keyboard(mock_transcripts)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2
        assert keyboard.inline_keyboard[0][0].text == "Russian (ru)"
        assert keyboard.inline_keyboard[0][0].callback_data == "lang_ru"
    
    def test_build_action_keyboard(self):
        """Тест создания клавиатуры выбора действия"""
        keyboard = bot.build_action_keyboard()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3
        
        # Проверяем тексты кнопок
        texts = [row[0].text for row in keyboard.inline_keyboard]
        assert "📄 Только субтитры" in texts
        assert "🤖 Субтитры + ИИ-суммаризация" in texts
        assert "🔮 Только ИИ-суммаризация" in texts
    
    def test_build_format_keyboard(self):
        """Тест создания клавиатуры выбора формата"""
        keyboard = bot.build_format_keyboard()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2
        
        texts = [row[0].text for row in keyboard.inline_keyboard]
        assert "С временными метками" in texts
        assert "Без временных меток" in texts
    
    @patch('bot.summarizer')
    def test_build_model_keyboard(self, mock_summarizer):
        """Тест создания клавиатуры выбора модели"""
        mock_models = ['model1', 'model2', 'model3', 'model4', 'model5', 'model6', 'model7']
        mock_summarizer.get_available_models.return_value = mock_models
        
        keyboard = bot.build_model_keyboard()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # 6 моделей + кнопка "Быстрый выбор"
        assert len(keyboard.inline_keyboard) == 7


class TestBotHandlers:
    """Тесты обработчиков бота"""
    
    @pytest.fixture
    def mock_update(self):
        """Фикстура для создания mock Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 123456
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.message.text = "test message"
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Фикстура для создания mock Context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.mark.asyncio
    async def test_start_handler(self, mock_update, mock_context):
        """Тест обработчика /start"""
        await bot.start(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert bot.START_MESSAGE in call_args[0]
    
    @pytest.mark.asyncio
    async def test_help_handler(self, mock_update, mock_context):
        """Тест обработчика /help"""
        await bot.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert bot.HELP_MESSAGE in call_args[0]
    
    @pytest.mark.asyncio
    async def test_handle_message_rate_limit(self, mock_update, mock_context):
        """Тест антиспама в handle_message с новыми функциями rate limiting"""
        import time
        
        # Устанавливаем время последнего запроса как текущее
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        mock_context.user_data = {}
        
        # Mock the processing message
        mock_processing_msg = MagicMock()
        mock_processing_msg.edit_text = AsyncMock()
        mock_update.message.reply_text.return_value = mock_processing_msg
        
        # Первый запрос должен пройти
        with patch('bot.rate_limit_check', return_value=True):
            with patch('bot.get_available_transcripts_with_retry') as mock_get_transcripts:
                mock_transcript = MagicMock()
                mock_transcript.language_code = 'ru'
                mock_transcript.language = 'Russian'
                mock_get_transcripts.return_value = ([mock_transcript], True, None)
                
                await bot.handle_message(mock_update, mock_context)
                
                # Проверяем, что запрос прошел успешно
                # Первый вызов - processing message
                mock_update.message.reply_text.assert_called_once_with('🔄 Получаю информацию о субтитрах...')
                # Второй вызов - результат через edit_text
                mock_processing_msg.edit_text.assert_called_once()
                call_args = mock_processing_msg.edit_text.call_args[0][0]
                assert "Что хотите получить?" in call_args
        
        # Второй запрос должен быть заблокирован
        with patch('bot.rate_limit_check', return_value=False):
            await bot.handle_message(mock_update, mock_context)
            
            # Должен быть дополнительный вызов reply_text для ошибки
            assert mock_update.message.reply_text.call_count >= 2
            # Проверяем последний вызов (ошибка rate limit)
            last_call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Слишком много запросов" in last_call_args
    
    @pytest.mark.asyncio
    async def test_handle_message_invalid_url(self, mock_update, mock_context):
        """Тест обработки невалидной ссылки"""
        mock_update.message.text = "invalid url"
        mock_context.user_data = {}
        
        await bot.handle_message(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "корректную ссылку" in call_args
    
    @pytest.mark.asyncio
    @patch('bot.get_available_transcripts_with_retry')
    async def test_handle_message_no_transcripts(self, mock_get_transcripts, mock_update, mock_context):
        """Тест когда субтитры недоступны"""
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        mock_context.user_data = {}
        mock_get_transcripts.return_value = (None, False, "Субтитры не найдены")
        
        # Mock the processing message
        mock_processing_msg = MagicMock()
        mock_processing_msg.edit_text = AsyncMock()
        mock_update.message.reply_text.return_value = mock_processing_msg
        
        # Mock rate limiting to allow the request
        with patch('bot.rate_limit_check', return_value=True):
            await bot.handle_message(mock_update, mock_context)
            
            # First call should be processing message
            mock_update.message.reply_text.assert_called_once_with('🔄 Получаю информацию о субтитрах...')
            # Second call should be error message
            mock_processing_msg.edit_text.assert_called_once_with('❌ Субтитры не найдены')
    
    @pytest.mark.asyncio
    @patch('bot.get_available_transcripts_with_retry')
    async def test_handle_message_single_language(self, mock_get_transcripts, mock_update, mock_context):
        """Тест с одним доступным языком"""
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        mock_context.user_data = {}
        
        mock_transcript = MagicMock()
        mock_transcript.language_code = 'ru'
        mock_transcript.language = 'Russian'
        mock_get_transcripts.return_value = ([mock_transcript], True, None)
        
        # Mock the processing message
        mock_processing_msg = MagicMock()
        mock_processing_msg.edit_text = AsyncMock()
        mock_update.message.reply_text.return_value = mock_processing_msg
        
        # Mock rate limiting to allow the request
        with patch('bot.rate_limit_check', return_value=True):
            await bot.handle_message(mock_update, mock_context)
            
            # Проверяем, что язык сохранился в контексте
            assert mock_context.user_data['lang_code'] == 'ru'
            assert mock_context.user_data['video_id'] == 'dQw4w9WgXcQ'
            
            # First call should be processing message
            mock_update.message.reply_text.assert_called_once_with('🔄 Получаю информацию о субтитрах...')
            # Second call should be result
            mock_processing_msg.edit_text.assert_called_once()
            call_args = mock_processing_msg.edit_text.call_args[0][0]
            assert "Что хотите получить?" in call_args
    
    @pytest.mark.asyncio
    async def test_language_callback(self, mock_context):
        """Тест callback для выбора языка"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "lang_en"
        query.edit_message_text = AsyncMock()
        
        update = MagicMock(spec=Update)
        update.callback_query = query
        
        await bot.language_callback(update, mock_context)
        
        assert mock_context.user_data['lang_code'] == 'en'
        query.answer.assert_called_once()
        query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_action_callback_subtitles_only(self, mock_context):
        """Тест callback для выбора действия 'только субтитры'"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "action_subtitles"
        query.edit_message_text = AsyncMock()
        
        update = MagicMock(spec=Update)
        update.callback_query = query
        
        await bot.action_callback(update, mock_context)
        
        assert mock_context.user_data['action'] == 'subtitles'
        query.edit_message_text.assert_called_once()
        call_args = query.edit_message_text.call_args[0][0]
        assert "формат субтитров" in call_args
    
    @pytest.mark.asyncio
    async def test_action_callback_ai_summary(self, mock_context):
        """Тест callback для выбора действия 'ИИ-суммаризация'"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "action_ai_summary"
        query.edit_message_text = AsyncMock()
        
        update = MagicMock(spec=Update)
        update.callback_query = query
        
        await bot.action_callback(update, mock_context)
        
        assert mock_context.user_data['action'] == 'ai_summary'
        query.edit_message_text.assert_called_once()
        call_args = query.edit_message_text.call_args[0][0]
        assert "ИИ-модель" in call_args
    
    @pytest.mark.asyncio 
    async def test_model_callback_auto(self, mock_context):
        """Тест callback для автоматического выбора модели"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "model_auto"
        query.edit_message_text = AsyncMock()
        
        update = MagicMock(spec=Update)
        update.callback_query = query
        
        mock_context.user_data = {'action': 'only_summary'}
        
        with patch('bot.process_request', new_callable=AsyncMock) as mock_process:
            await bot.model_callback(update, mock_context)
        
        assert mock_context.user_data['model_index'] == 0
        mock_process.assert_called_once_with(query, mock_context)
    
    @pytest.mark.asyncio
    async def test_format_callback(self, mock_context):
        """Тест callback для выбора формата"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "format_with_time"
        
        update = MagicMock(spec=Update)
        update.callback_query = query
        
        with patch('bot.process_request', new_callable=AsyncMock) as mock_process:
            await bot.format_callback(update, mock_context)
        
        assert mock_context.user_data['with_time'] is True
        mock_process.assert_called_once_with(query, mock_context)


class TestBotProcessRequest:
    """Тесты основной функции обработки запросов"""
    
    @pytest.fixture
    def mock_query(self):
        """Фикстура для mock CallbackQuery"""
        query = MagicMock(spec=CallbackQuery)
        query.edit_message_text = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        query.message.reply_document = AsyncMock()
        return query
    
    @pytest.fixture
    def mock_context_with_data(self):
        """Фикстура для контекста с данными"""
        context = MagicMock()
        context.user_data = {
            'video_id': 'dQw4w9WgXcQ',
            'lang_code': 'ru',
            'action': 'subtitles',
            'with_time': False,
            'model_index': 0
        }
        return context
    
    @pytest.mark.asyncio
    async def test_process_request_missing_data(self, mock_query):
        """Тест обработки запроса без данных"""
        context = MagicMock()
        context.user_data = {}
        
        await bot.process_request(mock_query, context)
        
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "не найдено видео или язык" in call_args
    
    @pytest.mark.asyncio
    @patch('bot.get_transcript_with_retry')
    @patch('bot.send_subtitles')
    async def test_process_request_subtitles_only(self, mock_send_subs, mock_get_transcript, 
                                                mock_query, mock_context_with_data):
        """Тест обработки запроса только субтитров"""
        mock_transcript = [
            {'start': 0.0, 'text': 'Тест'},
            {'start': 1.0, 'text': 'субтитров'}
        ]
        mock_get_transcript.return_value = (mock_transcript, True, None)
        mock_send_subs.return_value = AsyncMock()
        
        await bot.process_request(mock_query, mock_context_with_data)
        
        mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ', ['ru'])
        mock_send_subs.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('bot.get_transcript_with_retry')
    @patch('bot.summarizer.summarize_text')
    async def test_process_request_ai_summary(self, mock_summarize, mock_get_transcript,
                                            mock_query, mock_context_with_data):
        """Тест обработки запроса с ИИ-суммаризацией"""
        mock_context_with_data.user_data['action'] = 'only_summary'
        
        mock_transcript = [{'start': 0.0, 'text': 'Тестовый текст'}]
        mock_get_transcript.return_value = (mock_transcript, True, None)
        
        mock_summary = "Краткое изложение"
        mock_stats = {
            'model': 'test_model',
            'chunks': 1,
            'original_length': 100,
            'summary_length': 50
        }
        mock_summarize.return_value = (mock_summary, mock_stats)
        
        await bot.process_request(mock_query, mock_context_with_data)
        
        mock_summarize.assert_called_once()
        mock_query.edit_message_text.assert_called()
        
        # Проверяем, что отображался прогресс
        calls = mock_query.edit_message_text.call_args_list
        assert any("Создаю ИИ-суммаризацию" in str(call) for call in calls)
    
    @pytest.mark.asyncio
    @patch('bot.get_transcript_with_retry')
    async def test_process_request_transcript_error(self, mock_get_transcript, mock_query, mock_context_with_data):
        """Тест обработки ошибки получения субтитров"""
        mock_get_transcript.return_value = (None, False, "У этого видео субтитры отключены.")
        
        await bot.process_request(mock_query, mock_context_with_data)
        
        mock_query.edit_message_text.assert_called_once()
        call_args = mock_query.edit_message_text.call_args[0][0]
        assert "субтитры отключены" in call_args


class TestRateLimiting:
    """Тесты функций rate limiting"""
    
    def setup_method(self):
        """Сброс глобального состояния перед каждым тестом"""
        import bot
        bot.request_timestamps.clear()
        bot.global_last_request = 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_success(self):
        """Тест успешной проверки rate limit"""
        user_id = 12345
        
        # Первый запрос должен пройти
        result = await bot.rate_limit_check(user_id)
        assert result is True
        
        # Второй запрос сразу должен быть заблокирован
        result = await bot.rate_limit_check(user_id)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_after_interval(self):
        """Тест rate limit после истечения интервала"""
        user_id = 12345
        
        # Первый запрос
        result = await bot.rate_limit_check(user_id)
        assert result is True
        
        # Ждем больше интервала
        import time
        time.sleep(16)  # MIN_REQUEST_INTERVAL = 15
        
        # Запрос должен пройти
        result = await bot.rate_limit_check(user_id)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_global_rate_limit_check_success(self):
        """Тест успешной проверки глобального rate limit"""
        # Первый запрос должен пройти
        result = await bot.global_rate_limit_check()
        assert result is True
        
        # Второй запрос сразу должен быть заблокирован
        result = await bot.global_rate_limit_check()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_global_rate_limit_check_after_interval(self):
        """Тест глобального rate limit после истечения интервала"""
        # Первый запрос
        result = await bot.global_rate_limit_check()
        assert result is True
        
        # Ждем больше интервала
        import time
        time.sleep(3)  # 2 seconds minimum interval
        
        # Запрос должен пройти
        result = await bot.global_rate_limit_check()
        assert result is True
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.get_transcript')
    @patch('bot.global_rate_limit_check')
    async def test_get_transcript_with_retry_success(self, mock_global_check, mock_get_transcript):
        """Тест успешного получения транскрипта с retry"""
        mock_global_check.return_value = True
        mock_get_transcript.return_value = [{'start': 0, 'text': 'Test'}]
        
        result, success, error = await bot.get_transcript_with_retry("test_video", ["en"])
        
        assert success is True
        assert error is None
        assert result == [{'start': 0, 'text': 'Test'}]
        mock_get_transcript.assert_called_once_with("test_video", languages=["en"])
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.get_transcript')
    @patch('bot.global_rate_limit_check')
    async def test_get_transcript_with_retry_rate_limit(self, mock_global_check, mock_get_transcript):
        """Тест retry при rate limit"""
        mock_global_check.return_value = True
        mock_get_transcript.side_effect = Exception("Too Many Requests")
        
        result, success, error = await bot.get_transcript_with_retry("test_video", ["en"], max_retries=1)
        
        assert success is False
        assert "Превышен лимит запросов" in error
        assert result is None
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.get_transcript')
    @patch('bot.global_rate_limit_check')
    async def test_get_transcript_with_retry_transcripts_disabled(self, mock_global_check, mock_get_transcript):
        """Тест retry при отключенных субтитрах"""
        from youtube_transcript_api import TranscriptsDisabled
        
        mock_global_check.return_value = True
        mock_get_transcript.side_effect = TranscriptsDisabled("test_video_id")
        
        result, success, error = await bot.get_transcript_with_retry("test_video", ["en"], max_retries=1)
        
        assert success is False
        assert "Subtitles are disabled" in error or "субтитры отключены" in error
        assert result is None
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.get_transcript')
    @patch('bot.global_rate_limit_check')
    async def test_get_transcript_with_retry_no_transcript_found(self, mock_global_check, mock_get_transcript):
        """Тест retry при отсутствии субтитров"""
        from youtube_transcript_api import NoTranscriptFound
        
        mock_global_check.return_value = True
        mock_get_transcript.side_effect = NoTranscriptFound("test_video_id", ["en"], {})
        
        result, success, error = await bot.get_transcript_with_retry("test_video", ["en"], max_retries=1)
        
        assert success is False
        assert "No transcripts were found" in error or "не найдены" in error
        assert result is None
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.list_transcripts')
    @patch('bot.global_rate_limit_check')
    async def test_get_available_transcripts_with_retry_success(self, mock_global_check, mock_list_transcripts):
        """Тест успешного получения списка транскриптов с retry"""
        mock_global_check.return_value = True
        
        mock_transcript = MagicMock()
        mock_transcript.language_code = 'en'
        mock_transcript.language = 'English'
        mock_list_transcripts.return_value = [mock_transcript]
        
        result, success, error = await bot.get_available_transcripts_with_retry("test_video")
        
        assert success is True
        assert error is None
        assert len(result) == 1
        assert result[0].language_code == 'en'
        mock_list_transcripts.assert_called_once_with("test_video")
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.list_transcripts')
    @patch('bot.global_rate_limit_check')
    async def test_get_available_transcripts_with_retry_rate_limit(self, mock_global_check, mock_list_transcripts):
        """Тест retry при rate limit для списка транскриптов"""
        mock_global_check.return_value = True
        mock_list_transcripts.side_effect = Exception("Too Many Requests")
        
        result, success, error = await bot.get_available_transcripts_with_retry("test_video", max_retries=1)
        
        assert success is False
        assert "Превышен лимит запросов" in error
        assert result is None
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.list_transcripts')
    @patch('bot.global_rate_limit_check')
    async def test_get_available_transcripts_with_retry_video_unavailable(self, mock_global_check, mock_list_transcripts):
        """Тест retry при недоступном видео"""
        mock_global_check.return_value = True
        mock_list_transcripts.side_effect = Exception("Video unavailable")
        
        result, success, error = await bot.get_available_transcripts_with_retry("test_video", max_retries=1)
        
        assert success is False
        assert "недоступно" in error
        assert result is None
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_different_users(self):
        """Тест rate limit для разных пользователей"""
        user1 = 12345
        user2 = 67890
        
        # Оба пользователя должны иметь возможность сделать запросы
        result1 = await bot.rate_limit_check(user1)
        result2 = await bot.rate_limit_check(user2)
        
        assert result1 is True
        assert result2 is True
        
        # Повторные запросы должны быть заблокированы
        result1 = await bot.rate_limit_check(user1)
        result2 = await bot.rate_limit_check(user2)
        
        assert result1 is False
        assert result2 is False
    
    @pytest.mark.asyncio
    async def test_global_rate_limit_concurrent_requests(self):
        """Тест глобального rate limit при конкурентных запросах"""
        import asyncio
        
        # Создаем несколько конкурентных запросов
        async def make_request():
            return await bot.global_rate_limit_check()
        
        # Запускаем несколько запросов одновременно
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Только один запрос должен пройти
        assert sum(results) == 1 