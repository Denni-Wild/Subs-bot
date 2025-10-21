#!/usr/bin/env python3
"""
Скрипт для очистки и ротации логов
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_logs():
    """Очищает старые логи и создает ротацию"""
    
    log_dir = Path("logs")
    if not log_dir.exists():
        print("Директория logs не найдена")
        return
    
    # Настройки
    max_log_size = 10 * 1024 * 1024  # 10MB
    max_backup_age = 30  # дней
    max_backups = 5  # максимальное количество backup файлов
    
    print("🧹 Начинаю очистку логов...")
    
    # Обрабатываем основной лог
    main_log = log_dir / "bot.log"
    if main_log.exists():
        current_size = main_log.stat().st_size
        print(f"📊 Размер основного лога: {current_size / 1024 / 1024:.2f} MB")
        
        if current_size > max_log_size:
            # Создаем backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"bot_{timestamp}.log"
            backup_path = log_dir / backup_name
            
            try:
                shutil.move(str(main_log), str(backup_path))
                print(f"✅ Лог переименован в {backup_name}")
                
                # Создаем новый пустой лог
                with open(main_log, 'w', encoding='utf-8-sig') as f:
                    f.write(f"# Новый лог файл создан {datetime.now()}\n")
                print("✅ Создан новый лог файл")
                
            except Exception as e:
                print(f"❌ Ошибка при ротации лога: {e}")
    
    # Удаляем старые backup файлы
    backup_files = []
    for file in log_dir.glob("bot_*.log"):
        if file.name != "bot.log":
            backup_files.append(file)
    
    # Сортируем по дате создания
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Удаляем старые backup файлы
    for backup_file in backup_files[max_backups:]:
        try:
            backup_file.unlink()
            print(f"🗑️ Удален старый backup: {backup_file.name}")
        except Exception as e:
            print(f"⚠️ Не удалось удалить {backup_file.name}: {e}")
    
    # Удаляем очень старые backup файлы
    cutoff_date = datetime.now() - timedelta(days=max_backup_age)
    for backup_file in backup_files:
        if backup_file.stat().st_mtime < cutoff_date.timestamp():
            try:
                backup_file.unlink()
                print(f"🗑️ Удален устаревший backup: {backup_file.name}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {backup_file.name}: {e}")
    
    # Очищаем другие лог файлы
    other_logs = ["summarization.log", "orchestrator.log"]
    for log_name in other_logs:
        log_path = log_dir / log_name
        if log_path.exists():
            current_size = log_path.stat().st_size
            if current_size > 1024 * 1024:  # 1MB
                try:
                    # Создаем backup
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_name = f"{log_name.replace('.log', '')}_{timestamp}.log"
                    backup_path = log_dir / backup_name
                    shutil.move(str(log_path), str(backup_path))
                    print(f"✅ {log_name} переименован в {backup_name}")
                    
                    # Создаем новый пустой лог
                    with open(log_path, 'w', encoding='utf-8-sig') as f:
                        f.write(f"# Новый лог файл создан {datetime.now()}\n")
                except Exception as e:
                    print(f"⚠️ Ошибка при ротации {log_name}: {e}")
    
    print("✅ Очистка логов завершена")

if __name__ == "__main__":
    cleanup_logs()
