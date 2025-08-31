import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict
from .manager import Subscription

class SubscriptionStorage:
    """订阅存储管理器，支持内存存储和JSON文件存储"""
    
    def __init__(self, config, storage_type: str = "json"):
        """
        初始化存储管理器
        
        Args:
            config: 配置对象，需包含存储路径等信息
            storage_type: 存储类型，"memory" 或 "json"
        """
        self.logger = logging.getLogger(__name__)
        self.storage_type = storage_type
        self.subscriptions: Dict[int, Subscription] = {}
        self.next_id = 1  # 用于生成新订阅的ID
        
        # 配置JSON存储
        if storage_type == "json":
            self.storage_path = config.storage_path
            self._load_from_json()
        else:
            self.storage_path = None
            self.logger.info("使用内存存储订阅信息")

    def _get_next_id(self) -> int:
        """获取下一个可用的订阅ID"""
        current_id = self.next_id
        self.next_id += 1
        return current_id
    
    def _convert_to_dict(self, subscription: Subscription) -> Dict:
        """将Subscription对象转换为可序列化的字典"""
        return {
            "id": subscription.id,
            "repository": subscription.repository,
            "subscribers": subscription.subscribers,
            "last_checked": subscription.last_checked.isoformat(),
            "created_at": subscription.created_at.isoformat(),
            "daily_updates": subscription.daily_updates,
            "weekly_report": subscription.weekly_report
        }
    
    def _convert_from_dict(self, data: Dict) -> Subscription:
        """从字典转换为Subscription对象"""
        return Subscription(
            id=data["id"],
            repository=data["repository"],
            subscribers=data["subscribers"],
            last_checked=datetime.fromisoformat(data["last_checked"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            daily_updates=data["daily_updates"],
            weekly_report=data["weekly_report"]
        )
    
    def _save_to_json(self) -> None:
        """将所有订阅保存到JSON文件"""
        if self.storage_type != "json" or not self.storage_path:
            return
            
        try:
            # 转换所有订阅为字典列表
            data = [self._convert_to_dict(sub) for sub in self.subscriptions.values()]
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # 写入文件
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"已将 {len(data)} 个订阅保存到 {self.storage_path}")
        except Exception as e:
            self.logger.error(f"保存订阅到JSON文件失败: {str(e)}")
    
    def _load_from_json(self) -> None:
        """从JSON文件加载订阅"""
        if not self.storage_path or not os.path.exists(self.storage_path):
            self.logger.info(f"订阅文件 {self.storage_path} 不存在，将创建新文件")
            return
            
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                
            # 清空现有订阅
            self.subscriptions.clear()
            
            # 加载所有订阅
            for item in data:
                sub = self._convert_from_dict(item)
                self.subscriptions[sub.id] = sub
                
                # 更新下一个ID
                if sub.id >= self.next_id:
                    self.next_id = sub.id + 1
                    
            self.logger.info(f"从 {self.storage_path} 加载了 {len(self.subscriptions)} 个订阅")
        except Exception as e:
            self.logger.error(f"从JSON文件加载订阅失败: {str(e)}")
    
    def add_subscription(
        self, 
        repository: str, 
        subscribers: List[str],
        last_checked: datetime,
        created_at: datetime,
        daily_updates: bool = True,
        weekly_report: bool = True
    ) -> bool:
        """添加新订阅"""
        try:
            sub_id = self._get_next_id()
            subscription = Subscription(
                id=sub_id,
                repository=repository,
                subscribers=subscribers,
                last_checked=last_checked,
                created_at=created_at,
                daily_updates=daily_updates,
                weekly_report=weekly_report
            )
            
            self.subscriptions[sub_id] = subscription
            
            # 如果是JSON存储，保存到文件
            if self.storage_type == "json":
                self._save_to_json()
                
            self.logger.info(f"添加新订阅: {repository} (ID: {sub_id})")
            return True
        except Exception as e:
            self.logger.error(f"添加订阅失败: {str(e)}")
            return False
    
    def update_subscription(
        self, 
        sub_id: int,
        repository: str, 
        subscribers: List[str],
        last_checked: datetime,
        created_at: datetime,
        daily_updates: bool = True,
        weekly_report: bool = True
    ) -> bool:
        """更新现有订阅"""
        if sub_id not in self.subscriptions:
            self.logger.warning(f"订阅ID {sub_id} 不存在，无法更新")
            return False
            
        try:
            self.subscriptions[sub_id] = Subscription(
                id=sub_id,
                repository=repository,
                subscribers=subscribers,
                last_checked=last_checked,
                created_at=created_at,
                daily_updates=daily_updates,
                weekly_report=weekly_report
            )
            
            # 如果是JSON存储，保存到文件
            if self.storage_type == "json":
                self._save_to_json()
                
            self.logger.info(f"更新订阅: {repository} (ID: {sub_id})")
            return True
        except Exception as e:
            self.logger.error(f"更新订阅失败: {str(e)}")
            return False
    
    def delete_subscription(self, sub_id: int) -> bool:
        """删除订阅"""
        if sub_id not in self.subscriptions:
            self.logger.warning(f"订阅ID {sub_id} 不存在，无法删除")
            return False
            
        try:
            repository = self.subscriptions[sub_id].repository
            del self.subscriptions[sub_id]
            
            # 如果是JSON存储，保存到文件
            if self.storage_type == "json":
                self._save_to_json()
                
            self.logger.info(f"删除订阅: {repository} (ID: {sub_id})")
            return True
        except Exception as e:
            self.logger.error(f"删除订阅失败: {str(e)}")
            return False
    
    def get_subscription(self, sub_id: int) -> Optional[Subscription]:
        """通过ID获取订阅"""
        return self.subscriptions.get(sub_id)
    
    def get_all_subscriptions(self) -> List[Subscription]:
        """获取所有订阅"""
        return list(self.subscriptions.values())
    