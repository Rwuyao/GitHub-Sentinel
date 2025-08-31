import logging
from core.config import Config
from core.logger import setup_logger
from subscription.manager import SubscriptionManager
from github.client import GitHubClient

def main():
    # 初始化日志
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Starting GitHub Sentinel...")
    
    try:
        # 加载配置
        config = Config.from_env()
        logger.info("Configuration loaded successfully")
        
        # 初始化核心组件
        subscription_manager = SubscriptionManager(config)
        github_client = GitHubClient(config.github_token)
        
        # 示例：添加对langchain-ai/langchain的订阅
        langchain_repo = "langchain-ai/langchain"
        test_subscriber = "user@example.com"
        
        # 添加订阅（如果不存在）
        if not subscription_manager.get_subscription_by_repo(langchain_repo):
            success = subscription_manager.add_subscription(
                repository=langchain_repo,
                subscriber=test_subscriber,
                daily_updates=True,
                weekly_report=True
            )
            if success:
                logger.info(f"Successfully subscribed to {langchain_repo}")
            else:
                logger.error(f"Failed to subscribe to {langchain_repo}")
        
        # 这里可以添加更多初始化逻辑和任务调度
        
    except Exception as e:
        logger.error(f"Failed to start GitHub Sentinel: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
