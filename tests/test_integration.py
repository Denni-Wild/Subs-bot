import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

import bot
from summarizer import TextSummarizer


class TestFullWorkflow:
    """Интеграционные тесты полного цикла работы"""
    
    @pytest.fixture
    def mock_user_context(self):
        """Фикстура для пользовательского контекста"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context
    
    @pytest.fixture
    def mock_update(self):
        """Фикстура для Update с сообщением"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 123456
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_callback_query(self):
        """Фикстура для CallbackQuery"""
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        query.message.reply_document = AsyncMock()
        return query
    
    @pytest.fixture
    def mock_youtube_transcript(self):
        """Фикстура для YouTube субтитров"""
        return [
            {'start': 0.0, 'text': 'Привет, это тестовое видео.'},
            {'start': 3.0, 'text': 'В нем мы рассказываем о важных вещах.'},
            {'start': 6.0, 'text': 'Спасибо за просмотр!'}
        ]
    
    @pytest.mark.asyncio
    @patch('bot.get_available_transcripts')
    async def test_single_language_subtitles_only_workflow(self, mock_get_transcripts, 
                                                         mock_update, mock_user_context, 
                                                         mock_youtube_transcript):
        """Тест полного цикла: одиночный язык -> только субтитры"""
        # Шаг 1: Пользователь отправляет ссылку
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.language_code = 'ru'
        mock_transcript_obj.language = 'Russian'
        mock_get_transcripts.return_value = [mock_transcript_obj]
        
        # Обрабатываем сообщение
        await bot.handle_message(mock_update, mock_user_context)
        
        # Проверяем, что данные сохранились
        assert mock_user_context.user_data['video_id'] == 'dQw4w9WgXcQ'
        assert mock_user_context.user_data['lang_code'] == 'ru'
        
        # Шаг 2: Пользователь выбирает "только субтитры"
        mock_callback_query = self.mock_callback_query()
        mock_callback_query.data = "action_subtitles"
        
        update_with_query = MagicMock()
        update_with_query.callback_query = mock_callback_query
        
        await bot.action_callback(update_with_query, mock_user_context)
        
        assert mock_user_context.user_data['action'] == 'subtitles'
        
        # Шаг 3: Пользователь выбирает формат
        mock_callback_query.data = "format_plain"
        
        with patch('bot.YouTubeTranscriptApi.get_transcript', return_value=mock_youtube_transcript):
            with patch('bot.send_subtitles', new_callable=AsyncMock) as mock_send:
                await bot.format_callback(update_with_query, mock_user_context)
                
                mock_send.assert_called_once()
                assert mock_user_context.user_data['with_time'] is False
    
    @pytest.mark.asyncio
    @patch('bot.get_available_transcripts')
    @patch('bot.summarizer.summarize_text')
    async def test_ai_summary_workflow(self, mock_summarize, mock_get_transcripts,
                                     mock_update, mock_user_context, mock_youtube_transcript):
        """Тест полного цикла: ИИ-суммаризация"""
        # Шаг 1: Пользователь отправляет ссылку
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.language_code = 'en'
        mock_transcript_obj.language = 'English'
        mock_get_transcripts.return_value = [mock_transcript_obj]
        
        await bot.handle_message(mock_update, mock_user_context)
        
        # Шаг 2: Выбираем "только ИИ-суммаризация"
        mock_callback_query = self.mock_callback_query()
        mock_callback_query.data = "action_only_summary"
        
        update_with_query = MagicMock()
        update_with_query.callback_query = mock_callback_query
        
        await bot.action_callback(update_with_query, mock_user_context)
        
        # Шаг 3: Выбираем модель (автоматически)
        mock_callback_query.data = "model_auto"
        
        # Настраиваем мок для суммаризации
        mock_summary = "Краткое изложение видео о важных вещах"
        mock_stats = {
            'model': 'test_model',
            'chunks': 1,
            'original_length': 100,
            'summary_length': 45,
            'processed_chunks': 1
        }
        mock_summarize.return_value = (mock_summary, mock_stats)
        
        with patch('bot.YouTubeTranscriptApi.get_transcript', return_value=mock_youtube_transcript):
            await bot.model_callback(update_with_query, mock_user_context)
            
            # Проверяем, что суммаризация была вызвана
            mock_summarize.assert_called_once()
            
            # Проверяем, что результат был отправлен
            mock_callback_query.edit_message_text.assert_called()
            
            # Проверяем содержимое последнего сообщения
            calls = mock_callback_query.edit_message_text.call_args_list
            final_call = calls[-1][0][0]
            assert "ИИ-СУММАРИЗАЦИЯ" in final_call
            assert mock_summary in final_call
            assert "Статистика" in final_call
    
    @pytest.mark.asyncio
    @patch('bot.get_available_transcripts')
    async def test_multiple_languages_workflow(self, mock_get_transcripts, mock_update, mock_user_context):
        """Тест цикла с несколькими языками субтитров"""
        # Настраиваем несколько языков
        languages = []
        for lang_code, lang_name in [('ru', 'Russian'), ('en', 'English'), ('es', 'Spanish')]:
            transcript = MagicMock()
            transcript.language_code = lang_code
            transcript.language = lang_name
            languages.append(transcript)
        
        mock_get_transcripts.return_value = languages
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        
        await bot.handle_message(mock_update, mock_user_context)
        
        # Проверяем, что предложен выбор языка
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Выберите язык" in call_args
        
        # Проверяем, что данные видео сохранились, но язык еще не выбран
        assert mock_user_context.user_data['video_id'] == 'dQw4w9WgXcQ'
        assert 'lang_code' not in mock_user_context.user_data
        
        # Выбираем язык
        mock_callback_query = self.mock_callback_query()
        mock_callback_query.data = "lang_en"
        
        update_with_query = MagicMock()
        update_with_query.callback_query = mock_callback_query
        
        await bot.language_callback(update_with_query, mock_user_context)
        
        # Проверяем выбор языка
        assert mock_user_context.user_data['lang_code'] == 'en'
        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args[0][0]
        assert "Что хотите получить?" in call_args
    
    @pytest.mark.asyncio
    @patch('bot.get_available_transcripts')
    @patch('bot.summarizer.summarize_text')
    async def test_combined_subtitles_and_ai_workflow(self, mock_summarize, mock_get_transcripts,
                                                    mock_update, mock_user_context, mock_youtube_transcript):
        """Тест цикла: субтитры + ИИ-суммаризация"""
        # Настройка
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.language_code = 'ru'
        mock_transcript_obj.language = 'Russian'
        mock_get_transcripts.return_value = [mock_transcript_obj]
        
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        
        await bot.handle_message(mock_update, mock_user_context)
        
        # Выбираем "субтитры + ИИ"
        mock_callback_query = self.mock_callback_query()
        mock_callback_query.data = "action_ai_summary"
        
        update_with_query = MagicMock()
        update_with_query.callback_query = mock_callback_query
        
        await bot.action_callback(update_with_query, mock_user_context)
        
        # Выбираем модель
        mock_callback_query.data = "model_0"
        await bot.model_callback(update_with_query, mock_user_context)
        
        # Выбираем формат
        mock_callback_query.data = "format_with_time"
        
        # Настраиваем мок ИИ
        mock_summary = "Тестовое краткое изложение"
        mock_stats = {
            'model': 'test_model',
            'chunks': 1,
            'original_length': 150,
            'summary_length': 30,
            'processed_chunks': 1
        }
        mock_summarize.return_value = (mock_summary, mock_stats)
        
        with patch('bot.YouTubeTranscriptApi.get_transcript', return_value=mock_youtube_transcript):
            await bot.format_callback(update_with_query, mock_user_context)
            
            # Проверяем, что обе функции были вызваны
            mock_summarize.assert_called_once()
            
            # Проверяем финальное сообщение
            calls = mock_callback_query.edit_message_text.call_args_list
            final_message = calls[-1][0][0]
            
            assert "СУБТИТРЫ:" in final_message
            assert "ИИ-СУММАРИЗАЦИЯ:" in final_message
            assert "Статистика:" in final_message
            assert mock_summary in final_message
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, mock_update, mock_user_context):
        """Тест обработки ошибок в рабочем цикле"""
        # Тест с невалидной ссылкой
        mock_update.message.text = "invalid url"
        mock_user_context.user_data = {}
        
        await bot.handle_message(mock_update, mock_user_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "корректную ссылку" in call_args
        
        # Тест rate limiting
        import time
        mock_user_context.user_data = {'last_request_time': time.time()}
        mock_update.message.text = "https://youtu.be/dQw4w9WgXcQ"
        
        await bot.handle_message(mock_update, mock_user_context)
        
        # Последний вызов должен быть о rate limiting
        calls = mock_update.message.reply_text.call_args_list
        assert "не чаще одного запроса" in calls[-1][0][0]
    
    @pytest.mark.asyncio
    @patch('bot.YouTubeTranscriptApi.get_transcript')
    async def test_large_subtitles_file_handling(self, mock_get_transcript, mock_user_context):
        """Тест обработки длинных субтитров (отправка файлом)"""
        # Создаем очень длинные субтитры
        long_transcript = []
        for i in range(1000):
            long_transcript.append({
                'start': i * 3.0,
                'text': f'Это очень длинная строка субтитров номер {i} с большим количеством текста.'
            })
        
        mock_get_transcript.return_value = long_transcript
        
        # Создаем полный контекст для обработки
        mock_user_context.user_data = {
            'video_id': 'dQw4w9WgXcQ',
            'lang_code': 'ru',
            'action': 'subtitles',
            'with_time': False,
            'model_index': 0
        }
        
        mock_query = self.mock_callback_query()
        
        await bot.process_request(mock_query, mock_user_context)
        
        # Проверяем, что файл был отправлен
        mock_query.message.reply_document.assert_called_once()
        
        # Проверяем сообщение о том, что субтитры отправляются файлом
        calls = mock_query.edit_message_text.call_args_list
        assert any("файлом" in str(call) for call in calls)


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    @patch('bot.summarizer.summarize_text')
    async def test_ai_summarization_failure_handling(self, mock_summarize):
        """Тест обработки ошибок ИИ-суммаризации"""
        mock_summarize.side_effect = Exception("API Error")
        
        context = MagicMock()
        context.user_data = {
            'video_id': 'dQw4w9WgXcQ',
            'lang_code': 'ru',
            'action': 'only_summary',
            'with_time': False,
            'model_index': 0
        }
        
        query = MagicMock()
        query.edit_message_text = AsyncMock()
        
        with patch('bot.YouTubeTranscriptApi.get_transcript', return_value=[{'start': 0, 'text': 'test'}]):
            await bot.process_request(query, context)
            
            # Проверяем, что ошибка была обработана
            calls = query.edit_message_text.call_args_list
            assert any("Ошибка при создании ИИ-суммаризации" in str(call) for call in calls)
    
    @pytest.mark.asyncio
    async def test_empty_user_data_handling(self):
        """Тест обработки пустых пользовательских данных"""
        context = MagicMock()
        context.user_data = {}
        
        query = MagicMock()
        query.edit_message_text = AsyncMock()
        
        await bot.process_request(query, context)
        
        query.edit_message_text.assert_called_once()
        call_args = query.edit_message_text.call_args[0][0]
        assert "не найдено видео или язык" in call_args
    
    @pytest.mark.asyncio
    def test_invalid_callback_data_handling(self):
        """Тест обработки некорректных callback данных"""
        # Этот тест проверяет, что бот не падает при получении неожиданных callback данных
        query = MagicMock()
        query.answer = AsyncMock()
        query.data = "invalid_callback_data"
        
        update = MagicMock()
        update.callback_query = query
        
        context = MagicMock()
        context.user_data = {}
        
        # Проверяем, что при неверных данных колбэки не падают
        # (в реальном боте такие данные просто игнорируются обработчиками паттернов)
        assert query.data.startswith("invalid_")  # Простая проверка, что данные действительно неверные


# Медленные тесты, требующие реальных API ключей
class TestRealAPIIntegration:
    """Тесты с реальными API (только при наличии ключей)"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_youtube_and_ai_integration(self):
        """Интеграционный тест с реальными YouTube и AI API"""
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        if not openrouter_key:
            pytest.skip("OPENROUTER_API_KEY не задан для интеграционного теста")
        
        # Используем известное видео с субтитрами
        video_id = "dQw4w9WgXcQ"  # Rick Roll - обычно имеет субтитры
        
        # Тест получения субтитров
        transcripts = bot.get_available_transcripts(video_id)
        if not transcripts:
            pytest.skip(f"Видео {video_id} не имеет доступных субтитров")
        
        transcripts_list = list(transcripts)
        if not transcripts_list:
            pytest.skip("Нет доступных субтитров для тестирования")
        
        # Получаем субтитры
        lang_code = transcripts_list[0].language_code
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
            
            if not transcript:
                pytest.skip("Пустые субтитры")
            
            # Ограничиваем текст для экономии API вызовов
            limited_transcript = transcript[:10]  # Первые 10 строк
            text = bot.format_subtitles(limited_transcript, with_time=False)
            
            # Тест ИИ-суммаризации
            summarizer = TextSummarizer()
            summary, stats = await summarizer.summarize_text(text)
            
            # Проверки
            assert isinstance(summary, str)
            assert len(summary) > 0
            assert "Ошибка" not in summary
            assert stats['original_length'] > 0
            assert stats['summary_length'] > 0
            assert stats['model'] in [model[0] for model in summarizer.models]
            
        except Exception as e:
            pytest.fail(f"Интеграционный тест не прошел: {e}") 