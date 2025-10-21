#!/usr/bin/env python3
"""
Тест для улучшенного модуля транскрипции голосовых сообщений
"""

import os
import sys
import asyncio
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from voice_transcriber import VoiceTranscriber

class TestVoiceTranscriberImproved(unittest.TestCase):
    """Тесты для улучшенного VoiceTranscriber"""
    
    def setUp(self):
        """Настройка тестов"""
        # Создаем временный API ключ для тестов
        os.environ['SONIOX_API_KEY'] = 'test_api_key_12345'
        self.transcriber = VoiceTranscriber()
        
        # Создаем временный аудио файл для тестов
        self.temp_audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        self.temp_audio_file.write(b'fake_audio_data')
        self.temp_audio_file.close()
    
    def tearDown(self):
        """Очистка после тестов"""
        # Удаляем временный файл
        if os.path.exists(self.temp_audio_file.name):
            os.unlink(self.temp_audio_file.name)
        
        # Очищаем переменную окружения
        if 'SONIOX_API_KEY' in os.environ:
            del os.environ['SONIOX_API_KEY']
    
    def test_init_with_retry_settings(self):
        """Тест инициализации с настройками повторных попыток"""
        self.assertEqual(self.transcriber.max_retries, 3)
        self.assertEqual(self.transcriber.base_delay, 2)
        self.assertEqual(self.transcriber.max_delay, 30)
        self.assertIsNotNone(self.transcriber.session)
        self.assertEqual(self.transcriber.session.timeout, (10, 30))
    
    @patch('requests.Session.get')
    async def test_test_connection_with_retries_success(self, mock_get):
        """Тест успешного тестирования соединения с повторными попытками"""
        # Мокаем успешный ответ
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"models": ["test"]}'
        mock_get.return_value = mock_response
        
        result = await self.transcriber.test_connection_with_retries()
        self.assertTrue(result)
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    async def test_test_connection_with_retries_connection_error_then_success(self, mock_get):
        """Тест тестирования соединения с ошибкой соединения, затем успехом"""
        # Первая попытка - ошибка соединения
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Connection aborted"),
            Mock(status_code=200, text='{"models": ["test"]}')
        ]
        
        result = await self.transcriber.test_connection_with_retries()
        self.assertTrue(result)
        self.assertEqual(mock_get.call_count, 2)
    
    @patch('requests.Session.get')
    async def test_test_connection_with_retries_all_failed(self, mock_get):
        """Тест тестирования соединения со всеми неудачными попытками"""
        # Все попытки неудачны
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection aborted")
        
        result = await self.transcriber.test_connection_with_retries()
        self.assertFalse(result)
        self.assertEqual(mock_get.call_count, 3)
    
    @patch('requests.Session.post')
    async def test_upload_file_with_retries_success(self, mock_post):
        """Тест успешной загрузки файла с повторными попытками"""
        # Мокаем успешный ответ
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'file_id': 'test_file_123'}
        mock_post.return_value = mock_response
        
        result = await self.transcriber._upload_file_with_retries(self.temp_audio_file.name)
        self.assertEqual(result, 'test_file_123')
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    async def test_upload_file_with_retries_timeout_then_success(self, mock_post):
        """Тест загрузки файла с таймаутом, затем успехом"""
        # Первая попытка - таймаут
        mock_post.side_effect = [
            requests.exceptions.Timeout("Request timeout"),
            Mock(status_code=201, json=lambda: {'file_id': 'test_file_123'})
        ]
        
        result = await self.transcriber._upload_file_with_retries(self.temp_audio_file.name)
        self.assertEqual(result, 'test_file_123')
        self.assertEqual(mock_post.call_count, 2)
    
    @patch('requests.Session.post')
    async def test_start_transcription_with_retries_success(self, mock_post):
        """Тест успешного запуска транскрипции с повторными попытками"""
        # Мокаем успешный ответ
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'transcription_123'}
        mock_post.return_value = mock_response
        
        result = await self.transcriber._start_transcription_with_retries('test_file_123')
        self.assertEqual(result, 'transcription_123')
        mock_post.assert_called_once()
    
    @patch('requests.Session.get')
    async def test_get_transcript_with_retries_success(self, mock_get):
        """Тест успешного получения транскрипта с повторными попытками"""
        # Мокаем успешный ответ
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'text': 'Привет, это тестовое сообщение',
            'tokens': [{'confidence': 0.95}, {'confidence': 0.98}],
            'language': 'ru',
            'duration': 5.0
        }
        mock_get.return_value = mock_response
        
        text, stats = await self.transcriber._get_transcript_with_retries('transcription_123')
        
        self.assertEqual(text, 'Привет, это тестовое сообщение')
        self.assertEqual(stats['text_length'], 32)
        self.assertEqual(stats['tokens_count'], 2)
        self.assertEqual(stats['language'], 'ru')
        self.assertEqual(stats['duration'], 5.0)
        mock_get.assert_called_once()
    
    def test_calculate_average_confidence(self):
        """Тест вычисления средней уверенности"""
        tokens = [
            {'confidence': 0.8},
            {'confidence': 0.9},
            {'confidence': 1.0}
        ]
        
        avg_confidence = self.transcriber._calculate_average_confidence(tokens)
        self.assertAlmostEqual(avg_confidence, 0.9, places=2)
    
    def test_calculate_average_confidence_empty(self):
        """Тест вычисления средней уверенности для пустого списка"""
        avg_confidence = self.transcriber._calculate_average_confidence([])
        self.assertEqual(avg_confidence, 0.0)
    
    def test_is_available(self):
        """Тест проверки доступности сервиса"""
        self.assertTrue(self.transcriber.is_available())
        
        # Тест без API ключа
        del os.environ['SONIOX_API_KEY']
        transcriber_no_key = VoiceTranscriber()
        self.assertFalse(transcriber_no_key.is_available())

def run_tests():
    """Запуск тестов"""
    # Создаем event loop для асинхронных тестов
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Запускаем тесты
    unittest.main(verbosity=2)

if __name__ == '__main__':
    run_tests()
