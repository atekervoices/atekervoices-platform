from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from quart import current_app
import os
from typing import Optional, Dict, Any
import json

class User(UserMixin):    
    def __init__(self, id: str, username: str, password_hash: str, is_admin: bool = False):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.created_at = datetime.utcnow()
        self.last_login = None
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = cls(
            id=data['id'],
            username=data['username'],
            password_hash=data['password_hash'],
            is_admin=data.get('is_admin', False)
        )
        if 'created_at' in data and data['created_at']:
            user.created_at = datetime.fromisoformat(data['created_at'])
        if 'last_login' in data and data['last_login']:
            user.last_login = datetime.fromisoformat(data['last_login'])
        return user

class UserManager:
    def __init__(self, storage_path: str = 'users.json'):
        self.storage_path = storage_path
        self.users: Dict[str, User] = {}
        self._load_users()
    
    def _load_users(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    users_data = json.load(f)
                    self.users = {
                        user_id: User.from_dict(user_data) 
                        for user_id, user_data in users_data.items()
                    }
            except Exception as e:
                current_app.logger.error(f"Error loading users: {e}")
                self.users = {}
    
    def _save_users(self):
        try:
            users_data = {
                user_id: user.to_dict() 
                for user_id, user in self.users.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(users_data, f, indent=2, default=str)
        except Exception as e:
            current_app.logger.error(f"Error saving users: {e}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(str(user_id))
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self.users.values():
            if user.username.lower() == username.lower():
                return user
        return None
    
    def create_user(self, username: str, password: str, is_admin: bool = False) -> User:
        if self.get_user_by_username(username):
            raise ValueError("Username already exists")
        
        user_id = str(len(self.users) + 1)
        user = User(user_id, username, "")
        user.set_password(password)
        user.is_admin = is_admin
        self.users[user_id] = user
        self._save_users()
        return user
    
    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        user = self.get_user(user_id)
        if not user:
            return None
        
        if 'username' in kwargs:
            existing_user = self.get_user_by_username(kwargs['username'])
            if existing_user and existing_user.id != user_id:
                raise ValueError("Username already exists")
            user.username = kwargs['username']
        
        if 'password' in kwargs and kwargs['password']:
            user.set_password(kwargs['password'])
        
        if 'is_admin' in kwargs:
            user.is_admin = kwargs['is_admin']
        
        self._save_users()
        return user
    
    def delete_user(self, user_id: str) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            self._save_users()
            return True
        return False
    
    def list_users(self) -> list[User]:
        return list(self.users.values())
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if user and user.check_password(password):
            user.last_login = datetime.utcnow()
            self._save_users()
            return user
        return None

# Initialize user manager
user_manager = UserManager()
