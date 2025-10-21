"""
Тест для проверки системы состояний Mind Map
Проверяет корректную работу состояний пользователя при нажатии кнопки Mind Map
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from bot import (
    set_user_state, get_user_state, clear_user_state, 
    cleanup_expired_user_states, user_states
)

class TestMindMapStates:
    """Тесты для системы состояний Mind Map"""
    
    def setup_method(self):
        """Очищаем состояния перед каждым тестом"""
        user_states.clear()
    
    @pytest.mark.asyncio
    async def test_set_user_state(self):
        """Тест установки состояния пользователя"""
        user_id = 12345
        
        # Устанавливаем состояние
        await set_user_state(user_id, 'expecting_mind_map_text')
        
        # Проверяем, что состояние установлено
        assert user_id in user_states
        assert user_states[user_id] == 'expecting_mind_map_text'
    
    @pytest.mark.asyncio
    async def test_get_user_state(self):
        """Тест получения состояния пользователя"""
        user_id = 12345
        
        # Проверяем состояние по умолчанию
        state = await get_user_state(user_id)
        assert state == 'normal'
        
        # Устанавливаем состояние
        user_states[user_id] = 'expecting_mind_map_text'
        
        # Проверяем установленное состояние
        state = await get_user_state(user_id)
        assert state == 'expecting_mind_map_text'
    
    @pytest.mark.asyncio
    async def test_clear_user_state(self):
        """Тест очистки состояния пользователя"""
        user_id = 12345
        
        # Устанавливаем состояние
        user_states[user_id] = 'expecting_mind_map_text'
        assert user_id in user_states
        
        # Очищаем состояние
        await clear_user_state(user_id)
        
        # Проверяем, что состояние очищено
        assert user_id not in user_states
    
    @pytest.mark.asyncio
    async def test_multiple_users_states(self):
        """Тест работы с несколькими пользователями"""
        user1_id = 12345
        user2_id = 67890
        
        # Устанавливаем разные состояния для разных пользователей
        await set_user_state(user1_id, 'expecting_mind_map_text')
        await set_user_state(user2_id, 'normal')
        
        # Проверяем состояния
        assert await get_user_state(user1_id) == 'expecting_mind_map_text'
        assert await get_user_state(user2_id) == 'normal'
        
        # Очищаем состояние первого пользователя
        await clear_user_state(user1_id)
        
        # Проверяем, что второй пользователь не затронут
        assert user1_id not in user_states
        assert user2_id in user_states
        assert await get_user_state(user2_id) == 'normal'
    
    @pytest.mark.asyncio
    async def test_state_transitions(self):
        """Тест переходов между состояниями"""
        user_id = 12345
        
        # Начальное состояние
        assert await get_user_state(user_id) == 'normal'
        
        # Переход в режим Mind Map
        await set_user_state(user_id, 'expecting_mind_map_text')
        assert await get_user_state(user_id) == 'expecting_mind_map_text'
        
        # Возврат в нормальное состояние
        await clear_user_state(user_id)
        assert await get_user_state(user_id) == 'normal'
    
    def test_user_states_structure(self):
        """Тест структуры словаря состояний"""
        user_id = 12345
        
        # Проверяем, что словарь пустой
        assert len(user_states) == 0
        
        # Добавляем состояние
        user_states[user_id] = 'expecting_mind_map_text'
        
        # Проверяем структуру
        assert isinstance(user_states, dict)
        assert user_id in user_states
        assert isinstance(user_states[user_id], str)
        assert user_states[user_id] == 'expecting_mind_map_text'

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
