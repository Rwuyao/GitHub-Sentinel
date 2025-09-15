import os
import json
import time
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from core.config import Config

# 配置日志
logger = logging.getLogger(__name__)

# 简单的原始数据解析器替代类
class SimpleDataParser:
    """简单的数据解析器，用于处理原始数据"""
    
    def parse(self, raw_data: Dict) -> Dict:
        """解析原始数据为结构化信息"""
        if not raw_data:
            return {}
            
        # 提取基本信息
        repo_full_name = raw_data.get('repo_full_name', '未知仓库')
        
        # 提取时间范围
        start_time = raw_data.get('time_range', {}).get('start', '未知')
        end_time = raw_data.get('time_range', {}).get('end', '未知')
        time_range = f"{start_time} 至 {end_time}"
        
        # 统计提交信息
        commits = raw_data.get('commits', [])
        commit_count = len(commits)
        contributors = list(set(commit.get('author', {}).get('name', '未知') for commit in commits))
        
        # 统计Issues信息
        issues = raw_data.get('issues', [])
        open_issues = len([i for i in issues if i.get('state') == 'open'])
        closed_issues = len([i for i in issues if i.get('state') == 'closed'])
        
        # 统计PR信息
        pull_requests = raw_data.get('pull_requests', [])
        open_prs = len([pr for pr in pull_requests if pr.get('state') == 'open'])
        merged_prs = len([pr for pr in pull_requests if pr.get('merged', False)])
        
        # 构建结构化数据
        return {
            'repo_full_name': repo_full_name,
            'time_range': time_range,
            'commit_stats': {
                'total': commit_count,
                'contributors': contributors,
                'top_contributor': contributors[0] if contributors else '无'
            },
            'issue_stats': {
                'total': len(issues),
                'open': open_issues,
                'closed': closed_issues
            },
            'pr_stats': {
                'total': len(pull_requests),
                'open': open_prs,
                'merged': merged_prs
            }
        }

