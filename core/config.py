import os
import yaml
import logging
from typing import Dict, Optional

class Config:
    """配置管理类，支持环境变量优先于配置文件的加载策略"""
    
    def __init__(self, config_data: Dict = None):
        self.data = config_data or {}
        # 日志等级映射
        self._log_level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        # 处理环境变量覆盖
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖，环境变量优先级高于配置文件"""
        # GitHub Token 特殊处理：环境变量优先
        if 'GITHUB_TOKEN' in os.environ:
            self.data['github_token'] = os.environ['GITHUB_TOKEN']
        
        # 日志等级环境变量覆盖
        if 'LOG_LEVEL' in os.environ:
            if 'logging' not in self.data:
                self.data['logging'] = {}
            self.data['logging']['level'] = os.environ['LOG_LEVEL']
        
        # 其他需要环境变量覆盖的配置可以在这里添加
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Config':
        """从YAML文件加载配置，之后应用环境变量覆盖"""
        try:
            # 添加 encoding='utf-8'
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
            return cls(config_data)
        except FileNotFoundError:
            raise Exception(f"配置文件 {file_path} 不存在")
        except yaml.YAMLError as e:
            raise Exception(f"解析配置文件失败: {str(e)}")
    
    @classmethod
    def from_env(cls) -> 'Config':
        """仅从环境变量加载配置"""
        config_data = {}
        
        # GitHub Token
        if 'GITHUB_TOKEN' in os.environ:
            config_data['github_token'] = os.environ['GITHUB_TOKEN']
            
        # 日志等级
        if 'LOG_LEVEL' in os.environ:
            config_data['logging'] = {'level': os.environ['LOG_LEVEL']}
            
        return cls(config_data)
    
    def get(self, key: str, default: Optional[any] = None) -> any:
        """
        获取配置项，支持点符号嵌套访问
        
        Args:
            key: 配置项键名，如 "subscription.storage_path"
            default: 当配置项不存在时返回的默认值
        
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
        """获取日志等级对应的logging常量"""
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