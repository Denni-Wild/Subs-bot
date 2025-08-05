import os
import json
import asyncio
import logging
import tempfile
from io import BytesIO
from typing import Optional, Tuple
import requests
from telegram import Voice
from pydub import AudioSegment
import ffmpeg

logger = logging.getLogger(__name__)

class VoiceTranscriber:
    """Класс для расшифровки голосовых сообщений с использованием Soniox API"""
    
    def __init__(self):
        self.api_key = os.getenv('SONIOX_API_KEY')
        self.api_base = "https://api.soniox.com"
        
        if not self.api_key:
            logger.warning("SONIOX_API_KEY не найден в переменных окружения")
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.api_key}"
    
    async def transcribe_voice_message(self, voice: Voice, file_path: str) -> Tuple[bool, str, dict]:
        """
        Расшифровывает голосовое сообщение
        
        Args:
            voice: Объект голосового сообщения от Telegram
            file_path: Путь к сохраненному файлу
            
        Returns:
            Tuple[success, text, stats]
        """
        if not self.api_key:
            return False, "API ключ для распознавания речи не настроен", {}
        
        try:
            logger.info(f"🔄 Начинаю обработку голосового файла: {file_path}")
            
            # Конвертируем в формат, подходящий для API
            logger.info("🎵 Конвертирую аудио в подходящий формат")
            converted_path = await self._convert_audio_format(file_path)
            logger.info(f"✅ Аудио сконвертировано: {converted_path}")
            
            # Загружаем файл в Soniox
            logger.info("📤 Загружаю файл в Soniox API")
            file_id = await self._upload_file(converted_path)
            if not file_id:
                logger.error("❌ Ошибка загрузки аудио файла в Soniox")
                return False, "Ошибка загрузки аудио файла", {}
            logger.info(f"✅ Файл загружен в Soniox, file_id: {file_id}")
            
            # Запускаем расшифровку
            logger.info("🚀 Запускаю процесс транскрипции")
            transcription_id = await self._start_transcription(file_id)
            if not transcription_id:
                logger.error("❌ Ошибка запуска расшифровки")
                return False, "Ошибка запуска расшифровки", {}
            logger.info(f"✅ Транскрипция запущена, transcription_id: {transcription_id}")
            
            # Ждем завершения
            logger.info("⏳ Ожидаю завершения транскрипции")
            success = await self._wait_for_completion(transcription_id)
            if not success:
                logger.error("❌ Ошибка при расшифровке аудио")
                return False, "Ошибка при расшифровке аудио", {}
            logger.info("✅ Транскрипция завершена успешно")
            
            # Получаем результат
            logger.info("📥 Получаю результат транскрипции")
            text, stats = await self._get_transcript(transcription_id)
            logger.info(f"✅ Результат получен: {len(text)} символов, статистика: {stats}")
            
            # Очищаем ресурсы
            logger.info("🗑️ Очищаю ресурсы в Soniox")
            await self._cleanup(file_id, transcription_id)
            
            return True, text, stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка при расшифровке голосового сообщения: {e}", exc_info=True)
            return False, f"Ошибка при расшифровке: {str(e)}", {}
    
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
        """Загружает файл в Soniox"""
        try:
            with open(file_path, 'rb') as f:
                response = self.session.post(
                    f"{self.api_base}/v1/files",
                    files={"file": f}
                )
                response.raise_for_status()
                return response.json()["id"]
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")
            return None
    
    async def _start_transcription(self, file_id: str) -> Optional[str]:
        """Запускает процесс расшифровки"""
        try:
            response = self.session.post(
                f"{self.api_base}/v1/transcriptions",
                json={
                    "file_id": file_id,
                    "model": "stt-async-preview",
                    "language_hints": ["ru", "en"],  # Поддержка русского и английского
                    "enable_speaker_diarization": False,  # Отключаем для голосовых сообщений
                    "enable_language_identification": True
                }
            )
            response.raise_for_status()
            return response.json()["id"]
        except Exception as e:
            logger.error(f"Ошибка запуска расшифровки: {e}")
            return None
    
    async def _wait_for_completion(self, transcription_id: str, max_wait: int = 300) -> bool:  # Увеличено с 60 до 300 секунд
        """Ждет завершения расшифровки"""
        try:
            for _ in range(max_wait):
                response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}")
                response.raise_for_status()
                data = response.json()
                
                if data["status"] == "completed":
                    return True
                elif data["status"] == "error":
                    logger.error(f"Ошибка расшифровки: {data.get('error_message', 'Unknown error')}")
                    return False
                
                await asyncio.sleep(1)
            
            logger.warning(f"Превышено время ожидания расшифровки ({max_wait} секунд)")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при ожидании завершения: {e}")
            return False
    
    async def _get_transcript(self, transcription_id: str) -> Tuple[str, dict]:
        """Получает результат расшифровки"""
        try:
            response = self.session.get(f"{self.api_base}/v1/transcriptions/{transcription_id}/transcript")
            response.raise_for_status()
            data = response.json()
            
            text = data.get("text", "")
            
            # Собираем статистику
            stats = {
                "transcription_id": transcription_id,
                "text_length": len(text),
                "tokens_count": len(data.get("tokens", [])),
                "confidence_avg": self._calculate_average_confidence(data.get("tokens", []))
            }
            
            return text, stats
            
        except Exception as e:
            logger.error(f"Ошибка получения результата: {e}")
            return "", {}
    
    def _calculate_average_confidence(self, tokens: list) -> float:
        """Вычисляет среднюю уверенность распознавания"""
        if not tokens:
            return 0.0
        
        confidences = [token.get("confidence", 0.0) for token in tokens]
        return sum(confidences) / len(confidences)
    
    async def _cleanup(self, file_id: str, transcription_id: str):
        """Очищает ресурсы"""
        try:
            # Удаляем расшифровку
            self.session.delete(f"{self.api_base}/v1/transcriptions/{transcription_id}")
            
            # Удаляем файл
            self.session.delete(f"{self.api_base}/v1/files/{file_id}")
            
        except Exception as e:
            logger.warning(f"Ошибка при очистке ресурсов: {e}")
    
    def is_available(self) -> bool:
        """Проверяет доступность сервиса"""
        return bool(self.api_key) 