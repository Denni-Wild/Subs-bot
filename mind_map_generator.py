"""
Mind Map Generator для Subs-bot

Модуль для автоматической генерации mind map из текста (субтитры, суммаризация)
с использованием Mermaid или Markmap и последующей отправки в Telegram.

Основные функции:
1. Анализ и генерация смысловой структуры текста
2. Генерация Markdown для Markmap
3. Создание Mermaid диаграмм
4. Рендеринг PNG/PDF изображений
5. Генерация интерактивных HTML карт
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
import subprocess
import tempfile

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MindMapGenerator:
    """Основной класс для генерации mind map"""
    
    def __init__(self, openrouter_api_key: str):
        """
        Инициализация генератора mind map
        
        Args:
            openrouter_api_key: API ключ для OpenRouter
        """
        self.openrouter_api_key = openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        
    async def analyze_text_structure(self, text: str) -> Dict:
        """
        Анализ текста и генерация смысловой структуры с использованием OpenRouter LLMs
        
        Args:
            text: Входной текст для анализа
            
        Returns:
            Dict: Структурированная иерархия идей
        """
        try:
            # RAG/chunk-based обработка для длинных текстов
            chunks = self._chunk_text(text)
            
            # Анализ каждого чанка и объединение результатов
            all_ideas = []
            for chunk in chunks:
                chunk_ideas = await self._analyze_chunk_with_llm(chunk)
                all_ideas.extend(chunk_ideas)
            
            # Построение иерархии идей
            structure = self._build_hierarchy(all_ideas)
            
            logger.info("Структура текста успешно проанализирована")
            return structure
            
        except Exception as e:
            logger.error(f"Ошибка при анализе структуры текста: {e}")
            raise
    
    def _chunk_text(self, text: str, max_chunk_size: int = 2000) -> List[str]:
        """
        Разбиение текста на чанки для обработки LLM
        
        Args:
            text: Исходный текст
            max_chunk_size: Максимальный размер чанка
            
        Returns:
            List[str]: Список чанков текста
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    async def _analyze_chunk_with_llm(self, chunk: str) -> List[str]:
        """
        Анализ чанка текста с помощью OpenRouter LLM
        
        Args:
            chunk: Чанк текста для анализа
            
        Returns:
            List[str]: Список идей из чанка
        """
        try:
            import aiohttp
            
            # Промпт для анализа текста
            prompt = f"""
Проанализируй следующий текст и выдели основные идеи, концепции и темы.
Верни только список ключевых идей в формате JSON массива строк.

Текст для анализа:
{chunk}

Формат ответа:
["идея 1", "идея 2", "идея 3"]
"""
            
            # Параметры запроса к OpenRouter
            payload = {
                "model": "anthropic/claude-3-haiku",  # Быстрая и эффективная модель
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3  # Низкая температура для более структурированных ответов
            }
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Парсинг JSON ответа
                        try:
                            ideas = json.loads(content)
                            if isinstance(ideas, list):
                                return ideas
                            else:
                                logger.warning(f"Неожиданный формат ответа LLM: {content}")
                                return []
                        except json.JSONDecodeError:
                            logger.warning(f"Ошибка парсинга JSON от LLM: {content}")
                            return []
                    else:
                        logger.error(f"Ошибка API OpenRouter: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Ошибка при анализе чанка с LLM: {e}")
            return []
    
    def _build_hierarchy(self, ideas: List[str]) -> Dict:
        """
        Построение иерархии идей на основе списка
        
        Args:
            ideas: Список идей из анализа
            
        Returns:
            Dict: Иерархическая структура
        """
        if not ideas:
            return {"main_topic": "Анализ текста", "subtopics": {}}
        
        # Группировка идей по темам
        topics = {}
        for idea in ideas:
            # Простая группировка по ключевым словам
            if any(keyword in idea.lower() for keyword in ['искусственный интеллект', 'ai', 'машинное обучение']):
                if 'ИИ и ML' not in topics:
                    topics['ИИ и ML'] = []
                topics['ИИ и ML'].append(idea)
            elif any(keyword in idea.lower() for keyword in ['видео', 'youtube', 'субтитры']):
                if 'Видео контент' not in topics:
                    topics['Видео контент'] = []
                topics['Видео контент'].append(idea)
            elif any(keyword in idea.lower() for keyword in ['голос', 'аудио', 'транскрипция']):
                if 'Аудио обработка' not in topics:
                    topics['Аудио обработка'] = []
                topics['Аудио обработка'].append(idea)
            else:
                if 'Общие темы' not in topics:
                    topics['Общие темы'] = []
                topics['Общие темы'].append(idea)
        
        # Определение главной темы
        main_topic = max(topics.keys(), key=lambda k: len(topics[k])) if topics else "Анализ текста"
        
        return {
            "main_topic": main_topic,
            "subtopics": topics
        }
    
    def generate_markdown(self, structure: Dict) -> str:
        """
        Генерация Markdown для Markmap с улучшенной структурой
        
        Args:
            structure: Структура идей
            
        Returns:
            str: Markdown контент для Markmap
        """
        try:
            markdown = f"# {structure['main_topic']}\n\n"
            
            # Добавляем описание
            markdown += f"*Автоматически сгенерированная карта памяти*\n\n"
            
            # Сортируем подтемы по количеству идей
            sorted_subtopics = sorted(
                structure['subtopics'].items(), 
                key=lambda x: len(x[1]), 
                reverse=True
            )
            
            for subtopic, items in sorted_subtopics:
                if items:  # Пропускаем пустые подтемы
                    markdown += f"## {subtopic}\n\n"
                    
                    # Группируем идеи по важности
                    for i, item in enumerate(items, 1):
                        # Добавляем эмодзи для лучшей визуализации
                        if any(keyword in item.lower() for keyword in ['искусственный интеллект', 'ai', 'машинное обучение']):
                            emoji = "🤖"
                        elif any(keyword in item.lower() for keyword in ['видео', 'youtube', 'субтитры']):
                            emoji = "🎥"
                        elif any(keyword in item.lower() for keyword in ['голос', 'аудио', 'транскрипция']):
                            emoji = "🎵"
                        else:
                            emoji = "💡"
                        
                        markdown += f"{emoji} {item}\n"
                    
                    markdown += "\n"
            
            # Добавляем метаданные
            markdown += "---\n"
            markdown += f"**Сгенерировано**: {len(structure['subtopics'])} основных тем\n"
            markdown += f"**Всего идей**: {sum(len(items) for items in structure['subtopics'].values())}\n"
            markdown += f"**Главная тема**: {structure['main_topic']}\n"
            
            logger.info("Markdown для Markmap успешно сгенерирован")
            return markdown
            
        except Exception as e:
            logger.error(f"Ошибка при генерации Markdown: {e}")
            raise
    
    def generate_mermaid(self, structure: Dict) -> str:
        """
        Генерация Mermaid диаграммы с улучшенной визуализацией
        
        Args:
            structure: Структура идей
            
        Returns:
            str: Mermaid код для mind map
        """
        try:
            # Начинаем с корневой темы
            main_topic = structure['main_topic'].replace('"', '\\"')  # Экранируем кавычки
            mermaid = f'mindmap\n  root(("{main_topic}"))\n'
            
            # Сортируем подтемы по количеству идей
            sorted_subtopics = sorted(
                structure['subtopics'].items(), 
                key=lambda x: len(x[1]), 
                reverse=True
            )
            
            for subtopic, items in sorted_subtopics:
                if items:  # Пропускаем пустые подтемы
                    # Экранируем специальные символы
                    safe_subtopic = subtopic.replace('"', '\\"').replace('(', '\\(').replace(')', '\\)')
                    mermaid += f'    "{safe_subtopic}"\n'
                    
                    # Добавляем идеи с эмодзи
                    for item in items:
                        safe_item = item.replace('"', '\\"').replace('(', '\\(').replace(')', '\\)')
                        
                        # Определяем эмодзи для категории
                        if any(keyword in item.lower() for keyword in ['искусственный интеллект', 'ai', 'машинное обучение']):
                            emoji = "🤖"
                        elif any(keyword in item.lower() for keyword in ['видео', 'youtube', 'субтитры']):
                            emoji = "🎥"
                        elif any(keyword in item.lower() for keyword in ['голос', 'аудио', 'транскрипция']):
                            emoji = "🎵"
                        else:
                            emoji = "💡"
                        
                        mermaid += f'      "{emoji} {safe_item}"\n'
            
            logger.info("Mermaid диаграмма успешно сгенерирована")
            return mermaid
            
        except Exception as e:
            logger.error(f"Ошибка при генерации Mermaid: {e}")
            raise
    
    async def render_to_png(self, mermaid_code: str, output_path: str) -> bool:
        """
        Рендеринг Mermaid диаграммы в PNG
        
        Args:
            mermaid_code: Mermaid код
        output_path: Путь для сохранения PNG
            
        Returns:
            bool: True если успешно, False иначе
        """
        try:
            # Попытка использовать mermaid-cli
            if self._check_mermaid_cli():
                return await self._render_with_mermaid_cli(mermaid_code, output_path)
            
            # Альтернатива через kroki.io API
            return await self._render_with_kroki_api(mermaid_code, output_path)
            
        except Exception as e:
            logger.error(f"Ошибка при рендеринге PNG: {e}")
            return False
    
    def _check_mermaid_cli(self) -> bool:
        """Проверка доступности mermaid-cli"""
        try:
            result = subprocess.run(['mmdc', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    async def _render_with_mermaid_cli(self, mermaid_code: str, output_path: str) -> bool:
        """Рендеринг через mermaid-cli"""
        try:
            # Создаем временный файл с Mermaid кодом
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
                temp_file.write(mermaid_code)
                temp_mmd_path = temp_file.name
            
            # Рендерим через mmdc
            cmd = ['mmdc', '-i', temp_mmd_path, '-o', output_path, '--backgroundColor', 'white']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Удаляем временный файл
            os.unlink(temp_mmd_path)
            
            if result.returncode == 0:
                logger.info(f"PNG успешно создан: {output_path}")
                return True
            else:
                logger.error(f"Ошибка mermaid-cli: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при рендеринге через mermaid-cli: {e}")
            return False
    
    async def _render_with_kroki_api(self, mermaid_code: str, output_path: str) -> bool:
        """Рендеринг через kroki.io API"""
        try:
            import aiohttp
            import base64
            
            # Кодируем Mermaid код в base64
            encoded_code = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
            
            # Формируем URL для kroki.io
            kroki_url = f"https://kroki.io/mermaid/png/{encoded_code}"
            
            # Скачиваем изображение
            async with aiohttp.ClientSession() as session:
                async with session.get(kroki_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Создаем директорию если не существует
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        
                        # Сохраняем PNG
                        with open(output_path, 'wb') as f:
                            f.write(content)
                        
                        logger.info(f"PNG успешно создан через kroki.io: {output_path}")
                        return True
                    else:
                        logger.error(f"Ошибка kroki.io API: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Ошибка при рендеринге через kroki.io: {e}")
            return False
    
    def generate_html_markmap(self, markdown_content: str) -> str:
        """
        Генерация HTML файла с интерактивной Markmap картой
        
        Args:
            markdown_content: Markdown контент
            
        Returns:
            str: HTML контент
        """
        try:
            html_template = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mind Map - Subs-bot</title>
    
    <!-- Markmap CSS и JS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/markmap-toolbar@0.3.0/dist/style.css">
    <script src="https://cdn.jsdelivr.net/npm/markmap-toolbar@0.3.0/dist/index.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.3.0/dist/index.min.js"></script>
    
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .mindmap-container {{
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        #mindmap {{
            width: 100%;
            height: 80vh;
            min-height: 600px;
        }}
        
        .controls {{
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 10px 20px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }}
        
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: white;
            opacity: 0.8;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2rem; }}
            .controls {{ flex-direction: column; align-items: center; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Mind Map - Subs-bot</h1>
            <p>Интерактивная карта памяти, сгенерированная автоматически</p>
        </div>
        
        <div class="mindmap-container">
            <div class="controls">
                <button class="btn" onclick="zoomIn()">🔍 Увеличить</button>
                <button class="btn" onclick="zoomOut()">🔍 Уменьшить</button>
                <button class="btn" onclick="resetView()">🏠 Сброс</button>
                <button class="btn" onclick="downloadSVG()">💾 Скачать SVG</button>
                <button class="btn" onclick="showMarkdown()">📝 Показать Markdown</button>
            </div>
            
            <div id="mindmap"></div>
        </div>
        
        <div class="footer">
            <p>Создано с помощью Subs-bot Mind Map Generator</p>
        </div>
    </div>
    
    <script>
        // Markdown контент
        const markdown = `{markdown_content}`;
        
        // Инициализация Markmap
        let mm;
        
        async function initMarkmap() {{
            try {{
                const {{ Markmap, loadCSS, loadJS }} = await import('https://cdn.jsdelivr.net/npm/markmap-view@0.3.0/dist/index.min.js');
                
                // Создаем Markmap
                mm = Markmap.create('#mindmap', null, markdown);
                
                // Добавляем тулбар
                const toolbar = new markmap.toolbar.Toolbar();
                toolbar.attach(mm);
                
            }} catch (error) {{
                console.error('Ошибка инициализации Markmap:', error);
                document.getElementById('mindmap').innerHTML = 
                    '<div style="padding: 40px; text-align: center; color: #666;">' +
                    '<h3>Ошибка загрузки карты</h3>' +
                    '<p>Попробуйте обновить страницу</p>' +
                    '</div>';
            }}
        }}
        
        // Функции управления
        function zoomIn() {{
            if (mm) mm.zoomIn();
        }}
        
        function zoomOut() {{
            if (mm) mm.zoomOut();
        }}
        
        function resetView() {{
            if (mm) mm.fit();
        }}
        
        function downloadSVG() {{
            if (mm) {{
                const svg = document.querySelector('#mindmap svg');
                const serializer = new XMLSerializer();
                const svgString = serializer.serializeToString(svg);
                const blob = new Blob([svgString], {{type: 'image/svg+xml'}});
                const a = document.createElement('a');
                a.href = url;
                a.download = 'mindmap.svg';
                a.click();
                URL.revokeObjectURL(url);
            }}
        }}
        
        function showMarkdown() {{
            const markdownWindow = window.open('', '_blank');
            markdownWindow.document.write(`
                <html>
                <head><title>Markdown - Mind Map</title></head>
                <body style="font-family: monospace; padding: 20px; background: #f5f5f5;">
                    <h2>Markdown код:</h2>
                    <pre style="background: white; padding: 15px; border-radius: 5px; overflow-x: auto;">${{markdown}}</pre>
                </body>
                </html>
            `);
        }}
        
        // Инициализация при загрузке страницы
        document.addEventListener('DOMContentLoaded', initMarkmap);
    </script>
</body>
</html>
"""
            
            logger.info("HTML Markmap успешно сгенерирован")
            return html_template
            
        except Exception as e:
            logger.error(f"Ошибка при генерации HTML Markmap: {e}")
            raise
    
    async def create_mind_map(self, text: str, output_format: str = "all") -> Dict:
        """
        Основной метод для создания mind map
        
        Args:
            text: Входной текст
            output_format: Формат вывода ("markdown", "mermaid", "png", "html", "all")
            
        Returns:
            Dict: Результаты генерации
        """
        try:
            logger.info("Начинаю генерацию mind map")
            
            # 1. Анализ структуры текста
            structure = await self.analyze_text_structure(text)
            
            results = {
                "structure": structure,
                "markdown": None,
                "mermaid": None,
                "png_path": None,
                "html_content": None
            }
            
            # 2. Генерация Markdown
            if output_format in ["markdown", "html", "all"]:
                results["markdown"] = self.generate_markdown(structure)
            
            # 3. Генерация Mermaid
            if output_format in ["mermaid", "png", "all"]:
                results["mermaid"] = self.generate_mermaid(structure)
            
            # 4. Рендеринг PNG
            if output_format in ["png", "all"] and results["mermaid"]:
                png_path = f"mind_map_{hash(text) % 10000}.png"
                success = await self.render_to_png(results["mermaid"], png_path)
                if success:
                    results["png_path"] = png_path
            
            # 5. Генерация HTML
            if output_format in ["html", "all"] and results["markdown"]:
                results["html_content"] = self.generate_html_markmap(results["markdown"])
            
            logger.info("Mind map успешно создан")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при создании mind map: {e}")
            raise

# Пример использования
async def main():
    """Демонстрация работы модуля"""
    generator = MindMapGenerator("your_api_key_here")
    
    sample_text = """
    ИИ-суммаризация - это технология автоматического создания краткого содержания.
    YouTube субтитры используются для извлечения текста из видео.
    Распознавание речи позволяет конвертировать аудио в текст.
    Голосовые сообщения обрабатываются через Soniox API.
    Статистика качества показывает эффективность различных методов.
    """
    
    try:
        results = await generator.create_mind_map(sample_text, "all")
        print("Результаты генерации:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
