from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Subscription:
    """订阅模型类，存储订阅相关信息"""
    id: int
    repo_full_name: str  # GitHub仓库全名，格式为"owner/repo"
    subscribers: List[str]  # 订阅者邮箱列表
    created_at: datetime  # 创建时间
    time_range_type: str  # 时间范围类型："daily"（每日）或"custom"（自定义）
    custom_time_start: Optional[datetime] = None  # 自定义开始时间（仅当time_range_type为"custom"时有效）
    custom_time_end: Optional[datetime] = None  # 自定义结束时间（仅当time_range_type为"custom"时有效）
    enabled: bool = True  # 订阅是否启用
    last_processed_at: Optional[datetime] = None  # 最后处理时间
