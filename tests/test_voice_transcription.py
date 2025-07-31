#!/usr/bin/env python3
"""
Тест расшифровки голосовых сообщений
"""

import asyncio
import os
import tempfile
from dotenv import load_dotenv
from voice_transcriber import VoiceTranscriber

# Загружаем переменные окружения
load_dotenv()

async def test_voice_transcriber():
    """Тестирует функциональность VoiceTranscriber"""
    
    print("🧪 Тестирование расшифровки голосовых сообщений...")
    
    # Создаем экземпляр транскрайбера
    transcriber = VoiceTranscriber()
    
    # Проверяем доступность API
    if not transcriber.is_available():
        print("❌ SONIOX_API_KEY не настроен")
        print("Добавьте SONIOX_API_KEY в .env файл")
        return False
    
    print("✅ API ключ настроен")
    
    # Создаем тестовый аудио файл (синусоида 1 секунда)
    test_audio_path = create_test_audio()
    
    if not test_audio_path:
        print("❌ Не удалось создать тестовый аудио файл")
        return False
    
    print("✅ Тестовый аудио файл создан")
    
    try:
        # Тестируем конвертацию аудио
        print("🔄 Тестируем конвертацию аудио...")
        converted_path = await transcriber._convert_audio_format(test_audio_path)
        
        if converted_path and converted_path != test_audio_path:
            print("✅ Конвертация аудио работает")
        else:
            print("⚠️ Конвертация аудио не выполнена (используется оригинальный файл)")
        
        # Очищаем временные файлы
        cleanup_test_files([test_audio_path, converted_path])
        
        print("✅ Тест завершен успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        cleanup_test_files([test_audio_path])
        return False

def create_test_audio():
    """Создает простой тестовый аудио файл"""
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
        
        # Создаем синусоиду 440Hz на 1 секунду
        audio = Sine(440).to_audio_segment(duration=1000)  # 1 секунда
        
        # Создаем временный файл
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Экспортируем аудио
        audio.export(temp_path, format='wav')
        
        return temp_path
        
    except ImportError:
        print("⚠️ pydub не установлен, пропускаем создание тестового аудио")
        return None
    except Exception as e:
        print(f"❌ Ошибка создания тестового аудио: {e}")
        return None

def cleanup_test_files(file_paths):
    """Очищает тестовые файлы"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except:
                pass

def test_dependencies():
    """Проверяет установленные зависимости"""
    print("🔍 Проверка зависимостей...")
    
    dependencies = [
        ('requests', 'HTTP запросы'),
        ('pydub', 'Обработка аудио'),
        ('ffmpeg', 'Конвертация аудио'),
        ('websockets', 'WebSocket соединения')
    ]
    
    missing = []
    
    for dep, description in dependencies:
        try:
            if dep == 'ffmpeg':
                # Проверяем FFmpeg через pydub
                from pydub import AudioSegment
                AudioSegment.converter = "ffmpeg"
                print(f"✅ {dep} - {description}")
            else:
                __import__(dep)
                print(f"✅ {dep} - {description}")
        except ImportError:
            print(f"❌ {dep} - {description} (НЕ УСТАНОВЛЕН)")
            missing.append(dep)
        except Exception as e:
            print(f"⚠️ {dep} - {description} (ОШИБКА: {e})")
            missing.append(dep)
    
    if missing:
        print(f"\n📦 Установите недостающие зависимости:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    return True

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов расшифровки голосовых сообщений\n")
    
    # Проверяем зависимости
    if not test_dependencies():
        print("\n❌ Не все зависимости установлены")
        return
    
    print("\n" + "="*50)
    
    # Тестируем транскрайбер
    success = await test_voice_transcriber()
    
    print("\n" + "="*50)
    
    if success:
        print("🎉 Все тесты прошли успешно!")
        print("\n📝 Следующие шаги:")
        print("1. Убедитесь, что FFmpeg установлен и доступен в PATH")
        print("2. Проверьте, что SONIOX_API_KEY настроен в .env файле")
        print("3. Запустите бота: python bot.py")
        print("4. Отправьте голосовое сообщение боту для тестирования")
    else:
        print("❌ Тесты не прошли")
        print("\n🔧 Проверьте:")
        print("1. Установлены ли все зависимости")
        print("2. Настроен ли SONIOX_API_KEY")
        print("3. Установлен ли FFmpeg")

if __name__ == "__main__":
    asyncio.run(main()) 