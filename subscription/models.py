from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Subscription:
    """订阅信息类，存储单个仓库的订阅信息"""
    id: int
    repository: str  # 格式为 "owner/repo"
    subscribers: List[str]  # 订阅者邮箱列表
    last_checked: datetime
    created_at: datetime
    daily_updates: bool = True
    weekly_report: bool = True
