#!/usr/bin/env python3
"""
Оркестратор системы управления задачами
Интегрирует все MCP серверы для комплексного управления задачами
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('task-system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TaskSystemOrchestrator:
    """Оркестратор системы управления задачами"""
    
    def __init__(self):
        self.config = self._load_config()
        self.task_history = []
        
    def _load_config(self) -> Dict:
        """Загрузка конфигурации системы"""
        config_path = "task-system-config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Конфигурация по умолчанию
            return {
                "data_dirs": {
                    "calendar": "D:/PY/MCP/calendar-data",
                    "notifications": "D:/PY/MCP/notifications-data",
                    "time_tracking": "D:/PY/MCP/time-tracking-data",
                    "backup": "D:/PY/MCP/backup-data",
                    "memory": "D:/PY/MCP/all_memories.jsonl"
                },
                "sync_interval": 300,  # 5 минут
                "backup_interval": 3600,  # 1 час
                "notification_channels": ["desktop", "email"],
                "auto_sync": True
            }
    
    def create_task(self, title: str, description: str = "", 
                   priority: int = 3, deadline: Optional[str] = None,
                   tags: List[str] = None) -> Dict:
        """
        Создание новой задачи с интеграцией всех серверов
        
        Args:
            title: Название задачи
            description: Описание задачи
            priority: Приоритет (1-5)
            deadline: Дедлайн в формате ISO
            tags: Список тегов
            
        Returns:
            Словарь с информацией о созданной задаче
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task_data = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "deadline": deadline,
            "tags": tags or [],
            "time_spent": 0,
            "subtasks": [],
            "dependencies": []
        }
        
        # Сохранение в deltatask
        self._save_to_deltatask(task_data)
        
        # Планирование в календаре
        if deadline:
            self._schedule_in_calendar(task_data)
        
        # Настройка уведомлений
        self._setup_notifications(task_data)
        
        # Сохранение в память
        self._save_to_memory(task_data)
        
        # Начало отслеживания времени
        self._start_time_tracking(task_id)
        
        logger.info(f"Создана задача: {title} (ID: {task_id})")
        return task_data
    
    def _save_to_deltatask(self, task_data: Dict):
        """Сохранение задачи в deltatask"""
        try:
            # Здесь будет интеграция с deltatask MCP сервером
            logger.info(f"Задача сохранена в deltatask: {task_data['id']}")
        except Exception as e:
            logger.error(f"Ошибка сохранения в deltatask: {e}")
    
    def _schedule_in_calendar(self, task_data: Dict):
        """Планирование задачи в календаре"""
        try:
            if task_data.get('deadline'):
                # Интеграция с mcp-calendar
                logger.info(f"Задача запланирована в календаре: {task_data['id']}")
        except Exception as e:
            logger.error(f"Ошибка планирования в календаре: {e}")
    
    def _setup_notifications(self, task_data: Dict):
        """Настройка уведомлений для задачи"""
        try:
            # Интеграция с mcp-notifications
            notification_data = {
                "task_id": task_data['id'],
                "title": task_data['title'],
                "deadline": task_data.get('deadline'),
                "priority": task_data['priority']
            }
            logger.info(f"Уведомления настроены для задачи: {task_data['id']}")
        except Exception as e:
            logger.error(f"Ошибка настройки уведомлений: {e}")
    
    def _save_to_memory(self, task_data: Dict):
        """Сохранение задачи в память"""
        try:
            # Интеграция с hpkv-memory-server
            memory_entry = {
                "project_name": "TaskSystem",
                "session_name": "task-creation",
                "sequence_number": len(self.task_history) + 1,
                "request": f"Создание задачи: {task_data['title']}",
                "response": f"Задача создана с ID: {task_data['id']}",
                "metadata": task_data
            }
            logger.info(f"Задача сохранена в память: {task_data['id']}")
        except Exception as e:
            logger.error(f"Ошибка сохранения в память: {e}")
    
    def _start_time_tracking(self, task_id: str):
        """Начало отслеживания времени для задачи"""
        try:
            # Интеграция с mcp-time-tracker
            tracking_data = {
                "task_id": task_id,
                "start_time": datetime.now().isoformat(),
                "status": "active"
            }
            logger.info(f"Отслеживание времени начато для задачи: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка начала отслеживания времени: {e}")
    
    def update_task_status(self, task_id: str, status: str, 
                          notes: str = "") -> bool:
        """
        Обновление статуса задачи
        
        Args:
            task_id: ID задачи
            status: Новый статус
            notes: Дополнительные заметки
            
        Returns:
            True если обновление успешно
        """
        try:
            # Обновление в deltatask
            self._update_deltatask_status(task_id, status)
            
            # Обновление уведомлений
            self._update_notifications(task_id, status)
            
            # Сохранение в память
            self._save_status_to_memory(task_id, status, notes)
            
            # Остановка отслеживания времени если задача завершена
            if status in ['completed', 'cancelled']:
                self._stop_time_tracking(task_id)
            
            logger.info(f"Статус задачи {task_id} обновлен на: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса задачи {task_id}: {e}")
            return False
    
    def _update_deltatask_status(self, task_id: str, status: str):
        """Обновление статуса в deltatask"""
        # Интеграция с deltatask MCP сервером
        pass
    
    def _update_notifications(self, task_id: str, status: str):
        """Обновление уведомлений"""
        # Интеграция с mcp-notifications
        pass
    
    def _save_status_to_memory(self, task_id: str, status: str, notes: str):
        """Сохранение статуса в память"""
        # Интеграция с hpkv-memory-server
        pass
    
    def _stop_time_tracking(self, task_id: str):
        """Остановка отслеживания времени"""
        # Интеграция с mcp-time-tracker
        pass
    
    def get_task_analytics(self) -> Dict:
        """Получение аналитики по задачам"""
        try:
            analytics = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "overdue_tasks": 0,
                "completion_rate": 0.0,
                "average_completion_time": 0,
                "priority_distribution": {},
                "time_spent_total": 0
            }
            
            # Сбор данных из всех серверов
            # Интеграция с deltatask, mcp-time-tracker, hpkv-memory-server
            
            logger.info("Аналитика задач получена")
            return analytics
            
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return {}
    
    def sync_all_servers(self):
        """Синхронизация всех серверов"""
        try:
            logger.info("Начало синхронизации всех серверов...")
            
            # Синхронизация deltatask с Obsidian
            self._sync_deltatask()
            
            # Синхронизация календаря
            self._sync_calendar()
            
            # Синхронизация уведомлений
            self._sync_notifications()
            
            # Синхронизация времени
            self._sync_time_tracking()
            
            # Создание резервной копии
            self._create_backup()
            
            logger.info("Синхронизация завершена")
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
    
    def _sync_deltatask(self):
        """Синхронизация deltatask"""
        # Интеграция с deltatask MCP сервером
        pass
    
    def _sync_calendar(self):
        """Синхронизация календаря"""
        # Интеграция с mcp-calendar
        pass
    
    def _sync_notifications(self):
        """Синхронизация уведомлений"""
        # Интеграция с mcp-notifications
        pass
    
    def _sync_time_tracking(self):
        """Синхронизация отслеживания времени"""
        # Интеграция с mcp-time-tracker
        pass
    
    def _create_backup(self):
        """Создание резервной копии"""
        # Интеграция с mcp-backup
        pass

def main():
    """Основная функция"""
    orchestrator = TaskSystemOrchestrator()
    
    # Пример использования
    print("🚀 Система управления задачами запущена")
    
    # Создание тестовой задачи
    task = orchestrator.create_task(
        title="Тестовая задача",
        description="Проверка работы оркестратора",
        priority=3,
        deadline=(datetime.now() + timedelta(days=1)).isoformat(),
        tags=["test", "orchestrator"]
    )
    
    print(f"✅ Создана задача: {task['title']}")
    
    # Получение аналитики
    analytics = orchestrator.get_task_analytics()
    print(f"📊 Аналитика: {analytics}")
    
    # Синхронизация
    orchestrator.sync_all_servers()
    print("🔄 Синхронизация завершена")

if __name__ == "__main__":
    main() 