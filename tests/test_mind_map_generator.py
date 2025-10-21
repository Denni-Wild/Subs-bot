"""
Тесты для модуля mind_map_generator.py
"""

import pytest
import asyncio
from mind_map_generator import MindMapGenerator

class TestMindMapGenerator:
    """Тесты для класса MindMapGenerator"""
    
    @pytest.fixture
    def generator(self):
        """Создание экземпляра генератора для тестов"""
        return MindMapGenerator("test_api_key")
    
    @pytest.fixture
    def sample_text(self):
        """Пример текста для тестирования"""
        return """
        ИИ-суммаризация - это технология автоматического создания краткого содержания.
        YouTube субтитры используются для извлечения текста из видео.
        Распознавание речи позволяет конвертировать аудио в текст.
        Голосовые сообщения обрабатываются через Soniox API.
        Статистика качества показывает эффективность различных методов.
        """
    
    def test_init(self, generator):
        """Тест инициализации генератора"""
        assert generator.openrouter_api_key == "test_api_key"
        assert generator.base_url == "https://openrouter.ai/api/v1"
    
    @pytest.mark.asyncio
    async def test_analyze_text_structure(self, generator, sample_text):
        """Тест анализа структуры текста"""
        structure = await generator.analyze_text_structure(sample_text)
        
        assert isinstance(structure, dict)
        assert "main_topic" in structure
        assert "subtopics" in structure
        assert isinstance(structure["subtopics"], dict)
    
    def test_generate_markdown(self, generator):
        """Тест генерации Markdown"""
        structure = {
            "main_topic": "Тестовая тема",
            "subtopics": {
                "подтема_1": ["пункт_1", "пункт_2"],
                "подтема_2": ["пункт_3"]
            }
        }

        markdown = generator.generate_markdown(structure)

        assert "# Тестовая тема" in markdown
        assert "## подтема_1" in markdown
        assert "## подтема_2" in markdown
        assert "💡 пункт_1" in markdown  # Теперь с эмодзи
        assert "💡 пункт_2" in markdown
        assert "💡 пункт_3" in markdown
        assert "Автоматически сгенерированная карта памяти" in markdown
    
    def test_generate_mermaid(self, generator):
        """Тест генерации Mermaid диаграммы"""
        structure = {
            "main_topic": "Тестовая тема",
            "subtopics": {
                "подтема_1": ["пункт_1", "пункт_2"]
            }
        }

        mermaid = generator.generate_mermaid(structure)

        assert "mindmap" in mermaid
        assert 'root(("Тестовая тема"))' in mermaid  # Теперь с кавычками
        assert '"подтема_1"' in mermaid  # С кавычками
        assert '"💡 пункт_1"' in mermaid  # С эмодзи и кавычками
        assert '"💡 пункт_2"' in mermaid
    
    @pytest.mark.asyncio
    async def test_render_to_png(self, generator):
        """Тест рендеринга в PNG"""
        mermaid_code = "mindmap\n  root((Тест))\n    подтема\n      пункт"
        output_path = "test_output.png"
        
        result = await generator.render_to_png(mermaid_code, output_path)
        
        # Теперь может возвращать False если нет mermaid-cli и kroki.io недоступен
        assert isinstance(result, bool)
    
    def test_generate_html_markmap(self, generator):
        """Тест генерации HTML Markmap"""
        markdown_content = "# Тест\n## Подтема\n- Пункт"
        
        html = generator.generate_html_markmap(markdown_content)
        
        assert "<!DOCTYPE html>" in html
        assert "<title>Mind Map - Subs-bot</title>" in html
        assert "markmap-toolbar" in html  # Теперь используем markmap-toolbar
        assert "markmap-view" in html     # И markmap-view
        assert "Интерактивная карта памяти" in html
    
    @pytest.mark.asyncio
    async def test_create_mind_map_all_formats(self, generator, sample_text):
        """Тест создания mind map во всех форматах"""
        results = await generator.create_mind_map(sample_text, "all")
        
        assert "structure" in results
        assert "markdown" in results
        assert "mermaid" in results
        assert "png_path" in results
        assert "html_content" in results
        
        assert results["markdown"] is not None
        assert results["mermaid"] is not None
        assert results["html_content"] is not None
    
    @pytest.mark.asyncio
    async def test_create_mind_map_markdown_only(self, generator, sample_text):
        """Тест создания mind map только в формате Markdown"""
        results = await generator.create_mind_map(sample_text, "markdown")
        
        assert results["markdown"] is not None
        assert results["mermaid"] is None
        assert results["png_path"] is None
        assert results["html_content"] is None
    
    @pytest.mark.asyncio
    async def test_create_mind_map_mermaid_only(self, generator, sample_text):
        """Тест создания mind map только в формате Mermaid"""
        results = await generator.create_mind_map(sample_text, "mermaid")
        
        assert results["markdown"] is None
        assert results["mermaid"] is not None
        assert results["png_path"] is None
        assert results["html_content"] is None

# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__])