class AIReportGenerator:
    """AI报告生成器，用于处理原始数据并生成AI总结报告"""
    
    def __init__(self, config: Config, api_key: str, default_output_dir: str = "ai_reports",
                 raw_data_dir: str = "data/raw_subscription_data"):
        """
        初始化AI报告生成器
        
        参数:
            config: 配置对象
            api_key: AI模型API密钥
            default_output_dir: 默认报告输出目录
            raw_data_dir: 原始数据目录，默认为"data/raw_subscription_data"
        """
        self.config = config
        self.api_key = api_key
        self.default_output_dir = default_output_dir
        self.raw_data_dir = raw_data_dir  # 设置原始数据目录为指定路径
        
        # 确保目录存在
        os.makedirs(self.default_output_dir, exist_ok=True)
        os.makedirs(self.raw_data_dir, exist_ok=True)  # 确保原始数据目录存在
        
        # 使用简单的数据解析器
        self.data_parser = SimpleDataParser()
        
        # 从配置加载AI模型参数
        self.model_name = config.get("deepseek.model", "deepseek-chat")
        self.temperature = config.get("deepseek.temperature", 0.7)
        self.max_tokens = config.get("deepseek.max_tokens", 2048)
        
        # 初始化AI客户端
        self._init_ai_client()
    
    def _init_ai_client(self):
        """初始化AI模型客户端"""
        self.ai_client = None
        if self.api_key:
            try:
                logger.info(f"初始化AI客户端，模型: {self.model_name}")
                self.ai_client = {"initialized": True, "model": self.model_name}
            except Exception as e:
                logger.error(f"AI客户端初始化失败: {str(e)}")
                self.ai_client = None
    
    def generate_all_reports(self, output_dir: Optional[str] = None) -> Tuple[int, int, List[str]]:
        """生成所有未处理原始数据的AI报告"""
        # 确定输出目录
        output_dir = output_dir or self.default_output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 检查原始数据目录是否存在
        if not os.path.exists(self.raw_data_dir):
            logger.warning(f"原始数据目录不存在: {self.raw_data_dir}，已自动创建空目录")
            os.makedirs(self.raw_data_dir, exist_ok=True)
            return 0, 0, []
        
        # 筛选出未生成报告的原始数据文件
        raw_files = [f for f in os.listdir(self.raw_data_dir) if f.endswith("_raw_data.json")]
        report_files = [f.replace("_raw_data.json", "_ai_report.md") for f in raw_files]
        
        success_count = 0
        total_count = 0
        report_paths = []
        
        # 为每个原始数据文件生成报告
        for raw_file, report_file in zip(raw_files, report_files):
            total_count += 1
            raw_path = os.path.join(self.raw_data_dir, raw_file)
            report_path = os.path.join(output_dir, report_file)
            
            # 跳过已存在的报告
            if os.path.exists(report_path):
                logger.info(f"报告已存在，跳过: {report_path}")
                report_paths.append(report_path)
                success_count += 1
                continue
            
            # 生成报告
            try:
                logger.info(f"开始生成报告: {report_file}")
                success = self.generate_report(raw_path, report_path)
                
                if success:
                    success_count += 1
                    report_paths.append(report_path)
                    logger.info(f"报告生成成功: {report_path}")
                else:
                    logger.error(f"报告生成失败: {report_path}")
            
            except Exception as e:
                logger.error(f"生成报告时发生错误 {raw_file}: {str(e)}")
                continue
            
            # 避免API调用过于频繁
            time.sleep(1)
        
        return success_count, total_count, report_paths
    
    def generate_report(self, raw_data_path: str, report_path: str) -> bool:
        """为单个原始数据文件生成AI报告"""
        if not self.ai_client:
            logger.error("AI客户端未初始化，无法生成报告")
            return False
        
        # 解析原始数据
        try:
            with open(raw_data_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            # 解析数据为结构化信息
            parsed_data = self.data_parser.parse(raw_data)
            if not parsed_data:
                logger.error(f"无法解析原始数据: {raw_data_path}")
                return False
                
        except Exception as e:
            logger.error(f"解析原始数据失败 {raw_data_path}: {str(e)}")
            return False
        
        # 构建AI提示词
        prompt = self._build_prompt(parsed_data)
        
        # 调用AI生成报告
        try:
            ai_response = self._call_ai_api(prompt)
            if not ai_response:
                return False
                
        except Exception as e:
            logger.error(f"调用AI API失败: {str(e)}")
            return False
        
        # 保存报告
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(ai_response)
            return True
            
        except Exception as e:
            logger.error(f"保存报告失败 {report_path}: {str(e)}")
            return False
    
    def _build_prompt(self, parsed_data: Dict) -> str:
        """构建用于生成报告的AI提示词"""
        repo_name = parsed_data.get("repo_full_name", "未知仓库")
        time_range = parsed_data.get("time_range", "未知时间范围")
        
        prompt = f"""请分析以下GitHub仓库({repo_name})在{time_range}的活动数据，生成一份简洁明了的报告。
报告应包含以下几个部分:
1. 概述：简要总结这段时间的主要活动
2. 代码提交：总结提交次数、主要贡献者和关键变更
3. 问题(Issues)：总结新增、关闭的问题数量及主要类型
4. 拉取请求(Pull Requests)：总结新增、合并的PR数量及主要内容
5. 讨论要点：指出这段时间值得关注的重要讨论或决策

请使用简洁的文本格式输出，使用标题和列表突出重点，语言简洁专业。

原始数据摘要：
{json.dumps(parsed_data, ensure_ascii=False, indent=2)[:2000]}
"""
        return prompt
    
    def _call_ai_api(self, prompt: str) -> Optional[str]:
        """调用AI API生成报告内容（模拟实现）"""
        # 模拟API调用延迟
        time.sleep(1)
        
        # 模拟返回的报告内容
        mock_report = f"""# GitHub仓库活动报告
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. 概述
这是一份模拟的AI生成报告，基于提供的原始数据。在报告时间范围内，仓库有活跃的开发活动，包括多次代码提交和问题讨论。

## 2. 代码提交
- 提交次数：{len(prompt) % 10 + 1}次
- 主要贡献者：模拟用户
- 关键变更：修复了若干bug，添加了新功能

## 3. 问题(Issues)
- 新增：{len(prompt) % 5 + 1}个
- 关闭：{len(prompt) % 3 + 1}个
- 主要类型：功能请求、bug报告

## 4. 拉取请求(Pull Requests)
- 新增：{len(prompt) % 4 + 1}个
- 合并：{len(prompt) % 2 + 1}个
- 主要内容：功能实现、代码优化

## 5. 讨论要点
- 团队讨论了未来的开发计划
- 针对某个关键问题达成了共识
"""
        return mock_report