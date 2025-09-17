import click
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Tuple, List, Optional, Dict, Any
from core.config import Config
from core.logger import setup_logger
from github.client import GitHubClient
from subscription.manager import SubscriptionManager
from report.generator import AIReportGenerator
from scheduler.background_scheduler import BackgroundScheduler

def init_global_components() -> Tuple[Config, GitHubClient, SubscriptionManager, AIReportGenerator]:
    """初始化全局组件"""
    # 加载配置
    config = Config.from_file("config/config.yaml")
    
    # 初始化日志
    setup_logger(
        log_level=config.get("logging.level", "INFO"),
        log_file=config.get("logging.file", "logs/github-sentinel.log")
    )
    
    # 初始化GitHub客户端
    github_token = os.getenv("GITHUB_TOKEN") or config.get("github_token")
    if not github_token:
        click.echo("错误：未配置GitHub Token（请设置环境变量GITHUB_TOKEN或在config.yaml中配置）")
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
    report_generator = AIReportGenerator(
        config=config,
        deepseek_api_key=deepseek_api_key
    )
    
    return config, github_client, sub_manager, report_generator

def show_help():
    """显示帮助信息"""
    help_text = """
可用命令列表：

1. 订阅管理：
   - add-sub <仓库名> <订阅者邮箱1,邮箱2> [--time-type=custom --start=2024-01-01 --end=2024-01-02]
     示例：add-sub langchain-ai/langchain user1@test.com,user2@test.com
     说明：添加仓库订阅，支持每日更新或自定义时间范围

   - del-sub <订阅ID>
     示例：del-sub 1
     说明：通过ID删除订阅

   - list-subs [仓库名]
     示例：list-subs 或 list-subs pytorch/pytorch
     说明：查看所有订阅，可选指定仓库过滤

2. 订阅处理：
   - process-sub <订阅ID> [--start=2024-01-01 --end=2024-01-02]
     示例：process-sub 1 或 process-sub 1 --start=2024-05-01 --end=2024-05-02
     说明：立即处理指定订阅，默认处理前一天数据

   - process-all [--start=2024-01-01 --end=2024-01-02]
     示例：process-all
     说明：立即处理所有启用的订阅，自动按日期去重

3. 报告生成：
   - generate-report <订阅ID> [--start=2024-01-01 --end=2024-01-02]
     示例：generate-report 1 或 generate-report 1 --start=2024-05-01 --end=2024-05-07
     说明：生成报告，默认使用最新数据，指定时间则合并该范围数据

   - generate-all-reports
     示例：generate-all-reports
     说明：为所有未生成报告的原始数据生成AI总结

4. 定时任务：
   - start-scheduler [--background]
     示例：start-scheduler 或 start-scheduler --background
     说明：启动定时任务，默认前台运行，--background选项可后台运行

   - stop-scheduler
     示例：stop-scheduler
     说明：停止定时任务（包括后台进程）

   - status-scheduler
     示例：status-scheduler
     说明：查看定时任务运行状态

5. 其他：
   - help：显示此帮助信息
   - exit：退出工具
"""
    click.echo(help_text)

def parse_datetime_param(param: str) -> Optional[datetime]:
    """解析日期时间参数"""
    if not param:
        return None
    try:
        return datetime.strptime(param, "%Y-%m-%d")
    except ValueError:
        click.echo(f"错误：日期格式无效，请使用YYYY-MM-DD格式（输入：{param}）")
        return None

