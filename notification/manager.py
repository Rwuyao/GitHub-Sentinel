from typing import List, Dict
import logging
from .base import NotificationProvider
from .email import EmailNotification
from .slack import SlackNotification
from core.config import Config

class NotificationManager:
    """通知管理器，协调所有通知方式"""
    
    def __init__(self, config: Config):
        self.logger = logging.getLogger(__name__)
        self.providers: List[NotificationProvider] = []
        
        # 初始化所有通知提供者
        self._init_providers(config)
        
    def _init_providers(self, config: Config):
        """初始化所有可用的通知提供者"""
        notification_providers = config.get("notifications.notification_providers", "")
        
        # 添加邮件通知
        if "email" in notification_providers:
            self.providers.append(EmailNotification(config))
            
        # 添加Slack通知
        if "slack" in notification_providers:
            self.providers.append(SlackNotification(config))
            
        # 可以在这里添加其他通知方式，如Teams、Telegram等
        
        self.logger.info(f"已初始化 {len(self.providers)} 种通知方式")
    
    def send_notification(self, recipients: List[str], subject: str, content: str, provider_types: List[str] = None) -> bool:
        """
        发送通知
        
        Args:
            recipients: 接收者列表
            subject: 通知主题
            content: 通知内容
            provider_types: 指定发送方式，如["email", "slack"]，None表示使用所有启用的方式
            
        Returns:
            是否至少有一种方式发送成功
        """
        if not self.providers:
            self.logger.warning("没有可用的通知方式，无法发送通知")
            return False
            
        success = False
        
        for provider in self.providers:
            # 检查是否启用
            if not provider.is_enabled():
                continue
                
            # 检查是否在指定的提供者类型中
            if provider_types and provider.__class__.__name__.lower() not in [t.lower() for t in provider_types]:
                continue
                
            # 发送通知
            if isinstance(provider, SlackNotification):
                # Slack通常通过webhook指定频道，忽略recipients
                provider.send([], subject, content)
                success = True
            else:
                if provider.send(recipients, subject, content):
                    success = True
                    
        return success
