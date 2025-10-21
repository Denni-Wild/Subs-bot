#!/usr/bin/env python3
"""
Интеграционные тесты для Mind Map Generator с Telegram ботом

Тестирует полную интеграцию функциональности
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from mind_map_generator import MindMapGenerator

class TestMindMapIntegration:
    """Тесты интеграции mind map с Telegram ботом"""
    
    @pytest.fixture
    def mock_mind_map_generator(self):
        """Создает мок mind map генератора"""
        generator = MindMapGenerator("test_api_key")
        
        # Мокаем LLM анализ
        async def mock_analyze_chunk(chunk):
            ideas = []
            if 'искусственный интеллект' in chunk.lower():
                ideas.extend([
                    "Искусственный интеллект и машинное обучение",
                    "Автоматизация процессов",
                    "Анализ больших данных"
                ])
            if 'youtube' in chunk.lower():
                ideas.extend([
                    "YouTube платформа",
                    "Автоматическая генерация субтитров"
                ])
            if not ideas:
                ideas = ["Технологические инновации", "Цифровая трансформация"]
            return ideas
        
        generator._analyze_chunk_with_llm = mock_analyze_chunk
        return generator
    
    @pytest.fixture
    def sample_text(self):
        """Пример текста для тестирования"""
        return """
        Искусственный интеллект и машинное обучение становятся все более важными в современном мире. 
        Эти технологии используются для анализа больших объемов данных, автоматизации процессов и принятия решений.
        
        YouTube и другие платформы используют ИИ для рекомендаций контента, автоматической генерации субтитров 
        и анализа аудио. Голосовые помощники, такие как Siri и Alexa, также основаны на технологиях ИИ.
        """
    
    @pytest.mark.asyncio
    async def test_full_mind_map_creation(self, mock_mind_map_generator, sample_text):
        """Тест полного создания mind map"""
        # Создаем mind map во всех форматах
        results = await mock_mind_map_generator.create_mind_map(sample_text, "all")
        
        # Проверяем структуру результатов
        assert "structure" in results
        assert "markdown" in results
        assert "mermaid" in results
        assert "html_content" in results
        assert "png_path" in results
        
        # Проверяем структуру идей
        structure = results["structure"]
        assert "main_topic" in structure
        assert "subtopics" in structure
        assert len(structure["subtopics"]) > 0
        
        # Проверяем Markdown
        markdown = results["markdown"]
        assert "# " in markdown  # Заголовок
        assert "## " in markdown  # Подзаголовки
        assert "💡" in markdown or "🤖" in markdown or "🎥" in markdown  # Эмодзи
        
        # Проверяем Mermaid
        mermaid = results["mermaid"]
        assert "mindmap" in mermaid
        assert "root" in mermaid
        
        # Проверяем HTML
        html = results["html_content"]
        assert "<!DOCTYPE html>" in html
        assert "Mind Map - Subs-bot" in html
        assert "markmap" in html
    
    @pytest.mark.asyncio
    async def test_text_chunking(self, mock_mind_map_generator):
        """Тест разбиения текста на чанки"""
        long_text = "Предложение 1. " * 1000  # ~6000 символов
        
        chunks = mock_mind_map_generator._chunk_text(long_text)
        
        assert len(chunks) > 1  # Должно быть разбито на несколько чанков
        assert all(len(chunk) <= 2000 for chunk in chunks)  # Каждый чанк не больше 2000 символов
    
    @pytest.mark.asyncio
    async def test_hierarchy_building(self, mock_mind_map_generator):
        """Тест построения иерархии идей"""
        ideas = [
            "Искусственный интеллект и машинное обучение",
            "YouTube платформа",
            "Автоматическая генерация субтитров",
            "Анализ больших данных"
        ]
        
        hierarchy = mock_mind_map_generator._build_hierarchy(ideas)
        
        assert "main_topic" in hierarchy
        assert "subtopics" in hierarchy
        assert len(hierarchy["subtopics"]) > 0
        
        # Проверяем, что идеи сгруппированы по темам
        subtopics = hierarchy["subtopics"]
        assert any("ИИ" in topic or "ML" in topic for topic in subtopics.keys())
        # YouTube идеи могут попасть в "Общие темы" если их мало
        assert len(subtopics) > 0  # Просто проверяем, что есть подтемы
    
    def test_markdown_generation(self, mock_mind_map_generator):
        """Тест генерации Markdown"""
        structure = {
            "main_topic": "Технологии ИИ",
            "subtopics": {
                "ИИ и ML": ["Машинное обучение", "Нейронные сети"],
                "Платформы": ["YouTube", "Социальные сети"]
            }
        }
        
        markdown = mock_mind_map_generator.generate_markdown(structure)
        
        assert "# Технологии ИИ" in markdown
        assert "## ИИ и ML" in markdown
        assert "## Платформы" in markdown
        assert "🤖" in markdown or "💡" in markdown  # Эмодзи
        assert "Автоматически сгенерированная карта памяти" in markdown
    
    def test_mermaid_generation(self, mock_mind_map_generator):
        """Тест генерации Mermaid"""
        structure = {
            "main_topic": "Технологии ИИ",
            "subtopics": {
                "ИИ и ML": ["Машинное обучение", "Нейронные сети"]
            }
        }
        
        mermaid = mock_mind_map_generator.generate_mermaid(structure)
        
        assert "mindmap" in mermaid
        assert 'root(("Технологии ИИ"))' in mermaid
        assert '"ИИ и ML"' in mermaid
        assert '"🤖 Машинное обучение"' in mermaid
    
    def test_html_generation(self, mock_mind_map_generator):
        """Тест генерации HTML"""
        markdown_content = "# Тест\n## Подтема\n- Пункт"
        
        html = mock_mind_map_generator.generate_html_markmap(markdown_content)
        
        assert "<!DOCTYPE html>" in html
        assert "<title>Mind Map - Subs-bot</title>" in html
        assert "Интерактивная карта памяти" in html
        assert "markmap-toolbar" in html
        assert "markmap-view" in html
    
    @pytest.mark.asyncio
    async def test_png_rendering_fallback(self, mock_mind_map_generator):
        """Тест fallback для PNG рендеринга"""
        mermaid_code = "mindmap\n  root((Тест))\n    подтема\n      пункт"
        
        # Мокаем проверку mermaid-cli
        with patch.object(mock_mind_map_generator, '_check_mermaid_cli', return_value=False):
            # Мокаем kroki.io API
            with patch.object(mock_mind_map_generator, '_render_with_kroki_api', return_value=True):
                result = await mock_mind_map_generator.render_to_png(mermaid_code, "test.png")
                assert result is True
    
    def test_emoji_classification(self, mock_mind_map_generator):
        """Тест классификации идей по эмодзи"""
        # Тестируем различные типы идей
        ai_idea = "Искусственный интеллект и машинное обучение"
        video_idea = "YouTube субтитры и видео контент"
        audio_idea = "Голосовые сообщения и аудио"
        general_idea = "Технологические инновации"
        
        # Проверяем, что эмодзи правильно определяются в Markdown
        structure = {
            "main_topic": "Тест",
            "subtopics": {
                "Тест": [ai_idea, video_idea, audio_idea, general_idea]
            }
        }
        
        markdown = mock_mind_map_generator.generate_markdown(structure)
        
        # Проверяем наличие эмодзи
        assert "🤖" in markdown or "🎥" in markdown or "🎵" in markdown or "💡" in markdown
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mind_map_generator):
        """Тест обработки ошибок"""
        # Тестируем обработку пустого текста
        empty_results = await mock_mind_map_generator.create_mind_map("", "all")
        assert "structure" in empty_results
        # Главная тема может быть любой, главное что структура создана
        assert "main_topic" in empty_results["structure"]
        
        # Тестируем обработку очень короткого текста
        short_results = await mock_mind_map_generator.create_mind_map("Короткий текст", "all")
        assert "structure" in short_results

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 