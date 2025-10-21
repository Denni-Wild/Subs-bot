#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки последних записей в логах
"""

import os
from pathlib import Path

def check_logs():
    """Проверяет последние записи в логах"""
    log_dir = Path("logs")
    
    if not log_dir.exists():
        print("❌ Папка logs не найдена")
        return
    
    print("📁 Проверка логов:")
    
    # Проверяем bot.log
    bot_log = log_dir / "bot.log"
    if bot_log.exists():
        try:
            with open(bot_log, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                print(f"📋 bot.log: {len(lines)} строк")
                
                # Ищем последние ошибки
                error_lines = []
                for i, line in enumerate(lines[-100:], len(lines)-99):
                    if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'critical']):
                        error_lines.append(f"Строка {i}: {line.strip()}")
                
                if error_lines:
                    print(f"🚨 Найдено {len(error_lines)} ошибок:")
                    for error in error_lines[-5:]:  # Последние 5 ошибок
                        print(f"  {error}")
                else:
                    print("✅ Ошибок не найдено")
                    
        except Exception as e:
            print(f"❌ Ошибка чтения bot.log: {e}")
    
    # Проверяем summarization.log
    sum_log = log_dir / "summarization.log"
    if sum_log.exists():
        try:
            with open(sum_log, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                print(f"📋 summarization.log: {len(lines)} строк")
                
                # Последние записи
                if lines:
                    print("📝 Последние записи:")
                    for line in lines[-3:]:
                        print(f"  {line.strip()}")
                        
        except Exception as e:
            print(f"❌ Ошибка чтения summarization.log: {e}")

if __name__ == "__main__":
    check_logs()
