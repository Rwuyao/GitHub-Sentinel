import os
import json
import logging
from datetime import datetime
from typing import List, Tuple, Optional
from core.config import Config
from llm.deepseek import DeepSeekClient

class AIReportGenerator:
    """增强版报告生成器（读取订阅原始数据，生成AI总结）"""
    def __init__(self, config: Config, deepseek_api_key: Optional[str]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.raw_data_dir = config.get("subscription.raw_data_dir", "data/raw_subscription_data")
        self.report_output_dir = config.get("report.output_dir", "ai_reports")
        os.makedirs(self.report_output_dir, exist_ok=True)
        
        # 初始化大模型客户端
        self.deepseek_client = DeepSeekClient(
            api_key=deepseek_api_key,
            config=config
        ) if deepseek_api_key else None

    def load_subscription_raw_data(self, sub_id: Optional[int] = None) -> List[dict]:
        """加载订阅原始数据（可选过滤订阅ID）"""
        raw_data_list = []
        if not os.path.exists(self.raw_data_dir):
            return raw_data_list
        
        # 遍历所有原始数据文件
        for filename in os.listdir(self.raw_data_dir):
            if not filename.endswith("_raw.json"):
                continue
            file_path = os.path.join(self.raw_data_dir, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 过滤订阅ID（如果指定）
                if sub_id and data["subscription_id"] != sub_id:
                    continue
                raw_data_list.append(data)
            except Exception as e:
                self.logger.error(f"加载原始数据 {filename} 失败: {str(e)}")
        
        # 按时间排序（最新在前）
        return sorted(raw_data_list, key=lambda x: x["generated_at"], reverse=True)

    def generate_single_raw_report(self, raw_data: dict) -> Tuple[bool, str, Optional[str]]:
        """基于单条原始数据生成AI总结报告"""
        if not self.deepseek_client:
            return False, "未配置DeepSeek API Key，无法生成AI总结", None
        
        try:
            # 1. 提取原始数据
            sub_id = raw_data["subscription_id"]
            repo_full_name = raw_data["repo_full_name"]
            time_range = raw_data["time_range"]
            repo_info = raw_data["data"]["repo_info"]
            releases = raw_data["data"]["releases"]
            commits = raw_data["data"]["commits"]
            prs = raw_data["data"]["pull_requests"]
            issues = raw_data["data"]["issues"]

            # 2. AI总结
            self.logger.info(f"生成订阅ID {sub_id}（{repo_full_name}）的AI总结...")
            summaries = {
                "releases": self.deepseek_client.summarize_releases(releases),
                "commits": self.deepseek_client.summarize_commits(commits),
                "issues_prs": self.deepseek_client.summarize_issues_prs(issues, prs)
            }

            # 3. 生成Markdown内容
            markdown_content = self._format_markdown(
                repo_info=repo_info,
                time_range=time_range,
                summaries=summaries,
                raw_data=raw_data["data"]
            )

            # 4. 保存报告
            start_date = datetime.fromisoformat(time_range["start"]).strftime("%Y%m%d")
            safe_repo_name = repo_full_name.replace("/", "_")
            report_filename = f"{start_date}_sub{sub_id}_{safe_repo_name}_ai_report.md"
            report_path = os.path.join(self.report_output_dir, report_filename)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            return True, f"报告生成成功", report_path
        except Exception as e:
            return False, f"报告生成失败: {str(e)}", None

    def generate_subscription_report(self, sub_id: int) -> Tuple[bool, str, Optional[str]]:
        """生成指定订阅ID的最新报告"""
        raw_data_list = self.load_subscription_raw_data(sub_id)
        if not raw_data_list:
            return False, f"未找到订阅ID {sub_id} 的原始数据", None
        
        # 处理最新的一条原始数据
        latest_raw_data = raw_data_list[0]
        return self.generate_single_raw_report(latest_raw_data)

    def generate_all_reports(self) -> Tuple[int, int, List[str]]:
        """生成所有未处理的原始数据报告（按时间排序）"""
        raw_data_list = self.load_subscription_raw_data()
        if not raw_data_list:
            return 0, 0, []
        
        success_count = 0
        report_paths = []
        for raw_data in raw_data_list:
            # 检查报告是否已存在
            start_date = datetime.fromisoformat(raw_data["time_range"]["start"]).strftime("%Y%m%d")
            sub_id = raw_data["subscription_id"]
            safe_repo_name = raw_data["repo_full_name"].replace("/", "_")
            report_filename = f"{start_date}_sub{sub_id}_{safe_repo_name}_ai_report.md"
            report_path = os.path.join(self.report_output_dir, report_filename)
            
            if os.path.exists(report_path):
                self.logger.info(f"报告已存在，跳过：{report_filename}")
                continue
            
            # 生成报告
            success, msg, path = self.generate_single_raw_report(raw_data)
            if success and path:
                success_count += 1
                report_paths.append(path)
        
        return success_count, len(raw_data_list), report_paths

    def _format_markdown(self, repo_info: dict, time_range: dict, summaries: dict, raw_data: dict) -> str:
        """格式化Markdown报告内容"""
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = datetime.fromisoformat(time_range["start"]).strftime("%Y-%m-%d %H:%M")
        end_time = datetime.fromisoformat(time_range["end"]).strftime("%Y-%m-%d %H:%M")

        # 报告头部
        md = [
            f"# 🤖 GitHub订阅AI总结报告",
            f"**仓库**: {repo_info.get('full_name', '未知')} [{repo_info.get('html_url', '')}]({repo_info.get('html_url', '')})",
            f"**订阅ID**: {raw_data.get('subscription_id', '未知')}",
            f"**时间范围**: {start_time} ~ {end_time}",
            f"**报告生成时间**: {generated_at}",
            "",
            "---",
            "",
            "## 📊 仓库基本信息",
            f"- 名称: {repo_info.get('name', '未知')}",
            f"- 描述: {repo_info.get('description', '无描述')}",
            f"- 星级: {repo_info.get('stargazers_count', 0)} ⭐",
            f"- 分支: {repo_info.get('forks_count', 0)} 🍴",
            f"- 最后更新: {repo_info.get('updated_at', '未知')[:10]}",
            "",
            "---",
            "",
            "## 📝 AI智能总结",
        ]

        # 各模块总结
        md.extend([
            "### 🔖 发布总结",
            summaries["releases"],
            "",
            "### 💻 开发提交总结",
            summaries["commits"],
            "",
            "### 📢 社区活动总结（Issues/PR）",
            summaries["issues_prs"],
            "",
            "---",
            "",
        ])

        # 原始数据预览
        md.append("## 🔍 原始数据预览（前5条）")
        
        # 发布预览
        if raw_data["releases"]:
            md.extend([
                "### 最新发布",
                "| 版本 | 发布时间 | 标题 |",
                "|------|----------|------|",
            ])
            for r in raw_data["releases"][:5]:
                md.append(f"| {r.get('tag_name', '未知')} | {r.get('published_at', '')[:10]} | {r.get('name', '')[:50]} |")
            md.append("")
        
        # 提交预览
        if raw_data["commits"]:
            md.extend([
                "### 最近提交",
                "| 哈希 | 作者 | 时间 | 信息 |",
                "|------|------|------|------|",
            ])
            for c in raw_data["commits"][:5]:
                sha = c.get('sha', '')[:7]
                msg = c.get('commit', {}).get('message', '').splitlines()[0][:50]
                md.append(f"| {sha} | {c.get('author', {}).get('login', '未知')} | {c.get('commit', {}).get('committer', {}).get('date', '')[:10]} | {msg} |")
            md.append("")

        return "\n".join(md)