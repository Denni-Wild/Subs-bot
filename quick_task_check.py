#!/usr/bin/env python3
"""
Быстрая проверка статуса задач проекта Subs-bot

Запуск: python quick_task_check.py
"""

from task_manager import TaskManager

def main():
    """Быстрая проверка задач"""
    print("🚀 Subs-bot Task Manager")
    print("=" * 50)
    
    # Инициализация менеджера задач
    task_manager = TaskManager()
    
    # Показать сводку
    summary = task_manager.get_project_summary()
    print(f"\n📊 Сводка проекта:")
    print(f"  Всего задач: {summary['total_tasks']}")
    print(f"  Завершено: {summary['completed_tasks']}")
    print(f"  В работе: {summary['in_progress_tasks']}")
    print(f"  К выполнению: {summary['todo_tasks']}")
    print(f"  Средний прогресс: {summary['average_progress']}%")
    print(f"  Процент завершения: {summary['completion_rate']}%")
    
    # Показать задачи по категориям
    print(f"\n🏷️ Задачи по категориям:")
    categories = set(task.category for task in task_manager.tasks.values())
    
    for category in sorted(categories):
        category_tasks = task_manager.get_tasks_by_category(category)
        completed = len([t for t in category_tasks if t.status == "DONE"])
        total = len(category_tasks)
        
        print(f"\n  {category}: {completed}/{total} завершено")
        
        for task in category_tasks:
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
            
            print(f"    {status_emoji.get(task.status, '❓')} {task.id}: {task.name}")
            print(f"      Приоритет: {priority_emoji.get(task.priority, '')} {task.priority}")
            print(f"      Прогресс: {task.progress}%")
            if task.dependencies != "Нет":
                print(f"      Зависимости: {task.dependencies}")
    
    # Показать следующие шаги
    print(f"\n🎯 Следующие шаги:")
    todo_tasks = task_manager.get_tasks_by_status("TODO")
    high_priority_tasks = [t for t in todo_tasks if t.priority in ["Критический", "Высокий"]]
    
    if high_priority_tasks:
        print("  Приоритетные задачи для выполнения:")
        for task in sorted(high_priority_tasks, key=lambda x: x.priority):
            print(f"    🔴 {task.id}: {task.name}")
    
    # Команды для управления
    print(f"\n💡 Команды для управления:")
    print("  python task_manager.py --summary                    # Сводка")
    print("  python task_manager.py --category 'Mind Map'       # Задачи категории")
    print("  python task_manager.py --status 'TODO'             # Задачи к выполнению")
    print("  python task_manager.py --update-status TASK-007 IN_PROGRESS  # Обновить статус")
    print("  python task_manager.py --update-progress TASK-007 50        # Обновить прогресс")
    print("  python task_manager.py --export-md REPORT.md       # Экспорт в Markdown")
    print("  python task_manager.py --export-json tasks.json    # Экспорт в JSON")

if __name__ == "__main__":
    main()
