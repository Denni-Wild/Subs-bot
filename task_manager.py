"""
Task Manager для Subs-bot

Локальная система управления задачами проекта с возможностью:
- Создания и обновления задач
- Отслеживания прогресса
- Экспорта в различные форматы
- Интеграции с Git
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Task:
    """Модель задачи"""
    id: str
    name: str
    status: str  # TODO, IN_PROGRESS, REVIEW, DONE
    priority: str  # Критический, Высокий, Средний, Низкий
    category: str
    description: str
    dependencies: str
    progress: int  # 0-100
    created_at: str
    updated_at: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None

class TaskManager:
    """Менеджер задач проекта"""
    
    def __init__(self, tasks_file: str = "project_tasks.json"):
        self.tasks_file = tasks_file
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()
    
    def load_tasks(self):
        """Загрузка задач из файла"""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.values():
                        task = Task(**task_data)
                        self.tasks[task.id] = task
                logger.info(f"Загружено {len(self.tasks)} задач")
            else:
                self.create_default_tasks()
        except Exception as e:
            logger.error(f"Ошибка загрузки задач: {e}")
            self.create_default_tasks()
    
    def save_tasks(self):
        """Сохранение задач в файл"""
        try:
            tasks_dict = {task_id: asdict(task) for task_id, task in self.tasks.items()}
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_dict, f, indent=2, ensure_ascii=False)
            logger.info("Задачи сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения задач: {e}")
    
    def create_default_tasks(self):
        """Создание задач по умолчанию для mind map функциональности"""
        default_tasks = [
            {
                "id": "TASK-007",
                "name": "Анализ и генерация смысловой структуры текста",
                "status": "TODO",
                "priority": "Высокий",
                "category": "Mind Map",
                "description": "Реализовать RAG/chunk-based обработку текста для выделения основных идей, подтем и зависимостей. Построить иерархию 2-3 уровня с использованием OpenRouter LLMs.",
                "dependencies": "Нет",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "TASK-008",
                "name": "Генерация Markdown для Markmap",
                "status": "TODO",
                "priority": "Высокий",
                "category": "Mind Map",
                "description": "Создать модуль для генерации Markdown файлов на основе иерархии идей. Поддержка Markmap и Mermaid форматов.",
                "dependencies": "TASK-007",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "TASK-009",
                "name": "Рендеринг визуализации (PNG/PDF)",
                "status": "TODO",
                "priority": "Средний",
                "category": "Mind Map",
                "description": "Реализовать генерацию статичных изображений из Mermaid диаграмм. Установка mermaid-cli и настройка команд для экспорта.",
                "dependencies": "TASK-008",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "TASK-010",
                "name": "Создание интерактивных карт Markmap",
                "status": "TODO",
                "priority": "Средний",
                "category": "Mind Map",
                "description": "Реализовать генерацию HTML файлов с интерактивными картами Markmap. Настройка CDN и базового функционала.",
                "dependencies": "TASK-008",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "TASK-011",
                "name": "Интеграция с Telegram-ботом",
                "status": "TODO",
                "priority": "Высокий",
                "category": "Telegram Bot",
                "description": "Добавить функциональность mind map в существующий бот. Кнопки для генерации карт, отправка файлов и ссылок.",
                "dependencies": "TASK-009, TASK-010",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "TASK-012",
                "name": "Хостинг для интерактивных карт",
                "status": "TODO",
                "priority": "Низкий",
                "category": "Infrastructure",
                "description": "Настроить хостинг для интерактивных HTML карт. GitHub Pages, Netlify или Vercel для развертывания.",
                "dependencies": "TASK-010",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "TASK-013",
                "name": "Тестирование mind map функциональности",
                "status": "TODO",
                "priority": "Средний",
                "category": "Testing",
                "description": "Создать комплексные тесты для всех компонентов mind map системы. Unit тесты, интеграционные тесты и визуальные проверки.",
                "dependencies": "TASK-007, TASK-008, TASK-009, TASK-010",
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        
        for task_data in default_tasks:
            task = Task(**task_data)
            self.tasks[task.id] = task
        
        self.save_tasks()
        logger.info("Созданы задачи по умолчанию")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Получение задачи по ID"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: str) -> List[Task]:
        """Получение задач по статусу"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_category(self, category: str) -> List[Task]:
        """Получение задач по категории"""
        return [task for task in self.tasks.values() if task.category == category]
    
    def get_tasks_by_priority(self, priority: str) -> List[Task]:
        """Получение задач по приоритету"""
        return [task for task in self.tasks.values() if task.priority == priority]
    
    def update_task_status(self, task_id: str, new_status: str) -> bool:
        """Обновление статуса задачи"""
        task = self.get_task(task_id)
        if task:
            task.status = new_status
            task.updated_at = datetime.now().isoformat()
            self.save_tasks()
            logger.info(f"Статус задачи {task_id} обновлен на {new_status}")
            return True
        return False
    
    def update_task_progress(self, task_id: str, progress: int) -> bool:
        """Обновление прогресса задачи"""
        task = self.get_task(task_id)
        if task:
            task.progress = max(0, min(100, progress))
            task.updated_at = datetime.now().isoformat()
            self.save_tasks()
            logger.info(f"Прогресс задачи {task_id} обновлен на {progress}%")
            return True
        return False
    
    def add_task(self, task: Task) -> bool:
        """Добавление новой задачи"""
        if task.id not in self.tasks:
            self.tasks[task.id] = task
            self.save_tasks()
            logger.info(f"Добавлена новая задача: {task.id}")
            return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Удаление задачи"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.save_tasks()
            logger.info(f"Задача {task_id} удалена")
            return True
        return False
    
    def get_project_summary(self) -> Dict:
        """Получение сводки по проекту"""
        total_tasks = len(self.tasks)
        completed_tasks = len(self.get_tasks_by_status("DONE"))
        in_progress_tasks = len(self.get_tasks_by_status("IN_PROGRESS"))
        todo_tasks = len(self.get_tasks_by_status("TODO"))
        
        total_progress = sum(task.progress for task in self.tasks.values()) if self.tasks else 0
        average_progress = total_progress / total_tasks if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "in_progress_tasks": in_progress_tasks,
            "todo_tasks": todo_tasks,
            "average_progress": round(average_progress, 1),
            "completion_rate": round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
        }
    
    def export_to_markdown(self, output_file: str = "TASKS_REPORT.md"):
        """Экспорт задач в Markdown"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Отчет по задачам проекта Subs-bot\n\n")
                f.write(f"*Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                
                # Сводка
                summary = self.get_project_summary()
                f.write("## 📊 Сводка проекта\n\n")
                f.write(f"- **Всего задач**: {summary['total_tasks']}\n")
                f.write(f"- **Завершено**: {summary['completed_tasks']}\n")
                f.write(f"- **В работе**: {summary['in_progress_tasks']}\n")
                f.write(f"- **К выполнению**: {summary['todo_tasks']}\n")
                f.write(f"- **Средний прогресс**: {summary['average_progress']}%\n")
                f.write(f"- **Процент завершения**: {summary['completion_rate']}%\n\n")
                
                # Задачи по категориям
                categories = set(task.category for task in self.tasks.values())
                for category in sorted(categories):
                    f.write(f"## 🏷️ {category}\n\n")
                    category_tasks = self.get_tasks_by_category(category)
                    
                    for task in sorted(category_tasks, key=lambda x: x.priority):
                        status_emoji = {
                            "TODO": "⏳",
                            "IN_PROGRESS": "🔄",
                            "REVIEW": "👀",
                            "DONE": "✅"
                        }
                        
                        priority_emoji = {
                            "Критический": "🔴",
                            "Высокий": "🟠",
                            "Средний": "🟡",
                            "Низкий": "🟢"
                        }
                        
                        f.write(f"### {status_emoji.get(task.status, '❓')} {task.name}\n\n")
                        f.write(f"- **ID**: {task.id}\n")
                        f.write(f"- **Статус**: {task.status}\n")
                        f.write(f"- **Приоритет**: {priority_emoji.get(task.priority, '')} {task.priority}\n")
                        f.write(f"- **Прогресс**: {task.progress}%\n")
                        f.write(f"- **Зависимости**: {task.dependencies}\n")
                        f.write(f"- **Описание**: {task.description}\n")
                        f.write(f"- **Обновлено**: {task.updated_at[:10]}\n\n")
                
                f.write("---\n")
                f.write("*Отчет автоматически сгенерирован системой управления задачами*")
            
            logger.info(f"Отчет экспортирован в {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в Markdown: {e}")
            return False
    
    def export_to_json(self, output_file: str = "tasks_export.json"):
        """Экспорт задач в JSON"""
        try:
            tasks_dict = {task_id: asdict(task) for task_id, task in self.tasks.items()}
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Задачи экспортированы в {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            return False

# CLI интерфейс для управления задачами
def main():
    """Основная функция CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Task Manager для Subs-bot")
    parser.add_argument("--status", help="Показать задачи по статусу")
    parser.add_argument("--category", help="Показать задачи по категории")
    parser.add_argument("--priority", help="Показать задачи по приоритету")
    parser.add_argument("--update-status", nargs=2, help="Обновить статус задачи: ID НОВЫЙ_СТАТУС")
    parser.add_argument("--update-progress", nargs=2, help="Обновить прогресс задачи: ID ПРОГРЕСС")
    parser.add_argument("--export-md", help="Экспорт в Markdown")
    parser.add_argument("--export-json", help="Экспорт в JSON")
    parser.add_argument("--summary", action="store_true", help="Показать сводку проекта")
    
    args = parser.parse_args()
    
    task_manager = TaskManager()
    
    if args.status:
        tasks = task_manager.get_tasks_by_status(args.status)
        print(f"\nЗадачи со статусом '{args.status}':")
        for task in tasks:
            print(f"  {task.id}: {task.name} ({task.progress}%)")
    
    elif args.category:
        tasks = task_manager.get_tasks_by_category(args.category)
        print(f"\nЗадачи категории '{args.category}':")
        for task in tasks:
            print(f"  {task.id}: {task.name} - {task.status} ({task.progress}%)")
    
    elif args.priority:
        tasks = task_manager.get_tasks_by_priority(args.priority)
        print(f"\nЗадачи с приоритетом '{args.priority}':")
        for task in tasks:
            print(f"  {task.id}: {task.name} - {task.status} ({task.progress}%)")
    
    elif args.update_status:
        task_id, new_status = args.update_status
        if task_manager.update_task_status(task_id, new_status):
            print(f"Статус задачи {task_id} обновлен на {new_status}")
        else:
            print(f"Ошибка: задача {task_id} не найдена")
    
    elif args.update_progress:
        task_id, progress = args.update_progress
        try:
            progress_int = int(progress)
            if task_manager.update_task_progress(task_id, progress_int):
                print(f"Прогресс задачи {task_id} обновлен на {progress_int}%")
            else:
                print(f"Ошибка: задача {task_id} не найдена")
        except ValueError:
            print("Ошибка: прогресс должен быть числом")
    
    elif args.export_md:
        if task_manager.export_to_markdown(args.export_md):
            print(f"Отчет экспортирован в {args.export_md}")
        else:
            print("Ошибка экспорта")
    
    elif args.export_json:
        if task_manager.export_to_json(args.export_json):
            print(f"Задачи экспортированы в {args.export_json}")
        else:
            print("Ошибка экспорта")
    
    elif args.summary:
        summary = task_manager.get_project_summary()
        print("\n📊 Сводка проекта:")
        print(f"  Всего задач: {summary['total_tasks']}")
        print(f"  Завершено: {summary['completed_tasks']}")
        print(f"  В работе: {summary['in_progress_tasks']}")
        print(f"  К выполнению: {summary['todo_tasks']}")
        print(f"  Средний прогресс: {summary['average_progress']}%")
        print(f"  Процент завершения: {summary['completion_rate']}%")
    
    else:
        # Показать все задачи
        print("\n📋 Все задачи проекта:")
        for task_id, task in sorted(task_manager.tasks.items()):
            status_emoji = {"TODO": "⏳", "IN_PROGRESS": "🔄", "REVIEW": "👀", "DONE": "✅"}
            print(f"  {status_emoji.get(task.status, '❓')} {task.id}: {task.name}")
            print(f"    Статус: {task.status}, Прогресс: {task.progress}%, Категория: {task.category}")

if __name__ == "__main__":
    main()
