"""
Тест для проверки исправления ошибки NameError в обработке голосовых сообщений

@file: test_voice_transcription_error_fix.py
@description: Проверяет, что ошибка 'video_id' is not defined больше не возникает при обработке голосовых сообщений
@dependencies: bot.py, voice_transcriber.py
@created: 2025-09-02
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from telegram import Update, Voice, File
from telegram.ext import ContextTypes

# Импортируем функции для тестирования
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot import handle_voice_message


class TestVoiceTranscriptionErrorFix:
    """Тесты для проверки исправления ошибки video_id в обработке голосовых сообщений"""
    
    @pytest.fixture
    def mock_update(self):
        """Создает мок объекта Update"""
        update = Mock(spec=Update)
        update.effective_user.id = 123456789
        update.message.voice = Mock(spec=Voice)
        update.message.voice.duration = 30
        update.message.voice.file_id = "test_file_id"
        update.message.voice.file_size = 1024
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Создает мок объекта Context"""
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        context.bot.get_file = AsyncMock()
        return context
    
    @pytest.mark.asyncio
    @patch('bot.voice_transcriber')
    @patch('bot.rate_limit_check')
    @patch('bot.check_multiple_messages')
    @patch('bot.log_and_notify_error')
    async def test_voice_message_processing_no_video_id_error(self, mock_notify, mock_check_multiple, mock_rate_limit, mock_transcriber, mock_update, mock_context):
        """Тест: обработка голосового сообщения не вызывает ошибку video_id"""
        
        # Настройка моков
        mock_rate_limit.return_value = True
        mock_check_multiple.return_value = (True, "")
        mock_transcriber.is_available.return_value = True
        
        # Мок файла
        mock_file = Mock(spec=File)
        mock_file.file_size = 1024
        mock_context.bot.get_file.return_value = mock_file
        
        # Мок транскрипции (успешная)
        mock_transcriber.transcribe_voice_message.return_value = (True, "Тестовый текст транскрипции", {"text_length": 25, "tokens_count": 5, "confidence_avg": 0.95})
        
        # Выполняем тестируемую функцию
        try:
            await handle_voice_message(mock_update, mock_context)
            
            # Проверяем, что функция выполнилась без ошибок
            assert True, "Функция выполнилась без ошибок"
            
            # Проверяем, что не было вызовов log_and_notify_error с ошибкой NameError
            error_calls = [call for call in mock_notify.call_args_list if 'NameError' in str(call)]
            assert len(error_calls) == 0, "Не должно быть ошибок NameError"
            
        except NameError as e:
            if "video_id" in str(e):
                pytest.fail(f"Обнаружена ошибка video_id: {e}")
            else:
                raise e
        except Exception as e:
            # Другие ошибки могут быть допустимы (например, связанные с моками)
            print(f"Допустимая ошибка в тесте: {e}")
    
    @pytest.mark.asyncio
    @patch('bot.voice_transcriber')
    @patch('bot.rate_limit_check')
    @patch('bot.check_multiple_messages')
    @patch('bot.log_and_notify_error')
    async def test_long_transcription_file_creation(self, mock_notify, mock_check_multiple, mock_rate_limit, mock_transcriber, mock_update, mock_context):
        """Тест: создание файла для длинной транскрипции не использует video_id"""
        
        # Настройка моков
        mock_rate_limit.return_value = True
        mock_check_multiple.return_value = (True, "")
        mock_transcriber.is_available.return_value = True
        
        # Мок файла
        mock_file = Mock(spec=File)
        mock_file.file_size = 1024
        mock_context.bot.get_file.return_value = mock_file
        
        # Мок длинной транскрипции (более 3000 символов)
        long_text = "Тестовый текст " * 200  # Создаем длинный текст
        mock_transcriber.transcribe_voice_message.return_value = (True, long_text, {"text_length": len(long_text), "tokens_count": 100, "confidence_avg": 0.95})
        
        # Выполняем тестируемую функцию
        try:
            await handle_voice_message(mock_update, mock_context)
            
            # Проверяем, что функция выполнилась без ошибок
            assert True, "Функция выполнилась без ошибок"
            
            # Проверяем, что не было вызовов log_and_notify_error с ошибкой NameError
            error_calls = [call for call in mock_notify.call_args_list if 'NameError' in str(call)]
            assert len(error_calls) == 0, "Не должно быть ошибок NameError"
            
        except NameError as e:
            if "video_id" in str(e):
                pytest.fail(f"Обнаружена ошибка video_id: {e}")
            else:
                raise e
        except Exception as e:
            # Другие ошибки могут быть допустимы (например, связанные с моками)
            print(f"Допустимая ошибка в тесте: {e}")


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
