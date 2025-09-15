import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from .models import Subscription
from github.client import GitHubClient
from core.config import Config

# 配置日志
logger = logging.getLogger(__name__)

class SubscriptionManager:
    """订阅管理器，处理GitHub仓库订阅和数据获取"""
    
    def __init__(self, config: Config, github_client: GitHubClient, data_path: str):
        """
        初始化订阅管理器
        
        参数:
            config: 配置对象
            github_client: GitHub客户端
            data_path: 订阅数据存储路径
        """
        self.config = config
        self.github_client = github_client
        self.data_path = data_path
        
        # 配置原始数据目录
        self.raw_data_dir = "data/raw_subscription_data"
        os.makedirs(self.raw_data_dir, exist_ok=True)
        
        # 加载现有订阅
        self.subscriptions = self.load_subscriptions()
    
    def load_subscriptions(self) -> List[Subscription]:
        """从JSON文件加载订阅数据"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                subscriptions = []
                for item in data:
                    # 解析日期时间
                    created_at = datetime.fromisoformat(item["created_at"]) if item.get("created_at") else datetime.now()
                    last_processed_at = datetime.fromisoformat(item["last_processed_at"]) if item.get("last_processed_at") else None
                    custom_time_start = datetime.fromisoformat(item["custom_time_start"]) if item.get("custom_time_start") else None
                    custom_time_end = datetime.fromisoformat(item["custom_time_end"]) if item.get("custom_time_end") else None
                    
                    sub = Subscription(
                        id=item["id"],
                        repo_full_name=item["repo_full_name"],
                        subscribers=item["subscribers"],
                        created_at=created_at,
                        time_range_type=item.get("time_range_type", "daily"),
                        custom_time_start=custom_time_start,
                        custom_time_end=custom_time_end,
                        enabled=item.get("enabled", True),
                        last_processed_at=last_processed_at
                    )
                    subscriptions.append(sub)
                
                logger.info(f"从 {self.data_path} 加载了 {len(subscriptions)} 个订阅")
                return subscriptions
            else:
                logger.info(f"订阅数据文件不存在，将创建新文件: {self.data_path}")
                return []
                
        except Exception as e:
            logger.error(f"加载订阅失败: {str(e)}")
            return []
    
    def save_subscriptions(self) -> bool:
        """保存订阅数据到JSON文件"""
        try:
            # 准备序列化数据
            data = []
            for sub in self.subscriptions:
                item = {
                    "id": sub.id,
                    "repo_full_name": sub.repo_full_name,
                    "subscribers": sub.subscribers,
                    "created_at": sub.created_at.isoformat(),
                    "time_range_type": sub.time_range_type,
                    "enabled": sub.enabled,
                    "last_processed_at": sub.last_processed_at.isoformat() if sub.last_processed_at else None
                }
                
                # 添加可选的自定义时间范围
                if sub.custom_time_start:
                    item["custom_time_start"] = sub.custom_time_start.isoformat()
                if sub.custom_time_end:
                    item["custom_time_end"] = sub.custom_time_end.isoformat()
                
                data.append(item)
            
            # 保存到文件
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(self.subscriptions)} 个订阅到 {self.data_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存订阅失败: {str(e)}")
            return False
    
    def list_subscriptions(self) -> List[Subscription]:
        """获取所有订阅列表"""
        return self.subscriptions.copy()
    
    def add_subscription(self, repo_full_name: str, subscribers: List[str], 
                         time_range_type: str = "daily") -> Tuple[bool, str]:
        """
        添加新订阅
        
        参数:
            repo_full_name: 仓库全名 (owner/repo)
            subscribers: 订阅者邮箱列表
            time_range_type: 时间范围类型 ("daily" 或 "custom")
            
        返回:
            操作是否成功, 状态消息
        """
        try:
            # 检查仓库是否存在
            if not self.github_client.repo_exists(repo_full_name):
                return False, f"仓库不存在: {repo_full_name}"
            
            # 生成新ID
            new_id = max((sub.id for sub in self.subscriptions), default=0) + 1
            
            # 创建新订阅
            new_sub = Subscription(
                id=new_id,
                repo_full_name=repo_full_name,
                subscribers=subscribers,
                created_at=datetime.now(),
                time_range_type=time_range_type,
                enabled=True
            )
            
            # 添加并保存
            self.subscriptions.append(new_sub)
            if self.save_subscriptions():
                return True, f"成功添加订阅 (ID: {new_id})"
            else:
                return False, "添加订阅失败，无法保存数据"
                
        except Exception as e:
            logger.error(f"添加订阅失败: {str(e)}")
            return False, f"添加订阅失败: {str(e)}"
    
    def delete_subscription(self, sub_id: int) -> Tuple[bool, str]:
        """删除指定ID的订阅"""
        global subscriptions
        original_count = len(self.subscriptions)
        self.subscriptions = [sub for sub in self.subscriptions if sub.id != sub_id]
        
        if len(self.subscriptions) < original_count:
            if self.save_subscriptions():
                return True, f"已删除ID为 {sub_id} 的订阅"
            else:
                return False, "删除订阅失败，无法保存数据"
        else:
            return False, f"未找到ID为 {sub_id} 的订阅"
    
    def toggle_subscription_status(self, sub_id: int) -> Tuple[bool, str]:
        """切换订阅的启用/禁用状态"""
        for sub in self.subscriptions:
            if sub.id == sub_id:
                sub.enabled = not sub.enabled
                if self.save_subscriptions():
                    status = "启用" if sub.enabled else "禁用"
                    return True, f"订阅ID {sub_id} 已{status}"
                else:
                    return False, "切换状态失败，无法保存数据"
        
        return False, f"未找到ID为 {sub_id} 的订阅"
    
    def process_single_subscription(self, sub: Subscription, 
                                   custom_time_start: Optional[datetime] = None,
                                   custom_time_end: Optional[datetime] = None,
                                   avoid_duplicate: bool = True) -> Tuple[bool, str, List[str]]:
        """
        处理单个订阅，获取指定时间范围的GitHub数据
        
        参数:
            sub: 订阅对象
            custom_time_start: 自定义开始时间（覆盖订阅设置）
            custom_time_end: 自定义结束时间（覆盖订阅设置）
            avoid_duplicate: 是否避免重复处理（如果原始数据已存在则跳过）
            
        返回:
            操作是否成功, 状态消息, 生成的原始数据文件路径列表
        """
        if not sub.enabled:
            return False, f"订阅 {sub.id} 已禁用，跳过处理", []
            
        try:
            # 确定时间范围
            start_time, end_time, time_key = self._get_time_range(
                sub, custom_time_start, custom_time_end
            )
            
            # 构建原始数据文件名
            repo_safe_name = sub.repo_full_name.replace("/", "_")
            raw_data_filename = f"{time_key}_sub{sub.id}_{repo_safe_name}_raw_data.json"
            raw_data_path = os.path.join(self.raw_data_dir, raw_data_filename)
            
            # 检查是否已存在原始数据，如果存在且需要避免重复则跳过
            if avoid_duplicate and os.path.exists(raw_data_path):
                logger.info(f"原始数据 {raw_data_filename} 已存在，跳过数据获取")
                # 不更新最后处理时间，因为没有获取新数据
                return True, f"原始数据 {raw_data_filename} 已存在，跳过", [raw_data_path]
            
            # 获取GitHub数据
            logger.info(f"开始获取 {sub.repo_full_name} 的数据 ({start_time} 至 {end_time})")
            
            # 调用GitHub客户端获取各类数据
            data = {
                "repo_full_name": sub.repo_full_name,
                "subscription_id": sub.id,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "type": sub.time_range_type
                },
                "issues": self.github_client.get_recent_issues(
                    sub.repo_full_name, start_time, end_time
                ),
                "pull_requests": self.github_client.get_recent_pull_requests(
                    sub.repo_full_name, start_time, end_time
                ),
                "processed_at": datetime.now().isoformat()
            }
            
            # 保存原始数据
            with open(raw_data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 更新订阅的最后处理时间
            sub.last_processed_at = datetime.now()
            self.save_subscriptions()
            
            logger.info(f"成功获取并保存 {sub.repo_full_name} 的数据到 {raw_data_filename}")
            return True, f"成功处理订阅 {sub.id}", [raw_data_path]
            
        except Exception as e:
            logger.error(f"处理订阅 {sub.id} 失败: {str(e)}")
            return False, f"处理订阅失败: {str(e)}", []
    
    def _get_time_range(self, sub: Subscription, 
                       custom_start: Optional[datetime] = None,
                       custom_end: Optional[datetime] = None) -> Tuple[datetime, datetime, str]:
        """
        确定时间范围和时间关键字
        
        返回:
            开始时间, 结束时间, 时间关键字(用于文件名)
        """
        # 如果提供了自定义时间范围，则使用它
        if custom_start and custom_end:
            start_time = custom_start
            end_time = custom_end
            # 生成时间关键字 (例如: 20250901-20250910)
            time_key = f"{start_time.strftime('%Y%m%d')}-{end_time.strftime('%Y%m%d')}"
            return start_time, end_time, time_key
        
        # 否则使用订阅的时间范围设置
        if sub.time_range_type == "daily":
            # 默认为昨天的时间范围
            end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(days=1)
            time_key = start_time.strftime("%Y%m%d")  # 例如: 20250910
        elif sub.time_range_type == "custom" and sub.custom_time_start and sub.custom_time_end:
            start_time = sub.custom_time_start
            end_time = sub.custom_time_end
            time_key = f"{start_time.strftime('%Y%m%d')}-{end_time.strftime('%Y%m%d')}"
        else:
            # 默认使用昨天的时间范围
            end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(days=1)
            time_key = start_time.strftime("%Y%m%d")
        
        return start_time, end_time, time_key
