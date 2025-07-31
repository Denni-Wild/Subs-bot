#!/usr/bin/env python3
"""
Test MCP Integrations
Тестирование интеграций с MCP серверами
"""

import asyncio
import json
from datetime import datetime, timedelta
from enterprise_task_orchestrator import EnterpriseTaskOrchestrator, TaskData
from mcp_integrations import MCPIntegrationManager

async def test_basic_integrations():
    """Тестирование базовых интеграций"""
    print("🧪 Тестирование интеграций с MCP серверами")
    print("=" * 60)
    
    # Создание тестовой задачи
    test_task = TaskData(
        id="test_task_001",
        title="Тестовая задача интеграции",
        description="Проверка работы интеграций с MCP серверами",
        priority=4,
        deadline=(datetime.now() + timedelta(days=1)).isoformat(),
        tags=["test", "integration", "mcp"]
    )
    
    print(f"📋 Создана тестовая задача: {test_task.title}")
    
    # Тестирование через оркестратор
    print("\n🎯 Тестирование через Enterprise оркестратор...")
    
    orchestrator = EnterpriseTaskOrchestrator()
    
    try:
        # Создание задачи через оркестратор
        created_task = await orchestrator.create_task(
            title=test_task.title,
            description=test_task.description,
            priority=test_task.priority,
            deadline=test_task.deadline,
            tags=test_task.tags
        )
        
        print(f"✅ Задача создана через оркестратор: {created_task.id}")
        
        # Получение статуса здоровья
        health_status = orchestrator.get_health_status()
        print(f"🏥 Статус здоровья системы:")
        for server, status in health_status["server_health"].items():
            print(f"  {server}: {status['status']} (время отклика: {status['response_time']:.3f}s)")
        
        # Получение статистики
        stats = orchestrator.get_statistics()
        print(f"📊 Статистика системы:")
        print(f"  Общее количество операций: {stats['total_operations']}")
        print(f"  Статусы серверов: {stats['server_status']}")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании оркестратора: {e}")
    
    finally:
        await orchestrator.stop()

async def test_direct_integrations():
    """Тестирование прямых интеграций"""
    print("\n🔗 Тестирование прямых интеграций...")
    
    integration_manager = MCPIntegrationManager()
    
    # Тестирование статуса интеграций
    print("📡 Проверка статуса интеграций...")
    status = await integration_manager.get_integration_status()
    
    for server, is_online in status.items():
        status_icon = "✅" if is_online else "❌"
        print(f"  {status_icon} {server}: {'онлайн' if is_online else 'офлайн'}")
    
    # Тестирование создания задачи
    print("\n📝 Тестирование создания задачи...")
    test_task = TaskData(
        id="direct_test_001",
        title="Прямая интеграция тест",
        description="Тестирование прямых интеграций с MCP серверами",
        priority=3,
        tags=["direct", "test"]
    )
    
    try:
        results = await integration_manager.create_task_integrated(test_task)
        
        print("📊 Результаты создания задачи:")
        for server, response in results.items():
            status_icon = "✅" if response.success else "❌"
            print(f"  {status_icon} {server}: {response.success}")
            if not response.success:
                print(f"    Ошибка: {response.error}")
            print(f"    Время отклика: {response.response_time:.3f}s")
    
    except Exception as e:
        print(f"❌ Ошибка при тестировании прямых интеграций: {e}")

async def test_individual_servers():
    """Тестирование отдельных серверов"""
    print("\n🔧 Тестирование отдельных серверов...")
    
    from mcp_integrations import (
        DeltaTaskIntegration, ShrimpTaskManagerIntegration, 
        HPKVMemoryIntegration, NotificationsIntegration
    )
    
    # Тест deltatask
    print("📋 Тестирование deltatask...")
    try:
        async with DeltaTaskIntegration() as client:
            test_task = TaskData(
                id="deltatask_test",
                title="Deltatask тест",
                description="Тестирование интеграции с deltatask",
                priority=2
            )
            response = await client.create_task(test_task)
            print(f"  {'✅' if response.success else '❌'} Deltatask: {response.success}")
    except Exception as e:
        print(f"  ❌ Deltatask ошибка: {e}")
    
    # Тест shrimp-task-manager
    print("🦐 Тестирование shrimp-task-manager...")
    try:
        async with ShrimpTaskManagerIntegration() as client:
            response = await client.plan_task(
                "Тестирование планирования задач",
                "Проверка работы shrimp-task-manager"
            )
            print(f"  {'✅' if response.success else '❌'} Shrimp-task-manager: {response.success}")
    except Exception as e:
        print(f"  ❌ Shrimp-task-manager ошибка: {e}")
    
    # Тест hpkv-memory
    print("🧠 Тестирование hpkv-memory...")
    try:
        async with HPKVMemoryIntegration() as client:
            response = await client.store_memory(
                "test_project",
                "test_session",
                1,
                "Тестовое сообщение",
                "Тестовый ответ",
                {"test": True}
            )
            print(f"  {'✅' if response.success else '❌'} HPKV-memory: {response.success}")
    except Exception as e:
        print(f"  ❌ HPKV-memory ошибка: {e}")
    
    # Тест notifications
    print("🔔 Тестирование notifications...")
    try:
        async with NotificationsIntegration() as client:
            response = await client.send_notification(
                "Тестовое уведомление",
                "Это тестовое уведомление от MCP системы",
                "info"
            )
            print(f"  {'✅' if response.success else '❌'} Notifications: {response.success}")
    except Exception as e:
        print(f"  ❌ Notifications ошибка: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования MCP интеграций")
    print("=" * 60)
    
    try:
        # Тестирование базовых интеграций
        await test_basic_integrations()
        
        # Тестирование прямых интеграций
        await test_direct_integrations()
        
        # Тестирование отдельных серверов
        await test_individual_servers()
        
        print("\n🎉 Тестирование завершено!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 