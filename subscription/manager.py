import logging
from datetime import datetime
from typing import List, Optional
from .models import Subscription  # 从models导入，而非直接引用
from .storage import SubscriptionStorage

class SubscriptionManager:
    """订阅管理器，负责管理所有仓库订阅"""
    
    def __init__(self, config):
        self.storage = SubscriptionStorage(config)
        self.logger = logging.getLogger(__name__)
    
    def add_subscription(
        self, 
        repository: str, 
        subscriber: str,
        daily_updates: bool = True,
        weekly_report: bool = True
    ) -> bool:
        """添加订阅"""
        # 检查订阅是否已存在
        existing = self.get_subscription_by_repo(repository)
        
        if existing:
            # 如果订阅已存在，添加订阅者（如果不存在）
            if subscriber not in existing.subscribers:
                updated_subscribers = existing.subscribers + [subscriber]
                return self.storage.update_subscription(
                    existing.id,
                    repository,
                    updated_subscribers,
                    existing.last_checked,
                    existing.created_at,
                    daily_updates,
                    weekly_report
                )
            self.logger.info(f"Subscriber {subscriber} already subscribed to {repository}")
            return True
        
        # 创建新订阅
        return self.storage.add_subscription(
            repository,
            [subscriber],
            datetime.now(),  # 初始检查时间设为现在
            datetime.now(),
            daily_updates,
            weekly_report
        )
    
    def remove_subscription(self, subscription_id: int) -> bool:
        """移除整个订阅"""
        return self.storage.delete_subscription(subscription_id)
    
    def remove_subscriber(self, repository: str, subscriber: str) -> bool:
        """从订阅中移除特定订阅者"""
        sub = self.get_subscription_by_repo(repository)
        if not sub:
            return False
            
        if subscriber in sub.subscribers:
            new_subscribers = [s for s in sub.subscribers if s != subscriber]
            
            if not new_subscribers:
                # 如果没有订阅者了，删除整个订阅
                return self.remove_subscription(sub.id)
            else:
                # 否则更新订阅者列表
                return self.storage.update_subscription(
                    sub.id,
                    repository,
                    new_subscribers,
                    sub.last_checked,
                    sub.created_at,
                    sub.daily_updates,
                    sub.weekly_report
                )
        return True
    
    def get_all_subscriptions(self) -> List[Subscription]:
        """获取所有订阅"""
        return self.storage.get_all_subscriptions()
    
    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """通过ID获取订阅"""
        return self.storage.get_subscription(subscription_id)
    
    def get_subscription_by_repo(self, repository: str) -> Optional[Subscription]:
        """通过仓库名获取订阅"""
        for sub in self.get_all_subscriptions():
            if sub.repository == repository:
                return sub
        return None
    
    def get_subscriptions_for_subscriber(self, subscriber: str) -> List[Subscription]:
        """获取特定订阅者的所有订阅"""
        return [
            sub for sub in self.get_all_subscriptions()
            if subscriber in sub.subscribers
        ]
    
    def update_last_checked(self, subscription_id: int) -> bool:
        """更新订阅的最后检查时间"""
        sub = self.get_subscription(subscription_id)
        if not sub:
            return False
            
        return self.storage.update_subscription(
            sub.id,
            sub.repository,
            sub.subscribers,
            datetime.now(),  # 更新最后检查时间为现在
            sub.created_at,
            sub.daily_updates,
            sub.weekly_report
        )
