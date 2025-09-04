import click
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from core.config import Config
from core.logger import setup_logger
from github.client import GitHubClient
from subscription.manager import SubscriptionManager
from report.generator import AIReportGenerator
from scheduler.background_scheduler import BackgroundScheduler
from typing import Tuple, List, Optional  # 添加这行导入

# 初始化全局组件
def init_global_components() -> Tuple[Config, GitHubClient, SubscriptionManager, AIReportGenerator]:
    config = Config.from_file("config.yaml")
    setup_logger(log_level=config.get_log_level(), log_file=config.get("logging.file"))
    
    # 初始化GitHub客户端（优先环境变量）
    github_token = os.getenv("GITHUB_TOKEN") or config.get("github_token")
    if not github_token:
        click.echo("错误：未配置GitHub Token（环境变量GITHUB_TOKEN或config.yaml）")
        sys.exit(1)
    github_client = GitHubClient(
        github_token=github_token,
        timeout=config.get("api_timeout", 10),
        retries=config.get("api_retries", 3)
    )
    
    # 初始化订阅管理器
    sub_manager = SubscriptionManager(config, github_client)
    
    # 初始化AI报告生成器
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or config.get("deepseek.api_key")
    if not deepseek_api_key:
        click.echo("警告：未配置DeepSeek API Key，AI总结功能不可用")
    report_generator = AIReportGenerator(
        config=config,
        deepseek_api_key=deepseek_api_key
    )
    
    return config, github_client, sub_manager, report_generator

# 交互式命令组
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """GitHub Sentinel - 交互式GitHub仓库订阅与总结工具"""
    # 初始化组件并传入上下文
    if ctx.invoked_subcommand is None:
        # 无命令时进入交互模式
        click.echo("=" * 50)
        click.echo("GitHub Sentinel 交互式工具（输入 'help' 查看命令，'exit' 退出）")
        click.echo("=" * 50)
        
        # 初始化组件
        try:
            config, github_client, sub_manager, report_generator = init_global_components()
            scheduler = BackgroundScheduler(config, sub_manager, report_generator)
        except Exception as e:
            click.echo(f"初始化失败: {str(e)}")
            return
        
        # 交互循环
        while True:
            cmd = click.prompt("\n请输入命令", type=str).strip().lower()
            if cmd == "exit":
                click.echo("退出工具...")
                scheduler.stop()
                break
            elif cmd == "help":
                show_help()
            else:
                # 解析命令并执行
                execute_interactive_command(cmd, sub_manager, report_generator, scheduler)
    else:
        # 命令模式（直接执行单命令）
        ctx.obj = init_global_components()

# 帮助信息
def show_help():
    help_text = """
可用命令列表：
1. 订阅管理：
   - add-sub <仓库名> <订阅者邮箱1,邮箱2> [--time-type=custom --start=2024-01-01 --end=2024-01-02]
     示例：add-sub langchain-ai/langchain user1@test.com,user2@test.com
   - del-sub <订阅ID>
     示例：del-sub 1
   - list-subs [仓库名]
     示例：list-subs 或 list-subs pytorch/pytorch

2. 订阅处理：
   - process-sub <订阅ID> [--start=2024-01-01 --end=2024-01-02]
     示例：process-sub 1 （处理前一天数据）或 process-sub 1 --start=2024-05-01 --end=2024-05-02
   - process-all [--start=2024-01-01 --end=2024-01-02]
     示例：process-all （处理所有订阅的前一天数据）

3. 报告生成：
   - generate-report <订阅ID> [--start=2024-01-01 --end=2024-01-02]
     示例：generate-report 1 （基于原始数据生成AI总结报告）
   - generate-all-reports
     示例：generate-all-reports （生成所有未总结的原始数据报告）

4. 定时任务：
   - start-scheduler：启动后台定时任务（每日自动处理订阅）
   - stop-scheduler：停止后台定时任务
   - status-scheduler：查看定时任务状态

5. 其他：
   - help：查看帮助信息
   - exit：退出工具
"""
    click.echo(help_text)

