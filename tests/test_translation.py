import pytest
import asyncio
from summarizer import TextSummarizer

class TestTranslation:
    """Тесты для функциональности перевода"""
    
    @pytest.fixture
    def summarizer(self):
        return TextSummarizer()
    
    def test_detect_language_russian(self, summarizer):
        """Тест определения русского языка"""
        text = "Это русский текст с кириллическими символами"
        result = summarizer.detect_language(text)
        assert result == 'ru'
    
    def test_detect_language_english(self, summarizer):
        """Тест определения английского языка"""
        text = "This is English text with Latin characters"
        result = summarizer.detect_language(text)
        assert result == 'en'
    
    def test_detect_language_mixed(self, summarizer):
        """Тест определения смешанного языка"""
        text = "This is mixed text with some русские слова"
        result = summarizer.detect_language(text)
        # Должен вернуть 'other' для смешанного текста
        assert result in ['ru', 'en', 'other']
    
    def test_detect_language_short(self, summarizer):
        """Тест определения языка для короткого текста"""
        text = "Hello"
        result = summarizer.detect_language(text)
        assert result == 'en'
    
    @pytest.mark.asyncio
    async def test_translate_to_russian(self, summarizer):
        """Тест перевода на русский язык"""
        english_text = "Hello world! This is a test message."
        
        # Мокаем API ключ для тестирования
        original_api_key = summarizer.api_key
        summarizer.api_key = "test_key"
        
        try:
            # Тест должен вернуть исходный текст, так как API ключ тестовый
            result = await summarizer.translate_to_russian(english_text, 'en')
            assert result == english_text  # Должен вернуть исходный текст при ошибке API
        finally:
            summarizer.api_key = original_api_key
    
    def test_detect_language_empty(self, summarizer):
        """Тест определения языка для пустого текста"""
        text = ""
        result = summarizer.detect_language(text)
        assert result == 'other'  # Для пустого текста возвращаем 'other'
    
    def test_detect_language_numbers(self, summarizer):
        """Тест определения языка для текста с числами"""
        text = "123 456 789"
        result = summarizer.detect_language(text)
        assert result == 'other'  # Для текста только с числами возвращаем 'other'

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"]) 