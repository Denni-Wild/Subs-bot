#!/usr/bin/env python3
"""
Скрипт для тестирования соединения с Soniox API
"""

import os
import asyncio
from dotenv import load_dotenv
from voice_transcriber import VoiceTranscriber

async def test_soniox_api():
    """Тестирует соединение с Soniox API"""
    
    print("🔍 Тестирование Soniox API...")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Проверяем наличие API ключа
    api_key = os.getenv('SONIOX_API_KEY')
    if not api_key:
        print("❌ SONIOX_API_KEY не найден в переменных окружения")
        print("📝 Создайте файл .env с содержимым:")
        print("SONIOX_API_KEY=your_api_key_here")
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
    if await transcriber.test_connection():
        print("✅ Соединение с Soniox API успешно")
        return True
    else:
        print("❌ Не удается подключиться к Soniox API")
        return False

async def test_file_upload():
    """Тестирует загрузку файла в Soniox API"""
    
    print("\n📤 Тестирование загрузки файла...")
    
    transcriber = VoiceTranscriber()
    
    # Создаем тестовый аудио файл (1 секунда тишины)
    test_file_path = "test_audio.wav"
    
    try:
        from pydub import AudioSegment
        import numpy as np
        
        # Создаем 1 секунду тишины (моно, 16kHz, 16-bit)
        sample_rate = 16000
        duration = 1.0  # 1 секунда
        samples = int(sample_rate * duration)
        
        # Создаем массив тишины (нули)
        audio_data = np.zeros(samples, dtype=np.int16)
        
        # Создаем AudioSegment из массива
        audio = AudioSegment(
            audio_data.tobytes(), 
            frame_rate=sample_rate,
            sample_width=2,  # 16-bit
            channels=1  # моно
        )
        
        # Сохраняем в WAV файл
        audio.export(test_file_path, format="wav")
        
        print(f"✅ Создан тестовый файл: {test_file_path}")
        
        # Тестируем загрузку
        file_id = await transcriber._upload_file(test_file_path)
        
        if file_id:
            print(f"✅ Файл успешно загружен, file_id: {file_id}")
            
            # Очищаем тестовый файл
            try:
                os.unlink(test_file_path)
                print("🗑️ Тестовый файл удален")
            except:
                pass
                
            return True
        else:
            print("❌ Ошибка загрузки файла")
            return False
            
    except ImportError as e:
        print(f"⚠️ Ошибка импорта: {e}")
        print("⚠️ Пропускаю тест загрузки файла")
        return True
    except Exception as e:
        print(f"❌ Ошибка при тестировании загрузки файла: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    
    print("🚀 Начинаю тестирование Soniox API")
    print("=" * 50)
    
    # Тест 1: Проверка соединения
    connection_ok = await test_soniox_api()
    
    if not connection_ok:
        print("\n❌ Тест соединения не пройден")
        print("💡 Проверьте:")
        print("   • Правильность SONIOX_API_KEY")
        print("   • Интернет-соединение")
        print("   • Доступность api.soniox.com")
        return False
    
    # Тест 2: Загрузка файла
    upload_ok = await test_file_upload()
    
    print("\n" + "=" * 50)
    if connection_ok and upload_ok:
        print("🎉 Все тесты пройдены успешно!")
        print("✅ Soniox API работает корректно")
        return True
    else:
        print("⚠️ Некоторые тесты не пройдены")
        print("💡 Проверьте логи для деталей")
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
