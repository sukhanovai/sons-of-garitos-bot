# session_manager.py
import time
from typing import Dict, Any

class SessionManager:
    def __init__(self):
        self.sessions: Dict[int, Dict[str, Any]] = {}
        self.session_timeout = 3600  # 1 час
        
    def create_session(self, user_id: int):
        """Создает новую сессию для пользователя"""
        self.sessions[user_id] = {
            'created_at': time.time(),
            'current_section': None,
            'current_subsection': None,
            'current_post_index': 0,
            'posts': [],
            'adding_post': None,
            'creating_section': False,
            'creating_subsection': None
        }
        return self.sessions[user_id]
    
    def get_session(self, user_id: int):
        """Получает сессию пользователя"""
        session = self.sessions.get(user_id)
        if session and time.time() - session['created_at'] > self.session_timeout:
            del self.sessions[user_id]
            return None
        return session
    
    def update_session(self, user_id: int, updates: Dict[str, Any]):
        """Обновляет сессию пользователя"""
        if user_id in self.sessions:
            self.sessions[user_id].update(updates)
            self.sessions[user_id]['created_at'] = time.time()  # Обновляем время
        else:
            self.create_session(user_id)
            self.sessions[user_id].update(updates)
    
    def clear_session(self, user_id: int):
        """Очищает сессию пользователя"""
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def clear_adding_data(self, user_id: int):
        """Очищает данные о добавлении контента"""
        if user_id in self.sessions:
            self.sessions[user_id]['adding_post'] = None
            self.sessions[user_id]['creating_section'] = False
            self.sessions[user_id]['creating_subsection'] = None

# Глобальный менеджер сессий
session_manager = SessionManager()
