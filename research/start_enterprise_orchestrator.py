#!/usr/bin/env python3
"""
Enterprise Task Orchestrator Startup Script
Скрипт запуска enterprise оркестратора с проверкой зависимостей
"""

import asyncio
import sys
import os
import json
from pathlib import Path

def check_dependencies():
    """Проверка зависимостей"""
    required_packages = [
        'aiofiles',
        'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Отсутствуют зависимости: {', '.join(missing_packages)}")
        print("Установите их командой:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def check_config():
    """Проверка конфигурации"""
    config_file = "enterprise_config.json"
    
    if not Path(config_file).exists():
        print(f"❌ Файл конфигурации не найден: {config_file}")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Проверка обязательных полей
        required_fields = ['servers', 'data_dirs']
        for field in required_fields:
            if field not in config:
                print(f"❌ Отсутствует обязательное поле в конфигурации: {field}")
                return False
        
        print("✅ Конфигурация корректна")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка в JSON конфигурации: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка чтения конфигурации: {e}")
        return False

def check_directories():
    """Проверка директорий"""
    config_file = "enterprise_config.json"
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        data_dirs = config.get('data_dirs', {})
        missing_dirs = []
        
        for dir_name, dir_path in data_dirs.items():
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            print(f"⚠️ Отсутствуют директории: {', '.join(missing_dirs)}")
            print("Создаю директории...")
            
            for dir_path in missing_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                print(f"  ✅ Создана: {dir_path}")
        
        # Создание директории для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        print("✅ Все директории готовы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки директорий: {e}")
        return False

async def main():
    """Основная функция"""
    print("🚀 Enterprise Task Orchestrator")
    print("=" * 50)
    
    # Проверки
    if not check_dependencies():
        sys.exit(1)
    
    if not check_config():
        sys.exit(1)
    
    if not check_directories():
        sys.exit(1)
    
    print("\n🎯 Запуск оркестратора...")
    
    try:
        from enterprise_task_orchestrator import EnterpriseTaskOrchestrator
        
        orchestrator = EnterpriseTaskOrchestrator()
        
        # Запуск с обработкой сигналов
        await orchestrator.start()
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки")
    except Exception as e:
        print(f"❌ Ошибка запуска оркестратора: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 