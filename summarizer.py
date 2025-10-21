import os
import requests
import re
import time
import asyncio
import random
import logging
from typing import List, Optional, Tuple, Dict
from dotenv import load_dotenv

load_dotenv()

# Настройка логгера для суммаризации
summarization_logger = logging.getLogger('summarization')
summarization_logger.setLevel(logging.INFO)

# Создаем файловый обработчик для лога суммаризации
if not summarization_logger.handlers:
    # Убеждаемся что папка logs существует
    os.makedirs('logs', exist_ok=True)
    summarization_handler = logging.FileHandler('logs/summarization.log', encoding='utf-8-sig')
    summarization_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    summarization_handler.setFormatter(summarization_formatter)
    summarization_logger.addHandler(summarization_handler)

class TextSummarizer:
    """Класс для суммаризации текста через OpenRouter API с автоматическим выбором модели"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.chunk_size = 1000
        self.max_retries = 3
        self.retry_delay = 5
        self.rate_limit_delay = 60
        
        # Лимиты для текстов разной длины
        self.warning_threshold = 15000  # Предупреждение для текстов > 15K символов
        self.max_text_length = 50000    # Максимальная длина для обработки
        self.large_text_threshold = 30000  # Порог для "больших" текстов
        
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
        
        # История использованных моделей для текущей сессии
        self.used_models = set()
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://openrouter.ai/",
            "X-Title": "Telegram Subs-bot"
        }
    
    def check_text_length(self, text: str) -> dict:
        """
        Проверяет длину текста и возвращает рекомендации
        
        Args:
            text: текст для проверки
            
        Returns:
            dict: информация о длине текста и рекомендации
        """
        text_length = len(text)
        
        result = {
            "length": text_length,
            "chunks": len(self.split_text(text)),
            "status": "ok",
            "warning": None,
            "can_process": True
        }
        
        if text_length > self.max_text_length:
            result["status"] = "too_long"
            result["warning"] = f"❌ Текст слишком длинный ({text_length:,} символов). Максимальная длина: {self.max_text_length:,} символов."
            result["can_process"] = False
        elif text_length > self.large_text_threshold:
            result["status"] = "very_large"
            result["warning"] = f"⚠️ Текст очень длинный ({text_length:,} символов, {result['chunks']} частей). Обработка может занять 10-15 минут."
        elif text_length > self.warning_threshold:
            result["status"] = "large"
            result["warning"] = f"📝 Текст длинный ({text_length:,} символов, {result['chunks']} частей). Обработка займет 5-10 минут."
        
        return result
    
    def get_available_model_index(self) -> int:
        """Возвращает индекс доступной модели, избегая уже использованных"""
        available_models = [i for i in range(len(self.models)) if i not in self.used_models]
        
        if not available_models:
            # Если все модели использованы, сбрасываем историю
            self.used_models.clear()
            available_models = list(range(len(self.models)))
        
        # Выбираем случайную доступную модель
        selected_index = random.choice(available_models)
        self.used_models.add(selected_index)
        
        summarization_logger.info(f"🎯 Выбрана модель: {self.models[selected_index][0]} (индекс: {selected_index})")
        return selected_index
    
    def log_summarization_result(self, success: bool, model_name: str, text_length: int, 
                                summary_length: int, chunks: int, error: str = None, 
                                user_satisfied: bool = None):
        """Логирует результат суммаризации с информацией об удовлетворенности пользователя"""
        if success:
            satisfaction_info = f", Пользователь доволен: {user_satisfied}" if user_satisfied is not None else ""
            summarization_logger.info(
                f"✅ Суммаризация УСПЕШНА - Модель: {model_name}, "
                f"Исходный текст: {text_length} символов, "
                f"Суммаризация: {summary_length} символов, "
                f"Частей: {chunks}{satisfaction_info}"
            )
        else:
            summarization_logger.error(
                f"❌ Суммаризация НЕУСПЕШНА - Модель: {model_name}, "
                f"Исходный текст: {text_length} символов, "
                f"Ошибка: {error}, "
                f"Частей: {chunks}"
            )
    
    def log_user_feedback(self, model_name: str, text_length: int, summary_length: int, 
                          user_satisfied: bool, feedback_reason: str = None):
        """Логирует обратную связь пользователя"""
        feedback_text = f"Пользователь {'доволен' if user_satisfied else 'не доволен'}"
        if feedback_reason:
            feedback_text += f" - Причина: {feedback_reason}"
        
        summarization_logger.info(
            f"👤 Обратная связь - Модель: {model_name}, "
            f"Исходный текст: {text_length} символов, "
            f"Суммаризация: {summary_length} символов, "
            f"{feedback_text}"
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
    
    async def translate_to_russian(self, text: str, source_lang: str = None) -> str:
        """
        Переводит текст на русский язык с автоматическим выбором модели
        Args:
            text: текст для перевода
            source_lang: исходный язык (если известен)
        Returns:
            переведенный текст или исходный текст в случае ошибки
        """
        if not self.api_key:
            return text
        
        # Автоматически выбираем модель для перевода
        model_index = self.get_available_model_index()
        model_name, model_id = self.models[model_index]
        
        # Формируем промпт для перевода
        if source_lang == 'en':
            prompt = "Переведи следующий текст с английского на русский язык, сохранив смысл и стиль:"
        elif source_lang == 'other':
            prompt = "Переведи следующий текст на русский язык, сохранив смысл и стиль:"
        else:
            prompt = "Переведи следующий текст на русский язык, сохранив смысл и стиль:"
        
        messages = [
            {"role": "system", "content": """Ты - профессиональный переводчик. 

