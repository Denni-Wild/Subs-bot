import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
import responses
from summarizer import TextSummarizer


class TestTextSummarizer:
    """Тесты для класса TextSummarizer"""
    
    @pytest.fixture
    def summarizer(self):
        """Фикстура для создания экземпляра суммаризатора"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test_key'}):
            return TextSummarizer()
    
    def test_init(self, summarizer):
        """Тест инициализации класса"""
        assert summarizer.api_key == 'test_key'
        assert summarizer.chunk_size == 1000
        assert summarizer.max_retries == 3
        assert len(summarizer.models) >= 8
        assert summarizer.headers['Authorization'] == 'Bearer test_key'
    
    def test_split_text_short(self, summarizer):
        """Тест разбивки короткого текста"""
        text = "Короткий текст для теста"
        chunks = summarizer.split_text(text, max_len=100)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_split_text_long(self, summarizer):
        """Тест разбивки длинного текста"""
        words = ["слово"] * 200
        text = " ".join(words)
        chunks = summarizer.split_text(text, max_len=500)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 500
        
        # Проверяем, что текст не потерялся
        reconstructed = " ".join(chunks)
        assert len(reconstructed.split()) == len(words)
    
    def test_split_text_with_newlines(self, summarizer):
        """Тест разбивки текста с переносами строк"""
        text = "Первая строка\nВторая строка\nТретья строка\n" * 50
        chunks = summarizer.split_text(text, max_len=200)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 200
    
    @pytest.mark.asyncio
    @responses.activate
    async def test_make_request_success(self, summarizer):
        """Тест успешного запроса к API"""
        # Мокаем успешный ответ
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {"message": {"content": "Тестовая суммаризация"}}
                ]
            },
            status=200
        )
        
        messages = [
            {"role": "system", "content": "Test prompt"},
            {"role": "user", "content": "Test text"}
        ]
        
        result = await summarizer._make_request("test-model", messages)
        assert result == "Тестовая суммаризация"
    
    @pytest.mark.asyncio
    @responses.activate  
    async def test_make_request_rate_limit(self, summarizer):
        """Тест обработки rate limit (429 ошибка)"""
        # Первый запрос - rate limit
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            status=429
        )
        # Второй запрос - успех
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "choices": [
                    {"message": {"content": "Успешная суммаризация"}}
                ]
            },
            status=200
        )
        
        messages = [{"role": "user", "content": "Test"}]
        
        # Патчим sleep для ускорения теста
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await summarizer._make_request("test-model", messages)
        
        assert result == "Успешная суммаризация"
    
    @pytest.mark.asyncio
    @responses.activate
    async def test_make_request_failure(self, summarizer):
        """Тест обработки неудачных запросов"""
        responses.add(
            responses.POST,
            "https://openrouter.ai/api/v1/chat/completions",
            status=500
        )
        
        messages = [{"role": "user", "content": "Test"}]
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await summarizer._make_request("test-model", messages)
        
        assert "Ошибка после" in result
    
    @pytest.mark.asyncio
    async def test_summarize_text_no_api_key(self):
        """Тест суммаризации без API ключа"""
        with patch.dict(os.environ, {}, clear=True):
            summarizer = TextSummarizer()
            result, stats = await summarizer.summarize_text("Test text")
            
            assert "Не настроен OPENROUTER_API_KEY" in result
            assert stats == {}
    
    @pytest.mark.asyncio
    async def test_summarize_text_empty(self, summarizer):
        """Тест суммаризации пустого текста"""
        result, stats = await summarizer.summarize_text("")
        
        assert "Пустой текст" in result
        assert stats == {}
    
    @pytest.mark.asyncio
    async def test_summarize_text_short(self, summarizer):
        """Тест суммаризации короткого текста"""
        text = "Короткий текст для суммаризации"
        
        with patch.object(summarizer, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "Краткое изложение"
            
            result, stats = await summarizer.summarize_text(text)
            
            assert result == "Краткое изложение"
            assert stats['chunks'] == 1
            assert stats['original_length'] == len(text)
            assert 'model' in stats
    
    @pytest.mark.asyncio
    async def test_summarize_text_long(self, summarizer):
        """Тест суммаризации длинного текста"""
        text = "Длинный текст. " * 200  # ~2800 символов
        
        with patch.object(summarizer, '_make_request', new_callable=AsyncMock) as mock_request:
            # Возвращаем разные ответы для частей и финальной суммаризации
            mock_request.side_effect = [
                "Суммаризация части 1",
                "Суммаризация части 2", 
                "Суммаризация части 3",
                "Итоговая суммаризация"
            ]
            
            result, stats = await summarizer.summarize_text(text)
            
            assert result == "Итоговая суммаризация"
            assert stats['chunks'] > 1
            assert stats['processed_chunks'] >= 3
            assert mock_request.call_count == 4  # 3 части + финальная
    
    @pytest.mark.asyncio
    async def test_summarize_text_custom_prompt(self, summarizer):
        """Тест суммаризации с кастомным промптом"""
        text = "Текст для теста"
        custom_prompt = "Специальный промпт"
        
        with patch.object(summarizer, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "Результат"
            
            await summarizer.summarize_text(text, custom_prompt=custom_prompt)
            
            # Проверяем, что промпт передался корректно
            call_args = mock_request.call_args_list[0][0]
            messages = call_args[1]
            assert messages[0]['content'] == custom_prompt
    
    @pytest.mark.asyncio
    async def test_summarize_text_different_model(self, summarizer):
        """Тест выбора разных моделей"""
        text = "Текст"
        
        with patch.object(summarizer, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "Результат"
            
            result, stats = await summarizer.summarize_text(text, model_index=1)
            
            assert stats['model'] == summarizer.models[1][0]
            
            # Проверяем, что использовалась правильная модель
            call_args = mock_request.call_args_list[0][0]
            model_id = call_args[0]
            assert model_id == summarizer.models[1][1]
    
    @pytest.mark.asyncio
    async def test_summarize_text_invalid_model_index(self, summarizer):
        """Тест с неверным индексом модели"""
        text = "Текст"
        
        with patch.object(summarizer, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "Результат"
            
            result, stats = await summarizer.summarize_text(text, model_index=999)
            
            # Должна использоваться первая модель (индекс 0)
            assert stats['model'] == summarizer.models[0][0]
    
    def test_get_available_models(self, summarizer):
        """Тест получения списка доступных моделей"""
        models = summarizer.get_available_models()
        
        assert isinstance(models, list)
        assert len(models) >= 8
        assert all(isinstance(model, str) for model in models)
        
        # Проверяем, что модели соответствуют списку в классе
        expected_models = [name for name, _ in summarizer.models]
        assert models == expected_models


class TestTextSummarizerIntegration:
    """Интеграционные тесты для суммаризатора"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_api_call(self):
        """Тест реального API вызова (только если есть ключ)"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            pytest.skip("OPENROUTER_API_KEY не задан")
        
        summarizer = TextSummarizer()
        text = "Это тестовый текст для проверки API. Он содержит несколько предложений."
        
        result, stats = await summarizer.summarize_text(text)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Ошибка" not in result or "ошибка" not in result.lower()
        assert stats['original_length'] > 0
        assert stats['summary_length'] > 0 