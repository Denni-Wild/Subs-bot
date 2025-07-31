#!/usr/bin/env python3
"""
MCP Server Integrations for Enterprise Task Orchestrator
Интеграции с реальными MCP серверами
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
from enterprise_task_orchestrator import TaskData, TaskStatus

logger = logging.getLogger('mcp_integrations')

@dataclass
class MCPResponse:
    """Стандартный ответ от MCP сервера"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    server: str = ""
    response_time: float = 0.0

class MCPClient:
    """Базовый клиент для MCP серверов"""
    
    def __init__(self, server_name: str, timeout: int = 30):
        self.server_name = server_name
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> MCPResponse:
        """Выполнение запроса к MCP серверу"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Здесь будет реальная интеграция с MCP API
            # Пока используем имитацию
            await asyncio.sleep(0.1)  # Имитация сетевой задержки
            
            response_time = asyncio.get_event_loop().time() - start_time
            
            # Имитация успешного ответа
            return MCPResponse(
                success=True,
                data={"status": "success", "server": self.server_name},
                server=self.server_name,
                response_time=response_time
            )
            
        except Exception as e:
            response_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Error in {self.server_name}: {e}")
            return MCPResponse(
                success=False,
                error=str(e),
                server=self.server_name,
                response_time=response_time
            )

class DeltaTaskIntegration(MCPClient):
    """Интеграция с deltatask MCP сервером"""
    
    def __init__(self):
        super().__init__("deltatask", timeout=30)
    
    async def create_task(self, task_data: TaskData) -> MCPResponse:
        """Создание задачи в deltatask"""
        logger.info(f"Creating task in deltatask: {task_data.id}")
        
        # Преобразование в формат deltatask
        deltatask_data = {
            "title": task_data.title,
            "description": task_data.description,
            "urgency": self._convert_priority_to_urgency(task_data.priority),
            "effort": self._estimate_effort(task_data.description),
            "tags": task_data.tags
        }
        
        return await self._make_request("POST", "/tasks", deltatask_data)
    
    async def get_task(self, task_id: str) -> MCPResponse:
        """Получение задачи из deltatask"""
        return await self._make_request("GET", f"/tasks/{task_id}")
    
    async def update_task(self, task_id: str, updates: Dict) -> MCPResponse:
        """Обновление задачи в deltatask"""
        return await self._make_request("PUT", f"/tasks/{task_id}", updates)
    
    async def delete_task(self, task_id: str) -> MCPResponse:
        """Удаление задачи из deltatask"""
        return await self._make_request("DELETE", f"/tasks/{task_id}")
    
    async def list_tasks(self, tags: List[str] = None) -> MCPResponse:
        """Получение списка задач из deltatask"""
        params = {"tags": tags} if tags else {}
        return await self._make_request("GET", "/tasks", params)
    
    def _convert_priority_to_urgency(self, priority: int) -> int:
        """Конвертация приоритета в urgency для deltatask"""
        # deltatask использует urgency 1-5, где 1 - высший
        return max(1, 6 - priority)
    
    def _estimate_effort(self, description: str) -> int:
        """Оценка effort на основе описания"""
        words = len(description.split())
        if words < 10:
            return 1
        elif words < 50:
            return 2
        elif words < 100:
            return 3
        else:
            return 4

class ShrimpTaskManagerIntegration(MCPClient):
    """Интеграция с shrimp-task-manager MCP сервером"""
    
    def __init__(self):
        super().__init__("shrimp_task_manager", timeout=60)
    
    async def plan_task(self, description: str, requirements: str = "") -> MCPResponse:
        """Планирование задачи с помощью shrimp-task-manager"""
        logger.info(f"Planning task with shrimp-task-manager")
        
        plan_data = {
            "description": description,
            "requirements": requirements
        }
        
        return await self._make_request("POST", "/plan_task", plan_data)
    
    async def analyze_task(self, summary: str, initial_concept: str) -> MCPResponse:
        """Анализ задачи"""
        analyze_data = {
            "summary": summary,
            "initialConcept": initial_concept
        }
        
        return await self._make_request("POST", "/analyze_task", analyze_data)
    
    async def split_tasks(self, tasks_raw: str, update_mode: str = "clearAllTasks") -> MCPResponse:
        """Разбивка задачи на подзадачи"""
        split_data = {
            "updateMode": update_mode,
            "tasksRaw": tasks_raw
        }
        
        return await self._make_request("POST", "/split_tasks", split_data)
    
    async def execute_task(self, task_id: str) -> MCPResponse:
        """Выполнение задачи"""
        return await self._make_request("POST", f"/execute_task/{task_id}")
    
    async def verify_task(self, task_id: str, summary: str, score: int) -> MCPResponse:
        """Верификация задачи"""
        verify_data = {
            "summary": summary,
            "score": score
        }
        
        return await self._make_request("POST", f"/verify_task/{task_id}", verify_data)
    
    async def list_tasks(self, status: str = "all") -> MCPResponse:
        """Получение списка задач"""
        return await self._make_request("GET", f"/list_tasks?status={status}")

class HPKVMemoryIntegration(MCPClient):
    """Интеграция с hpkv-memory-server MCP сервером"""
    
    def __init__(self):
        super().__init__("hpkv_memory", timeout=30)
    
    async def store_memory(self, project_name: str, session_name: str, 
                          sequence_number: int, request: str, response: str,
                          metadata: Dict = None) -> MCPResponse:
        """Сохранение памяти"""
        memory_data = {
            "project_name": project_name,
            "session_name": session_name,
            "sequence_number": sequence_number,
            "request": request,
            "response": response,
            "metadata": metadata or {}
        }
        
        return await self._make_request("POST", "/store_memory", memory_data)
    
    async def search_memory(self, query: str) -> MCPResponse:
        """Поиск в памяти"""
        search_data = {"query": query}
        return await self._make_request("POST", "/search_memory", search_data)
    
    async def search_keys(self, query: str, top_k: int = 10, min_score: float = 0.65) -> MCPResponse:
        """Поиск ключей памяти"""
        search_data = {
            "query": query,
            "topK": top_k,
            "minScore": min_score
        }
        
        return await self._make_request("POST", "/search_keys", search_data)
    
    async def get_memory(self, key: str) -> MCPResponse:
        """Получение конкретной памяти"""
        return await self._make_request("GET", f"/get_memory?key={key}")

class MemoryIntegration(MCPClient):
    """Интеграция с memory MCP сервером (граф знаний)"""
    
    def __init__(self):
        super().__init__("memory", timeout=30)
    
    async def add_memory(self, content: str, metadata: Dict = None) -> MCPResponse:
        """Добавление памяти в граф знаний"""
        memory_data = {
            "content": content,
            "metadata": metadata or {}
        }
        
        return await self._make_request("POST", "/add_memory", memory_data)
    
    async def search_memory(self, query: str) -> MCPResponse:
        """Поиск в графе знаний"""
        search_data = {"query": query}
        return await self._make_request("POST", "/search_memory", search_data)
    
    async def get_related_memories(self, memory_id: str) -> MCPResponse:
        """Получение связанных воспоминаний"""
        return await self._make_request("GET", f"/related_memories/{memory_id}")

class CalendarIntegration(MCPClient):
    """Интеграция с mcp-calendar MCP сервером"""
    
    def __init__(self):
        super().__init__("calendar", timeout=20)
    
    async def create_event(self, title: str, start_time: str, end_time: str,
                          description: str = "", location: str = "") -> MCPResponse:
        """Создание события в календаре"""
        event_data = {
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "location": location
        }
        
        return await self._make_request("POST", "/events", event_data)
    
    async def get_events(self, start_date: str = None, end_date: str = None) -> MCPResponse:
        """Получение событий из календаря"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        return await self._make_request("GET", "/events", params)
    
    async def update_event(self, event_id: str, updates: Dict) -> MCPResponse:
        """Обновление события"""
        return await self._make_request("PUT", f"/events/{event_id}", updates)
    
    async def delete_event(self, event_id: str) -> MCPResponse:
        """Удаление события"""
        return await self._make_request("DELETE", f"/events/{event_id}")

