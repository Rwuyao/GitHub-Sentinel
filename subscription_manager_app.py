import gradio as gr
import os
import json
import yaml
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
import pandas as pd
from subscription.manager import SubscriptionManager
from subscription.models import Subscription
from report.generator import AIReportGenerator
from core.config import Config
from github.client import GitHubClient
from core.logger import setup_logger

# 初始化配置和日志
config = Config.from_file("config/config.yaml")
setup_logger(
    log_level=config.get("logging.level", "INFO"),
    log_file=config.get("logging.file", "logs/app.log")
)

# 配置文件路径 - 明确设置订阅数据和报告的存储路径
SUBSCRIPTION_DATA_PATH = config.get("subscription.raw_data_dir", "data/raw_subscription_data")
AI_REPORTS_DIR = config.get("report.output_dir", "ai_reports")

# 初始化核心组件
github_token = os.getenv("GITHUB_TOKEN") or config.get("github_token")
github_client = GitHubClient(github_token=github_token) if github_token else None

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or config.get("deepseek.api_key")
report_generator = AIReportGenerator(config, deepseek_api_key)

# 初始化订阅管理器时指定订阅数据路径
sub_manager = SubscriptionManager(config, github_client) if github_client else None

# 全局状态存储
state = {
    "selected_subscriptions": [],
    "selected_report": None,
    "current_config": config.get_all() if hasattr(config, 'get_all') else {}
}

# 工具函数
def format_datetime(dt: datetime) -> str:
    """格式化日期时间为字符串"""
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "N/A"

