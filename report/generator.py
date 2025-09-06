import os
import json
import logging
from datetime import datetime, date, timezone
from typing import List, Tuple, Optional, Dict
from core.config import Config
from llm.deepseek import DeepSeekClient

class AIReportGenerator:
    """报告生成器：读取订阅原始数据，生成AI总结报告"""
    
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

    @staticmethod
    def _ensure_naive_datetime(dt: datetime) -> datetime:
        """确保datetime对象不包含时区信息（转为offset-naive）"""
        if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
            # 转换为UTC时间后移除时区信息
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    @staticmethod
    def _parse_iso_datetime(date_str: str) -> datetime:
        """解析ISO格式的时间字符串，返回无时区信息的datetime对象"""
        dt = datetime.fromisoformat(date_str)
        return AIReportGenerator._ensure_naive_datetime(dt)

    def load_subscription_raw_data(self, 
                                  sub_id: Optional[int] = None,
                                  start_time: Optional[datetime] = None,
                                  end_time: Optional[datetime] = None) -> List[dict]:
        """
        加载订阅原始数据（支持时间范围筛选）
        
        Args:
            sub_id: 可选，订阅ID过滤
            start_time: 可选，开始时间过滤
            end_time: 可选，结束时间过滤
            
        Returns:
            符合条件的原始数据列表
        """
        raw_data_list = []
        if not os.path.exists(self.raw_data_dir):
            return raw_data_list
        
        # 处理查询时间（确保无时区信息）
        query_start = self._ensure_naive_datetime(start_time) if start_time else None
        query_end = self._ensure_naive_datetime(end_time) if end_time else None
        
        # 遍历所有原始数据文件
        for filename in os.listdir(self.raw_data_dir):
            if not filename.endswith("_raw.json"):
                continue
            file_path = os.path.join(self.raw_data_dir, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 筛选订阅ID
                if sub_id is not None and data["subscription_id"] != sub_id:
                    continue
                
                # 解析数据时间范围（确保无时区信息）
                try:
                    data_start = self._parse_iso_datetime(data["time_range"]["start"])
                    data_end = self._parse_iso_datetime(data["time_range"]["end"])
                except Exception as e:
                    self.logger.warning(f"解析 {filename} 的时间范围失败: {str(e)}")
                    continue
                
                # 筛选时间范围
                if query_start and data_end < query_start:
                    continue
                if query_end and data_start > query_end:
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
            prs = raw_data["data"]["pull_requests"]
            issues = raw_data["data"]["issues"]

            # 2. AI总结
            self.logger.info(f"生成订阅ID {sub_id}（{repo_full_name}）的AI总结...")
            summaries = {
                "releases": self.deepseek_client.summarize_releases(releases),
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
            start_date = self._parse_iso_datetime(time_range["start"]).strftime("%Y%m%d")
            safe_repo_name = repo_full_name.replace("/", "_")
            report_filename = f"{start_date}_sub{sub_id}_{safe_repo_name}_ai_report.md"
            report_path = os.path.join(self.report_output_dir, report_filename)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            return True, f"报告生成成功", report_path
        except Exception as e:
            return False, f"报告生成失败: {str(e)}"

    def generate_subscription_report(self, 
                                    sub_id: int,
                                    start_time: Optional[datetime] = None,
                                    end_time: Optional[datetime] = None) -> Tuple[bool, str, Optional[str]]:
        """生成报告（支持时间范围，默认最新数据）"""
        # 加载符合条件的原始数据
        raw_data_list = self.load_subscription_raw_data(
            sub_id=sub_id,
            start_time=start_time,
            end_time=end_time
        )
        if not raw_data_list:
            return False, f"未找到订阅ID {sub_id} 的原始数据", None
        
        # 按时间范围生成报告（多份数据合并）
        if start_time and end_time:
            return self._generate_merged_report(raw_data_list, start_time, end_time)
        # 否则使用最新的单份数据
        return self.generate_single_raw_report(raw_data_list[0])

    def _generate_merged_report(self, raw_data_list: List[dict], start_time: datetime, end_time: datetime) -> Tuple[bool, str, Optional[str]]:
        """合并多个原始数据生成报告"""
        if not self.deepseek_client:
            return False, "未配置DeepSeek API Key", None
        
        try:
            # 合并数据
            merged_data = {
                "releases": [],
                "pull_requests": [],
                "issues": []
            }
            repo_info = raw_data_list[0]["data"]["repo_info"]
            for data in raw_data_list:
                merged_data["releases"].extend(data["data"]["releases"])
                merged_data["pull_requests"].extend(data["data"]["pull_requests"])
                merged_data["issues"].extend(data["data"]["issues"])
            
            # 去重（按ID）
            merged_data["releases"] = list({r["id"]: r for r in merged_data["releases"]}.values())
            merged_data["pull_requests"] = list({p["id"]: p for p in merged_data["pull_requests"]}.values())
            merged_data["issues"] = list({i["id"]: i for i in merged_data["issues"]}.values())

            # AI总结
            summaries = {
                "releases": self.deepseek_client.summarize_releases(merged_data["releases"]),
                "issues_prs": self.deepseek_client.summarize_issues_prs(
                    merged_data["issues"], 
                    merged_data["pull_requests"]
                )
            }

            # 生成报告
            start_str = self._ensure_naive_datetime(start_time).strftime("%Y%m%d")
            end_str = self._ensure_naive_datetime(end_time).strftime("%Y%m%d")
            safe_repo_name = repo_info["full_name"].replace("/", "_")
            report_filename = f"{start_str}_to_{end_str}_sub{raw_data_list[0]['subscription_id']}_{safe_repo_name}_ai_report.md"
            report_path = os.path.join(self.report_output_dir, report_filename)

            markdown_content = self._format_markdown(
                repo_info=repo_info,
                time_range={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                summaries=summaries,
                raw_data=merged_data
            )

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            return True, f"合并报告生成成功", report_path
        except Exception as e:
            return False, f"合并报告失败: {str(e)}", None

    def generate_all_reports(self) -> Tuple[int, int, List[str]]:
        """生成所有未处理的原始数据报告（按时间排序）"""
        raw_data_list = self.load_subscription_raw_data()
        if not raw_data_list:
            return 0, 0, []
        
        success_count = 0
        report_paths = []
        for raw_data in raw_data_list:
            # 检查报告是否已存在
            start_date = self._parse_iso_datetime(raw_data["time_range"]["start"]).strftime("%Y%m%d")
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
        start_time = self._parse_iso_datetime(time_range["start"]).strftime("%Y-%m-%d %H:%M")
        end_time = self._parse_iso_datetime(time_range["end"]).strftime("%Y-%m-%d %H:%M")

        # 报告头部
        md = [
            f"# 🤖 GitHub订阅AI总结报告",
            f"**仓库**: {repo_info.get('full_name', '未知')} [{repo_info.get('html_url', '')}]({repo_info.get('html_url', '')})",
            f"**时间范围**: {start_time} ~ {end_time}",
            f"**生成时间**: {generated_at}",
            "",
            "## 📊 仓库基本信息",
            f"- 名称: {repo_info.get('name', '未知')}",
            f"- 描述: {repo_info.get('description', '无描述')}",
            f"- 星级: {repo_info.get('stargazers_count', 0)} ⭐",
            f"- 分支: {repo_info.get('forks_count', 0)} 🍴",
            "",
            "---",
            "## 📝 AI智能总结",
        ]

        # 各模块总结
        md.extend([
            "### 🔖 发布总结",
            summaries["releases"] if summaries["releases"] else "该时间段内无发布记录",
            "",
            "### 📢 社区活动总结（Issues/PR）",
            summaries["issues_prs"] if summaries["issues_prs"] else "该时间段内无Issues和PR活动",
            "",
            "---",
            "",
        ])

        # 原始数据预览
        md.append("## 🔍 原始数据预览")
        
        # 发布预览
        if raw_data["releases"]:
            md.extend([
                "### 最新发布",
                "| 版本 | 发布时间 | 标题 |",
                "|------|----------|------|",
            ])
            for r in raw_data["releases"][:5]:
                publish_time = self._parse_iso_datetime(r.get('published_at')).strftime("%Y-%m-%d")
                md.append(f"| {r.get('tag_name', '未知')} | {publish_time} | {r.get('name', '')[:50]} |")
            md.append("")
        
        # PR预览
        if raw_data["pull_requests"]:
            md.extend([
                "### 最近PR",
                "| 编号 | 状态 | 标题 | 创建者 |",
                "|------|------|------|--------|",
            ])
            for pr in raw_data["pull_requests"][:5]:
                md.append(f"| #{pr.get('number')} | {pr.get('state')} | {pr.get('title', '')[:50]} | {pr.get('user', {}).get('login')} |")
            md.append("")

        # Issues预览
        if raw_data["issues"]:
            md.extend([
                "### 最近Issues",
                "| 编号 | 状态 | 标题 | 创建者 |",
                "|------|------|------|--------|",
            ])
            for issue in raw_data["issues"][:5]:
                md.append(f"| #{issue.get('number')} | {issue.get('state')} | {issue.get('title', '')[:50]} | {issue.get('user', {}).get('login')} |")
            md.append("")

        return "\n".join(md)
    