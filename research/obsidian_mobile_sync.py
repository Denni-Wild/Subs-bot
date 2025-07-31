#!/usr/bin/env python3
"""
Obsidian и мобильная синхронизация для системы управления задачами
Интеграция с Obsidian, мобильные API и веб-интерфейс
"""

import os
import json
import asyncio
import aiohttp
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
import sqlite3
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ObsidianNote:
    """Структура заметки Obsidian"""
    title: str
    content: str
    tags: List[str]
    created: str
    modified: str
    path: str
    metadata: Dict = None

@dataclass
class MobileTask:
    """Структура задачи для мобильного доступа"""
    id: str
    title: str
    description: str
    status: str
    priority: int
    deadline: Optional[str]
    tags: List[str]
    time_spent: int
    created_at: str
    modified_at: str
    subtasks: List[str]
    dependencies: List[str]

class ObsidianSync:
    """Синхронизация с Obsidian"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.tasks_folder = self.vault_path / "Tasks"
        self.calendar_folder = self.vault_path / "Calendar"
        self.notes_folder = self.vault_path / "Notes"
        
        # Создаем папки если не существуют
        self.tasks_folder.mkdir(exist_ok=True)
        self.calendar_folder.mkdir(exist_ok=True)
        self.notes_folder.mkdir(exist_ok=True)
    
    async def sync_task_to_obsidian(self, task_data: Dict) -> bool:
        """Синхронизация задачи в Obsidian"""
        try:
            # Создаем заметку задачи
            note_content = self._create_task_note_content(task_data)
            note_path = self.tasks_folder / f"{task_data['id']}.md"
            
            async with aiofiles.open(note_path, 'w', encoding='utf-8') as f:
                await f.write(note_content)
            
            # Создаем календарное событие если есть дедлайн
            if task_data.get('deadline'):
                await self._create_calendar_event(task_data)
            
            logger.info(f"Задача {task_data['id']} синхронизирована с Obsidian")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации с Obsidian: {e}")
            return False
    
    def _create_task_note_content(self, task_data: Dict) -> str:
        """Создание содержимого заметки задачи"""
        tags = " ".join([f"#{tag}" for tag in task_data.get('tags', [])])
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }
        
        content = f"""---
title: {task_data['title']}
id: {task_data['id']}
status: {task_data['status']}
priority: {task_data['priority']}
created: {task_data['created_at']}
modified: {datetime.now().isoformat()}
deadline: {task_data.get('deadline', '')}
tags: {tags}
---

# {status_emoji.get(task_data['status'], '📋')} {task_data['title']}

## 📝 Описание
{task_data.get('description', 'Описание отсутствует')}

## 📊 Детали
- **Статус**: {task_data['status']}
- **Приоритет**: {task_data['priority']}
- **Создано**: {task_data['created_at']}
- **Время**: {task_data.get('time_spent', 0)} минут
- **Дедлайн**: {task_data.get('deadline', 'Не установлен')}

## 📋 Подзадачи
"""
        
        # Добавляем подзадачи
        for subtask in task_data.get('subtasks', []):
            content += f"- [ ] {subtask}\n"
        
        # Добавляем зависимости
        if task_data.get('dependencies'):
            content += "\n## 🔗 Зависимости\n"
            for dep in task_data['dependencies']:
                content += f"- [[{dep}]]\n"
        
        # Добавляем теги
        if task_data.get('tags'):
            content += f"\n## 🏷️ Теги\n{tags}\n"
        
        return content
    
    async def _create_calendar_event(self, task_data: Dict) -> None:
        """Создание календарного события"""
        if not task_data.get('deadline'):
            return
        
        try:
            deadline = datetime.fromisoformat(task_data['deadline'])
            event_content = f"""---
title: {task_data['title']}
date: {deadline.strftime('%Y-%m-%d')}
time: {deadline.strftime('%H:%M')}
type: task
priority: {task_data['priority']}
---

# 📅 {task_data['title']}

