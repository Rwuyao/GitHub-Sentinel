import os
import yaml
import logging  # 引入logging模块
from typing import Dict, Optional

class Config:
    """配置管理类，支持从文件和环境变量加载配置"""
    
    def __init__(self, config_data: Dict = None):
        self.data = config_data or {}
        # 映射日志等级字符串到logging模块的常量
        self._log_level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """从YAML文件加载配置"""
        try:
            with open(file_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            return cls(config_data)
        except FileNotFoundError:
            raise Exception(f"配置文件 {file_path} 不存在")
        except yaml.YAMLError as e:
            raise Exception(f"解析配置文件失败: {str(e)}")
    
    @classmethod
    def from_env(cls) -> 'Config':
        """从环境变量加载配置"""
        config_data = {}
        
        # 读取GitHub相关配置
        if 'GITHUB_TOKEN' in os.environ:
            config_data['github_token'] = os.environ['GITHUB_TOKEN']
            
        # 读取日志配置
        if 'LOG_LEVEL' in os.environ:
            config_data.setdefault('logging', {})['level'] = os.environ['LOG_LEVEL']
            
        # 可以添加更多环境变量的映射
        return cls(config_data)
    
    def get(self, key: str, default: Optional[any] = None) -> any:
        """
        获取配置项，支持点符号嵌套访问
        
        Args:
            key: 配置项键名，如 "scheduler.daily_time"
            default: 默认值
        
        Returns:
            配置值或默认值
        """
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_log_level(self) -> int:
        """获取日志等级对应的logging模块常量"""
        level_str = self.get('logging.level', 'INFO').upper()
        return self._log_level_mapping.get(level_str, logging.INFO)
    
    def set(self, key: str, value: any) -> None:
        """设置配置项，支持点符号嵌套访问"""
        keys = key.split('.')
        data = self.data
        
        for i, k in enumerate(keys[:-1]):
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value

def generate_default_config(file_path: str = "config.yaml") -> None:
    """生成默认配置文件"""
    default_config = {
        "github_token": "your_github_personal_access_token_here",
        "api_timeout": 10,
        "api_retries": 3,
        "scheduler": {
            "daily_time": "08:30",
            "weekly_day": "monday",
            "weekly_time": "09:00",
            "check_interval": 60
        },
        "subscription": {
            "storage_type": "json",
            "storage_path": "data/subscriptions.json",
            "auto_save_interval": 300
        },
        "notifications": {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_use_tls": True,
                "smtp_username": "your-email@gmail.com",
                "smtp_password": "your-app-password",
                "from_address": "github-sentinel@example.com",
                "subject_prefix": "[GitHub Sentinel] ",
                "content_type": "html"
            },
            "slack": {
                "enabled": False,
                "webhook_url": "https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX",
                "message_prefix": ":github: GitHub 更新通知: ",
                "include_links": True
            }
        },
        "report": {
            "save_path": "reports/",
            "format": "markdown",
            "retention_days": 30,
            "include": {
                "releases": True,
                "commits": True,
                "pull_requests": True,
                "issues": True,
                "max_items": 20
            }
        },
        "logging": {
            "level": "INFO",
            "file": "logs/github-sentinel.log",
            "max_size": 10,
            "max_backup": 5
        }
    }
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            yaml.dump(default_config, f, sort_keys=False, allow_unicode=True)
        print(f"默认配置文件已生成: {file_path}")
    except Exception as e:
        print(f"生成配置文件失败: {str(e)}")
