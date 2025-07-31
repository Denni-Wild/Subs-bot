# 🎯 Система управления задачами с MCP серверами

Полноценная система управления задачами, построенная на интеграции нескольких MCP серверов для максимальной эффективности и автоматизации.

## 🏗️ Архитектура системы

```
┌─────────────────────────────────────────┐
│          ИНТЕРФЕЙСЫ                     │
│    Slack/Discord + Notifications        │
├─────────────────────────────────────────┤
│          ОРКЕСТРАЦИЯ                    │
│        shrimp-task-manager              │
├─────────────────────────────────────────┤
│      ПЛАНИРОВАНИЕ ВРЕМЕНИ               │
│     Calendar + Time Tracker             │
├─────────────────────────────────────────┤
│         ХРАНИЛИЩЕ ЗАДАЧ                 │
│           deltatask                     │
├─────────────────────────────────────────┤
│        ИНТЕГРАЦИИ                       │
│      Git + Filesystem                   │
├─────────────────────────────────────────┤
│        ПАМЯТЬ И БЭКАПЫ                  │
│  hpkv-memory + memory + backup          │
└─────────────────────────────────────────┘
```

## 🔧 Установка и настройка

### 1. Быстрая установка

```powershell
# Запустить PowerShell от имени администратора
.\setup-mcp-servers.ps1
```

### 2. Ручная установка

#### Шаг 1: Создание директорий
```powershell
New-Item -ItemType Directory -Path "D:/PY/MCP/calendar-data" -Force
New-Item -ItemType Directory -Path "D:/PY/MCP/notifications-data" -Force
New-Item -ItemType Directory -Path "D:/PY/MCP/time-tracking-data" -Force
New-Item -ItemType Directory -Path "D:/PY/MCP/backup-data" -Force
```

#### Шаг 2: Установка MCP серверов
```bash
npx -y @modelcontextprotocol/server-calendar
npx -y @modelcontextprotocol/server-notifications
npx -y @modelcontextprotocol/server-time-tracking
npx -y @modelcontextprotocol/server-git
npx -y @modelcontextprotocol/server-filesystem
npx -y @modelcontextprotocol/server-backup
```

#### Шаг 3: Обновление конфигурации
Скопировать содержимое `mcp-config-updated.json` в `%USERPROFILE%\.cursor\mcp.json`

#### Шаг 4: Перезапуск Cursor
Перезапустить Cursor для применения новой конфигурации

## 📋 Компоненты системы

### 🎯 Основные серверы

| Сервер | Назначение | Статус |
|--------|------------|--------|
| **deltatask** | Базовое управление задачами | ✅ Работает |
| **shrimp-task-manager** | Интеллектуальная оркестрация | ✅ Работает |
| **hpkv-memory-server** | Семантическая память | ✅ Работает |
| **memory** | Граф знаний | ✅ Работает |

### 🆕 Новые серверы

| Сервер | Назначение | Статус |
|--------|------------|--------|
| **mcp-calendar** | Планирование времени | 🔄 Установка |
| **mcp-notifications** | Система уведомлений | 🔄 Установка |
| **mcp-time-tracker** | Отслеживание времени | 🔄 Установка |
| **mcp-git** | Интеграция с Git | 🔄 Установка |
| **mcp-filesystem** | Файловое хранилище | 🔄 Установка |
| **mcp-backup** | Резервное копирование | 🔄 Установка |

## 🚀 Использование

### Создание задачи через оркестратор

```python
from task_system_orchestrator import TaskSystemOrchestrator

orchestrator = TaskSystemOrchestrator()

# Создание задачи
task = orchestrator.create_task(
    title="Разработка новой функции",
    description="Создать API для интеграции с внешними сервисами",
    priority=4,
    deadline="2024-01-15T18:00:00",
    tags=["development", "api", "high-priority"]
)

# Обновление статуса
orchestrator.update_task_status(task['id'], "in_progress", "Начал разработку")

# Получение аналитики
analytics = orchestrator.get_task_analytics()
```

### Рабочий процесс

1. **Планирование** → shrimp-task-manager анализирует цель
2. **Разбиение** → Создает подзадачи с зависимостями  
3. **Сохранение** → deltatask хранит структурированные задачи
4. **Планирование** → mcp-calendar создает события
5. **Уведомления** → mcp-notifications настраивает алерты
6. **Отслеживание** → mcp-time-tracker мониторит время
7. **Контекст** → hpkv-memory-server сохраняет историю
8. **Связи** → memory строит граф знаний
9. **Выполнение** → shrimp-task-manager координирует
10. **Верификация** → Проверка качества выполнения
11. **Резервное копирование** → mcp-backup сохраняет данные

## 🔄 Синхронизация

### Автоматическая синхронизация
```python
# Синхронизация всех серверов
orchestrator.sync_all_servers()
```

### Ручная синхронизация
```bash
# Синхронизация deltatask с Obsidian
python -c "from task_system_orchestrator import TaskSystemOrchestrator; TaskSystemOrchestrator()._sync_deltatask()"
```

## 📊 Аналитика и отчеты

### Доступные метрики
- Общее количество задач
- Процент выполнения
- Среднее время выполнения
- Распределение по приоритетам
- Затраченное время
- Просроченные задачи

### Получение отчетов
```python
analytics = orchestrator.get_task_analytics()
print(f"Процент выполнения: {analytics['completion_rate']:.1f}%")
print(f"Всего задач: {analytics['total_tasks']}")
print(f"Завершено: {analytics['completed_tasks']}")
```

## 🔧 Конфигурация

### Настройка путей
Отредактируйте `task-system-config.json`:

```json
{
  "data_dirs": {
    "calendar": "D:/PY/MCP/calendar-data",
    "notifications": "D:/PY/MCP/notifications-data",
    "time_tracking": "D:/PY/MCP/time-tracking-data",
    "backup": "D:/PY/MCP/backup-data",
    "memory": "D:/PY/MCP/all_memories.jsonl"
  },
  "sync_interval": 300,
  "backup_interval": 3600,
  "notification_channels": ["desktop", "email"],
  "auto_sync": true
}
```

### Настройка уведомлений
```json
{
  "notifications": {
    "desktop": true,
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your-email@gmail.com",
      "password": "your-app-password"
    },
    "slack": {
      "enabled": false,
      "webhook_url": ""
    }
  }
}
```

## 🛠️ Устранение неполадок

### Проблемы с подключением серверов
1. Проверьте, что все серверы установлены: `npx list -g | grep mcp`
2. Перезапустите Cursor
3. Проверьте логи в `task-system.log`

### Проблемы с синхронизацией
1. Убедитесь, что все директории существуют
2. Проверьте права доступа к файлам
3. Запустите ручную синхронизацию

### Проблемы с уведомлениями
1. Проверьте настройки SMTP для email
2. Убедитесь, что уведомления включены в системе
3. Проверьте логи уведомлений

## 📈 Расширение функциональности

### Добавление новых интеграций
1. Создайте новый MCP сервер
2. Добавьте его в конфигурацию
3. Интегрируйте в оркестратор
4. Обновите документацию

### Кастомные уведомления
```python
def custom_notification_handler(task_id, event_type, data):
    # Ваша логика обработки уведомлений
    pass

orchestrator.register_notification_handler(custom_notification_handler)
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.

## 🆘 Поддержка

- Создайте Issue в GitHub
- Обратитесь к документации MCP серверов
- Проверьте логи в `task-system.log`

---

**🎉 Готово!** Ваша система управления задачами настроена и готова к использованию! 