import os
import yaml
import logging
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Config:
    """应用配置类，管理所有应用设置"""
    
    # GitHub API 配置
    github_api_token: str = ""
    github_api_url: str = ""
    
    # 调度配置
    run_daily: bool = True
    daily_time: str = ""  # 每天检查时间
    run_weekly: bool = True
    weekly_day: str = ""  # 每周报告日
    
    # 存储配置
    storage_type: str = ""
    storage_path: str = ""
    
    # 日志配置
    log_level: str = ""
    log_file: Optional[str] = None
    
    # 通知配置
    notification_providers: Dict = None
    
    def __init__(self, config_file: str = "config.yaml"):
        """从配置文件加载配置"""
        self.notification_providers = {}
        self._load_from_file(config_file)
        self._load_from_env()
    
    def _load_from_file(self, config_file: str):
        """从YAML文件加载配置"""
        if os.path.exists(config_file):
            with open(config_file, 'r',encoding='UTF-8') as f:
                config_data = yaml.safe_load(f) or {}
                
                # 加载GitHub配置
                if 'github' in config_data:
                    self.github_api_token = config_data['github'].get('api_token', self.github_api_token)
                    self.github_api_url = config_data['github'].get('api_url', self.github_api_url)
                
                # 加载调度配置
                if 'schedule' in config_data:
                    self.run_daily = config_data['schedule'].get('run_daily', self.run_daily)
                    self.daily_time = config_data['schedule'].get('daily_time', self.daily_time)
                    self.run_weekly = config_data['schedule'].get('run_weekly', self.run_weekly)
                    self.weekly_day = config_data['schedule'].get('weekly_day', self.weekly_day)
                
                # 加载存储配置
                if 'subscription' in config_data:
                    self.storage_type = config_data['subscription'].get('type', self.storage_type)
                    self.storage_path = config_data['subscription'].get('path', self.storage_path)
                
                # 加载日志配置
                if 'logging' in config_data:
                    self.log_level = config_data['logging'].get('level', self.log_level)
                    self.log_file = config_data['logging'].get('file', self.log_file)
                
                # 加载通知配置
                if 'notifications' in config_data:
                    self.notification_providers = config_data['notifications']
    
    def _load_from_env(self):
        """从环境变量加载配置，覆盖文件配置"""
        # 从环境变量获取GitHub token（优先级更高）
        self.github_api_token = os.getenv('GITHUB_TOKEN', self.github_api_token)
    
    def get_log_level(self) -> int:
        """将日志级别字符串转换为logging模块的常量"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(self.log_level.upper(), logging.INFO)