def execute_interactive_command(cmd: str, 
                               sub_manager: SubscriptionManager, 
                               report_generator: AIReportGenerator,
                               scheduler: BackgroundScheduler):
    """执行交互式命令"""
    parts = cmd.split()
    if not parts:
        return

    try:
        # 新增订阅
        if parts[0] == "add-sub":
            if len(parts) < 3:
                click.echo("用法：add-sub <仓库名> <订阅者邮箱1,邮箱2> [--time-type=custom --start=2024-01-01 --end=2024-01-02]")
                return
            
            repo_full_name = parts[1]
            subscribers = parts[2].split(",")
            time_type = "daily"

            # 解析可选参数
            for i in range(3, len(parts)):
                if parts[i].startswith("--time-type="):
                    time_type = parts[i].split("=")[1]

            success, msg = sub_manager.add_subscription(
                repo_full_name=repo_full_name,
                subscribers=subscribers,
                time_range_type=time_type
            )
            click.echo(msg)

        # 删除订阅
        elif parts[0] == "del-sub":
            if len(parts) < 2:
                click.echo("用法：del-sub <订阅ID>")
                return
            
            try:
                sub_id = int(parts[1])
                success, msg = sub_manager.delete_subscription(sub_id)
                click.echo(msg)
            except ValueError:
                click.echo("错误：订阅ID必须是数字")

        # 查看订阅
        elif parts[0] == "list-subs":
            repo_full_name = parts[1] if len(parts) > 1 else None
            subs = sub_manager.list_subscriptions(repo_full_name)
            
            if not subs:
                click.echo("暂无订阅数据")
                return

            # 格式化输出
            click.echo(f"\n订阅列表（共 {len(subs)} 个）：")
            click.echo("-" * 130)
            click.echo(f"{'ID':<4} {'仓库名':<30} {'订阅者':<30} {'时间类型':<10} {'状态':<8} {'最后处理时间':<20}")
            click.echo("-" * 130)
            
            for sub in subs:
                subscribers_str = ",".join(sub.subscribers[:2]) + ("..." if len(sub.subscribers) > 2 else "")
                status = "启用" if sub.enabled else "禁用"
                last_processed = sub.last_processed_at.strftime("%Y-%m-%d %H:%M") if sub.last_processed_at else "未处理"
                click.echo(f"{sub.id:<4} {sub.repo_full_name:<30} {subscribers_str:<30} {sub.time_range_type:<10} {status:<8} {last_processed:<20}")

        # 处理单个订阅
        elif parts[0] == "process-sub":
            if len(parts) < 2:
                click.echo("用法：process-sub <订阅ID> [--start=2024-01-01 --end=2024-01-02]")
                return
            
            try:
                sub_id = int(parts[1])
                custom_start = None
                custom_end = None

                # 解析时间参数
                for i in range(2, len(parts)):
                    if parts[i].startswith("--start="):
                        custom_start = parse_datetime_param(parts[i].split("=")[1])
                    elif parts[i].startswith("--end="):
                        custom_end = parse_datetime_param(parts[i].split("=")[1])

                # 查找订阅
                subs = sub_manager.list_subscriptions()
                sub = next((s for s in subs if s.id == sub_id), None)
                if not sub:
                    click.echo(f"未找到订阅ID: {sub_id}")
                    return

                # 执行处理
                success, msg, raw_path = sub_manager.process_single_subscription(
                    sub, 
                    custom_time_start=custom_start, 
                    custom_time_end=custom_end,
                    avoid_duplicate=True
                )
                click.echo(msg)
                if raw_path:
                    click.echo(f"原始数据文件：{raw_path}")

            except ValueError:
                click.echo("错误：订阅ID必须是数字")

        # 处理所有订阅
        elif parts[0] == "process-all":
            custom_start = None
            custom_end = None

            # 解析时间参数
            for i in range(1, len(parts)):
                if parts[i].startswith("--start="):
                    custom_start = parse_datetime_param(parts[i].split("=")[1])
                elif parts[i].startswith("--end="):
                    custom_end = parse_datetime_param(parts[i].split("=")[1])

            # 执行处理
            results = sub_manager.process_all_subscriptions(
                custom_time_start=custom_start, 
                custom_time_end=custom_end,
                avoid_duplicate=True
            )
            
            click.echo(f"\n处理完成（共 {len(results)} 个订阅）：")
            for i, (success, msg, raw_path) in enumerate(results, 1):
                click.echo(f"{i}. {msg}")
                if raw_path:
                    click.echo(f"   原始文件：{raw_path}")

        # 生成单个报告
        elif parts[0] == "generate-report":
            if len(parts) < 2:
                click.echo("用法：generate-report <订阅ID> [--start=2024-01-01 --end=2024-01-02]")
                return
            
            try:
                sub_id = int(parts[1])
                start_time = None
                end_time = None

                # 解析时间参数
                for i in range(2, len(parts)):
                    if parts[i].startswith("--start="):
                        start_time = parse_datetime_param(parts[i].split("=")[1])
                    elif parts[i].startswith("--end="):
                        end_time = parse_datetime_param(parts[i].split("=")[1])

                # 生成报告
                success, msg, report_path = report_generator.generate_subscription_report(
                    sub_id=sub_id,
                    start_time=start_time,
                    end_time=end_time
                )
                click.echo(msg)
                if report_path:
                    click.echo(f"报告文件：{report_path}")

            except ValueError:
                f"生成报告失败"

        # 生成所有报告
        elif parts[0] == "generate-all-reports":
            success_count, total_count, report_paths = report_generator.generate_all_reports()
            click.echo(f"生成完成：共 {total_count} 个原始数据文件，成功生成 {success_count} 个报告")
            for path in report_paths[:5]:  # 只显示前5个
                click.echo(f"- {path}")
            if len(report_paths) > 5:
                click.echo(f"... 还有 {len(report_paths) - 5} 个报告未显示")

        # 启动定时任务
        elif parts[0] == "start-scheduler":
            if scheduler.is_running():
                click.echo("定时任务已在运行")
                return
            
            run_in_background = "--background" in parts
            scheduler.start(run_in_background=run_in_background)
            
            if run_in_background:
                click.echo("定时任务已以后台进程启动（日志：scheduler.log，错误日志：scheduler_error.log）")
            else:
                click.echo(f"定时任务已启动（每日 {scheduler.schedule_time} 执行）")

        # 停止定时任务
        elif parts[0] == "stop-scheduler":
            if not scheduler.is_running():
                click.echo("定时任务未在运行")
                return
            
            scheduler.stop()
            click.echo("定时任务已停止")

        # 查看定时任务状态
        elif parts[0] == "status-scheduler":
            if scheduler.is_running():
                next_run = scheduler.get_next_run_time()
                click.echo(f"定时任务状态：运行中")
                click.echo(f"下次执行时间：{next_run or '未知'}")
            else:
                click.echo("定时任务状态：已停止")

        # 未知命令
        else:
            click.echo(f"未知命令：{parts[0]}（输入 'help' 查看可用命令）")

    except Exception as e:
        click.echo(f"命令执行失败: {str(e)}")
        logging.exception("命令执行异常")

