import os
import yaml
from typing import Dict, Optional, Any

class Config:
    """配置管理类，支持从YAML配置文件和提示词文件加载配置"""
    
    def __init__(self):
        """初始化配置对象"""
        self._config = {}
        self._prompts = {}  
    
    @classmethod
    def from_file(cls, config_path: str = "config.yaml") -> "Config":
        """
        从配置文件创建Config实例
        
        参数:
            config_path: 配置文件路径
            
        返回:
            Config实例
        """
        config = cls()
        config.load_config(config_path)
        return config
    
    def load_config(self, config_path: str) -> bool:
        """
        加载YAML格式的配置文件
        
        参数:
            config_path: 配置文件路径
            
        返回:
            是否加载成功
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                return True
            else:
                print(f"配置文件不存在: {config_path}，使用默认配置")
                self._config = {}
                return False
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            return False
    
    def load_prompt(self, prompt_key: str, file_path: str) -> bool:
        """
        从文本文件加载提示词并存储
        
        参数:
            prompt_key: 提示词的键名，用于后续获取
            file_path: 提示词文件路径
            
        返回:
            是否加载成功
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    self._prompts[prompt_key] = f.read().strip()
                return True
            else:
                print(f"提示词文件不存在: {file_path}")
                return False
        except Exception as e:
            print(f"加载提示词文件失败 {file_path}: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        参数:
            key: 配置键名，支持"parent.child"形式的嵌套键
            default: 默认值
            
        返回:
            配置值或默认值
        """
        keys = key.split('.')
        current = self._config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def get_prompt(self, prompt_key: str, default: str = "") -> str:
        """
        获取指定键的提示词
        
        参数:
            prompt_key: 提示词键名
            default: 默认值
            
        返回:
            提示词内容
        """
        return self._prompts.get(prompt_key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        参数:
            key: 配置键名，支持"parent.child"形式的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        current = self._config
        
        for i, k in enumerate(keys[:-1]):
            if not isinstance(current.get(k), dict):
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config.copy()