**Требования к переводу:**
• Переводи текст на русский язык
• Сохраняй смысл, стиль и структуру
• Сохраняй форматирование (абзацы, **жирный текст**, списки)
• Адаптируй под русский язык, но сохраняй оригинальный стиль
• Используй правильную русскую пунктуацию"""},
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
                
                # Получаем основной контент
                content = result["choices"][0]["message"]["content"]
                
                # Получаем дополнительную информацию
                usage = result.get("usage", {})
                model_info = result.get("model", model_id)
                
                # Сохраняем дополнительную информацию для статистики
                if not hasattr(self, '_last_api_info'):
                    self._last_api_info = {}
                
                self._last_api_info = {
                    "model_used": model_info,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "finish_reason": result["choices"][0].get("finish_reason", "unknown")
                }
                
                return content
                
            except Exception as e:
                if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                    # Rate limit - ждем дольше
                    await asyncio.sleep(self.rate_limit_delay)
                elif attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    return f"Ошибка после {self.max_retries} попыток: {str(e)}"
        
        return None
    
    async def summarize_text(self, text: str, custom_prompt: str = None, forced_model_index: int = None) -> Tuple[str, dict]:
        """
        Суммаризирует текст по частям с автоматическим выбором модели
        
        Args:
            text: текст для суммаризации
            custom_prompt: пользовательский промпт
            forced_model_index: принудительный индекс модели (для retry механизма)
        
        Returns:
            Tuple[str, dict]: (итоговая суммаризация, статистика)
        """
        if not self.api_key:
            error_msg = "❌ Не настроен OPENROUTER_API_KEY"
            self.log_summarization_result(False, "none", len(text), 0, 0, error_msg)
            return error_msg, {}
        
        # Выбираем модель: либо принудительно, либо автоматически
        if forced_model_index is not None:
            model_index = forced_model_index
        else:
            model_index = self.get_available_model_index()
        
        model_name, model_id = self.models[model_index]
        
        prompt = custom_prompt or (
            "Ты — эксперт по созданию кратких и информативных суммаризаций.\n"
            "Требования к формату (Markdown):\n"
            "• Разбивай мыслительные блоки на абзацы и разделяй абзацы пустой строкой.\n"
            "• Выделяй ключевые понятия **жирным**.\n"
            "• Используй маркированные списки там, где уместно.\n"
            "• Допускается использовать уместные эмодзи в заголовках/маркерах (не злоупотребляй).\n"
            "• Пиши по-русски, соблюдая пунктуацию."
        )
        
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
                {
                    "role": "system",
                    "content": (
                        "Ты — эксперт по созданию кратких и информативных суммаризаций. "
                        "Строго соблюдай Markdown-оформление: абзацы с пустыми строками, **жирные** ключи, списки; "
                        "уместные эмодзи разрешены."
                    )
                },
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
                
                # Добавляем дополнительную информацию от API
                if hasattr(self, '_last_api_info'):
                    stats.update(self._last_api_info)
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
        final_prompt = (
            "Создай единую связную суммаризацию на основе этих фрагментов. "
            "Строго оформи в Markdown: абзацы разделяй пустой строкой, выделяй **ключевые понятия**, "
            "используй маркированные списки там, где это улучшает читабельность, допускай уместные эмодзи."
        )
        combined_text = "\n\n".join(chunk_summaries)
        
        # Улучшенная итоговая суммаризация с retry механизмом
        final_summary = await self._create_final_summary_with_retry(model_id, combined_text, final_prompt)
        
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
            
            # Добавляем дополнительную информацию от API
            if hasattr(self, '_last_api_info'):
                stats.update(self._last_api_info)
            self.log_summarization_result(True, model_name, len(text), len(final_summary), len(chunks))
            return final_summary, stats
        else:
            # Неуспешная итоговая суммаризация - возвращаем промежуточные результаты
            error_msg = final_summary or "❌ Не удалось создать итоговую суммаризацию"
            
            # Fallback: возвращаем промежуточные результаты
            if chunk_summaries:
                fallback_summary = self._create_fallback_summary(chunk_summaries)
                warning_msg = f"⚠️ Итоговая суммаризация не удалась. Возвращаю промежуточные результаты:\n\n{fallback_summary}"
                
                stats = {
                    "model": model_name,
                    "chunks": len(chunks),
                    "original_length": len(text),
                    "summary_length": len(fallback_summary),
                    "processed_chunks": successful_chunks,
                    "source_language": source_language,
                    "fallback_used": True,
                    "final_summary_failed": True
                }
                
                if hasattr(self, '_last_api_info'):
                    stats.update(self._last_api_info)
                
                self.log_summarization_result(False, model_name, len(text), len(fallback_summary), len(chunks), error_msg)
                return warning_msg, stats
            else:
                # Полный провал
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
    
    async def summarize_with_retry(self, text: str, custom_prompt: str = None, max_retries: int = 3) -> Tuple[str, dict, bool]:
        """
        Суммаризирует текст с возможностью повторной попытки при неудовлетворительном результате
        
        Args:
            text: текст для суммаризации
            custom_prompt: пользовательский промпт
            max_retries: максимальное количество попыток с разными моделями
        
        Returns:
            Tuple[str, dict, bool]: (суммаризация, статистика, успешность)
        """
        used_models = []
        last_error = None
        
        for attempt in range(max_retries):
            # Выбираем модель, избегая уже использованных
            model_index = self.get_available_model_index()
            model_name, model_id = self.models[model_index]
            used_models.append(model_name)
            
            summarization_logger.info(f"🔄 Попытка {attempt + 1}/{max_retries} с моделью: {model_name}")
            
            try:
                summary, stats = await self.summarize_text(text, custom_prompt, model_index)
                success = not summary.startswith("❌")
                
                if success:
                    summarization_logger.info(f"✅ Суммаризация успешна с моделью {model_name} на попытке {attempt + 1}")
                    return summary, stats, True
                else:
                    last_error = summary
                    summarization_logger.warning(f"⚠️ Попытка {attempt + 1} с моделью {model_name} не удалась: {summary}")
                    
            except Exception as e:
                last_error = f"Ошибка: {str(e)}"
                summarization_logger.error(f"❌ Исключение при попытке {attempt + 1} с моделью {model_name}: {e}")
            
            # Небольшая пауза между попытками
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
        
        # Все попытки исчерпаны
        error_msg = f"❌ Все {max_retries} попытки суммаризации не удались. Использованные модели: {', '.join(used_models)}. Последняя ошибка: {last_error}"
        summarization_logger.error(error_msg)
        
        # Возвращаем пустую статистику при неудаче
        failed_stats = {
            "model": "multiple_attempts",
            "chunks": 0,
            "original_length": len(text),
            "summary_length": 0,
            "used_models": used_models,
            "last_error": last_error
        }
        
        return error_msg, failed_stats, False
    
    async def _create_final_summary_with_retry(self, model_id: str, combined_text: str, prompt: str, max_retries: int = 3) -> str:
        """
        Создает итоговую суммаризацию с retry механизмом
        
        Args:
            model_id: ID модели для использования
            combined_text: объединенный текст всех частей
            prompt: промпт для итоговой суммаризации
            max_retries: максимальное количество попыток
            
        Returns:
            итоговая суммаризация или сообщение об ошибке
        """
        for attempt in range(1, max_retries + 1):
            try:
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": combined_text}
                ]
                
                result = await self._make_request(model_id, messages)
                
                if result and not result.startswith("❌"):
                    return result
                else:
                    summarization_logger.warning(f"⚠️ Попытка {attempt}/{max_retries} итоговой суммаризации не удалась: {result}")
                    
            except Exception as e:
                summarization_logger.error(f"❌ Исключение при попытке {attempt}/{max_retries} итоговой суммаризации: {e}")
            
            # Пауза между попытками
            if attempt < max_retries:
                await asyncio.sleep(self.retry_delay * attempt)  # Увеличиваем паузу с каждой попыткой
        
        return "❌ Не удалось создать итоговую суммаризацию после всех попыток"
    
    def _create_fallback_summary(self, chunk_summaries: List[str]) -> str:
        """
        Создает fallback суммаризацию из промежуточных результатов
        
        Args:
            chunk_summaries: список суммаризаций частей
            
        Returns:
            fallback суммаризация
        """
        if not chunk_summaries:
            return "❌ Нет промежуточных результатов для создания fallback суммаризации"
        
        # Объединяем промежуточные результаты с разделителями
        fallback_parts = []
        for i, summary in enumerate(chunk_summaries, 1):
            fallback_parts.append(f"**Часть {i}:**\n{summary}")
        
        fallback_text = "\n\n---\n\n".join(fallback_parts)
        
        # Добавляем заголовок
        header = f"⚠️ **ПРОМЕЖУТОЧНЫЕ РЕЗУЛЬТАТЫ**\n\n*Итоговая суммаризация не удалась, но вот что получилось по частям:*\n\n"
        
        return header + fallback_text
    
    async def summarize_with_feedback(self, text: str, custom_prompt: str = None) -> Tuple[str, dict, bool]:
        """
        Суммаризирует текст и возвращает результат для запроса обратной связи
        
        Args:
            text: текст для суммаризации
            custom_prompt: пользовательский промпт
        
        Returns:
            Tuple[str, dict, bool]: (суммаризация, статистика, успешность)
        """
        summary, stats = await self.summarize_text(text, custom_prompt)
        success = not summary.startswith("❌")
        return summary, stats, success
    
    def get_available_models(self) -> List[str]:
        """Возвращает список доступных моделей"""
        return [name for name, _ in self.models]
    
    def get_model_usage_stats(self) -> Dict[str, int]:
        """Возвращает статистику использования моделей в текущей сессии"""
        return {self.models[i][0]: 1 for i in self.used_models} 