def interactive_loop(sub_manager: SubscriptionManager, 
                    report_generator: AIReportGenerator,
                    scheduler: BackgroundScheduler):
    """交互式命令循环"""
    while True:
        try:
            cmd = click.prompt("\n请输入命令", type=str).strip().lower()
            if cmd == "exit":
                click.echo("退出工具...")
                # 停止定时任务（如果运行中）
                if scheduler.is_running():
                    scheduler.stop()
                break
            elif cmd == "help":
                show_help()
            else:
                execute_interactive_command(cmd, sub_manager, report_generator, scheduler)
        except KeyboardInterrupt:
            click.echo("\n操作被中断，输入 'exit' 退出工具")
        except Exception as e:
            click.echo(f"交互出错: {str(e)}")
            logging.exception("交互循环异常")

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """GitHub Sentinel - 交互式GitHub仓库订阅与总结工具"""
    if ctx.invoked_subcommand is None:
        # 显示欢迎信息
        click.echo("=" * 60)
        click.echo("GitHub Sentinel v2.0 - 仓库订阅与AI总结工具")
        click.echo("=" * 60)

        # 首次运行显示帮助信息
        first_run_flag = ".first_run"
        if not os.path.exists(first_run_flag):
            click.echo("📚 首次使用，以下是可用命令帮助：")
            show_help()
            # 创建标记文件
            with open(first_run_flag, "w", encoding="utf-8") as f:
                f.write(f"首次运行时间: {datetime.now().isoformat()}")
        else:
            click.echo("提示：输入 'help' 查看命令列表，'exit' 退出工具")

        # 初始化组件并进入交互循环
        try:
            config, github_client, sub_manager, report_generator = init_global_components()
            scheduler = BackgroundScheduler(config, sub_manager, report_generator)
            interactive_loop(sub_manager, report_generator, scheduler)
        except Exception as e:
            click.echo(f"初始化失败: {str(e)}")
            sys.exit(1)
    else:
        # 命令模式：传递初始化组件
        ctx.obj = init_global_components()

# 命令模式支持（非交互式）
@cli.command()
@click.argument("repo_full_name")
@click.argument("subscribers")
@click.option("--time-type", default="daily", help="时间类型：daily（默认）/ custom")
@click.option("--start", help="自定义开始时间（格式：YYYY-MM-DD）")
@click.option("--end", help="自定义结束时间（格式：YYYY-MM-DD）")
@click.pass_obj
def add_sub(obj, repo_full_name, subscribers, time_type, start, end):
    """新增订阅（命令模式）"""
    _, _, sub_manager, _ = obj
    custom_start = parse_datetime_param(start) if start else None
    custom_end = parse_datetime_param(end) if end else None
    
    if time_type == "custom" and (not custom_start or not custom_end):
        click.echo("错误：自定义时间范围需要同时指定--start和--end")
        return
        
    success, msg = sub_manager.add_subscription(
        repo_full_name=repo_full_name,
        subscribers=subscribers.split(","),
        time_range_type=time_type,
        custom_time_start=custom_start,
        custom_time_end=custom_end
    )
    click.echo(msg)

@cli.command()
@click.argument("sub_id", type=int)
@click.pass_obj
def del_sub(obj, sub_id):
    """删除订阅（命令模式）"""
    _, _, sub_manager, _ = obj
    success, msg = sub_manager.delete_subscription(sub_id)
    click.echo(msg)

@cli.command()
@click.argument("repo_full_name", required=False, default=None)
@click.pass_obj
def list_subs(obj, repo_full_name):
    """查看订阅（命令模式）"""
    _, _, sub_manager, _ = obj
    subs = sub_manager.list_subscriptions(repo_full_name)
    
    if not subs:
        click.echo("暂无订阅数据")
        return
        
    click.echo(f"订阅列表（共 {len(subs)} 个）：")
    for sub in subs:
        click.echo(f"ID: {sub.id}, 仓库: {sub.repo_full_name}, 状态: {'启用' if sub.enabled else '禁用'}")

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n工具被手动中断")
        sys.exit(0)
    except Exception as e:
        click.echo(f"工具运行出错: {str(e)}")
        sys.exit(1)
    