def parse_date(date_str: str) -> Optional[date]:
    """解析日期字符串为date对象"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def load_subscriptions() -> pd.DataFrame:
    """加载订阅数据并转换为DataFrame，从subscription_data/subscriptions.json读取"""
    if not sub_manager:
        return pd.DataFrame(columns=["ID", "仓库", "订阅者", "创建时间", "状态", "最后处理时间"])
    
    subs = sub_manager.list_subscriptions()
    data = []
    for sub in subs:
        data.append({
            "ID": sub.id,
            "仓库": sub.repo_full_name,
            "订阅者": ", ".join(sub.subscribers),
            "创建时间": format_datetime(sub.created_at),
            "状态": "启用" if sub.enabled else "禁用",
            "最后处理时间": format_datetime(sub.last_processed_at)
        })
    return pd.DataFrame(data)

def load_reports() -> pd.DataFrame:
    """加载报告数据并转换为DataFrame，从ai_reports目录读取"""
    if not os.path.exists(AI_REPORTS_DIR):
        return pd.DataFrame(columns=["文件名", "订阅ID", "仓库", "日期", "生成时间"])
    
    reports = []
    for filename in os.listdir(AI_REPORTS_DIR):
        if filename.endswith("_ai_report.md"):
            parts = filename.split("_")
            if len(parts) >= 4 and parts[3].startswith("sub"):
                try:
                    date_str = parts[0]+parts[1]+parts[2]
                    sub_id = parts[3][3:]  # 从"sub123"提取"123"
                    repo_name = "_".join(parts[5:-2]).replace("_", "/")
                    
                    # 获取文件创建时间
                    file_path = os.path.join(AI_REPORTS_DIR, filename)
                    create_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    reports.append({
                        "文件名": filename,
                        "订阅ID": sub_id,
                        "仓库": repo_name,
                        "日期": date_str,
                        "生成时间": format_datetime(create_time)
                    })
                except Exception as e:
                    print(f"解析报告文件名失败 {filename}: {e}")
    
    return pd.DataFrame(reports)

def load_report_content(filename: str) -> str:
    """加载报告内容，从ai_reports目录读取"""
    if not filename:
        return "请选择一个报告"
    
    file_path = os.path.join(AI_REPORTS_DIR, filename)
    
    if not os.path.exists(file_path):
        return f"报告文件不存在: {filename}"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取报告失败: {str(e)}"

# 刷新功能
def refresh_subscriptions():
    """刷新订阅列表"""
    return load_subscriptions(), "订阅列表已刷新"

def refresh_reports():
    """刷新报告列表"""
    return load_reports(), "报告列表已刷新"

# 订阅管理页签功能
def add_subscription(repo_url: str, subscribers: str) -> Tuple[pd.DataFrame, str]:
    """添加新订阅，保存到subscription_data/subscriptions.json"""
    if not sub_manager:
        return load_subscriptions(), "GitHub客户端未初始化，请检查配置"
    
    if not repo_url.strip():
        return load_subscriptions(), "请输入仓库地址"
    
    # 从URL提取仓库全名（owner/repo）
    repo_parts = repo_url.strip().rstrip('/').split('/')
    if len(repo_parts) < 2:
        repo_full_name = repo_url.strip()
    else:
        repo_full_name = f"{repo_parts[-2]}/{repo_parts[-1]}"
    
    subscriber_list = [s.strip() for s in subscribers.split(',') if s.strip()]
    if not subscriber_list:
        return load_subscriptions(), "请至少输入一个订阅者邮箱"
    
    success, msg = sub_manager.add_subscription(
        repo_full_name=repo_full_name,
        subscribers=subscriber_list
    )
    
    return load_subscriptions(), msg

def delete_selected_subscriptions() -> Tuple[pd.DataFrame, str]:
    """删除选中的订阅，更新subscription_data/subscriptions.json"""
    if not sub_manager:
        return load_subscriptions(), "GitHub客户端未初始化，请检查配置"
    
    if not state["selected_subscriptions"]:
        return load_subscriptions(), "请先选择要删除的订阅"
    
    for sub_id in state["selected_subscriptions"]:
        sub_manager.delete_subscription(sub_id)
    
    # 清除选中状态
    state["selected_subscriptions"] = []
    return load_subscriptions(), "已删除选中的订阅"

def toggle_subscription_status() -> Tuple[pd.DataFrame, str]:
    """切换订阅状态（启用/禁用），更新subscription_data/subscriptions.json"""
    if not sub_manager or not state["selected_subscriptions"]:
        return load_subscriptions(), "请先选择一个订阅"
    
    # 只处理第一个选中的订阅
    sub_id = state["selected_subscriptions"][0]
    success, msg = sub_manager.toggle_subscription_status(int(sub_id))
    return load_subscriptions(), msg

def on_subscription_select(evt: gr.SelectData) -> str:
    """处理订阅选择事件，实现多选功能"""
    if evt is None:
        state["selected_subscriptions"] = []
        return "未选择任何订阅"
    
    # 获取选中的订阅ID
    df = load_subscriptions()
    if evt.index[0] < len(df):
        sub_id = df.iloc[evt.index[0]]["ID"]
        # 切换选中状态（添加/移除）
        if sub_id in state["selected_subscriptions"]:
            state["selected_subscriptions"].remove(sub_id)
        else:
            state["selected_subscriptions"].append(sub_id)
    
    return f"已选择 {len(state['selected_subscriptions'])} 个订阅"

# 报告管理页签功能
def on_report_select(evt: gr.SelectData) -> Tuple[str, str]:
    """处理报告选择事件"""
    if evt is None:
        state["selected_report"] = None
        return "请选择一个报告", ""
    
    df = load_reports()
    if evt.index[0] < len(df):
        filename = df.iloc[evt.index[0]]["文件名"]
        state["selected_report"] = filename
        content = load_report_content(filename)
        return filename, content
    
    return "未选择任何报告", ""

def generate_reports(sub_id: str, start_date_str: str, end_date_str: str) -> Tuple[pd.DataFrame, str]:
    """生成报告，保存到ai_reports目录"""
    if not sub_manager or not report_generator:
        return load_reports(), "初始化失败，请检查配置"
    
    if not sub_id or not sub_id.isdigit():
        return load_reports(), "请输入有效的订阅ID"
    
    # 解析日期
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    
    if not start_date or not end_date:
        return load_reports(), "日期格式错误，请使用YYYY-MM-DD格式"
    
    # 验证日期范围（最大1个月）
    if start_date >= end_date:
        return load_reports(), "开始日期必须早于结束日期"
    
    if (end_date - start_date).days > 31:
        return load_reports(), "日期范围不能超过1个月"
    
    # 转换为datetime
    start_time = datetime.combine(start_date, datetime.min.time())
    end_time = datetime.combine(end_date, datetime.max.time())
    
    # 处理订阅数据
    sub_id_int = int(sub_id)
    success, msg, file_paths = sub_manager.process_single_subscription(
        sub=next((s for s in sub_manager.list_subscriptions() if s.id == sub_id_int), None),
        custom_time_start=start_time,
        custom_time_end=end_time,
        avoid_duplicate=True
    )
    
    if not success:
        return load_reports(), f"数据处理失败: {msg}"
    
    # 生成AI报告，指定输出目录为ai_reports
    success_count, total_count, report_paths = report_generator.generate_subscription_report(
                    sub_id=sub_id_int,
                    start_time=start_time,
                    end_time=end_time
                )
    
    return load_reports(), f"报告生成完成: 成功 {success_count}"

# 配置管理页签功能
def save_config(config_data: Dict) -> str:
    """保存配置信息"""
    try:
        # 更新全局配置
        for key, value in config_data.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    config.set(f"{key}.{subkey}", subvalue)
            else:
                config.set(key, value)
        
        # 更新状态中的配置数据
        state["current_config"] = config.get_all() if hasattr(config, 'get_all') else config_data.copy()
        
        # 保存到文件
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)
        
        # 重新初始化相关组件，确保使用新的路径配置
        global github_client, sub_manager, report_generator
        
        github_token = config.get("github_token") or os.getenv("GITHUB_TOKEN")
        github_client = GitHubClient(github_token=github_token) if github_token else None
        
        deepseek_api_key = config.get("deepseek.api_key") or os.getenv("DEEPSEEK_API_KEY")
        report_generator = AIReportGenerator(config, deepseek_api_key)
        
        sub_manager = SubscriptionManager(config, github_client, data_path=SUBSCRIPTION_DATA_PATH) if github_client else None
        
        return "配置保存成功"
    except Exception as e:
        return f"配置保存失败: {str(e)}"

# 创建Gradio界面
def create_interface():
    with gr.Blocks(title="GitHub订阅管理系统") as app:
        gr.Markdown("# GitHub订阅管理系统")
        
        with gr.Tabs():
            # 第一个页签：订阅管理
            with gr.Tab("订阅管理"):
                gr.Markdown("## 订阅列表")
                gr.Markdown("数据存储路径: subscription_data/subscriptions.json")
                gr.Markdown("提示：点击行进行选择/取消选择，可多选")
                
                with gr.Row():
                    with gr.Column(scale=3):
                        sub_table = gr.Dataframe(
                            value=load_subscriptions(),
                            headers=["ID", "仓库", "订阅者", "创建时间", "状态", "最后处理时间"],
                            interactive=True,
                            row_count=10
                        )
                        
                        sub_status = gr.Textbox(label="状态", value="请选择订阅")
                        
                        # 添加手动刷新按钮
                        refresh_sub_btn = gr.Button("刷新订阅列表")
                    
                    with gr.Column(scale=1):
                        repo_url = gr.Textbox(label="仓库地址或全名(owner/repo)")
                        subscribers = gr.Textbox(label="订阅者邮箱(逗号分隔)")
                        add_btn = gr.Button("新增订阅")
                        
                        delete_btn = gr.Button("删除选中订阅", variant="stop")
                        
                        toggle_btn = gr.Button("切换选中订阅状态")
            
            # 第二个页签：报告管理
            with gr.Tab("报告管理"):
                gr.Markdown("## 报告列表")
                gr.Markdown("报告存储路径: ai_reports/")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        report_table = gr.Dataframe(
                            value=load_reports(),
                            headers=["文件名", "订阅ID", "仓库", "日期", "生成时间"],
                            interactive=True,
                            row_count=10
                        )
                        
                        # 添加手动刷新按钮
                        refresh_report_btn = gr.Button("刷新报告列表")
                        
                        with gr.Accordion("生成新报告", open=False):
                            sub_id_input = gr.Textbox(label="订阅ID")
                            
                            # 使用文本输入替代DatePicker
                            today = date.today().strftime("%Y-%m-%d")
                            last_month = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
                            
                            start_date_input = gr.Textbox(
                                label="开始日期 (YYYY-MM-DD)",
                                value=last_month
                            )
                            end_date_input = gr.Textbox(
                                label="结束日期 (YYYY-MM-DD)",
                                value=today
                            )
                            
                            generate_btn = gr.Button("生成报告", variant="primary")
                            generate_status = gr.Textbox(label="生成状态")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("## 报告内容")
                        report_filename = gr.Textbox(label="报告名称", interactive=False)
                        report_content = gr.Textbox(label="报告内容", lines=20, interactive=False)
            
            # 第三个页签：配置管理
            with gr.Tab("配置管理"):
                gr.Markdown("## 系统配置")
                
                config_json = gr.JSON(value=state["current_config"], label="配置内容")
                save_config_btn = gr.Button("保存配置", variant="primary")
                config_status = gr.Textbox(label="配置状态")
        
        # 设置事件监听
        # 订阅管理
        sub_table.select(
            fn=on_subscription_select,
            outputs=sub_status
        )
        
        add_btn.click(
            fn=add_subscription,
            inputs=[repo_url, subscribers],
            outputs=[sub_table, sub_status]
        )
        
        delete_btn.click(
            fn=delete_selected_subscriptions,
            outputs=[sub_table, sub_status]
        )
        
        toggle_btn.click(
            fn=toggle_subscription_status,
            outputs=[sub_table, sub_status]
        )
        
        # 订阅列表刷新
        refresh_sub_btn.click(
            fn=refresh_subscriptions,
            outputs=[sub_table, sub_status]
        )
        
        # 报告管理
        report_table.select(
            fn=on_report_select,
            outputs=[report_filename, report_content]
        )
        
        generate_btn.click(
            fn=generate_reports,
            inputs=[sub_id_input, start_date_input, end_date_input],
            outputs=[report_table, generate_status]
        )
        
        # 报告列表刷新
        refresh_report_btn.click(
            fn=refresh_reports,
            outputs=[report_table, generate_status]
        )
        
        # 配置管理
        save_config_btn.click(
            fn=save_config,
            inputs=[config_json],
            outputs=[config_status]
        )
    
    return app

# 运行应用
if __name__ == "__main__":
    app = create_interface()
    app.launch(debug=True)
