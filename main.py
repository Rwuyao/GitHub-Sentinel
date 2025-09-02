import logging
import argparse
from datetime import datetime, timedelta
from core.config import Config, generate_default_config
from core.logger import setup_logger
from github.update_summarizer import GitHubAIReportGenerator

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="GitHub仓库AI总结工具")
    parser.add_argument("--repo", required=True, help="GitHub仓库全名 (格式: owner/repo)")
    parser.add_argument("--days", type=int, default=7, help="时间范围（天），默认7天")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--generate-config", action="store_true", help="生成默认配置文件")
    args = parser.parse_args()
    
    # 生成默认配置文件（如果需要）
    if args.generate_config:
        generate_default_config(args.config)
        return
    
    try:
        # 加载配置
        config = Config.from_file("config.yaml")
        
        # 初始化日志
        setup_logger(
            log_level=config.get_log_level(),
            log_file=config.get("logging.file")
        )
        logger = logging.getLogger(__name__)
        logger.info("GitHub仓库AI总结工具启动")
        
        # 验证必要配置
        github_token = config.get("github_token")
        deepseek_api_key = config.get("deepseek.api_key")
        
        if not github_token:
            logger.error("配置中未找到github_token，请检查配置文件")
            return
            
        if not deepseek_api_key:
            logger.error("配置中未找到deepseek.api_key，请检查配置文件")
            return
        
        # 计算时间范围
        since = datetime.now() - timedelta(days=args.days)
        time_range_desc = f"最近{args.days}天"
        
        # 初始化报告生成器
        report_generator = GitHubAIReportGenerator(
            github_token=github_token,
            deepseek_api_key=deepseek_api_key,
            config=config
        )
        
        # 生成报告
        report_path = report_generator.generate_ai_enhanced_report(
            repo_full_name=args.repo,
            since=since,
            time_range_desc=time_range_desc
        )
        
        if report_path:
            logger.info(f"报告生成成功: {report_path}")
        else:
            logger.error("报告生成失败")
            
    except Exception as e:
        logging.error(f"程序运行出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