class NotificationsIntegration(MCPClient):
    """Интеграция с mcp-notifications MCP сервером"""
    
    def __init__(self):
        super().__init__("notifications", timeout=15)
    
    async def send_notification(self, title: str, message: str, 
                               notification_type: str = "info",
                               recipients: List[str] = None) -> MCPResponse:
        """Отправка уведомления"""
        notification_data = {
            "title": title,
            "message": message,
            "type": notification_type,
            "recipients": recipients or []
        }
        
        return await self._make_request("POST", "/send", notification_data)
    
    async def send_telegram(self, message: str, chat_id: str = None) -> MCPResponse:
        """Отправка в Telegram"""
        telegram_data = {
            "message": message,
            "chat_id": chat_id
        }
        
        return await self._make_request("POST", "/telegram", telegram_data)
    
    async def send_email(self, to: str, subject: str, body: str) -> MCPResponse:
        """Отправка email"""
        email_data = {
            "to": to,
            "subject": subject,
            "body": body
        }
        
        return await self._make_request("POST", "/email", email_data)

class TimeTrackerIntegration(MCPClient):
    """Интеграция с mcp-time-tracker MCP сервером"""
    
    def __init__(self):
        super().__init__("time_tracker", timeout=20)
    
    async def start_tracking(self, task_id: str, description: str = "") -> MCPResponse:
        """Начало отслеживания времени"""
        tracking_data = {
            "task_id": task_id,
            "description": description,
            "start_time": datetime.now().isoformat()
        }
        
        return await self._make_request("POST", "/start", tracking_data)
    
    async def stop_tracking(self, task_id: str) -> MCPResponse:
        """Остановка отслеживания времени"""
        return await self._make_request("POST", f"/stop/{task_id}")
    
    async def get_time_log(self, task_id: str) -> MCPResponse:
        """Получение лога времени для задачи"""
        return await self._make_request("GET", f"/log/{task_id}")
    
    async def get_total_time(self, task_id: str) -> MCPResponse:
        """Получение общего времени для задачи"""
        return await self._make_request("GET", f"/total/{task_id}")

