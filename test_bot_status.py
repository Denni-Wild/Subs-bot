#!/usr/bin/env python3
"""
Простой тест для проверки статуса бота
"""

import requests
import json
import os
from dotenv import load_dotenv

def test_bot_status():
    """Тестирует доступность бота через Telegram API"""
    
    # Загружаем переменные окружения
    load_dotenv()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env файле")
        return
    
    print(f"🔍 Проверяю статус бота с токеном: {token[:10]}...")
    
    try:
        # Проверяем информацию о боте
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_data = bot_info['result']
                print("✅ Бот доступен!")
                print(f"   🤖 Имя: {bot_data.get('first_name', 'N/A')}")
                print(f"   📝 Username: @{bot_data.get('username', 'N/A')}")
                print(f"   🆔 ID: {bot_data.get('id', 'N/A')}")
                print(f"   📋 Может присоединяться к группам: {bot_data.get('can_join_groups', 'N/A')}")
                print(f"   📢 Может читать сообщения: {bot_data.get('can_read_all_group_messages', 'N/A')}")
                
                # Проверяем последние обновления
                print("\n🔄 Проверяю последние обновления...")
                updates_url = f"https://api.telegram.org/bot{token}/getUpdates"
                updates_response = requests.get(updates_url, timeout=10)
                
                if updates_response.status_code == 200:
                    updates_info = updates_response.json()
                    if updates_info.get('ok'):
                        updates_count = len(updates_info.get('result', []))
                        print(f"   📊 Получено обновлений: {updates_count}")
                        
                        if updates_count > 0:
                            print("   📝 Последние обновления:")
                            for i, update in enumerate(updates_info['result'][-3:]):  # Показываем последние 3
                                update_id = update.get('update_id', 'N/A')
                                message_type = 'message' if 'message' in update else 'callback_query' if 'callback_query' in update else 'unknown'
                                print(f"      {i+1}. ID: {update_id}, Тип: {message_type}")
                    else:
                        print(f"   ⚠️ Ошибка при получении обновлений: {updates_info.get('description', 'Unknown error')}")
                else:
                    print(f"   ❌ Не удалось получить обновления: HTTP {updates_response.status_code}")
                
            else:
                print(f"❌ Ошибка API: {bot_info.get('description', 'Unknown error')}")
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            print(f"   Ответ: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Таймаут при подключении к Telegram API")
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":
    test_bot_status()
