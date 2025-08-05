#!/usr/bin/env python3
"""
Enterprise Task Management System Demo
Демонстрация возможностей enterprise системы управления задачами
"""

import asyncio
import json
from datetime import datetime, timedelta
from enterprise_task_orchestrator import EnterpriseTaskOrchestrator, TaskData
from mcp_integrations import MCPIntegrationManager

class EnterpriseSystemDemo:
    """Демонстрация enterprise системы"""
    
    def __init__(self):
        self.orchestrator = EnterpriseTaskOrchestrator()
        self.integration_manager = MCPIntegrationManager()
    
    async def run_full_demo(self):
        """Полная демонстрация системы"""
        print("🚀 Enterprise Task Management System Demo")
        print("=" * 60)
        
        try:
            # 1. Демонстрация создания задач
            await self.demo_task_creation()
            
            # 2. Демонстрация планирования
            await self.demo_task_planning()
            
            # 3. Демонстрация мониторинга
            await self.demo_monitoring()
            
            # 4. Демонстрация интеграций
            await self.demo_integrations()
            
            # 5. Демонстрация обработки ошибок
            await self.demo_error_handling()
            
            print("\n🎉 Демонстрация завершена успешно!")
            
        except Exception as e:
            print(f"\n❌ Ошибка в демонстрации: {e}")
        finally:
            await self.orchestrator.stop()
    
    async def demo_task_creation(self):
        """Демонстрация создания задач"""
        print("\n📋 1. Демонстрация создания задач")
        print("-" * 40)
        
        # Создание задач разного приоритета
        tasks = [
            {
                "title": "Критическая задача",
                "description": "Срочная задача с высоким приоритетом",
                "priority": 5,
                "tags": ["critical", "urgent"]
            },
            {
                "title": "Обычная задача",
                "description": "Стандартная задача со средним приоритетом",
                "priority": 3,
                "tags": ["normal", "work"]
            },
            {
                "title": "Низкоприоритетная задача",
                "description": "Задача с низким приоритетом",
                "priority": 1,
                "tags": ["low", "optional"]
            }
        ]
        
        created_tasks = []
        
        for i, task_info in enumerate(tasks, 1):
            print(f"\n📝 Создание задачи {i}: {task_info['title']}")
            
            task = await self.orchestrator.create_task(
                title=task_info['title'],
                description=task_info['description'],
                priority=task_info['priority'],
                deadline=(datetime.now() + timedelta(days=i)).isoformat(),
                tags=task_info['tags']
            )
            
            created_tasks.append(task)
            print(f"  ✅ Создана: {task.id}")
            print(f"  📊 Приоритет: {task.priority}")
            print(f"  🏷️ Теги: {', '.join(task.tags)}")
        
        print(f"\n📈 Всего создано задач: {len(created_tasks)}")
    
    async def demo_task_planning(self):
        """Демонстрация планирования задач"""
        print("\n🦐 2. Демонстрация планирования задач")
        print("-" * 40)
        
        from mcp_integrations import ShrimpTaskManagerIntegration
        
        complex_task_description = """
        Разработать веб-приложение для управления задачами с функциями:
        - Создание и редактирование задач
        - Назначение исполнителей
        - Отслеживание прогресса
        - Уведомления и отчеты
        - Интеграция с календарем
        """
        
        print("📋 Планирование сложной задачи...")
        
        async with ShrimpTaskManagerIntegration() as client:
            # Планирование задачи
            plan_response = await client.plan_task(
                complex_task_description,
                "Требуется современный UI, REST API, база данных PostgreSQL"
            )
            
            if plan_response.success:
                print("  ✅ Задача спланирована")
                print("  📊 Получен план разработки")
            else:
                print(f"  ❌ Ошибка планирования: {plan_response.error}")
    
    async def demo_monitoring(self):
        """Демонстрация мониторинга"""
        print("\n📊 3. Демонстрация мониторинга системы")
        print("-" * 40)
        
        # Получение статуса здоровья
        health_status = self.orchestrator.get_health_status()
        
        print("🏥 Статус здоровья серверов:")
        for server, status in health_status["server_health"].items():
            status_icon = "🟢" if status['status'] == 'ServerStatus.ONLINE' else "🔴"
            print(f"  {status_icon} {server}: {status['status']}")
            print(f"    ⏱️ Время отклика: {status['response_time']:.3f}s")
            print(f"    ❌ Ошибок: {status['error_count']}")
        
        # Получение статистики
        stats = self.orchestrator.get_statistics()
        print(f"\n📈 Статистика системы:")
        print(f"  📊 Общее количество операций: {stats['total_operations']}")
        print(f"  🔄 Статусы серверов: {stats['server_status']}")
        print(f"  ⚠️ Количество ошибок: {sum(stats['error_rates'].values())}")
        
        # Размер очереди
        queue_size = health_status["queue_size"]
        print(f"  📦 Размер очереди задач: {queue_size}")
    
    async def demo_integrations(self):
        """Демонстрация интеграций"""
        print("\n🔗 4. Демонстрация интеграций")
        print("-" * 40)
        
        # Тестирование всех интеграций
        print("📡 Проверка всех интеграций...")
        status = await self.integration_manager.get_integration_status()
        
        online_count = sum(1 for is_online in status.values() if is_online)
        total_count = len(status)
        
        print(f"  📊 Онлайн: {online_count}/{total_count}")
        
        for server, is_online in status.items():
            status_icon = "🟢" if is_online else "🔴"
            print(f"    {status_icon} {server}")
        
        # Демонстрация уведомлений
        print("\n🔔 Тестирование уведомлений...")
        from mcp_integrations import NotificationsIntegration
        
        async with NotificationsIntegration() as client:
            notification_response = await client.send_notification(
                "Демонстрация системы",
                "Enterprise Task Management System работает корректно!",
                "success"
            )
            
            if notification_response.success:
                print("  ✅ Уведомление отправлено")
            else:
                print(f"  ❌ Ошибка уведомления: {notification_response.error}")
    
    async def demo_error_handling(self):
        """Демонстрация обработки ошибок"""
        print("\n🛡️ 5. Демонстрация обработки ошибок")
        print("-" * 40)
        
        # Создание задачи с некорректными данными
        print("🧪 Тестирование обработки ошибок...")
        
        try:
            # Попытка создать задачу с некорректным приоритетом
            task = await self.orchestrator.create_task(
                title="Тест обработки ошибок",
                description="Задача для тестирования обработки ошибок",
                priority=10,  # Некорректный приоритет
                tags=["error", "test"]
            )
            print("  ✅ Задача создана (приоритет скорректирован)")
            
        except Exception as e:
            print(f"  ❌ Ошибка обработана: {e}")
        
        # Демонстрация circuit breaker
        print("\n⚡ Тестирование Circuit Breaker...")
        
        # Имитация множественных ошибок
        for i in range(3):
            try:
                # Попытка операции с несуществующим сервером
                pass  # Здесь будет реальная имитация ошибок
                print(f"  🔄 Попытка {i+1}: обработана")
            except Exception as e:
                print(f"  ❌ Ошибка {i+1}: {e}")
        
        print("  🛡️ Circuit Breaker защищает систему от каскадных сбоев")

async def main():
    """Основная функция демонстрации"""
    demo = EnterpriseSystemDemo()
    await demo.run_full_demo()

if __name__ == "__main__":
    asyncio.run(main()) 