class GitIntegration(MCPClient):
    """Интеграция с mcp-git MCP сервером"""
    
    def __init__(self):
        super().__init__("git", timeout=30)
    
    async def create_branch(self, branch_name: str, base_branch: str = "main") -> MCPResponse:
        """Создание ветки"""
        branch_data = {
            "branch_name": branch_name,
            "base_branch": base_branch
        }
        
        return await self._make_request("POST", "/branches", branch_data)
    
    async def commit_changes(self, message: str, files: List[str] = None) -> MCPResponse:
        """Коммит изменений"""
        commit_data = {
            "message": message,
            "files": files or []
        }
        
        return await self._make_request("POST", "/commit", commit_data)
    
    async def link_task_to_commit(self, task_id: str, commit_hash: str) -> MCPResponse:
        """Связывание задачи с коммитом"""
        link_data = {
            "task_id": task_id,
            "commit_hash": commit_hash
        }
        
        return await self._make_request("POST", "/link_task", link_data)

class FilesystemIntegration(MCPClient):
    """Интеграция с mcp-filesystem MCP сервером"""
    
    def __init__(self):
        super().__init__("filesystem", timeout=25)
    
    async def attach_file_to_task(self, task_id: str, file_path: str, 
                                 description: str = "") -> MCPResponse:
        """Прикрепление файла к задаче"""
        attach_data = {
            "task_id": task_id,
            "file_path": file_path,
            "description": description
        }
        
        return await self._make_request("POST", "/attach_file", attach_data)
    
    async def get_task_files(self, task_id: str) -> MCPResponse:
        """Получение файлов задачи"""
        return await self._make_request("GET", f"/task_files/{task_id}")
    
    async def create_task_folder(self, task_id: str, folder_name: str) -> MCPResponse:
        """Создание папки для задачи"""
        folder_data = {
            "task_id": task_id,
            "folder_name": folder_name
        }
        
        return await self._make_request("POST", "/create_folder", folder_data)

