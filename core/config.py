import os
import yaml
import logging
from typing import Dict, Optional

class Config:
    """配置管理类，环境变量优先级高于配置文件"""
    
    def __init__(self, config_data: Dict = None):
        self.data = config_data or {}
        self._log_level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # GitHub Token
        if 'GITHUB_TOKEN' in os.environ:
            self.data['github_token'] = os.environ['GITHUB_TOKEN']
        
        # DeepSeek API Key
        if 'DEEPSEEK_API_KEY' in os.environ:
            if 'deepseek' not in self.data:
                self.data['deepseek'] = {}
            self.data['deepseek']['api_key'] = os.environ['DEEPSEEK_API_KEY']
        
        # 日志等级
        if 'LOG_LEVEL' in os.environ:
            if 'logging' not in self.data:
                self.data['logging'] = {}
            self.data['logging']['level'] = os.environ['LOG_LEVEL']
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """从YAML文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            return cls(config_data)
        except FileNotFoundError:
            raise Exception(f"配置文件 {file_path} 不存在")
        except yaml.YAMLError as e:
            raise Exception(f"解析配置文件失败: {str(e)}")
    
    def get(self, key: str, default: Optional[any] = None) -> any:
        """获取配置项，支持点符号访问"""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_log_level(self) -> int:
        """获取日志等级"""
        level_str = self.get('logging.level', 'INFO').upper()
        return self._log_level_mapping.get(level_str, logging.INFO)

def generate_default_config(file_path: str = "config.yaml") -> None:
    """生成默认配置文件"""
    default_config = {
        "github_token": "your_github_token_here",
        "deepseek": {
            "api_key": "your_deepseek_api_key_here",
            "model": "deepseek-chat",
            "api_url": "https://api.deepseek.com/v1/chat/completions",
            "temperature": 0.3,
            "max_tokens": 1000
        },
        "api_timeout": 10,
        "api_retries": 3,
        "report": {
            "output_dir": "ai_reports",
            "max_preview_items": {
                "releases": 3,
                "commits": 5,
                "pull_requests": 5,
                "issues": 5
            }
        },
        "logging": {
            "level": "INFO",
            "file": "logs/github-ai-summarizer.log",
            "max_size": 10,
            "max_backup": 5
        }
    }
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, sort_keys=False, allow_unicode=True)
        print(f"默认配置文件已生成: {file_path}")
    except Exception as e:
        print(f"生成配置文件失败: {str(e)}")