# 解析并执行交互式命令
def execute_interactive_command(cmd: str, sub_manager: SubscriptionManager, 
                               report_generator: AIReportGenerator,
                               scheduler: BackgroundScheduler):
    parts = cmd.split()
    if not parts:
        return
    
    try:
        # 1. 新增订阅
        if parts[0] == "add-sub":
            if len(parts) < 3:
                click.echo("用法：add-sub <仓库名> <订阅者邮箱1,邮箱2> [--time-type=custom --start=2024-01-01 --end=2024-01-02]")
                return
            repo_full_name = parts[1]
            subscribers = parts[2].split(",")
            # 解析可选参数
            time_type = "daily"
            custom_start = None
            custom_end = None
            for i in range(3, len(parts)):
                if parts[i].startswith("--time-type="):
                    time_type = parts[i].split("=")[1]
                elif parts[i].startswith("--start="):
                    custom_start = datetime.strptime(parts[i].split("=")[1], "%Y-%m-%d")
                elif parts[i].startswith("--end="):
                    custom_end = datetime.strptime(parts[i].split("=")[1], "%Y-%m-%d")
            # 执行新增
            success, msg = sub_manager.add_subscription(
                repo_full_name=repo_full_name,
                subscribers=subscribers,
                time_range_type=time_type,
                custom_time_start=custom_start,
                custom_time_end=custom_end
            )
            click.echo(msg)
        
        # 2. 删除订阅
        elif parts[0] == "del-sub":
            if len(parts) < 2:
                click.echo("用法：del-sub <订阅ID>")
                return
            sub_id = int(parts[1])
            success, msg = sub_manager.delete_subscription(sub_id)
            click.echo(msg)
        
        # 3. 查看订阅
        elif parts[0] == "list-subs":
            repo_full_name = parts[1] if len(parts) > 1 else None
            subs = sub_manager.list_subscriptions(repo_full_name)
            if not subs:
                click.echo("暂无订阅数据")
                return
            # 格式化输出
            click.echo(f"\n订阅列表（共 {len(subs)} 个）：")
            click.echo("-" * 120)
            click.echo(f"{'ID':<4} {'仓库名':<30} {'订阅者':<30} {'时间类型':<10} {'状态':<8} {'最后处理时间':<20}")
            click.echo("-" * 120)
            for sub in subs:
                subscribers_str = ",".join(sub.subscribers[:2]) + ("..." if len(sub.subscribers) > 2 else "")
                status = "启用" if sub.enabled else "禁用"
                last_processed = sub.last_processed_at.strftime("%Y-%m-%d %H:%M") if sub.last_processed_at else "未处理"
                click.echo(f"{sub.id:<4} {sub.repo_full_name:<30} {subscribers_str:<30} {sub.time_range_type:<10} {status:<8} {last_processed:<20}")
        
        # 4. 处理单个订阅
        elif parts[0] == "process-sub":
            if len(parts) < 2:
                click.echo("用法：process-sub <订阅ID> [--start=2024-01-01 --end=2024-01-02]")
                return
            sub_id = int(parts[1])
            # 解析时间参数
            custom_start = None
            custom_end = None
            for i in range(2, len(parts)):
                if parts[i].startswith("--start="):
                    custom_start = datetime.strptime(parts[i].split("=")[1], "%Y-%m-%d")
                elif parts[i].startswith("--end="):
                    custom_end = datetime.strptime(parts[i].split("=")[1], "%Y-%m-%d")
            # 查找订阅
            subs = sub_manager.list_subscriptions()
            sub = next((s for s in subs if s.id == sub_id), None)
            if not sub:
                click.echo(f"未找到订阅ID: {sub_id}")
                return
            # 执行处理
            success, msg, raw_path = sub_manager.process_single_subscription(sub, custom_start, custom_end)
            click.echo(msg)
            if raw_path:
                click.echo(f"原始数据文件：{raw_path}")
        
        # 5. 处理所有订阅
        elif parts[0] == "process-all":
            # 解析时间参数
            custom_start = None
            custom_end = None
            for i in range(1, len(parts)):
                if parts[i].startswith("--start="):
                    custom_start = datetime.strptime(parts[i].split("=")[1], "%Y-%m-%d")
                elif parts[i].startswith("--end="):
                    custom_end = datetime.strptime(parts[i].split("=")[1], "%Y-%m-%d")
            # 执行处理
            results = sub_manager.process_all_subscriptions(custom_start, custom_end)
            click.echo(f"\n处理完成（共 {len(results)} 个订阅）：")
            for i, (success, msg, raw_path) in enumerate(results, 1):
                click.echo(f"{i}. {msg}")
                if raw_path:
                    click.echo(f"   原始文件：{raw_path}")
        
        # 6. 生成单个报告
        elif parts[0] == "generate-report":
            if len(parts) < 2:
                click.echo("用法：generate-report <订阅ID> [--start=2024-01-01 --end=2024-01-02]")
                return
            sub_id = int(parts[1])
            # 生成报告
            success, msg, report_path = report_generator.generate_subscription_report(sub_id)
            click.echo(msg)
            if report_path:
                click.echo(f"报告文件：{report_path}")
        
        # 7. 生成所有报告
        elif parts[0] == "generate-all-reports":
            success_count, total_count, report_paths = report_generator.generate_all_reports()
            click.echo(f"生成完成：共 {total_count} 个原始数据文件，成功 {success_count} 个")
            for path in report_paths:
                click.echo(f"- {path}")
        
        # 8. 定时任务：启动
        elif parts[0] == "start-scheduler":
            if scheduler.is_running():
                click.echo("定时任务已在运行")
                return
            scheduler.start()
            click.echo("定时任务已启动（每日自动处理前一天订阅并生成报告）")
        
        # 9. 定时任务：停止
        elif parts[0] == "stop-scheduler":
            if not scheduler.is_running():
                click.echo("定时任务未在运行")
                return
            scheduler.stop()
            click.echo("定时任务已停止")
        
        # 10. 定时任务：状态
        elif parts[0] == "status-scheduler":
            if scheduler.is_running():
                click.echo("定时任务状态：运行中（下次执行时间：{scheduler.get_next_run_time()}）")
            else:
                click.echo("定时任务状态：已停止")
        
        else:
            click.echo(f"未知命令：{parts[0]}（输入 'help' 查看可用命令）")
    
    except Exception as e:
        click.echo(f"命令执行失败: {str(e)}")

# 命令模式支持（直接执行单命令，如 python main.py add-sub ...）
@cli.command()
@click.argument("repo_full_name")
@click.argument("subscribers")
@click.option("--time-type", default="daily", help="时间类型：daily（默认）/ custom")
@click.option("--start", help="自定义开始时间（格式：2024-01-01）")
@click.option("--end", help="自定义结束时间（格式：2024-01-02）")
@click.pass_obj
def add_sub(obj, repo_full_name, subscribers, time_type, start, end):
    """新增订阅：add-sub <仓库名> <订阅者邮箱1,邮箱2>"""
    config, github_client, sub_manager, _ = obj
    custom_start = datetime.strptime(start, "%Y-%m-%d") if start else None
    custom_end = datetime.strptime(end, "%Y-%m-%d") if end else None
    success, msg = sub_manager.add_subscription(
        repo_full_name=repo_full_name,
        subscribers=subscribers.split(","),
        time_range_type=time_type,
        custom_time_start=custom_start,
        custom_time_end=custom_end
    )
    click.echo(msg)

# 其他命令模式（del-sub、list-subs等）类似，此处省略，可参考add_sub实现

if __name__ == "__main__":
    cli()