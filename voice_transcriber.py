#!/usr/bin/env python3
"""
Модуль для расшифровки голосовых сообщений через Soniox API
"""

import os
import json
import time
import asyncio
import tempfile
import traceback
from typing import Optional, Tuple
from datetime import datetime, timedelta

import requests
from pydub import AudioSegment
import logging

logger = logging.getLogger(__name__)

class VoiceTranscriber:
    """Класс для расшифровки голосовых сообщений с использованием Soniox API"""
    
    def __init__(self):
        self.api_key = os.getenv('SONIOX_API_KEY')
        self.api_base = "https://api.soniox.com"
        
        if not self.api_key:
            logger.warning("SONIOX_API_KEY не найден в переменных окружения")
        
        # Настройки повторных попыток
        self.max_retries = 3
        self.base_delay = 2
        self.max_delay = 30
        
        # Создаем сессию с улучшенными настройками
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Улучшенные настройки сессии для стабильности
        self.session.timeout = (10, 30)  # (connect_timeout, read_timeout)
        
        # Настройки адаптера для лучшей обработки соединений
        adapter = requests.adapters.HTTPAdapter(
            max_retries=0,  # Отключаем встроенные повторные попытки
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    async def transcribe_voice_message(self, file_path: str) -> Tuple[bool, str, dict]:
        """Расшифровывает голосовое сообщение"""
        logger.info(f"🎤 Начинаю расшифровку голосового сообщения: {file_path}")
        
        # Проверяем соединение с API с повторными попытками
        if not await self.test_connection_with_retries():
            logger.error("❌ Не удается подключиться к Soniox API после всех попыток")
            return False, "Не удается подключиться к сервису распознавания речи. Проверьте интернет-соединение и попробуйте позже.", {}
        
        try:
            logger.info(f"🔄 Начинаю обработку голосового файла: {file_path}")
            
            # Проверяем существование файла
            if not os.path.exists(file_path):
                error_msg = f"Файл не найден: {file_path}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {}
            
            # Проверяем размер файла
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                error_msg = "Файл пустой (0 байт)"
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {}
            
            logger.info(f"📁 Размер файла: {file_size} байт")
            
            # Конвертируем в формат, подходящий для API
            logger.info("🎵 Конвертирую аудио в подходящий формат")
            try:
                converted_path = await self._convert_audio_format(file_path)
                if not converted_path or not os.path.exists(converted_path):
                    error_msg = "Ошибка конвертации аудио: файл не создан"
                    logger.error(f"❌ {error_msg}")
                    return False, error_msg, {}
                logger.info(f"✅ Аудио сконвертировано: {converted_path}")
            except Exception as conv_error:
                error_msg = f"Ошибка конвертации аудио: {str(conv_error)}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Stack trace конвертации: {traceback.format_exc()}")
                return False, error_msg, {}
            
            # Загружаем файл в Soniox
            logger.info("📤 Загружаю файл в Soniox API")
            file_id = await self._upload_file_with_retries(converted_path)
            if not file_id:
                error_msg = "Ошибка загрузки аудио файла в Soniox API. Попробуйте позже."
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {}
            logger.info(f"✅ Файл загружен в Soniox, file_id: {file_id}")
            
            # Запускаем расшифровку
            logger.info("🚀 Запускаю процесс транскрипции")
            transcription_id = await self._start_transcription_with_retries(file_id)
            if not transcription_id:
                error_msg = "Ошибка запуска расшифровки. Попробуйте позже."
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {}
            logger.info(f"✅ Транскрипция запущена, transcription_id: {transcription_id}")
            
            # Ждем завершения
            logger.info("⏳ Ожидаю завершения транскрипции")
            success = await self._wait_for_completion(transcription_id)
            if not success:
                error_msg = "Ошибка при расшифровке аудио. Попробуйте позже."
                logger.error(f"❌ {error_msg}")
                return False, error_msg, {}
            logger.info("✅ Транскрипция завершена успешно")
            
            # Получаем результат
            logger.info("📥 Получаю результат транскрипции")
            text, stats = await self._get_transcript_with_retries(transcription_id)
            logger.info(f"✅ Результат получен: {len(text)} символов, статистика: {stats}")
            
            # Очищаем ресурсы
            logger.info("🗑️ Очищаю ресурсы в Soniox")
            await self._cleanup(file_id, transcription_id)
            
            # Очищаем временный конвертированный файл
            try:
                if converted_path != file_path and os.path.exists(converted_path):
                    os.unlink(converted_path)
                    logger.info(f"🗑️ Временный конвертированный файл удален: {converted_path}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Не удалось удалить временный конвертированный файл: {cleanup_error}")
            
            return True, text, stats
            
        except Exception as e:
            import traceback
            error_msg = f"Критическая ошибка при расшифровке: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Дополнительная диагностика
            try:
                if 'file_path' in locals():
                    logger.error(f"📁 Путь к файлу: {file_path}")
                    if os.path.exists(file_path):
                        logger.error(f"📊 Размер файла: {os.path.getsize(file_path)} байт")
                    else:
                        logger.error("📁 Файл не существует")
            except Exception as diag_error:
                logger.error(f"⚠️ Ошибка при диагностике: {diag_error}")
            
            return False, error_msg, {}
    
    async def _convert_audio_format(self, file_path: str) -> str:
        """Конвертирует аудио в формат, подходящий для API"""
        try:
            # Загружаем аудио с помощью pydub
            audio = AudioSegment.from_file(file_path)
            
            # Конвертируем в моно, 16kHz, 16-bit PCM
            audio = audio.set_channels(1)  # Моно
            audio = audio.set_frame_rate(16000)  # 16kHz
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Сохраняем во временный файл
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio.export(temp_file.name, format='wav')
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Ошибка конвертации аудио: {e}")
            # Если конвертация не удалась, возвращаем оригинальный файл
            return file_path
    
    async def _upload_file(self, file_path: str) -> Optional[str]:
        """Загружает файл в Soniox API"""
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл не найден: {file_path}")
            return None
        
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        logger.info(f"📁 Размер файла для загрузки: {file_size / 1024:.2f} KB")
        
        if file_size == 0:
            logger.error("❌ Файл пустой, загрузка невозможна")
            return None
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"📤 Попытка загрузки файла {attempt + 1}/{max_retries}")
                
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    response = self.session.post(f"{self.api_base}/v1/files", files=files)
                    
                    logger.info(f"📡 Ответ API: статус {response.status_code}")
                    
                    if response.status_code in [200, 201]:  # 200 OK или 201 Created
                        try:
                            result = response.json()
                            logger.info(f"📋 Ответ API: {result}")
                            
                            # Soniox API может возвращать file_id в разных полях
                            file_id = result.get('file_id') or result.get('id') or result.get('fileId')
                            
                            if file_id:
                                logger.info(f"✅ Файл успешно загружен, получен file_id: {file_id}")
                                return file_id
                            else:
                                logger.error(f"❌ В ответе API не найден file_id. Полный ответ: {result}")
                                return None
                                
                        except json.JSONDecodeError as json_error:
                            logger.error(f"❌ Ошибка парсинга JSON ответа: {json_error}")
                            logger.error(f"📋 Сырой ответ: {response.text}")
                            return None
                            
                    elif response.status_code == 401:
                        logger.error("❌ Ошибка авторизации: проверьте SONIOX_API_KEY")
                        return None
                    elif response.status_code == 413:
                        logger.error("❌ Файл слишком большой для API")
                        return None
                    elif response.status_code == 429:
                        logger.error("❌ Превышен лимит запросов к API")
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * 2
                            logger.info(f"⏳ Ожидаю {wait_time} секунд перед повторной попыткой...")
                            await asyncio.sleep(wait_time)
                            retry_delay *= 2
                            continue
                        return None
                    else:
                        logger.error(f"❌ Ошибка загрузки файла: {response.status_code} - {response.text}")
                        return None
                        
            except requests.exceptions.SSLError as ssl_error:
                logger.error(f"🔒 SSL ошибка при загрузке файла (попытка {attempt + 1}/{max_retries}): {ssl_error}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Повторная попытка через {retry_delay} секунд...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Экспоненциальная задержка
                else:
                    logger.error("❌ Все попытки загрузки файла исчерпаны из-за SSL ошибок")
                    return None
                    
            except requests.exceptions.RequestException as req_error:
                logger.error(f"🌐 Ошибка сети при загрузке файла (попытка {attempt + 1}/{max_retries}): {req_error}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Повторная попытка через {retry_delay} секунд...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("❌ Все попытки загрузки файла исчерпаны из-за сетевых ошибок")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при загрузке файла: {e}")
                import traceback
                logger.error(f"Stack trace: {traceback.format_exc()}")
                return None
        
        logger.error("❌ Все попытки загрузки файла исчерпаны")
        return None
    
    async def _start_transcription(self, file_id: str) -> Optional[str]:
        """Запускает процесс расшифровки"""
        try:
            logger.info(f"🚀 Запускаю транскрипцию для file_id: {file_id}")
            
            request_data = {
                "file_id": file_id,
                "model": "stt-async-preview",
                "language_hints": ["ru", "en"],  # Поддержка русского и английского
                "enable_speaker_diarization": False,  # Отключаем для голосовых сообщений
                "enable_language_identification": True
            }
            
            logger.info(f"📋 Параметры запроса: {request_data}")
            
            response = self.session.post(
                f"{self.api_base}/v1/transcriptions",
                json=request_data
            )
            
            logger.info(f"📡 Ответ API транскрипции: статус {response.status_code}")
            
            if response.status_code in [200, 201]:  # 200 OK или 201 Created
                try:
                    result = response.json()
                    logger.info(f"📋 Ответ API транскрипции: {result}")
                    
                    transcription_id = result.get("id") or result.get("transcription_id")
                    
                    if transcription_id:
                        logger.info(f"✅ Транскрипция запущена, получен ID: {transcription_id}")
                        return transcription_id
                    else:
                        logger.error(f"❌ В ответе API не найден ID транскрипции. Полный ответ: {result}")
                        return None
                        
                except json.JSONDecodeError as json_error:
                    logger.error(f"❌ Ошибка парсинга JSON ответа транскрипции: {json_error}")
                    logger.error(f"📋 Сырой ответ: {response.text}")
                    return None
                    
            elif response.status_code == 401:
                logger.error("❌ Ошибка авторизации при запуске транскрипции: проверьте SONIOX_API_KEY")
                return None
            elif response.status_code == 400:
                logger.error(f"❌ Ошибка в запросе транскрипции: {response.text}")
                return None
            elif response.status_code == 404:
                logger.error(f"❌ Файл не найден для транскрипции: {file_id}")
                return None
            elif response.status_code == 429:
                logger.error("❌ Превышен лимит запросов транскрипции к API")
                return None
            else:
                logger.error(f"❌ Ошибка запуска транскрипции: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.SSLError as ssl_error:
            logger.error(f"🔒 SSL ошибка при запуске транскрипции: {ssl_error}")
            return None
        except requests.exceptions.RequestException as req_error:
            logger.error(f"🌐 Ошибка сети при запуске транскрипции: {req_error}")
            return None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при запуске транскрипции: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    async def _wait_for_completion(self, transcription_id: str, max_wait: int = 300) -> bool:  # Увеличено с 60 до 300 секунд
        """Ждет завершения расшифровки"""
        try:
            logger.info(f"⏳ Ожидаю завершения транскрипции {transcription_id} (максимум {max_wait} сек)")
            
            for i in range(max_wait):
                if i % 10 == 0:  # Логируем каждые 10 секунд
                    logger.info(f"⏳ Проверяю статус транскрипции... ({i}/{max_wait} сек)")
                
                try:
                    response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status", "unknown")
                        
                        logger.debug(f"📊 Статус транскрипции: {status}")
                        
                        if status == "completed":
                            logger.info(f"✅ Транскрипция {transcription_id} завершена успешно")
                            return True
                        elif status == "error":
                            error_msg = data.get('error_message', 'Unknown error')
                            logger.error(f"❌ Ошибка транскрипции {transcription_id}: {error_msg}")
                            return False
                        elif status == "processing":
                            # Продолжаем ожидание
                            pass
                        else:
                            logger.info(f"📊 Неизвестный статус транскрипции: {status}")
                            
                    elif response.status_code == 404:
                        logger.error(f"❌ Транскрипция {transcription_id} не найдена")
                        return False
                    elif response.status_code == 401:
                        logger.error(f"❌ Ошибка авторизации при проверке статуса транскрипции")
                        return False
                    else:
                        logger.warning(f"⚠️ Неожиданный статус при проверке транскрипции: {response.status_code}")
                        
                except requests.exceptions.SSLError as ssl_error:
                    logger.warning(f"🔒 SSL ошибка при проверке статуса (попытка {i+1}): {ssl_error}")
                    # Продолжаем ожидание при SSL ошибках
                except requests.exceptions.RequestException as req_error:
                    logger.warning(f"🌐 Ошибка сети при проверке статуса (попытка {i+1}): {req_error}")
                    # Продолжаем ожидание при сетевых ошибках
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при проверке статуса (попытка {i+1}): {e}")
                    # Продолжаем ожидание при других ошибках
                
                await asyncio.sleep(1)
            
            logger.warning(f"⏰ Превышено время ожидания транскрипции {transcription_id} ({max_wait} секунд)")
            return False
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при ожидании завершения транскрипции {transcription_id}: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
    
    async def _get_transcript(self, transcription_id: str) -> Tuple[str, dict]:
        """Получает результат расшифровки"""
        try:
            logger.info(f"📥 Получаю результат транскрипции {transcription_id}")
            
            # Сначала проверяем статус транскрипции
            status_response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}")
            logger.info(f"📡 Статус транскрипции: {status_response.status_code}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                logger.info(f"📋 Статус транскрипции: {status_data}")
                
                # Проверяем, завершена ли транскрипция
                status = status_data.get("status", "unknown")
                if status != "completed":
                    logger.warning(f"⚠️ Транскрипция еще не завершена, статус: {status}")
                    return "", {}
                
                # Получаем длительность из статуса
                duration_ms = status_data.get("audio_duration_ms", 0)
                if duration_ms:
                    duration = duration_ms / 1000.0  # Конвертируем в секунды
                else:
                    duration = 0
            else:
                logger.error(f"❌ Не удалось получить статус транскрипции: {status_response.status_code}")
                return "", {}
            
            # Получаем результат транскрипции - пробуем разные endpoints
            # Сначала пробуем получить транскрипт напрямую
            response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}/transcript")
            
            # Если не получилось, пробуем получить транскрипт из основного endpoint
            if response.status_code != 200:
                logger.info(f"⚠️ Endpoint /transcript не сработал, пробую основной endpoint")
                response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}")
                
                # Если это статус транскрипции, то нужно получить сам транскрипт
                if response.status_code == 200:
                    status_data = response.json()
                    if status_data.get("status") == "completed":
                        # Пробуем получить транскрипт через другой endpoint
                        transcript_response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}/result")
                        if transcript_response.status_code == 200:
                            response = transcript_response
                            logger.info(f"✅ Получил транскрипт через /result endpoint")
                        else:
                            logger.warning(f"⚠️ Endpoint /result тоже не сработал: {transcript_response.status_code}")
                            # Возвращаем статус как есть, возможно там есть текст
                            data = status_data
                            logger.info(f"📋 Использую данные статуса: {data}")
                            
                            # Проверяем, есть ли текст в статусе
                            text = status_data.get("text") or status_data.get("transcript") or status_data.get("content", "")
                            
                            if not text:
                                logger.warning(f"⚠️ Текст не найден в статусе транскрипции")
                                text = "[Текст не распознан - проверьте аудио файл]"
                            else:
                                text = " ".join(text.split())
                                logger.info(f"✅ Текст найден в статусе: {len(text)} символов")
                            
                            # Собираем статистику из статуса
                            stats = {
                                "transcription_id": transcription_id,
                                "text_length": len(text),
                                "tokens_count": 0,
                                "confidence_avg": 0.0,
                                "language": status_data.get("language", "unknown"),
                                "duration": duration,
                                "status": status
                            }
                            
                            logger.info(f"✅ Результат получен из статуса: {len(text)} символов, статистика: {stats}")
                            return text, stats
            
            logger.info(f"📡 Ответ API получения транскрипта: статус {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"📋 Ответ API получения транскрипта: {data}")
                    
                    # Детальная диагностика структуры ответа
                    logger.info(f"🔍 Анализирую структуру ответа API:")
                    for key, value in data.items():
                        logger.info(f"   • {key}: {type(value).__name__} = {repr(value)}")
                    
                    # Soniox API может возвращать текст в разных полях
                    text = data.get("text") or data.get("transcript") or data.get("content") or data.get("result", "")
                    
                    # Если текст все еще пустой, проверяем другие возможные поля
                    if not text:
                        # Проверяем, есть ли текст в segments или words
                        segments = data.get("segments", [])
                        if segments:
                            logger.info(f"📝 Найдены сегменты: {len(segments)}")
                            text_parts = []
                            for segment in segments:
                                segment_text = segment.get("text", "")
                                if segment_text:
                                    text_parts.append(segment_text)
                            if text_parts:
                                text = " ".join(text_parts)
                                logger.info(f"✅ Текст собран из сегментов: {len(text)} символов")
                        
                        # Если все еще нет текста, проверяем words
                        if not text:
                            words = data.get("words", [])
                            if words:
                                logger.info(f"📝 Найдены слова: {len(words)}")
                                word_texts = []
                                for word in words:
                                    word_text = word.get("text", "")
                                    if word_text:
                                        word_texts.append(word_text)
                                if word_texts:
                                    text = " ".join(word_texts)
                                    logger.info(f"✅ Текст собран из слов: {len(text)} символов")
                    
                    if not text:
                        logger.warning(f"⚠️ Транскрипция завершена, но текст не найден в ответе API")
                        logger.warning(f"📋 Полная структура ответа: {data}")
                        text = "[Текст не распознан - проверьте аудио файл]"
                    else:
                        # Очищаем текст от лишних пробелов и переносов
                        text = " ".join(text.split())
                        logger.info(f"✅ Текст очищен: {len(text)} символов")
                    
                    # Собираем статистику
                    tokens = data.get("tokens", [])
                    stats = {
                        "transcription_id": transcription_id,
                        "text_length": len(text),
                        "tokens_count": len(tokens),
                        "confidence_avg": self._calculate_average_confidence(tokens),
                        "language": data.get("language", "unknown"),
                        "duration": duration,
                        "status": status
                    }
                    
                    logger.info(f"✅ Результат получен: {len(text)} символов, статистика: {stats}")
                    return text, stats
                    
                except json.JSONDecodeError as json_error:
                    logger.error(f"❌ Ошибка парсинга JSON ответа транскрипта: {json_error}")
                    logger.error(f"📋 Сырой ответ: {response.text}")
                    return "", {}
                    
            elif response.status_code == 404:
                logger.error(f"❌ Транскрипт для {transcription_id} не найден")
                return "", {}
            elif response.status_code == 401:
                logger.error(f"❌ Ошибка авторизации при получении транскрипта")
                return "", {}
            elif response.status_code == 400:
                logger.error(f"❌ Ошибка в запросе получения транскрипта: {response.text}")
                return "", {}
            else:
                logger.error(f"❌ Ошибка получения транскрипта: {response.status_code} - {response.text}")
                return "", {}
                
        except requests.exceptions.SSLError as ssl_error:
            logger.error(f"🔒 SSL ошибка при получении транскрипта: {ssl_error}")
            return "", {}
        except requests.exceptions.RequestException as req_error:
            logger.error(f"🌐 Ошибка сети при получении транскрипта: {req_error}")
            return "", {}
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при получении транскрипта: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return "", {}
    
    def _calculate_average_confidence(self, tokens: list) -> float:
        """Вычисляет среднюю уверенность распознавания"""
        if not tokens:
            return 0.0
        
        confidences = [token.get("confidence", 0.0) for token in tokens]
        return sum(confidences) / len(confidences)
    
    async def _cleanup(self, file_id: str, transcription_id: str):
        """Очищает ресурсы в Soniox API"""
        try:
            logger.info(f"🗑️ Начинаю очистку ресурсов: file_id={file_id}, transcription_id={transcription_id}")
            
            # Удаляем расшифровку
            try:
                response = self.session.delete(f"{self.api_base}/v1/transcriptions/{transcription_id}")
                if response.status_code in [200, 204]:  # 200 OK или 204 No Content
                    logger.info(f"✅ Транскрипция {transcription_id} успешно удалена")
                elif response.status_code == 404:
                    logger.info(f"ℹ️ Транскрипция {transcription_id} уже удалена")
                else:
                    logger.warning(f"⚠️ Неожиданный статус при удалении транскрипции: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при удалении транскрипции {transcription_id}: {e}")
            
            # Удаляем файл
            try:
                response = self.session.delete(f"{self.api_base}/v1/files/{file_id}")
                if response.status_code in [200, 204]:  # 200 OK или 204 No Content
                    logger.info(f"✅ Файл {file_id} успешно удален")
                elif response.status_code == 404:
                    logger.info(f"ℹ️ Файл {file_id} уже удален")
                else:
                    logger.warning(f"⚠️ Неожиданный статус при удалении файла: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при удалении файла {file_id}: {e}")
            
            logger.info(f"✅ Очистка ресурсов завершена")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при очистке ресурсов: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
    
    def is_available(self) -> bool:
        """Проверяет доступность сервиса"""
        return bool(self.api_key)
    
    async def test_connection_with_retries(self) -> bool:
        """Тестирует соединение с Soniox API с повторными попытками"""
        if not self.api_key:
            logger.error("❌ SONIOX_API_KEY не настроен")
            return False
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔍 Тестирую соединение с Soniox API (попытка {attempt + 1}/{self.max_retries})...")
                
                # Простой запрос для проверки доступности
                response = self.session.get(f"{self.api_base}/v1/models", timeout=(5, 10))
                
                if response.status_code in [200, 201, 204]:  # 200 OK, 201 Created, 204 No Content
                    logger.info("✅ Соединение с Soniox API успешно")
                    return True
                elif response.status_code == 401:
                    logger.error("❌ Ошибка авторизации: проверьте SONIOX_API_KEY")
                    return False
                elif response.status_code == 403:
                    logger.error("❌ Доступ запрещен: проверьте права доступа к API")
                    return False
                elif response.status_code == 429:
                    logger.error("❌ Превышен лимит запросов к API")
                    return False
                else:
                    logger.warning(f"⚠️ Неожиданный статус при тестировании: {response.status_code}")
                    logger.info(f"📋 Ответ API: {response.text[:200]}...")  # Первые 200 символов
                    
                    # Если это не критическая ошибка, пробуем еще раз
                    if response.status_code < 500:  # Клиентские ошибки
                        return False
                    
            except requests.exceptions.SSLError as ssl_error:
                logger.error(f"🔒 SSL ошибка при тестировании соединения (попытка {attempt + 1}): {ssl_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                    await asyncio.sleep(delay)
                continue
                
            except requests.exceptions.Timeout as timeout_error:
                logger.error(f"⏰ Таймаут при тестировании соединения (попытка {attempt + 1}): {timeout_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                    await asyncio.sleep(delay)
                continue
                
            except requests.exceptions.ConnectionError as conn_error:
                logger.error(f"🌐 Ошибка соединения при тестировании (попытка {attempt + 1}): {conn_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                    await asyncio.sleep(delay)
                continue
                
            except requests.exceptions.RequestException as req_error:
                logger.error(f"🌐 Ошибка сети при тестировании соединения (попытка {attempt + 1}): {req_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                    await asyncio.sleep(delay)
                continue
                
            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при тестировании соединения (попытка {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                    await asyncio.sleep(delay)
                continue
        
        logger.error(f"❌ Не удалось установить соединение с Soniox API после {self.max_retries} попыток")
        return False

    async def _upload_file_with_retries(self, file_path: str) -> Optional[str]:
        """Загружает файл в Soniox API с повторными попытками"""
        if not os.path.exists(file_path):
            logger.error(f"❌ Файл не найден: {file_path}")
            return None
        
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        logger.info(f"📁 Размер файла для загрузки: {file_size / 1024:.2f} KB")
        
        if file_size == 0:
            logger.error("❌ Файл пустой, загрузка невозможна")
            return None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"📤 Попытка загрузки файла {attempt + 1}/{self.max_retries}")
                
                with open(file_path, 'rb') as f:
                    files = {'file': f}
                    response = self.session.post(f"{self.api_base}/v1/files", files=files, timeout=(30, 60))
                    
                    logger.info(f"📡 Ответ API: статус {response.status_code}")
                    
                    if response.status_code in [200, 201]:  # 200 OK или 201 Created
                        try:
                            result = response.json()
                            logger.info(f"📋 Ответ API: {result}")
                            
                            # Soniox API может возвращать file_id в разных полях
                            file_id = result.get('file_id') or result.get('id') or result.get('fileId')
                            
                            if file_id:
                                logger.info(f"✅ Файл успешно загружен, получен file_id: {file_id}")
                                return file_id
                            else:
                                logger.error(f"❌ В ответе API не найден file_id. Полный ответ: {result}")
                                return None
                                
                        except json.JSONDecodeError as json_error:
                            logger.error(f"❌ Ошибка парсинга JSON ответа: {json_error}")
                            logger.error(f"📋 Сырой ответ: {response.text}")
                            return None
                            
                    elif response.status_code == 401:
                        logger.error("❌ Ошибка авторизации: проверьте SONIOX_API_KEY")
                        return None
                    elif response.status_code == 413:
                        logger.error("❌ Файл слишком большой для API")
                        return None
                    elif response.status_code == 429:
                        logger.error("❌ Превышен лимит запросов к API")
                        if attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                            await asyncio.sleep(delay)
                            continue
                        return None
                    else:
                        logger.error(f"❌ Ошибка загрузки файла: {response.status_code} - {response.text}")
                        if attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                            await asyncio.sleep(delay)
                            continue
                        return None
                        
            except requests.exceptions.SSLError as ssl_error:
                logger.error(f"🔒 SSL ошибка при загрузке файла (попытка {attempt + 1}/{self.max_retries}): {ssl_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки загрузки файла исчерпаны из-за SSL ошибок")
                    return None
                    
            except requests.exceptions.Timeout as timeout_error:
                logger.error(f"⏰ Таймаут при загрузке файла (попытка {attempt + 1}/{self.max_retries}): {timeout_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки загрузки файла исчерпаны из-за таймаутов")
                    return None
                    
            except requests.exceptions.ConnectionError as conn_error:
                logger.error(f"🌐 Ошибка соединения при загрузке файла (попытка {attempt + 1}/{self.max_retries}): {conn_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки загрузки файла исчерпаны из-за ошибок соединения")
                    return None
                    
            except requests.exceptions.RequestException as req_error:
                logger.error(f"🌐 Ошибка сети при загрузке файла (попытка {attempt + 1}/{self.max_retries}): {req_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки загрузки файла исчерпаны из-за сетевых ошибок")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при загрузке файла (попытка {attempt + 1}/{self.max_retries}): {e}")
                import traceback
                logger.error(f"Stack trace: {traceback.format_exc()}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                return None
        
        logger.error("❌ Все попытки загрузки файла исчерпаны")
        return None

    async def _start_transcription_with_retries(self, file_id: str) -> Optional[str]:
        """Запускает процесс расшифровки с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🚀 Запускаю транскрипцию для file_id: {file_id} (попытка {attempt + 1}/{self.max_retries})")
                
                request_data = {
                    "file_id": file_id,
                    "model": "stt-async-preview",
                    "language_hints": ["ru", "en"],  # Поддержка русского и английского
                    "enable_speaker_diarization": False,  # Отключаем для голосовых сообщений
                    "enable_language_identification": True
                }
                
                logger.info(f"📋 Параметры запроса: {request_data}")
                
                response = self.session.post(
                    f"{self.api_base}/v1/transcriptions",
                    json=request_data,
                    timeout=(10, 30)
                )
                
                logger.info(f"📡 Ответ API транскрипции: статус {response.status_code}")
                
                if response.status_code in [200, 201]:  # 200 OK или 201 Created
                    try:
                        result = response.json()
                        logger.info(f"📋 Ответ API транскрипции: {result}")
                        
                        transcription_id = result.get("id") or result.get("transcription_id")
                        
                        if transcription_id:
                            logger.info(f"✅ Транскрипция запущена, получен ID: {transcription_id}")
                            return transcription_id
                        else:
                            logger.error(f"❌ В ответе API не найден ID транскрипции. Полный ответ: {result}")
                            return None
                            
                    except json.JSONDecodeError as json_error:
                        logger.error(f"❌ Ошибка парсинга JSON ответа транскрипции: {json_error}")
                        logger.error(f"📋 Сырой ответ: {response.text}")
                        return None
                        
                elif response.status_code == 401:
                    logger.error("❌ Ошибка авторизации при запуске транскрипции")
                    return None
                elif response.status_code == 400:
                    logger.error(f"❌ Ошибка в запросе транскрипции: {response.text}")
                    return None
                elif response.status_code == 429:
                    logger.error("❌ Превышен лимит запросов к API")
                    if attempt < self.max_retries - 1:
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                        await asyncio.sleep(delay)
                        continue
                    return None
                else:
                    logger.error(f"❌ Ошибка запуска транскрипции: {response.status_code} - {response.text}")
                    if attempt < self.max_retries - 1:
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                        await asyncio.sleep(delay)
                        continue
                    return None
                        
            except requests.exceptions.SSLError as ssl_error:
                logger.error(f"🔒 SSL ошибка при запуске транскрипции (попытка {attempt + 1}/{self.max_retries}): {ssl_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки запуска транскрипции исчерпаны из-за SSL ошибок")
                    return None
                    
            except requests.exceptions.Timeout as timeout_error:
                logger.error(f"⏰ Таймаут при запуске транскрипции (попытка {attempt + 1}/{self.max_retries}): {timeout_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки запуска транскрипции исчерпаны из-за таймаутов")
                    return None
                    
            except requests.exceptions.ConnectionError as conn_error:
                logger.error(f"🌐 Ошибка соединения при запуске транскрипции (попытка {attempt + 1}/{self.max_retries}): {conn_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки запуска транскрипции исчерпаны из-за ошибок соединения")
                    return None
                    
            except requests.exceptions.RequestException as req_error:
                logger.error(f"🌐 Ошибка сети при запуске транскрипции (попытка {attempt + 1}/{self.max_retries}): {req_error}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки запуска транскрипции исчерпаны из-за сетевых ошибок")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при запуске транскрипции (попытка {attempt + 1}/{self.max_retries}): {e}")
                import traceback
                logger.error(f"Stack trace: {traceback.format_exc()}")
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                return None
        
        logger.error("❌ Все попытки запуска транскрипции исчерпаны")
        return None

    async def _get_transcript_with_retries(self, transcription_id: str) -> Tuple[str, dict]:
        """Получает результат транскрипции с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"📥 Получаю результат транскрипции {transcription_id} (попытка {attempt + 1}/{self.max_retries})")
                
                # Используем улучшенный метод получения транскрипта
                text, stats = await self._get_transcript(transcription_id)
                
                if text and text != "[Текст не распознан - проверьте аудио файл]":
                    logger.info(f"✅ Транскрипт успешно получен: {len(text)} символов")
                    return text, stats
                else:
                    logger.warning(f"⚠️ Попытка {attempt + 1}: Транскрипт пустой или не распознан")
                    
                    if attempt < self.max_retries - 1:
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        logger.info(f"⏳ Ожидаю {delay} секунд перед повторной попыткой...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error("❌ Все попытки получения транскрипта исчерпаны")
                        return text, stats  # Возвращаем последний результат
                        
            except Exception as e:
                logger.error(f"❌ Ошибка при получении транскрипта (попытка {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"⏳ Повторная попытка через {delay} секунд...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ Все попытки получения транскрипта исчерпаны")
                    return "", {}
        
        logger.error("❌ Все попытки получения транскрипта исчерпаны")
        return "", {}

    async def test_connection(self) -> bool:
        """Тестирует соединение с Soniox API (устаревший метод, используйте test_connection_with_retries)"""
        return await self.test_connection_with_retries() 