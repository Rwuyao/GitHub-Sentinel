from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Subscription:
    """订阅数据模型"""
    id: int  # 唯一标识
    repo_full_name: str  # 仓库名（owner/repo）
    subscribers: List[str]  # 订阅者邮箱（用于后续通知扩展）
    created_at: datetime  # 订阅创建时间
    last_processed_at: Optional[datetime] = None  # 最后处理时间
    time_range_type: str = "daily"  # 时间范围类型：daily（每日）/ custom（自定义）
    enabled: bool = True  # 是否启用订阅

    def to_dict(self) -> dict:
        """转换为字典（用于持久化）"""
        return {
            "id": self.id,
            "repo_full_name": self.repo_full_name,
            "subscribers": self.subscribers,
            "created_at": self.created_at.isoformat(),
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
            "time_range_type": self.time_range_type,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Subscription":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            repo_full_name=data["repo_full_name"],
            subscribers=data["subscribers"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_processed_at=datetime.fromisoformat(data["last_processed_at"]) if data["last_processed_at"] else None,
            time_range_type=data.get("time_range_type", "daily"),
            enabled=data.get("enabled", True)
        )