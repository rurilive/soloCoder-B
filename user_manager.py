import json
import os
import hashlib
from typing import Dict, Optional

DATA_FILE = 'users.json'
DEFAULT_ADMIN_PASSWORD = 'admin123'


class UserManager:
    def __init__(self):
        self.users = {}
        self._load_users()
    
    def _load_users(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                self.users = json.load(f)
        
        if 'admin' not in self.users:
            self.users['admin'] = {
                'password': self._hash_password(DEFAULT_ADMIN_PASSWORD),
                'is_admin': True,
                'usage_limit': -1,
                'usage_count': 0
            }
            self._save_users()
    
    def _save_users(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def get_user(self, username: str) -> Optional[Dict]:
        return self.users.get(username)
    
    def verify_password(self, username: str, password: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        return user['password'] == self._hash_password(password)
    
    def create_user(self, username: str, password: str, is_admin: bool = False, usage_limit: int = 10) -> bool:
        if self.get_user(username):
            return False
        
        self.users[username] = {
            'password': self._hash_password(password),
            'is_admin': is_admin,
            'usage_limit': usage_limit,
            'usage_count': 0
        }
        self._save_users()
        return True
    
    def update_user(self, username: str, password: Optional[str] = None, 
                   usage_limit: Optional[int] = None, is_admin: Optional[bool] = None) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        
        if password is not None:
            user['password'] = self._hash_password(password)
        if usage_limit is not None:
            user['usage_limit'] = usage_limit
        if is_admin is not None:
            user['is_admin'] = is_admin
        
        self._save_users()
        return True
    
    def delete_user(self, username: str) -> bool:
        if username == 'admin' or username not in self.users:
            return False
        del self.users[username]
        self._save_users()
        return True
    
    def check_usage_limit(self, username: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        if user['is_admin'] or user['usage_limit'] == -1:
            return True
        return user['usage_count'] < user['usage_limit']
    
    def increment_usage(self, username: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        if not self.check_usage_limit(username):
            return False
        
        user['usage_count'] += 1
        self._save_users()
        return True
    
    def get_all_users(self) -> Dict:
        return self.users.copy()


user_manager = UserManager()
