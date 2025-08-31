import logging
from core.scheduler import Scheduler
from core.config import Config
from core.logger import setup_logger
from subscription.manager import SubscriptionManager
from github.client import GitHubClient
from notification.manager import NotificationManager
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
    report_generator = ReportGenerator(github_client)
    report_generator.generate_repo_report("langchain-ai/langchain")

if __name__ == "__main__":
    main()
