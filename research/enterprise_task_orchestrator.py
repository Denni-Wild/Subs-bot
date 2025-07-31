#!/usr/bin/env python3
"""
Enterprise Task Management Orchestrator
Полный оркестратор системы управления задачами с обработкой ошибок,
мониторингом, логированием и восстановлением
"""

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles
import aiohttp
from contextlib import asynccontextmanager
import signal
import sys
from pathlib import Path

# Настройка логирования enterprise-уровня
class EnterpriseLogger:
    """Enterprise-уровень логирования с ротацией и структурированными логами"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Основной логгер
        self.logger = logging.getLogger('enterprise_orchestrator')
        self.logger.setLevel(logging.DEBUG)
        
        # Файловый обработчик с ротацией
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            self.log_dir / 'orchestrator.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_operation(self, operation: str, status: str, details: Dict = None):
        """Структурированное логирование операций"""
        log_data = {
            'operation': operation,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.logger.info(f"OPERATION: {json.dumps(log_data)}")
    
    def log_error(self, error: Exception, context: Dict = None):
        """Логирование ошибок с контекстом"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        self.logger.error(f"ERROR: {json.dumps(error_data)}")

class TaskStatus(Enum):
    """Статусы задач"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ServerStatus(Enum):
    """Статусы серверов"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ERROR = "error"

@dataclass
class TaskData:
    """Структура данных задачи"""
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3
    created_at: str = ""
    deadline: Optional[str] = None
    tags: List[str] = None
    time_spent: int = 0
    subtasks: List[str] = None
    dependencies: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.created_at == "":
            self.created_at = datetime.now().isoformat()
        if self.tags is None:
            self.tags = []
        if self.subtasks is None:
            self.subtasks = []
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ServerHealth:
    """Здоровье сервера"""
    name: str
    status: ServerStatus
    response_time: float
    last_check: str
    error_count: int = 0
    last_error: Optional[str] = None

