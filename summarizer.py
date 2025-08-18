import os
import requests
import re
import time
import asyncio
import random
import logging
from typing import List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Настройка логгера для суммаризации
summarization_logger = logging.getLogger('summarization')
summarization_logger.setLevel(logging.INFO)

# Создаем файловый обработчик для лога суммаризации
if not summarization_logger.handlers:
    # Убеждаемся, что папка logs существует
    os.makedirs('logs', exist_ok=True)
    summarization_handler = logging.FileHandler('logs/summarization.log', encoding='utf-8-sig')
    summarization_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    summarization_handler.setFormatter(summarization_formatter)
    summarization_logger.addHandler(summarization_handler)

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
    
    def get_random_model_index(self) -> int:
        """Возвращает случайный индекс модели для суммаризации"""
        return random.randint(0, len(self.models) - 1)
    
    def log_summarization_result(self, success: bool, model_name: str, text_length: int, 
                                summary_length: int, chunks: int, error: str = None):
        """Логирует результат суммаризации"""
        if success:
            summarization_logger.info(
                f"✅ Суммаризация УСПЕШНА - Модель: {model_name}, "
                f"Исходный текст: {text_length} символов, "
                f"Суммаризация: {summary_length} символов, "
                f"Частей: {chunks}"
            )
        else:
            summarization_logger.error(
                f"❌ Суммаризация НЕУСПЕШНА - Модель: {model_name}, "
                f"Исходный текст: {text_length} символов, "
                f"Ошибка: {error}, "
                f"Частей: {chunks}"
            )
    
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
    
    async def translate_to_russian(self, text: str, source_lang: str = None, model_index: int = None) -> str:
        """
        Переводит текст на русский язык
        Args:
            text: текст для перевода
            source_lang: исходный язык (если известен)
            model_index: индекс модели для перевода (если None, выбирается случайно)
        Returns:
            переведенный текст или исходный текст в случае ошибки
        """
        if not self.api_key:
            return text
        
        # Если индекс модели не указан, выбираем случайно
        if model_index is None:
            model_index = self.get_random_model_index()
        elif model_index >= len(self.models):
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
            if result and not result.startswith("❌"):
                # Успешный перевод
                summarization_logger.info(
                    f"✅ Перевод УСПЕШЕН - Модель: {model_name}, "
                    f"Исходный язык: {source_lang or 'unknown'}, "
                    f"Исходный текст: {len(text)} символов, "
                    f"Перевод: {len(result)} символов"
                )
                return result
            else:
                # Неуспешный перевод
                summarization_logger.error(
                    f"❌ Перевод НЕУСПЕШЕН - Модель: {model_name}, "
                    f"Исходный язык: {source_lang or 'unknown'}, "
                    f"Исходный текст: {len(text)} символов, "
                    f"Ошибка: {result or 'Неизвестная ошибка'}"
                )
                return text
        except Exception as e:
            error_msg = f"Ошибка перевода: {e}"
            summarization_logger.error(
                f"❌ Перевод НЕУСПЕШЕН - Модель: {model_name}, "
                f"Исходный язык: {source_lang or 'unknown'}, "
                f"Исходный текст: {len(text)} символов, "
                f"Исключение: {error_msg}"
            )
            print(error_msg)
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
    
    async def summarize_text(self, text: str, model_index: int = None, custom_prompt: str = None) -> Tuple[str, dict]:
        """
        Суммаризирует текст по частям, затем создает итоговую суммаризацию
        
        Args:
            text: текст для суммаризации
            model_index: индекс модели (если None, выбирается случайно)
            custom_prompt: пользовательский промпт
        
        Returns:
            Tuple[str, dict]: (итоговая суммаризация, статистика)
        """
        if not self.api_key:
            error_msg = "❌ Не настроен OPENROUTER_API_KEY"
            self.log_summarization_result(False, "none", len(text), 0, 0, error_msg)
            return error_msg, {}
        
        # Если индекс модели не указан, выбираем случайно
        if model_index is None:
            model_index = self.get_random_model_index()
        elif model_index >= len(self.models):
            model_index = 0
        
        model_name, model_id = self.models[model_index]
        prompt = custom_prompt or "Кратко изложи основные мысли этого фрагмента текста."
        
        # Определяем язык исходного текста
        source_language = self.detect_language(text)
        
        # Разбиваем текст на части
        chunks = self.split_text(text)
        
        if not chunks:
            error_msg = "❌ Пустой текст для суммаризации"
            self.log_summarization_result(False, model_name, len(text), 0, 0, error_msg)
            return error_msg, {}
        
        # Если текст короткий - обрабатываем сразу
        if len(chunks) == 1 and len(text) < 2000:
            messages = [
                {"role": "system", "content": "Создай краткую и содержательную суммаризацию текста."},
                {"role": "user", "content": text}
            ]
            result = await self._make_request(model_id, messages)
            
            if result and not result.startswith("❌"):
                # Успешная суммаризация
                stats = {
                    "model": model_name,
                    "chunks": 1,
                    "original_length": len(text),
                    "summary_length": len(result),
                    "source_language": source_language
                }
                self.log_summarization_result(True, model_name, len(text), len(result), 1)
                return result, stats
            else:
                # Неуспешная суммаризация
                error_msg = result or "❌ Не удалось создать суммаризацию"
                stats = {
                    "model": model_name,
                    "chunks": 1,
                    "original_length": len(text),
                    "summary_length": 0,
                    "source_language": source_language
                }
                self.log_summarization_result(False, model_name, len(text), 0, 1, error_msg)
                return error_msg, stats
        
        # Обрабатываем по частям
        chunk_summaries = []
        successful_chunks = 0
        
        for i, chunk in enumerate(chunks):
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": chunk}
            ]
            
            summary = await self._make_request(model_id, messages)
            
            if summary and not summary.startswith("❌"):
                chunk_summaries.append(summary)
                successful_chunks += 1
            
            # Небольшая пауза между запросами
            if i < len(chunks) - 1:
                await asyncio.sleep(2)
        
        if not chunk_summaries:
            error_msg = "❌ Не удалось создать суммаризацию ни одной части"
            self.log_summarization_result(False, model_name, len(text), 0, len(chunks), error_msg)
            return error_msg, {}
        
        # Создаем итоговую суммаризацию
        final_prompt = "Создай единую связную суммаризацию на основе этих фрагментов:"
        combined_text = "\n\n".join(chunk_summaries)
        
        final_messages = [
            {"role": "system", "content": final_prompt},
            {"role": "user", "content": combined_text}
        ]
        
        final_summary = await self._make_request(model_id, final_messages)
        
        if final_summary and not final_summary.startswith("❌"):
            # Успешная итоговая суммаризация
            stats = {
                "model": model_name,
                "chunks": len(chunks),
                "original_length": len(text),
                "summary_length": len(final_summary),
                "processed_chunks": successful_chunks,
                "source_language": source_language
            }
            self.log_summarization_result(True, model_name, len(text), len(final_summary), len(chunks))
            return final_summary, stats
        else:
            # Неуспешная итоговая суммаризация
            error_msg = final_summary or "❌ Не удалось создать итоговую суммаризацию"
            stats = {
                "model": model_name,
                "chunks": len(chunks),
                "original_length": len(text),
                "summary_length": 0,
                "processed_chunks": successful_chunks,
                "source_language": source_language
            }
            self.log_summarization_result(False, model_name, len(text), 0, len(chunks), error_msg)
            return error_msg, stats
    
    def get_available_models(self) -> List[str]:
        """Возвращает список доступных моделей"""
        return [name for name, _ in self.models] 