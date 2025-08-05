import os
import requests
import re
import time
import asyncio
from typing import List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class TextSummarizer:
    """Класс для суммаризации текста через OpenRouter API"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.chunk_size = 1000
        self.max_retries = 3
        self.retry_delay = 5
        self.rate_limit_delay = 60
        
        # Список бесплатных моделей OpenRouter
        self.models = [
            ("venice_uncensored", "venice/uncensored:free"),
            ("google_gemma_3n_2b", "google/gemma-3n-e2b-it:free"),
            ("tencent_hunyuan_a13b", "tencent/hunyuan-a13b-instruct:free"),
            ("tng_deepseek_r1t2_chimera", "tngtech/deepseek-r1t2-chimera:free"),
            ("cypher_alpha", "openrouter/cypher-alpha:free"),
            ("mistral_small_3_2_24b", "mistralai/mistral-small-3.2-24b-instruct:free"),
            ("kimi_dev_72b", "moonshotai/kimi-dev-72b:free"),
            ("deepseek_r1_0528", "deepseek/deepseek-r1-0528:free"),
        ]
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://openrouter.ai/",
            "X-Title": "Telegram Subs-bot"
        }
    
    def detect_language(self, text: str) -> str:
        """
        Определяет язык текста на основе простых эвристик
        Returns: код языка ('ru', 'en', 'other')
        """
        # Простые эвристики для определения языка
        text_lower = text.lower()
        
        # Русский язык
        russian_chars = re.findall(r'[а-яё]', text_lower)
        russian_ratio = len(russian_chars) / len(text_lower.replace(' ', '')) if text_lower.replace(' ', '') else 0
        
        # Английский язык
        english_chars = re.findall(r'[a-z]', text_lower)
        english_ratio = len(english_chars) / len(text_lower.replace(' ', '')) if text_lower.replace(' ', '') else 0
        
        # Определяем язык по преобладанию символов
        if russian_ratio > 0.3:  # Если больше 30% русских символов
            return 'ru'
        elif english_ratio > 0.5:  # Если больше 50% английских символов
            return 'en'
        else:
            return 'other'
    
    async def translate_to_russian(self, text: str, source_lang: str = None, model_index: int = 0) -> str:
        """
        Переводит текст на русский язык
        Args:
            text: текст для перевода
            source_lang: исходный язык (если известен)
            model_index: индекс модели для перевода
        Returns:
            переведенный текст или исходный текст в случае ошибки
        """
        if not self.api_key:
            return text
        
        if model_index >= len(self.models):
            model_index = 0
        
        model_name, model_id = self.models[model_index]
        
        # Формируем промпт для перевода
        if source_lang == 'en':
            prompt = "Переведи следующий текст с английского на русский язык, сохранив смысл и стиль:"
        elif source_lang == 'other':
            prompt = "Переведи следующий текст на русский язык, сохранив смысл и стиль:"
        else:
            prompt = "Переведи следующий текст на русский язык, сохранив смысл и стиль:"
        
        messages = [
            {"role": "system", "content": "Ты - профессиональный переводчик. Переводи текст на русский язык, сохраняя смысл, стиль и структуру."},
            {"role": "user", "content": f"{prompt}\n\n{text}"}
        ]
        
        try:
            result = await self._make_request(model_id, messages)
            return result if result else text
        except Exception as e:
            print(f"Ошибка перевода: {e}")
            return text
    
    def split_text(self, text: str, max_len: int = None) -> List[str]:
        """Разбивает текст на части, не разрывая слова"""
        max_len = max_len or self.chunk_size
        words = re.findall(r'\S+|\n', text)
        chunks = []
        current = ''
        
        for word in words:
            if len(current) + len(word) + 1 > max_len:
                if current.strip():
                    chunks.append(current.strip())
                current = word if word != '\n' else ''
            else:
                current += (' ' if current and word != '\n' and not current.endswith('\n') else '') + word
        
        if current.strip():
            chunks.append(current.strip())
        
        return chunks
    
    async def _make_request(self, model_id: str, messages: List[dict]) -> Optional[str]:
        """Делает запрос к OpenRouter API с повторными попытками"""
        data = {
            "model": model_id,
            "messages": messages
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Делаем синхронный запрос в отдельном потоке
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=self.headers,
                        json=data,
                        timeout=120
                    )
                )
                
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
            except Exception as e:
                if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                    # Rate limit - ждем дольше
                    await asyncio.sleep(self.rate_limit_delay)
                elif attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return f"Ошибка после {self.max_retries} попыток: {str(e)}"
        
        return None
    
    async def summarize_text(self, text: str, model_index: int = 0, custom_prompt: str = None) -> Tuple[str, dict]:
        """
        Суммаризирует текст по частям, затем создает итоговую суммаризацию
        
        Returns:
            Tuple[str, dict]: (итоговая суммаризация, статистика)
        """
        if not self.api_key:
            return "❌ Не настроен OPENROUTER_API_KEY", {}
        
        if model_index >= len(self.models):
            model_index = 0
        
        model_name, model_id = self.models[model_index]
        prompt = custom_prompt or "Кратко изложи основные мысли этого фрагмента текста."
        
        # Определяем язык исходного текста
        source_language = self.detect_language(text)
        
        # Разбиваем текст на части
        chunks = self.split_text(text)
        
        if not chunks:
            return "❌ Пустой текст для суммаризации", {}
        
        # Если текст короткий - обрабатываем сразу
        if len(chunks) == 1 and len(text) < 2000:
            messages = [
                {"role": "system", "content": "Создай краткую и содержательную суммаризацию текста."},
                {"role": "user", "content": text}
            ]
            result = await self._make_request(model_id, messages)
            stats = {
                "model": model_name,
                "chunks": 1,
                "original_length": len(text),
                "summary_length": len(result) if result else 0,
                "source_language": source_language
            }
            return result or "❌ Не удалось создать суммаризацию", stats
        
        # Обрабатываем по частям
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks):
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": chunk}
            ]
            
            summary = await self._make_request(model_id, messages)
            
            if summary:
                chunk_summaries.append(summary)
            
            # Небольшая пауза между запросами
            if i < len(chunks) - 1:
                await asyncio.sleep(2)
        
        if not chunk_summaries:
            return "❌ Не удалось создать суммаризацию ни одной части", {}
        
        # Создаем итоговую суммаризацию
        final_prompt = "Создай единую связную суммаризацию на основе этих фрагментов:"
        combined_text = "\n\n".join(chunk_summaries)
        
        final_messages = [
            {"role": "system", "content": final_prompt},
            {"role": "user", "content": combined_text}
        ]
        
        final_summary = await self._make_request(model_id, final_messages)
        
        stats = {
            "model": model_name,
            "chunks": len(chunks),
            "original_length": len(text),
            "summary_length": len(final_summary) if final_summary else 0,
            "processed_chunks": len(chunk_summaries),
            "source_language": source_language
        }
        
        return final_summary or "❌ Не удалось создать итоговую суммаризацию", stats
    
    def get_available_models(self) -> List[str]:
        """Возвращает список доступных моделей"""
        return [name for name, _ in self.models] 