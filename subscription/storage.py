import sqlite3
from datetime import datetime
from typing import List, Optional
from .manager import Subscription

class SubscriptionStorage:
    """订阅数据存储，使用SQLite"""
    
    def __init__(self, config):
        self.db_path = config.database_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 创建订阅表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository TEXT NOT NULL UNIQUE,
                subscribers TEXT NOT NULL,  # 用逗号分隔的邮箱列表
                last_checked TEXT NOT NULL,
                created_at TEXT NOT NULL,
                daily_updates BOOLEAN NOT NULL,
                weekly_report BOOLEAN NOT NULL
            )
            ''')
            conn.commit()
    
    def add_subscription(
        self, 
        repository: str, 
        subscribers: List[str],
        last_checked: datetime,
        created_at: datetime,
        daily_updates: bool,
        weekly_report: bool
    ) -> bool:
        """添加新订阅"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO subscriptions 
                (repository, subscribers, last_checked, created_at, daily_updates, weekly_report)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    repository,
                    ','.join(subscribers),
                    last_checked.isoformat(),
                    created_at.isoformat(),
                    1 if daily_updates else 0,
                    1 if weekly_report else 0
                ))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_all_subscriptions(self) -> List[Subscription]:
        """获取所有订阅"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM subscriptions')
            rows = cursor.fetchall()
            
            return [
                Subscription(
                    id=row['id'],
                    repository=row['repository'],
                    subscribers=row['subscribers'].split(','),
                    last_checked=datetime.fromisoformat(row['last_checked']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    daily_updates=bool(row['daily_updates']),
                    weekly_report=bool(row['weekly_report'])
                )
                for row in rows
            ]
    
    # 其他方法实现（update_subscription, delete_subscription等）
    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """通过ID获取订阅"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,))
            row = cursor.fetchone()
            
            if row:
                return Subscription(
                    id=row['id'],
                    repository=row['repository'],
                    subscribers=row['subscribers'].split(','),
                    last_checked=datetime.fromisoformat(row['last_checked']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    daily_updates=bool(row['daily_updates']),
                    weekly_report=bool(row['weekly_report'])
                )
            return None
    
    def update_subscription(
        self, 
        subscription_id: int,
        repository: str,
        subscribers: List[str],
        last_checked: datetime,
        created_at: datetime,
        daily_updates: bool,
        weekly_report: bool
    ) -> bool:
        """更新订阅信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE subscriptions SET
                repository = ?,
                subscribers = ?,
                last_checked = ?,
                created_at = ?,
                daily_updates = ?,
                weekly_report = ?
                WHERE id = ?
                ''', (
                    repository,
                    ','.join(subscribers),
                    last_checked.isoformat(),
                    created_at.isoformat(),
                    1 if daily_updates else 0,
                    1 if weekly_report else 0,
                    subscription_id
                ))
                conn.commit()
            return True
        except Exception:
            return False
    
    def delete_subscription(self, subscription_id: int) -> bool:
        """删除订阅"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM subscriptions WHERE id = ?', (subscription_id,))
                conn.commit()
            return True
        except Exception:
            return False
