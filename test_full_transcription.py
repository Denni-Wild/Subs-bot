#!/usr/bin/env python3
"""
Полный тест транскрипции через Soniox API
"""

import os
import asyncio
from dotenv import load_dotenv
from voice_transcriber import VoiceTranscriber
from pydub import AudioSegment
import numpy as np

async def test_full_transcription():
    """Тестирует полный процесс транскрипции"""
    
    print("🚀 Начинаю полный тест транскрипции")
    print("=" * 60)
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем наличие API ключа
    api_key = os.getenv('SONIOX_API_KEY')
    if not api_key:
        print("❌ SONIOX_API_KEY не найден в переменных окружения")
        return False
    
    print(f"✅ API ключ найден: {api_key[:10]}...")
    
    # Создаем экземпляр транскрайбера
    transcriber = VoiceTranscriber()
    
    # Проверяем доступность
    if not transcriber.is_available():
        print("❌ Транскрайбер недоступен")
        return False
    
    print("✅ Транскрайбер доступен")
    
    # Тестируем соединение
    print("🔍 Тестирую соединение с API...")
    if not await transcriber.test_connection():
        print("❌ Не удается подключиться к Soniox API")
        return False
    
    print("✅ Соединение с Soniox API успешно")
    
    # Создаем тестовый аудио файл (2 секунды с простым тоном)
    print("\n🎵 Создаю тестовый аудио файл...")
    test_file_path = "test_audio_full.wav"
    
    try:
        # Создаем простой тон (440 Hz - нота A)
        sample_rate = 16000
        duration = 2.0  # 2 секунды
        samples = int(sample_rate * duration)
        
        # Создаем синусоидальный сигнал
        t = np.linspace(0, duration, samples, False)
        frequency = 440  # Hz
        audio_data = np.sin(2 * np.pi * frequency * t)
        
        # Конвертируем в 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Создаем AudioSegment
        audio = AudioSegment(
            audio_data.tobytes(), 
            frame_rate=sample_rate,
            sample_width=2,  # 16-bit
            channels=1  # моно
        )
        
        # Сохраняем в WAV файл
        audio.export(test_file_path, format="wav")
        
        print(f"✅ Создан тестовый файл: {test_file_path}")
        print(f"📊 Размер файла: {os.path.getsize(test_file_path)} байт")
        
        # Тестируем полную транскрипцию
        print("\n🎤 Начинаю транскрипцию...")
        success, text, stats = await transcriber.transcribe_voice_message(test_file_path)
        
        if success:
            print("✅ Транскрипция успешна!")
            print(f"📝 Текст: {text}")
            print(f"📊 Статистика: {stats}")
        else:
            print(f"❌ Транскрипция неудачна: {text}")
            return False
        
        # Очищаем тестовый файл
        try:
            os.unlink(test_file_path)
            print("🗑️ Тестовый файл удален")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

async def main():
    """Основная функция тестирования"""
    
    try:
        result = await test_full_transcription()
        
        print("\n" + "=" * 60)
        if result:
            print("🎉 Полный тест транскрипции пройден успешно!")
            print("✅ Soniox API полностью функционален")
            return True
        else:
            print("❌ Тест транскрипции не пройден")
            print("💡 Проверьте логи для деталей")
            return False
            
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
        exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        exit(1)
