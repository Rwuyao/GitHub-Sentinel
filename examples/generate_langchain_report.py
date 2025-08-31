import os
from core.config import Config
from core.logger import setup_logger
from github.client import GitHubClient
from report.generator import ReportGenerator

def main():
    # 初始化
    setup_logger()
    
    # 从环境变量获取GitHub令牌
    if not os.getenv("GITHUB_TOKEN"):
        print("请设置GITHUB_TOKEN环境变量")
        return
    
    # 加载配置
    config = Config.from_env()
    
    # 初始化客户端和报告生成器
    github_client = GitHubClient(config.github_token)
    report_generator = ReportGenerator(github_client)
    
    # 生成langchain-ai/langchain仓库的报告
    repo = "langchain-ai/langchain"
    report = report_generator.generate_repo_report(repo)
    
    # 打印报告
    print(report)
    
    # 保存报告到文件
    report_generator.save_report(report, repo)

if __name__ == "__main__":
    main()
