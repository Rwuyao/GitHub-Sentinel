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
    github_client = GitHubClient(config.github_api_token)
    notification_manager = NotificationManager(config)
    report_generator = ReportGenerator(github_client)
    # 生成langchain仓库的最新报告
    report = report_generator.generate_repo_report("langchain-ai/langchain")

    # 保存报告到文件
    report_path = report_generator.save_report(report, "langchain-ai/langchain")
    print(f"报告已保存到: {report_path}")

if __name__ == "__main__":
    main()
