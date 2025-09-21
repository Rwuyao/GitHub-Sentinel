import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from hackernews.hackernews_crawler import HackerNewsCrawler
from llm.deepseek import DeepSeekClient
from utils.markdown_converter import MarkdownConverter
from core.config import Config

# 配置日志
logger = logging.getLogger("hackernews-llm-report")

class HackerNewsLLMTrendReporter:
    """结合大模型分析的HackerNews技术趋势报告生成器"""
    
    def __init__(self, 
                 deepseek_api_key: str,
                 config: Config,
                 max_items: int = 10):
        """
        初始化报告生成器
        
        参数:
            config: 配置对象
            max_items: 分析的热点数量
        """
        self.config = config
        self.output_dir = config.get("report.hackernews.output_dir", "data/hackernews")
        self.max_items = max_items
        
        # 初始化组件
        self.crawler = HackerNewsCrawler(max_items=max_items)
        self.llm_client = DeepSeekClient(api_key=deepseek_api_key,
            config=config)
        self.md_converter = MarkdownConverter()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_report(self, 
                       save_raw: bool = True,
                       filter_tech: bool = True) -> Tuple[bool, str, str]:
        """
        生成技术趋势报告
        
        参数:
            save_raw: 是否保存原始数据
            filter_tech: 是否只分析技术相关内容
            
        返回:
            成功标志, 报告Markdown内容, 报告HTML内容
        """
        try:
            # 1. 获取最新热点
            logger.info("开始获取HackerNews热点数据")
            stories = self.crawler.get_latest_stories()
            if not stories:
                logger.error("没有获取到有效热点数据，无法生成报告")
                return False, "", ""
            
            # 2. 筛选技术相关内容
            if filter_tech:
                stories = self.crawler.filter_tech_related(stories)
                if not stories:
                    logger.error("没有筛选出技术相关的热点内容")
                    return False, "", ""
            
            # 3. 保存原始数据
            if save_raw:
                raw_data_path = os.path.join(
                    self.output_dir, 
                    f"hackernews_raw_{datetime.now().strftime('%Y%m%d')}.json"
                )
                with open(raw_data_path, "w", encoding="utf-8") as f:
                    json.dump(stories, f, ensure_ascii=False, indent=2)
                logger.info(f"原始数据已保存至: {raw_data_path}")
            
            # 4. 调用大模型分析热点趋势
            logger.info("调用大模型分析技术趋势...")
            llm_analysis = self.llm_client.analyze_hackernews_trends(stories)
            if not llm_analysis:
                logger.error("大模型分析失败，无法生成报告")
                return False, "", ""
            
            # 5. 生成结构化报告
            md_content = self._format_report(llm_analysis, len(stories))
            
            # 6. 转换为HTML
            html_content = self.md_converter.convert(md_content)
            
            # 7. 保存报告
            report_filename = f"hackernews_tech_trend_{datetime.now().strftime('%Y%m%d')}.md"
            report_path = os.path.join(self.output_dir, report_filename)
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            logger.info(f"技术趋势报告生成成功: {report_path}")
            return True, md_content, html_content
            
        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            return False, "", ""
    
    def _format_report(self, llm_analysis: str, total_stories: int) -> str:
        """格式化报告内容"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 报告头部
        report_header = f"""# HackerNews 技术热点趋势报告 ({current_date})

本报告基于HackerNews最新{total_stories}条技术相关热点，通过AI分析生成。
报告反映了当前技术社区的热门话题、讨论焦点和发展趋势。

---

"""
        
        # 报告尾部
        report_footer = f"""

---

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据来源: HackerNews 最新热点
分析模型: {self.llm_client.model}
"""
        
        # 组合完整报告
        return report_header + llm_analysis + report_footer

# 示例用法
if __name__ == "__main__":
    # 加载配置
    config = Config.from_file("config.yaml")
    
    # 初始化报告生成器
    reporter = HackerNewsLLMTrendReporter(
        config=config,
        output_dir="reports/hackernews_llm",
        max_items=50
    )
    
    # 生成报告
    success, md_content, html_content = reporter.generate_report(
        save_raw=True,
        filter_tech=True
    )
    
    if success:
        # 发送邮件示例
        from utils.qq_email_sender import QQEmailSender
        
        email_sender = QQEmailSender(
            sender_email=config.get("email.sender"),
            auth_code=config.get("email.auth_code")
        )
        
        email_sender.send_html_email(
            recipients=config.get("email.recipients", []),
            subject=f"HackerNews技术趋势报告 {datetime.now().strftime('%Y-%m-%d')}",
            html_content=html_content
        )