**Дедлайн**: {deadline.strftime('%d.%m.%Y %H:%M')}
**Приоритет**: {task_data['priority']}

{task_data.get('description', '')}

[[{task_data['id']}]]
"""
            
            event_path = self.calendar_folder / f"{task_data['id']}_deadline.md"
            async with aiofiles.open(event_path, 'w', encoding='utf-8') as f:
                await f.write(event_content)
                
        except Exception as e:
            logger.error(f"Ошибка создания календарного события: {e}")
    
    async def read_obsidian_tasks(self) -> List[Dict]:
        """Чтение задач из Obsidian"""
        tasks = []
        
        try:
            for file_path in self.tasks_folder.glob("*.md"):
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                task_data = self._parse_obsidian_note(content, file_path.name)
                if task_data:
                    tasks.append(task_data)
                    
        except Exception as e:
            logger.error(f"Ошибка чтения задач из Obsidian: {e}")
        
        return tasks
    
    def _parse_obsidian_note(self, content: str, filename: str) -> Optional[Dict]:
        """Парсинг заметки Obsidian"""
        try:
            # Извлекаем YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    note_content = parts[2]
                    
                    # Простой парсинг YAML
                    metadata = {}
                    for line in yaml_content.strip().split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()
                    
                    return {
                        'id': metadata.get('id', filename.replace('.md', '')),
                        'title': metadata.get('title', ''),
                        'status': metadata.get('status', 'pending'),
                        'priority': int(metadata.get('priority', 3)),
                        'created_at': metadata.get('created', ''),
                        'modified_at': metadata.get('modified', ''),
                        'deadline': metadata.get('deadline', ''),
                        'tags': metadata.get('tags', '').split() if metadata.get('tags') else [],
                        'description': self._extract_description(note_content)
                    }
        except Exception as e:
            logger.error(f"Ошибка парсинга заметки {filename}: {e}")
        
        return None
    
    def _extract_description(self, content: str) -> str:
        """Извлечение описания из содержимого заметки"""
        lines = content.split('\n')
        description_lines = []
        in_description = False
        
        for line in lines:
            if line.startswith('## 📝 Описание'):
                in_description = True
                continue
            elif line.startswith('##') and in_description:
                break
            elif in_description and line.strip():
                description_lines.append(line)
        
        return '\n'.join(description_lines).strip()

class MobileAPI:
    """Мобильный API для доступа к задачам"""
    
    def __init__(self, db_path: str = "mobile_tasks.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 3,
                deadline TEXT,
                tags TEXT,
                time_spent INTEGER DEFAULT 0,
                created_at TEXT,
                modified_at TEXT,
                subtasks TEXT,
                dependencies TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def sync_tasks_to_mobile(self, tasks: List[Dict]) -> bool:
        """Синхронизация задач в мобильную базу"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for task in tasks:
                cursor.execute('''
                    INSERT OR REPLACE INTO tasks 
                    (id, title, description, status, priority, deadline, tags, 
                     time_spent, created_at, modified_at, subtasks, dependencies)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task['id'],
                    task['title'],
                    task.get('description', ''),
                    task['status'],
                    task['priority'],
                    task.get('deadline', ''),
                    json.dumps(task.get('tags', [])),
                    task.get('time_spent', 0),
                    task['created_at'],
                    datetime.now().isoformat(),
                    json.dumps(task.get('subtasks', [])),
                    json.dumps(task.get('dependencies', []))
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Синхронизировано {len(tasks)} задач в мобильную базу")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации в мобильную базу: {e}")
            return False
    
    async def get_mobile_tasks(self, status: Optional[str] = None, 
                             priority: Optional[int] = None) -> List[MobileTask]:
        """Получение задач для мобильного приложения"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM tasks"
            params = []
            
            if status or priority:
                query += " WHERE"
                if status:
                    query += " status = ?"
                    params.append(status)
                if priority:
                    if status:
                        query += " AND"
                    query += " priority = ?"
                    params.append(priority)
            
            query += " ORDER BY priority DESC, created_at DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            tasks = []
            for row in rows:
                task = MobileTask(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    status=row[3],
                    priority=row[4],
                    deadline=row[5],
                    tags=json.loads(row[6]) if row[6] else [],
                    time_spent=row[7],
                    created_at=row[8],
                    modified_at=row[9],
                    subtasks=json.loads(row[10]) if row[10] else [],
                    dependencies=json.loads(row[11]) if row[11] else []
                )
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка получения мобильных задач: {e}")
            return []
    
    async def update_task_status(self, task_id: str, status: str) -> bool:
        """Обновление статуса задачи"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tasks 
                SET status = ?, modified_at = ?
                WHERE id = ?
            ''', (status, datetime.now().isoformat(), task_id))
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса задачи: {e}")
            return False

