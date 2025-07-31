#!/usr/bin/env python3
"""
Скрипт для запуска тестов Telegram YouTube Subtitles Bot
Поддерживает различные режимы тестирования
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description=""):
    """Запускает команду и выводит результат"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"Команда: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ УСПЕШНО")
        if result.stdout:
            print(f"Вывод:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ ОШИБКА")
        print(f"Код возврата: {e.returncode}")
        if e.stdout:
            print(f"Вывод:\n{e.stdout}")
        if e.stderr:
            print(f"Ошибки:\n{e.stderr}")
        return False


def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        'pytest',
        'pytest-asyncio',
        'responses',
        'python-telegram-bot',
        'youtube-transcript-api'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Отсутствуют пакеты: {', '.join(missing_packages)}")
        print("Установите их командой:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Все зависимости установлены")
    return True


def run_unit_tests():
    """Запускает юнит-тесты"""
    cmd = [
        sys.executable, '-m', 'pytest',
        'test_summarizer.py::TestTextSummarizer',
        'test_bot.py::TestBotUtilityFunctions',
        'test_bot.py::TestBotKeyboards',
        '-v', '--tb=short'
    ]
    return run_command(cmd, "Юнит-тесты (быстрые, без внешних API)")


def run_integration_tests():
    """Запускает интеграционные тесты"""
    cmd = [
        sys.executable, '-m', 'pytest',
        'test_bot.py::TestBotHandlers',
        'test_integration.py::TestFullWorkflow',
        'test_integration.py::TestEdgeCases',
        '-v', '--tb=short'
    ]
    return run_command(cmd, "Интеграционные тесты (с мокированными API)")


def run_slow_tests():
    """Запускает медленные тесты с реальными API"""
    print("\n⚠️  ВНИМАНИЕ: Медленные тесты требуют:")
    print("   • OPENROUTER_API_KEY в переменных окружения")
    print("   • Интернет-соединение")
    print("   • Могут занять несколько минут")
    
    response = input("\nПродолжить? (y/N): ").strip().lower()
    if response != 'y':
        print("Пропускаем медленные тесты")
        return True
    
    cmd = [
        sys.executable, '-m', 'pytest',
        '--run-slow',
        '-v', '--tb=short'
    ]
    return run_command(cmd, "Медленные тесты (с реальными API)")


def run_all_tests():
    """Запускает все тесты кроме медленных"""
    cmd = [
        sys.executable, '-m', 'pytest',
        '-v', '--tb=short',
        '--durations=10'
    ]
    return run_command(cmd, "Все тесты (кроме медленных)")


def run_coverage_tests():
    """Запускает тесты с анализом покрытия"""
    try:
        import coverage
    except ImportError:
        print("❌ Пакет 'coverage' не установлен")
        print("Установите: pip install coverage pytest-cov")
        return False
    
    cmd = [
        sys.executable, '-m', 'pytest',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing',
        '--cov-exclude=test_*',
        '-v'
    ]
    return run_command(cmd, "Тесты с анализом покрытия кода")


def run_specific_test():
    """Запускает конкретный тест"""
    print("\nДоступные тестовые файлы:")
    test_files = list(Path('.').glob('test_*.py'))
    
    for i, file in enumerate(test_files, 1):
        print(f"  {i}. {file.name}")
    
    try:
        choice = int(input(f"\nВыберите файл (1-{len(test_files)}): ")) - 1
        if 0 <= choice < len(test_files):
            test_file = test_files[choice]
            cmd = [sys.executable, '-m', 'pytest', str(test_file), '-v']
            return run_command(cmd, f"Тесты из {test_file.name}")
        else:
            print("❌ Неверный выбор")
            return False
    except (ValueError, KeyboardInterrupt):
        print("Отменено")
        return False


def show_test_structure():
    """Показывает структуру тестов"""
    print("\n📋 СТРУКТУРА ТЕСТОВ:")
    print("\n1. test_summarizer.py:")
    print("   • TestTextSummarizer - тесты класса суммаризации")
    print("   • TestTextSummarizerIntegration - интеграционные тесты ИИ")
    
    print("\n2. test_bot.py:")
    print("   • TestBotUtilityFunctions - вспомогательные функции")
    print("   • TestBotKeyboards - создание клавиатур")
    print("   • TestBotHandlers - обработчики команд")
    print("   • TestBotProcessRequest - основная логика бота")
    
    print("\n3. test_integration.py:")
    print("   • TestFullWorkflow - полные пользовательские сценарии")
    print("   • TestEdgeCases - граничные случаи")
    print("   • TestRealAPIIntegration - тесты с реальными API")
    
    print("\n4. conftest.py:")
    print("   • Общие фикстуры и настройки")
    
    print("\n📊 МАРКЕРЫ ТЕСТОВ:")
    print("   • @pytest.mark.slow - медленные тесты (реальные API)")
    print("   • @pytest.mark.integration - интеграционные тесты")
    print("   • @pytest.mark.asyncio - асинхронные тесты")


def main():
    """Главная функция"""
    print("🤖 ТЕСТИРОВАНИЕ TELEGRAM YOUTUBE SUBTITLES BOT")
    print("=" * 60)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    while True:
        print("\n📋 ВЫБЕРИТЕ РЕЖИМ ТЕСТИРОВАНИЯ:")
        print("1. 🚀 Быстрые юнит-тесты")
        print("2. 🔗 Интеграционные тесты") 
        print("3. 🌐 Медленные тесты (реальные API)")
        print("4. 📊 Все тесты (кроме медленных)")
        print("5. 📈 Тесты с покрытием кода")
        print("6. 🎯 Конкретный тестовый файл")
        print("7. 📋 Показать структуру тестов")
        print("8. ❌ Выход")
        
        try:
            choice = input("\nВаш выбор (1-8): ").strip()
            
            if choice == '1':
                run_unit_tests()
            elif choice == '2':
                run_integration_tests()
            elif choice == '3':
                run_slow_tests()
            elif choice == '4':
                run_all_tests()
            elif choice == '5':
                run_coverage_tests()
            elif choice == '6':
                run_specific_test()
            elif choice == '7':
                show_test_structure()
            elif choice == '8':
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
                
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break


if __name__ == '__main__':
    main() 