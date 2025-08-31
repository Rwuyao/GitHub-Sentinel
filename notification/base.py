from abc import ABC, abstractmethod
from typing import List, Dict
import logging

class NotificationProvider(ABC):
    """通知提供者基类，所有通知方式都应实现此类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(f"notification.{self.__class__.__name__}")
        self.enabled = self.config.get("enabled", False)
        
    @abstractmethod
    def send(self, recipients: List[str], subject: str, content: str) -> bool:
        """
        发送通知
        
        Args:
            recipients: 接收者列表
            subject: 通知主题
            content: 通知内容
            
        Returns:
            是否发送成功
        """
        pass
        
    def is_enabled(self) -> bool:
        """检查当前通知方式是否启用"""
        return self.enabled