class WebInterface:
    """Простой веб-интерфейс для мобильного доступа"""
    
    def __init__(self, mobile_api: MobileAPI, port: int = 8080):
        self.mobile_api = mobile_api
        self.port = port
    
    async def start_server(self):
        """Запуск веб-сервера"""
        from aiohttp import web
        
        app = web.Application()
        
        # Статические файлы
        app.router.add_static('/static', path='static', name='static')
        
        # API endpoints
        app.router.add_get('/api/tasks', self.get_tasks_api)
        app.router.add_post('/api/tasks/{task_id}/status', self.update_task_status_api)
        app.router.add_get('/', self.index_page)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Веб-интерфейс запущен на http://localhost:{self.port}")
    
    async def get_tasks_api(self, request):
        """API для получения задач"""
        status = request.query.get('status')
        priority = request.query.get('priority')
        
        if priority:
            priority = int(priority)
        
        tasks = await self.mobile_api.get_mobile_tasks(status, priority)
        return web.json_response([asdict(task) for task in tasks])
    
    async def update_task_status_api(self, request):
        """API для обновления статуса задачи"""
        task_id = request.match_info['task_id']
        data = await request.json()
        status = data.get('status')
        
        if not status:
            return web.json_response({'error': 'Status required'}, status=400)
        
        success = await self.mobile_api.update_task_status(task_id, status)
        return web.json_response({'success': success})
    
    async def index_page(self, request):
        """Главная страница"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Task Manager Mobile</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                .task { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
                .priority-high { border-left: 4px solid #ff4444; }
                .priority-medium { border-left: 4px solid #ffaa00; }
                .priority-low { border-left: 4px solid #44aa44; }
                .status-pending { background-color: #fff3cd; }
                .status-in_progress { background-color: #d1ecf1; }
                .status-completed { background-color: #d4edda; }
                .filters { margin-bottom: 20px; }
                .filter-btn { margin: 5px; padding: 8px 15px; border: none; border-radius: 3px; cursor: pointer; }
                .filter-btn.active { background-color: #007bff; color: white; }
            </style>
        </head>
        <body>
            <h1>📱 Task Manager Mobile</h1>
            
            <div class="filters">
                <button class="filter-btn active" onclick="filterTasks('all')">Все</button>
                <button class="filter-btn" onclick="filterTasks('pending')">Ожидают</button>
                <button class="filter-btn" onclick="filterTasks('in_progress')">В работе</button>
                <button class="filter-btn" onclick="filterTasks('completed')">Завершены</button>
            </div>
            
            <div id="tasks"></div>
            
            <script>
                let currentFilter = 'all';
                
                async function loadTasks(filter = 'all') {
                    const response = await fetch(`/api/tasks${filter !== 'all' ? '?status=' + filter : ''}`);
                    const tasks = await response.json();
                    displayTasks(tasks);
                }
                
                function displayTasks(tasks) {
                    const container = document.getElementById('tasks');
                    container.innerHTML = '';
                    
                    tasks.forEach(task => {
                        const taskDiv = document.createElement('div');
                        taskDiv.className = `task priority-${getPriorityClass(task.priority)} status-${task.status}`;
                        
                        const statusEmoji = {
                            'pending': '⏳',
                            'in_progress': '🔄',
                            'completed': '✅',
                            'failed': '❌'
                        };
                        
                        taskDiv.innerHTML = `
                            <h3>${statusEmoji[task.status]} ${task.title}</h3>
                            <p>${task.description || 'Описание отсутствует'}</p>
                            <p><strong>Приоритет:</strong> ${task.priority}</p>
                            <p><strong>Время:</strong> ${task.time_spent} мин</p>
                            ${task.deadline ? `<p><strong>Дедлайн:</strong> ${new Date(task.deadline).toLocaleString()}</p>` : ''}
                            <div>
                                <button onclick="updateStatus('${task.id}', 'pending')" ${task.status === 'pending' ? 'disabled' : ''}>⏳ Ожидает</button>
                                <button onclick="updateStatus('${task.id}', 'in_progress')" ${task.status === 'in_progress' ? 'disabled' : ''}>🔄 В работе</button>
                                <button onclick="updateStatus('${task.id}', 'completed')" ${task.status === 'completed' ? 'disabled' : ''}>✅ Завершено</button>
                            </div>
                        `;
                        
                        container.appendChild(taskDiv);
                    });
                }
                
                function getPriorityClass(priority) {
                    if (priority <= 2) return 'high';
                    if (priority <= 3) return 'medium';
                    return 'low';
                }
                
                async function updateStatus(taskId, status) {
                    const response = await fetch(`/api/tasks/${taskId}/status`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({status})
                    });
                    
                    if (response.ok) {
                        loadTasks(currentFilter);
                    }
                }
                
                function filterTasks(filter) {
                    currentFilter = filter;
                    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                    event.target.classList.add('active');
                    loadTasks(filter);
                }
                
                // Загружаем задачи при загрузке страницы
                loadTasks();
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

class SyncManager:
    """Менеджер синхронизации"""
    
    def __init__(self, obsidian_path: str, db_path: str = "mobile_tasks.db"):
        self.obsidian_sync = ObsidianSync(obsidian_path)
        self.mobile_api = MobileAPI(db_path)
        self.web_interface = WebInterface(self.mobile_api)
    
    async def sync_all(self, tasks: List[Dict]) -> Dict[str, bool]:
        """Полная синхронизация"""
        results = {
            'obsidian': False,
            'mobile': False
        }
        
        # Синхронизация с Obsidian
        obsidian_success = True
        for task in tasks:
            if not await self.obsidian_sync.sync_task_to_obsidian(task):
                obsidian_success = False
        results['obsidian'] = obsidian_success
        
        # Синхронизация с мобильной базой
        results['mobile'] = await self.mobile_api.sync_tasks_to_mobile(tasks)
        
        return results
    
    async def start_web_interface(self):
        """Запуск веб-интерфейса"""
        await self.web_interface.start_server()

# Пример использования
async def main():
    # Настройки
    obsidian_vault = "D:/ObsidianVault"  # Путь к вашему vault Obsidian
    sync_manager = SyncManager(obsidian_vault)
    
    # Пример задач
    sample_tasks = [
        {
            'id': 'task_001',
            'title': 'Разработка новой функции',
            'description': 'Создать API для интеграции с внешними сервисами',
            'status': 'in_progress',
            'priority': 4,
            'deadline': '2024-01-15T18:00:00',
            'tags': ['development', 'api'],
            'time_spent': 120,
            'created_at': '2024-01-10T10:00:00',
            'subtasks': ['Анализ требований', 'Дизайн API', 'Реализация'],
            'dependencies': []
        }
    ]
    
    # Синхронизация
    results = await sync_manager.sync_all(sample_tasks)
    print(f"Результаты синхронизации: {results}")
    
    # Запуск веб-интерфейса
    await sync_manager.start_web_interface()
    
    # Держим сервер запущенным
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main()) 