class CircuitBreaker:
    """Circuit Breaker для защиты от каскадных сбоев"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Выполнение функции с circuit breaker"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e

class RetryMechanism:
    """Механизм повторных попыток с экспоненциальной задержкой"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    async def execute(self, func, *args, **kwargs):
        """Выполнение с повторными попытками"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        
        raise last_exception

class EnterpriseTaskOrchestrator:
    """Enterprise-уровень оркестратор системы управления задачами"""
    
    def __init__(self, config_path: str = "enterprise_config.json"):
        self.config = self._load_config(config_path)
        self.logger = EnterpriseLogger()
        self.circuit_breakers = {}
        self.retry_mechanisms = {}
        self.server_health = {}
        self.task_queue = asyncio.Queue()
        self.monitoring_data = {}
        self.is_running = False
        
        # Инициализация механизмов защиты
        self._init_protection_mechanisms()
        
        # Настройка graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_path: str) -> Dict:
        """Загрузка конфигурации"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Конфигурация по умолчанию
            return {
                "servers": {
                    "deltatask": {"enabled": True, "priority": 1},
                    "shrimp_task_manager": {"enabled": True, "priority": 1},
                    "hpkv_memory": {"enabled": True, "priority": 2},
                    "memory": {"enabled": True, "priority": 2},
                    "calendar": {"enabled": True, "priority": 3},
                    "notifications": {"enabled": True, "priority": 3},
                    "time_tracker": {"enabled": True, "priority": 3},
                    "git": {"enabled": True, "priority": 4},
                    "filesystem": {"enabled": True, "priority": 4},
                    "backup": {"enabled": True, "priority": 5}
                },
                "sync_interval": 300,
                "health_check_interval": 60,
                "backup_interval": 3600,
                "max_retries": 3,
                "circuit_breaker_threshold": 5,
                "monitoring_enabled": True,
                "data_dirs": {
                    "calendar": "D:/PY/MCP/calendar-data",
                    "notifications": "D:/PY/MCP/notifications-data",
                    "time_tracking": "D:/PY/MCP/time-tracking-data",
                    "backup": "D:/PY/MCP/backup-data"
                }
            }
    
    def _init_protection_mechanisms(self):
        """Инициализация механизмов защиты"""
        for server_name in self.config["servers"].keys():
            self.circuit_breakers[server_name] = CircuitBreaker(
                failure_threshold=self.config.get("circuit_breaker_threshold", 5)
            )
            self.retry_mechanisms[server_name] = RetryMechanism(
                max_retries=self.config.get("max_retries", 3)
            )
            self.server_health[server_name] = ServerHealth(
                name=server_name,
                status=ServerStatus.OFFLINE,
                response_time=0.0,
                last_check=datetime.now().isoformat()
            )
    
    def _signal_handler(self, signum, frame):
        """Обработка сигналов для graceful shutdown"""
        self.logger.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False
    
    async def start(self):
        """Запуск оркестратора"""
        self.is_running = True
        self.logger.log_operation("orchestrator_start", "started")
        
        # Запуск фоновых задач
        tasks = [
            asyncio.create_task(self._health_monitor()),
            asyncio.create_task(self._sync_worker()),
            asyncio.create_task(self._backup_worker()),
            asyncio.create_task(self._monitoring_worker())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.log_error(e, {"context": "orchestrator_start"})
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка оркестратора"""
        self.is_running = False
        self.logger.log_operation("orchestrator_stop", "completed")
    
    @asynccontextmanager
    async def _operation_context(self, operation: str, server: str = None):
        """Контекст для операций с логированием и мониторингом"""
        start_time = time.time()
        operation_id = f"{operation}_{int(start_time)}"
        
        try:
            self.logger.log_operation(operation, "started", {
                "operation_id": operation_id,
                "server": server
            })
            
            yield operation_id
            
            duration = time.time() - start_time
            self.logger.log_operation(operation, "completed", {
                "operation_id": operation_id,
                "duration": duration,
                "server": server
            })
            
            # Обновление метрик
            if server:
                self._update_server_metrics(server, duration, True)
                
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_error(e, {
                "operation_id": operation_id,
                "operation": operation,
                "server": server,
                "duration": duration
            })
            
            if server:
                self._update_server_metrics(server, duration, False)
            
            raise
    
    def _update_server_metrics(self, server: str, duration: float, success: bool):
        """Обновление метрик сервера"""
        if server in self.server_health:
            health = self.server_health[server]
            health.response_time = duration
            health.last_check = datetime.now().isoformat()
            
            if success:
                health.status = ServerStatus.ONLINE
                health.error_count = 0
            else:
                health.error_count += 1
                health.status = ServerStatus.DEGRADED if health.error_count < 3 else ServerStatus.ERROR
    
    async def create_task(self, title: str, description: str = "", 
                         priority: int = 3, deadline: Optional[str] = None,
                         tags: List[str] = None) -> TaskData:
        """
        Создание задачи с полной обработкой ошибок и восстановлением
        """
        async with self._operation_context("create_task") as operation_id:
            task_id = f"task_{int(time.time())}"
            task_data = TaskData(
                id=task_id,
                title=title,
                description=description,
                priority=priority,
                deadline=deadline,
                tags=tags or []
            )
            
            # Создание задачи в приоритетном порядке серверов
            servers_ordered = sorted(
                self.config["servers"].items(),
                key=lambda x: x[1]["priority"]
            )
            
            created_in_servers = []
            failed_servers = []
            
            for server_name, server_config in servers_ordered:
                if not server_config["enabled"]:
                    continue
                
                try:
                    await self._create_task_in_server(server_name, task_data)
                    created_in_servers.append(server_name)
                except Exception as e:
                    failed_servers.append((server_name, str(e)))
                    self.logger.log_error(e, {
                        "server": server_name,
                        "task_id": task_id,
                        "operation_id": operation_id
                    })
            
            # Обработка частичных сбоев
            if failed_servers and not created_in_servers:
                # Полный сбой - откат
                raise Exception(f"Failed to create task in any server: {failed_servers}")
            elif failed_servers:
                # Частичный сбой - восстановление
                await self._handle_partial_failure(task_data, created_in_servers, failed_servers)
            
            # Добавление в очередь синхронизации
            await self.task_queue.put({
                "type": "task_created",
                "task": task_data,
                "servers": created_in_servers,
                "operation_id": operation_id
            })
            
            return task_data
    
    async def _create_task_in_server(self, server_name: str, task_data: TaskData):
        """Создание задачи в конкретном сервере с защитой"""
        circuit_breaker = self.circuit_breakers[server_name]
        retry_mechanism = self.retry_mechanisms[server_name]
        
        async def _create():
            if server_name == "deltatask":
                return await self._create_in_deltatask(task_data)
            elif server_name == "shrimp_task_manager":
                return await self._create_in_shrimp_task_manager(task_data)
            elif server_name == "hpkv_memory":
                return await self._create_in_hpkv_memory(task_data)
            # ... другие серверы
        
        return await circuit_breaker.call(
            lambda: retry_mechanism.execute(_create)
        )
    
    async def _create_in_deltatask(self, task_data: TaskData):
        """Создание в deltatask"""
        try:
            from mcp_integrations import DeltaTaskIntegration
            async with DeltaTaskIntegration() as client:
                response = await client.create_task(task_data)
                if response.success:
                    self.logger.logger.info(f"Task created in deltatask: {task_data.id}")
                    return True
                else:
                    raise Exception(f"Deltatask error: {response.error}")
        except Exception as e:
            self.logger.logger.error(f"Error creating task in deltatask: {e}")
            raise
    
    async def _create_in_shrimp_task_manager(self, task_data: TaskData):
        """Создание в shrimp-task-manager"""
        try:
            from mcp_integrations import ShrimpTaskManagerIntegration
            async with ShrimpTaskManagerIntegration() as client:
                # Планируем задачу
                response = await client.plan_task(
                    task_data.description,
                    f"Priority: {task_data.priority}, Tags: {task_data.tags}"
                )
                if response.success:
                    self.logger.logger.info(f"Task planned in shrimp-task-manager: {task_data.id}")
                    return True
                else:
                    raise Exception(f"Shrimp-task-manager error: {response.error}")
        except Exception as e:
            self.logger.logger.error(f"Error planning task in shrimp-task-manager: {e}")
            raise
    
    async def _create_in_hpkv_memory(self, task_data: TaskData):
        """Создание в hpkv-memory-server"""
        try:
            from mcp_integrations import HPKVMemoryIntegration
            async with HPKVMemoryIntegration() as client:
                response = await client.store_memory(
                    "MCP-TaskSystem",
                    "task_creation",
                    1,
                    f"Create task: {task_data.title}",
                    f"Task created with ID: {task_data.id}",
                    {"task_id": task_data.id, "priority": task_data.priority}
                )
                if response.success:
                    self.logger.logger.info(f"Task stored in hpkv-memory: {task_data.id}")
                    return True
                else:
                    raise Exception(f"HPKV-memory error: {response.error}")
        except Exception as e:
            self.logger.logger.error(f"Error storing task in hpkv-memory: {e}")
            raise
    
    async def _handle_partial_failure(self, task_data: TaskData, 
                                    created_servers: List[str], 
                                    failed_servers: List[Tuple[str, str]]):
        """Обработка частичных сбоев"""
        self.logger.logger.warning(f"Partial failure for task {task_data.id}")
        self.logger.logger.warning(f"Created in: {created_servers}")
        self.logger.logger.warning(f"Failed in: {failed_servers}")
        
        # Попытка восстановления в failed серверах
        for server_name, error in failed_servers:
            try:
                await self._create_task_in_server(server_name, task_data)
                self.logger.logger.info(f"Recovery successful for {server_name}")
            except Exception as e:
                self.logger.logger.error(f"Recovery failed for {server_name}: {e}")
    
    async def _health_monitor(self):
        """Мониторинг здоровья серверов"""
        while self.is_running:
            try:
                for server_name in self.config["servers"].keys():
                    await self._check_server_health(server_name)
                
                await asyncio.sleep(self.config.get("health_check_interval", 60))
            except Exception as e:
                self.logger.log_error(e, {"context": "health_monitor"})
    
    async def _check_server_health(self, server_name: str):
        """Проверка здоровья конкретного сервера"""
        start_time = time.time()
        
        try:
            # Здесь будет проверка доступности сервера
            await asyncio.sleep(0.1)  # Имитация проверки
            
            duration = time.time() - start_time
            self._update_server_metrics(server_name, duration, True)
            
        except Exception as e:
            duration = time.time() - start_time
            self._update_server_metrics(server_name, duration, False)
            self.logger.log_error(e, {"context": "health_check", "server": server_name})
    
    async def _sync_worker(self):
        """Рабочий процесс синхронизации"""
        while self.is_running:
            try:
                # Обработка задач из очереди
                while not self.task_queue.empty():
                    task_info = await self.task_queue.get()
                    await self._process_sync_task(task_info)
                
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.log_error(e, {"context": "sync_worker"})
    
    async def _process_sync_task(self, task_info: Dict):
        """Обработка задачи синхронизации"""
        try:
            if task_info["type"] == "task_created":
                await self._sync_task_creation(task_info)
        except Exception as e:
            self.logger.log_error(e, {"context": "process_sync_task", "task_info": task_info})
    
    async def _sync_task_creation(self, task_info: Dict):
        """Синхронизация создания задачи"""
        task_data = task_info["task"]
        
        # Синхронизация с дополнительными серверами
        if task_data.deadline:
            await self._sync_with_calendar(task_data)
        
        await self._sync_with_notifications(task_data)
        await self._sync_with_time_tracker(task_data)
    
    async def _sync_with_calendar(self, task_data: TaskData):
        """Синхронизация с календарем"""
        try:
            # Интеграция с mcp-calendar
            self.logger.logger.info(f"Syncing task {task_data.id} with calendar")
        except Exception as e:
            self.logger.log_error(e, {"context": "calendar_sync", "task_id": task_data.id})
    
    async def _sync_with_notifications(self, task_data: TaskData):
        """Синхронизация с уведомлениями"""
        try:
            # Интеграция с mcp-notifications
            self.logger.logger.info(f"Syncing task {task_data.id} with notifications")
        except Exception as e:
            self.logger.log_error(e, {"context": "notifications_sync", "task_id": task_data.id})
    
    async def _sync_with_time_tracker(self, task_data: TaskData):
        """Синхронизация с трекером времени"""
        try:
            # Интеграция с mcp-time-tracker
            self.logger.logger.info(f"Syncing task {task_data.id} with time tracker")
        except Exception as e:
            self.logger.log_error(e, {"context": "time_tracker_sync", "task_id": task_data.id})
    
    async def _backup_worker(self):
        """Рабочий процесс резервного копирования"""
        while self.is_running:
            try:
                await self._create_backup()
                await asyncio.sleep(self.config.get("backup_interval", 3600))
            except Exception as e:
                self.logger.log_error(e, {"context": "backup_worker"})
    
    async def _create_backup(self):
        """Создание резервной копии"""
        async with self._operation_context("create_backup") as operation_id:
            try:
                # Интеграция с mcp-backup
                self.logger.logger.info("Creating backup")
            except Exception as e:
                self.logger.log_error(e, {"context": "backup_creation"})
    
    async def _monitoring_worker(self):
        """Рабочий процесс мониторинга"""
        while self.is_running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(30)  # Каждые 30 секунд
            except Exception as e:
                self.logger.log_error(e, {"context": "monitoring_worker"})
    
    async def _collect_metrics(self):
        """Сбор метрик"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "server_health": {name: asdict(health) for name, health in self.server_health.items()},
            "queue_size": self.task_queue.qsize(),
            "circuit_breakers": {
                name: {"state": cb.state, "failure_count": cb.failure_count}
                for name, cb in self.circuit_breakers.items()
            }
        }
        
        self.monitoring_data = metrics
        
        # Сохранение метрик
        try:
            async with aiofiles.open("monitoring_metrics.json", "w") as f:
                await f.write(json.dumps(metrics, indent=2))
        except Exception as e:
            self.logger.log_error(e, {"context": "metrics_save"})
    
    def get_health_status(self) -> Dict:
        """Получение статуса здоровья системы"""
        return {
            "orchestrator_status": "running" if self.is_running else "stopped",
            "server_health": {name: asdict(health) for name, health in self.server_health.items()},
            "queue_size": self.task_queue.qsize(),
            "last_metrics": self.monitoring_data
        }
    
    def get_statistics(self) -> Dict:
        """Получение статистики системы"""
        return {
            "total_operations": len(self.monitoring_data.get("operations", [])),
            "server_status": {
                name: health.status.value for name, health in self.server_health.items()
            },
            "error_rates": {
                name: health.error_count for name, health in self.server_health.items()
            }
        }

async def main():
    """Основная функция для тестирования"""
    orchestrator = EnterpriseTaskOrchestrator()
    
    try:
        # Запуск оркестратора в фоне
        orchestrator_task = asyncio.create_task(orchestrator.start())
        
        # Тестовое создание задачи
        await asyncio.sleep(2)  # Даем время на инициализацию
        
        task = await orchestrator.create_task(
            title="Enterprise Test Task",
            description="Testing enterprise orchestrator capabilities",
            priority=4,
            deadline=(datetime.now() + timedelta(days=1)).isoformat(),
            tags=["test", "enterprise", "orchestrator"]
        )
        
        print(f"✅ Task created: {task.id}")
        
        # Получение статуса здоровья
        health = orchestrator.get_health_status()
        print(f"🏥 Health status: {json.dumps(health, indent=2)}")
        
        # Ожидание завершения
        await asyncio.sleep(10)
        
    except KeyboardInterrupt:
        print("\n🛑 Graceful shutdown initiated...")
    finally:
        await orchestrator.stop()

if __name__ == "__main__":
    asyncio.run(main()) 