#!/usr/bin/env python3
"""
Тест функциональности серий голосовых сообщений
"""

import asyncio
import time
from bot import (
    add_voice_to_series, 
    get_voice_series, 
    cleanup_expired_voice_series,
    voice_series_groups,
    voice_series_timeout
)

async def test_voice_series():
    """Тестирует функциональность серий голосовых сообщений"""
    print("🧪 Тестирование функциональности серий голосовых сообщений")
    
    # Создаем мок-объект голосового сообщения
    class MockVoice:
        def __init__(self, duration, file_id):
            self.duration = duration
            self.file_id = file_id
    
    user_id = 12345
    
    print(f"\n1️⃣ Добавление первого голосового сообщения...")
    voice1 = MockVoice(30, "file_id_1")
    series_id1 = await add_voice_to_series(user_id, voice1)
    print(f"   ✅ Создана серия: {series_id1}")
    
    print(f"\n2️⃣ Добавление второго голосового сообщения...")
    voice2 = MockVoice(45, "file_id_2")
    series_id2 = await add_voice_to_series(user_id, voice2)
    print(f"   ✅ Добавлено в серию: {series_id2}")
    
    print(f"\n3️⃣ Проверка содержимого серии...")
    series_messages = await get_voice_series(user_id, series_id1)
    print(f"   📊 Сообщений в серии: {len(series_messages)}")
    for i, msg in enumerate(series_messages):
        print(f"      {i+1}. Длительность: {msg['voice'].duration}с, file_id: {msg['voice'].file_id}")
    
    print(f"\n4️⃣ Проверка состояния глобального словаря...")
    print(f"   🌐 Всего серий: {len(voice_series_groups)}")
    for series_id, messages in voice_series_groups.items():
        print(f"      {series_id}: {len(messages)} сообщений")
    
    print(f"\n5️⃣ Симуляция очистки устаревших серий...")
    # Устанавливаем старое время для первой серии
    if series_id1 in voice_series_groups and voice_series_groups[series_id1]:
        voice_series_groups[series_id1][0]['timestamp'] = time.time() - voice_series_timeout - 10
    
    await cleanup_expired_voice_series()
    print(f"   🧹 После очистки серий: {len(voice_series_groups)}")
    
    print(f"\n✅ Тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_voice_series())
