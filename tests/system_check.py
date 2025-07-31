#!/usr/bin/env python3
"""
Enterprise Task Management System - Final Check
Финальная проверка всей enterprise системы
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

def check_files():
    """Проверка наличия всех файлов"""
    print("📁 Проверка файлов системы...")
    
    required_files = [
        "enterprise_task_orchestrator.py",
        "mcp_integrations.py", 
        "enterprise_config.json",
        "start_enterprise_orchestrator.py",
        "test_integrations.py",
        "demo_enterprise_system.py",
        "ENTERPRISE_SYSTEM_README.md"
    ]
    
    missing_files = []
    existing_files = []
    
    for file in required_files:
        if Path(file).exists():
            existing_files.append(file)
            print(f"  ✅ {file}")
        else:
            missing_files.append(file)
            print(f"  ❌ {file}")
    
    print(f"\n📊 Результат: {len(existing_files)}/{len(required_files)} файлов найдено")
    
    if missing_files:
        print(f"⚠️ Отсутствуют файлы: {', '.join(missing_files)}")
        return False
    
    return True

def check_dependencies():
    """Проверка зависимостей"""
    print("\n📦 Проверка зависимостей...")
    
    required_packages = ['aiofiles', 'aiohttp']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️ Установите зависимости: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_config():
    """Проверка конфигурации"""
    print("\n⚙️ Проверка конфигурации...")
    
    try:
        with open("enterprise_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Проверка обязательных секций
        required_sections = ['servers', 'data_dirs', 'sync_interval']
        for section in required_sections:
            if section in config:
                print(f"  ✅ {section}")
            else:
                print(f"  ❌ {section}")
                return False
        
        # Проверка серверов
        servers = config.get('servers', {})
        print(f"  📡 Настроено серверов: {len(servers)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка конфигурации: {e}")
        return False

async def check_integrations():
    """Проверка интеграций"""
    print("\n🔗 Проверка интеграций...")
    
    try:
        from mcp_integrations import MCPIntegrationManager
        
        manager = MCPIntegrationManager()
        status = await manager.get_integration_status()
        
        online_count = sum(1 for is_online in status.values() if is_online)
        total_count = len(status)
        
        print(f"  📊 Онлайн серверов: {online_count}/{total_count}")
        
        for server, is_online in status.items():
            status_icon = "🟢" if is_online else "🔴"
            print(f"    {status_icon} {server}")
        
        return online_count == total_count
        
    except Exception as e:
        print(f"  ❌ Ошибка интеграций: {e}")
        return False

async def check_orchestrator():
    """Проверка оркестратора"""
    print("\n🎯 Проверка оркестратора...")
    
    try:
        from enterprise_task_orchestrator import EnterpriseTaskOrchestrator
        
        orchestrator = EnterpriseTaskOrchestrator()
        
        # Проверка создания задачи
        test_task = await orchestrator.create_task(
            title="Системная проверка",
            description="Задача для проверки работы оркестратора",
            priority=3,
            tags=["system", "check"]
        )
        
        print(f"  ✅ Задача создана: {test_task.id}")
        
        # Проверка здоровья
        health = orchestrator.get_health_status()
        print(f"  🏥 Статус здоровья: {health['orchestrator_status']}")
        
        # Проверка статистики
        stats = orchestrator.get_statistics()
        print(f"  📈 Операций: {stats['total_operations']}")
        
        await orchestrator.stop()
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка оркестратора: {e}")
        return False

def check_logs():
    """Проверка логов"""
    print("\n📝 Проверка логов...")
    
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        print(f"  📁 Найдено логов: {len(log_files)}")
        
        for log_file in log_files:
            print(f"    📄 {log_file.name}")
        
        return True
    else:
        print("  ⚠️ Директория логов не найдена")
        return False

def generate_report(results):
    """Генерация отчета"""
    print("\n📊 ОТЧЕТ О ПРОВЕРКЕ СИСТЕМЫ")
    print("=" * 50)
    
    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)
    
    print(f"📈 Всего проверок: {total_checks}")
    print(f"✅ Пройдено: {passed_checks}")
    print(f"❌ Провалено: {total_checks - passed_checks}")
    print(f"📊 Процент успеха: {(passed_checks/total_checks)*100:.1f}%")
    
    print("\n📋 Детали:")
    for check_name, result in results.items():
        status_icon = "✅" if result else "❌"
        print(f"  {status_icon} {check_name}")
    
    if passed_checks == total_checks:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Система готова к работе!")
    else:
        print(f"\n⚠️ Проблемы найдены в {total_checks - passed_checks} проверках")
    
    # Сохранение отчета
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "results": results
    }
    
    with open("system_check_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Отчет сохранен: system_check_report.json")

async def main():
    """Основная функция проверки"""
    print("🔍 Enterprise Task Management System - Final Check")
    print("=" * 60)
    
    results = {}
    
    # Проверки
    results["Файлы системы"] = check_files()
    results["Зависимости"] = check_dependencies()
    results["Конфигурация"] = check_config()
    results["Интеграции"] = await check_integrations()
    results["Оркестратор"] = await check_orchestrator()
    results["Логи"] = check_logs()
    
    # Генерация отчета
    generate_report(results)
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("1. Запустите демонстрацию: python demo_enterprise_system.py")
    print("2. Изучите документацию: ENTERPRISE_SYSTEM_README.md")
    print("3. Настройте уведомления в enterprise_config.json")
    print("4. Мониторьте логи в директории logs/")

if __name__ == "__main__":
    asyncio.run(main()) 