class BackupIntegration(MCPClient):
    """Интеграция с mcp-backup MCP сервером"""
    
    def __init__(self):
        super().__init__("backup", timeout=120)
    
    async def create_backup(self, backup_name: str = None, 
                           include_files: bool = True) -> MCPResponse:
        """Создание резервной копии"""
        backup_data = {
            "backup_name": backup_name or f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "include_files": include_files
        }
        
        return await self._make_request("POST", "/create", backup_data)
    
    async def restore_backup(self, backup_id: str) -> MCPResponse:
        """Восстановление из резервной копии"""
        return await self._make_request("POST", f"/restore/{backup_id}")
    
    async def list_backups(self) -> MCPResponse:
        """Получение списка резервных копий"""
        return await self._make_request("GET", "/list")
    
    async def delete_backup(self, backup_id: str) -> MCPResponse:
        """Удаление резервной копии"""
        return await self._make_request("DELETE", f"/delete/{backup_id}")

class MCPIntegrationManager:
    """Менеджер интеграций с MCP серверами"""
    
    def __init__(self):
        self.integrations = {
            "deltatask": DeltaTaskIntegration(),
            "shrimp_task_manager": ShrimpTaskManagerIntegration(),
            "hpkv_memory": HPKVMemoryIntegration(),
            "memory": MemoryIntegration(),
            "calendar": CalendarIntegration(),
            "notifications": NotificationsIntegration(),
            "time_tracker": TimeTrackerIntegration(),
            "git": GitIntegration(),
            "filesystem": FilesystemIntegration(),
            "backup": BackupIntegration()
        }
    
    async def create_task_integrated(self, task_data: TaskData) -> Dict[str, MCPResponse]:
        """Создание задачи во всех интегрированных серверах"""
        results = {}
        
        # Основные серверы (приоритет 1)
        for server_name in ["deltatask", "shrimp_task_manager"]:
            if server_name in self.integrations:
                async with self.integrations[server_name] as client:
                    if server_name == "deltatask":
                        results[server_name] = await client.create_task(task_data)
                    elif server_name == "shrimp_task_manager":
                        # Для shrimp-task-manager сначала планируем
                        plan_result = await client.plan_task(
                            task_data.description, 
                            f"Priority: {task_data.priority}, Tags: {task_data.tags}"
                        )
                        results[server_name] = plan_result
        
        # Серверы памяти (приоритет 2)
        for server_name in ["hpkv_memory", "memory"]:
            if server_name in self.integrations:
                async with self.integrations[server_name] as client:
                    if server_name == "hpkv_memory":
                        results[server_name] = await client.store_memory(
                            "MCP-TaskSystem",
                            "task_creation",
                            1,
                            f"Create task: {task_data.title}",
                            f"Task created with ID: {task_data.id}",
                            {"task_id": task_data.id, "priority": task_data.priority}
                        )
                    elif server_name == "memory":
                        results[server_name] = await client.add_memory(
                            f"Task created: {task_data.title} - {task_data.description}",
                            {"task_id": task_data.id, "type": "task_creation"}
                        )
        
        # Дополнительные серверы (приоритет 3+)
        if task_data.deadline and "calendar" in self.integrations:
            async with self.integrations["calendar"] as client:
                results["calendar"] = await client.create_event(
                    task_data.title,
                    task_data.deadline,
                    (datetime.fromisoformat(task_data.deadline) + timedelta(hours=1)).isoformat(),
                    task_data.description
                )
        
        if "notifications" in self.integrations:
            async with self.integrations["notifications"] as client:
                results["notifications"] = await client.send_notification(
                    "Новая задача создана",
                    f"Задача '{task_data.title}' создана с приоритетом {task_data.priority}",
                    "info"
                )
        
        return results
    
    async def get_integration_status(self) -> Dict[str, bool]:
        """Получение статуса всех интеграций"""
        status = {}
        
        for server_name, integration in self.integrations.items():
            try:
                async with integration as client:
                    # Простая проверка доступности
                    test_response = await client._make_request("GET", "/health")
                    status[server_name] = test_response.success
            except Exception as e:
                logger.error(f"Error checking {server_name}: {e}")
                status[server_name] = False
        
        return status

# Экспорт для использования в оркестраторе
__all__ = [
    'MCPIntegrationManager',
    'DeltaTaskIntegration',
    'ShrimpTaskManagerIntegration',
    'HPKVMemoryIntegration',
    'MemoryIntegration',
    'CalendarIntegration',
    'NotificationsIntegration',
    'TimeTrackerIntegration',
    'GitIntegration',
    'FilesystemIntegration',
    'BackupIntegration',
    'MCPResponse'
] 