import logging
from core.scheduler import Scheduler
from core.config import Config
from core.logger import setup_logger
from subscription.manager import SubscriptionManager
from github.client import GitHubClient
from notification.base import NotificationManager
from report.generator import ReportGenerator

def main():
    # 初始化配置
    config = Config()
    
    # 初始化日志
    setup_logger(config.get_log_level())
    logger = logging.getLogger(__name__)
    logger.info("Starting GitHub Sentinel...")
    
    # 初始化核心组件
    subscription_manager = SubscriptionManager(config)
    github_client = GitHubClient(config)
    notification_manager = NotificationManager(config)
    report_generator = ReportGenerator()
    
    # 设置调度器
    scheduler = Scheduler(config)
    
    # 添加每日任务
    if config.run_daily():
        scheduler.add_daily_task(
            lambda: run_update_check(
                subscription_manager, 
                github_client, 
                report_generator, 
                notification_manager
            )
        )
    
    # 添加每周任务
    if config.run_weekly():
        scheduler.add_weekly_task(
            lambda: run_weekly_report(
                subscription_manager, 
                github_client, 
                report_generator, 
                notification_manager
            )
        )
    
    # 启动调度器
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down GitHub Sentinel...")
        scheduler.shutdown()

def run_update_check(subscription_manager, github_client, report_generator, notification_manager):
    """执行每日更新检查"""
    logger = logging.getLogger(__name__)
    logger.info("Running daily update check...")
    
    # 获取所有订阅
    subscriptions = subscription_manager.get_all_subscriptions()
    
    # 检查每个仓库的更新
    for sub in subscriptions:
        try:
            updates = github_client.get_recent_updates(
                sub.repository, 
                since=sub.last_checked
            )
            
            if updates:
                # 生成报告
                report = report_generator.generate_update_report(sub.repository, updates)
                
                # 发送通知
                notification_manager.send_notifications(
                    sub.subscribers, 
                    f"Updates in {sub.repository}", 
                    report
                )
                
                # 更新最后检查时间
                subscription_manager.update_last_checked(sub.id)
                
        except Exception as e:
            logger.error(f"Error checking updates for {sub.repository}: {str(e)}")

def run_weekly_report(subscription_manager, github_client, report_generator, notification_manager):
    """生成每周报告"""
    logger = logging.getLogger(__name__)
    logger.info("Generating weekly report...")
    
    # 获取所有订阅
    subscriptions = subscription_manager.get_all_subscriptions()
    
    # 按订阅者分组生成报告
    subscriber_reports = {}
    
    for sub in subscriptions:
        try:
            weekly_updates = github_client.get_weekly_updates(sub.repository)
            
            if weekly_updates:
                for subscriber in sub.subscribers:
                    if subscriber not in subscriber_reports:
                        subscriber_reports[subscriber] = []
                    subscriber_reports[subscriber].append(
                        (sub.repository, weekly_updates)
                    )
                
        except Exception as e:
            logger.error(f"Error generating weekly report for {sub.repository}: {str(e)}")
    
    # 发送每周报告
    for subscriber, repo_updates in subscriber_reports.items():
        report = report_generator.generate_weekly_report(repo_updates)
        notification_manager.send_notifications(
            [subscriber], 
            "GitHub Sentinel Weekly Report", 
            report
        )

if __name__ == "__main__":
    main()
