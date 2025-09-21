import logging
import os
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict
from .models import Subscription
from .storage import SubscriptionStorage
from github.client import GitHubClient
from core.config import Config

class SubscriptionManager:
    """订阅管理核心类，支持处理连续日期范围内的所有数据"""
    
    def __init__(self, config: Config, github_client: GitHubClient):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.github_client = github_client
        self.storage = SubscriptionStorage(config)
        self.raw_data_dir = config.get("subscription.raw_data_dir", "data/raw_subscription_data")
        
        # 确保原始数据目录存在
        os.makedirs(self.raw_data_dir, exist_ok=True)
        
        # 默认时间范围：每日处理前一天数据（00:00 ~ 次日00:00）
        self.default_time_range = {
            "start": lambda: datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=1),
            "end": lambda: datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        }

    # 保持其他方法(add_subscription, delete_subscription等)不变...
    def add_subscription(self, 
                        repo_full_name: str, 
                        subscribers: List[str], 
                        time_range_type: str = "daily") -> Tuple[bool, str]:
        # 原始实现保持不变
        repo_info = self.github_client.get_repo_info(repo_full_name)
        if not repo_info:
            return False, f"仓库 {repo_full_name} 不存在或无权限访问"
        
        subs = self.storage.load_subscriptions()
        if any(sub.repo_full_name == repo_full_name for sub in subs):
            return False, f"仓库 {repo_full_name} 已在订阅列表中"
        
        new_sub = Subscription(
            id=self.storage.get_next_id(),
            repo_full_name=repo_full_name,
            subscribers=subscribers,
            created_at=datetime.now(),
            time_range_type=time_range_type,
            enabled=True
        )
        
        subs.append(new_sub)
        self.storage.save_subscriptions(subs)
        return True, f"订阅成功！订阅ID: {new_sub.id}（仓库: {repo_full_name}）"

    def delete_subscription(self, sub_id: int) -> Tuple[bool, str]:
        # 原始实现保持不变
        subs = self.storage.load_subscriptions()
        original_count = len(subs)
        subs = [sub for sub in subs if sub.id != sub_id]
        
        if len(subs) == original_count:
            return False, f"未找到订阅ID: {sub_id}"
        
        self.storage.save_subscriptions(subs)
        return True, f"订阅ID {sub_id} 已成功删除"

    def list_subscriptions(self, repo_full_name: Optional[str] = None) -> List[Subscription]:
        # 原始实现保持不变
        subs = self.storage.load_subscriptions()
        if repo_full_name:
            subs = [sub for sub in subs if sub.repo_full_name == repo_full_name]
        return sorted(subs, key=lambda x: x.id)

    def toggle_subscription_status(self, sub_id: int) -> Tuple[bool, str]:
        # 原始实现保持不变
        subs = self.storage.load_subscriptions()
        for sub in subs:
            if sub.id == sub_id:
                sub.enabled = not sub.enabled
                self.storage.save_subscriptions(subs)
                status = "启用" if sub.enabled else "禁用"
                return True, f"订阅ID {sub_id} 已{status}"
        return False, f"未找到订阅ID: {sub_id}"

    def get_subscription_time_range(self, sub: Subscription) -> Tuple[datetime, datetime]:
        # 原始实现保持不变
        if sub.time_range_type == "custom" and sub.custom_time_start and sub.custom_time_end:
            return sub.custom_time_start, sub.custom_time_end
        return self.default_time_range["start"](), self.default_time_range["end"]()

    def _is_duplicate_raw_data(self, sub: Subscription, start_date: date) -> bool:
        # 原始实现保持不变
        safe_repo_name = sub.repo_full_name.replace("/", "_")
        date_str = start_date.strftime("%Y%m%d")
        target_filename = f"{date_str}_sub{sub.id}_{safe_repo_name}_raw.json"
        return os.path.exists(os.path.join(self.raw_data_dir, target_filename))

    def _generate_date_list(self, start_date: date, end_date: date) -> List[date]:
        """
        生成从开始日期到结束日期的所有日期列表（包含两端）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            日期列表
        """
        date_list = []
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list

    def process_single_subscription(self, 
                                   sub: Subscription, 
                                   custom_time_start: Optional[datetime] = None,
                                   custom_time_end: Optional[datetime] = None,
                                   avoid_duplicate: bool = False) -> Tuple[bool, str, List[str]]:
        """
        处理单个订阅，确保处理时间范围内的所有日期
        
        关键改进：即使某一天数据已存在，仍会继续处理后续日期
        
        Args:
            sub: 订阅对象
            custom_time_start: 自定义开始时间
            custom_time_end: 自定义结束时间
            avoid_duplicate: 是否避免重复生成
            
        Returns:
            (是否成功, 提示信息, 原始数据文件路径列表)
        """
        # 检查订阅是否启用
        if not sub.enabled:
            return False, f"订阅ID {sub.id} 已禁用，跳过处理", []
        
        # 确定时间范围
        default_start, default_end = self.get_subscription_time_range(sub)
        start_time = custom_time_start or default_start
        end_time = custom_time_end or default_end
        
        # 确保时间带有时区信息
        start_time = self.github_client._ensure_utc_timezone(start_time)
        end_time = self.github_client._ensure_utc_timezone(end_time)
        
        # 验证时间范围有效性
        if start_time >= end_time:
            self.logger.info("开始时间必须早于结束时间")
            return False, "开始时间必须早于结束时间", []
        
        # 转换为日期对象（仅日期部分）
        start_date = start_time.date()
        end_date = end_time.date()
        
        # 生成所有需要处理的日期列表
        date_list = self._generate_date_list(start_date, end_date)
        total_days = len(date_list)
        
        self.logger.info(
            f"处理订阅ID {sub.id}（{sub.repo_full_name}），时间范围："
            f"{start_date} ~ {end_date}，共 {total_days} 天"
        )
        
        # 初始化统计变量
        success_count = 0
        skipped_count = 0
        failed_count = 0
        raw_file_paths = []
        error_messages = []

        # 遍历每个日期并处理
        for current_date in date_list:
            # 检查是否已存在该日期的数据
            if avoid_duplicate and self._is_duplicate_raw_data(sub, current_date):
                self.logger.info(f"日期 {current_date} 已存在数据，跳过")
                skipped_count += 1
                continue  # 跳过当前日期，但继续处理下一个日期

            # 为当前日期创建时间范围（当天00:00到次日00:00）
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = day_start + timedelta(days=1)
            
            # 确保时间带有时区信息
            day_start = self.github_client._ensure_utc_timezone(day_start)
            day_end = self.github_client._ensure_utc_timezone(day_end)

            try:
                # 获取GitHub数据
                repo_info = self.github_client.get_repo_info(sub.repo_full_name)
                releases = self.github_client.get_latest_releases(
                    sub.repo_full_name, 
                    start_time=day_start, 
                    end_time=day_end,
                    limit=500
                )
                prs = self.github_client.get_recent_pull_requests(
                    sub.repo_full_name, 
                    start_time=day_start, 
                    end_time=day_end,
                    limit=500
                )
                issues = self.github_client.get_recent_issues(
                    sub.repo_full_name, 
                    start_time=day_start, 
                    end_time=day_end,
                    limit=500
                )
            except Exception as e:
                error_msg = f"日期 {current_date} 获取数据失败: {str(e)}"
                self.logger.error(error_msg)
                failed_count += 1
                error_messages.append(error_msg)
                continue  # 获取数据失败，继续处理下一个日期

            # 准备原始数据
            raw_data = {
                "subscription_id": sub.id,
                "repo_full_name": sub.repo_full_name,
                "time_range": {
                    "start": day_start.isoformat(),
                    "end": day_end.isoformat()
                },
                "data": {
                    "repo_info": repo_info,
                    "releases": releases,
                    "pull_requests": prs,
                    "issues": issues
                },
                "generated_at": datetime.now().isoformat()
            }

            # 生成文件名并保存
            try:
                safe_repo_name = sub.repo_full_name.replace("/", "_")
                date_str = current_date.strftime("%Y%m%d")
                filename = f"{date_str}_sub{sub.id}_{safe_repo_name}_raw.json"
                raw_file_path = os.path.join(self.raw_data_dir, filename)

                with open(raw_file_path, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, ensure_ascii=False, indent=2)

                success_count += 1
                raw_file_paths.append(raw_file_path)
                self.logger.info(f"日期 {current_date} 数据处理成功")

            except Exception as e:
                error_msg = f"日期 {current_date} 保存数据失败: {str(e)}"
                self.logger.error(error_msg)
                failed_count += 1
                error_messages.append(error_msg)
                continue  # 保存失败，继续处理下一个日期

        # 更新订阅最后处理时间（如果有成功处理的日期）
        if success_count > 0:
            subs = self.storage.load_subscriptions()
            for s in subs:
                if s.id == sub.id:
                    s.last_processed_at = datetime.now()
                    break
            self.storage.save_subscriptions(subs)

        # 准备结果信息
        summary = (
            f"总天数: {total_days}, "
            f"成功: {success_count}, "
            f"已跳过: {skipped_count}, "
            f"失败: {failed_count}"
        )

        if success_count > 0 or skipped_count > 0:
            return True, f"处理完成。{summary}", raw_file_paths
        else:
            return False, f"处理失败。{summary} 错误: {'; '.join(error_messages[:3])}", raw_file_paths

    def process_all_subscriptions(self, 
                                 custom_time_start: Optional[datetime] = None,
                                 custom_time_end: Optional[datetime] = None,
                                 avoid_duplicate: bool = True) -> List[Tuple[bool, str, List[str]]]:
        """处理所有启用的订阅，返回多日期处理结果"""
        subs = self.list_subscriptions()
        results = []
        
        for sub in subs:
            if sub.enabled:
                res = self.process_single_subscription(
                    sub, 
                    custom_time_start=custom_time_start,
                    custom_time_end=custom_time_end,
                    avoid_duplicate=avoid_duplicate
                )
                results.append(res)
            else:
                self.logger.info("订阅ID {sub.id} 已禁用，未处理")
                results.append((False, f"订阅ID {sub.id} 已禁用，未处理", []))
        
        return results
    