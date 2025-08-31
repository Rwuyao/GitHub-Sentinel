import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """应用配置类"""
    github_token: str
    database_path: str
    log_level: str = "INFO"
    daily_check_time: str = "09:00"  # 每日检查时间
    weekly_check_day: str = "Monday"  # 每周检查日
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN 环境变量未设置")
            
        return cls(
            github_token=github_token,
            database_path=os.getenv("DATABASE_PATH", "sentinel.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            daily_check_time=os.getenv("DAILY_CHECK_TIME", "09:00"),
            weekly_check_day=os.getenv("WEEKLY_CHECK_DAY", "Monday")
        )
