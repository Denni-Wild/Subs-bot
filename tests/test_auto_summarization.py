"""
Тесты для автоматического выбора модели суммаризации
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from summarizer import TextSummarizer

@pytest.fixture
def summarizer():
    """Создает экземпляр суммаризатора для тестов"""
    return TextSummarizer()

class TestAutoModelSelection:
    """Тесты автоматического выбора модели"""
    
    def test_get_available_model_index(self, summarizer):
        """Тест автоматического выбора модели"""
        # Проверяем, что возвращается валидный индекс
        index = summarizer.get_available_model_index()
        assert 0 <= index < len(summarizer.models)
        
        # Проверяем, что модель добавляется в использованные
        assert index in summarizer.used_models
        
        # Проверяем, что при повторном выборе возвращается другая модель
        second_index = summarizer.get_available_model_index()
        assert second_index != index
        assert second_index in summarizer.used_models
    
    def test_model_rotation(self, summarizer):
        """Тест ротации моделей"""
        used_indices = set()
        
        # Выбираем все доступные модели
        for _ in range(len(summarizer.models)):
            index = summarizer.get_available_model_index()
            used_indices.add(index)
        
        # Проверяем, что все модели были использованы
        assert len(used_indices) == len(summarizer.models)
        
        # При следующем выборе история должна сброситься
        next_index = summarizer.get_available_model_index()
        assert next_index in summarizer.used_models
        assert len(summarizer.used_models) == 1

class TestSummarizeWithRetry:
    """Тесты системы повторных попыток"""
    
    @pytest.mark.asyncio
    async def test_summarize_with_retry_success_first_try(self, summarizer):
        """Тест успешной суммаризации с первой попытки"""
        with patch.object(summarizer, 'summarize_text', new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = ("Успешная суммаризация", {"model": "test_model"})
            
            result, stats, success = await summarizer.summarize_with_retry("Тестовый текст", max_retries=3)
            
            assert success is True
            assert result == "Успешная суммаризация"
            assert stats["model"] == "test_model"
            mock_summarize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_summarize_with_retry_failure_then_success(self, summarizer):
        """Тест успешной суммаризации со второй попытки"""
        with patch.object(summarizer, 'summarize_text', new_callable=AsyncMock) as mock_summarize:
            # Первая попытка неудачна, вторая успешна
            mock_summarize.side_effect = [
                ("❌ Ошибка", {"model": "first_model"}),
                ("Успешная суммаризация", {"model": "second_model"})
            ]
            
            result, stats, success = await summarizer.summarize_with_retry("Тестовый текст", max_retries=3)
            
            assert success is True
            assert result == "Успешная суммаризация"
            assert stats["model"] == "second_model"
            assert mock_summarize.call_count == 2
    
    @pytest.mark.asyncio
    async def test_summarize_with_retry_all_failures(self, summarizer):
        """Тест всех неудачных попыток"""
        with patch.object(summarizer, 'summarize_text', new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = ("❌ Ошибка", {"model": "test_model"})
            
            result, stats, success = await summarizer.summarize_with_retry("Тестовый текст", max_retries=2)
            
            assert success is False
            assert result.startswith("❌ Все 2 попытки суммаризации не удались")
            assert "used_models" in stats
            assert mock_summarize.call_count == 2

class TestUserFeedbackLogging:
    """Тесты логирования обратной связи пользователя"""
    
    def test_log_user_feedback_positive(self, summarizer):
        """Тест логирования положительной обратной связи"""
        with patch.object(summarizer.summarization_logger, 'info') as mock_logger:
            summarizer.log_user_feedback(
                model_name="test_model",
                text_length=1000,
                summary_length=200,
                user_satisfied=True
            )
            
            mock_logger.assert_called_once()
            log_message = mock_logger.call_args[0][0]
            assert "Пользователь доволен" in log_message
            assert "test_model" in log_message
    
    def test_log_user_feedback_negative_with_reason(self, summarizer):
        """Тест логирования отрицательной обратной связи с причиной"""
        with patch.object(summarizer.summarization_logger, 'info') as mock_logger:
            summarizer.log_user_feedback(
                model_name="test_model",
                text_length=1000,
                summary_length=200,
                user_satisfied=False,
                feedback_reason="Низкое качество"
            )
            
            mock_logger.assert_called_once()
            log_message = mock_logger.call_args[0][0]
            assert "Пользователь не доволен" in log_message
            assert "Низкое качество" in log_message

class TestModelUsageStats:
    """Тесты статистики использования моделей"""
    
    def test_get_model_usage_stats(self, summarizer):
        """Тест получения статистики использования моделей"""
        # Используем несколько моделей
        summarizer.get_available_model_index()
        summarizer.get_available_model_index()
        
        stats = summarizer.get_model_usage_stats()
        
        # Проверяем, что статистика содержит информацию о использованных моделях
        assert len(stats) == 2
        assert all(isinstance(count, int) for count in stats.values())
        assert all(count == 1 for count in stats.values())

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
