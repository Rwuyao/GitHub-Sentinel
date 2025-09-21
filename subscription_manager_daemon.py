#!/usr/bin/env python3
import os
import sys
import time
import json
import schedule
import argparse
import logging
import subprocess
import signal
from datetime import datetime, timedelta, timezone
from typing import Optional

# 导入项目相关模块
from github.client import GitHubClient
from subscription.manager import SubscriptionManager
from report.generator import AIReportGenerator
from core.config import Config
from core.logger import setup_logger

# 初始化配置和日志
config = Config.from_file("config/config.yaml")
setup_logger(
    log_level=config.get("logging.level", "INFO"),
    log_file=config.get("logging.file", "logs/daemon.log")
)
logger=logging.getLogger(__name__)
# 全局配置
PID_FILE_PATH = "data/daemon.pid"
DEFAULT_SCHEDULE_TIME = "02:00"  # 每天凌晨2点执行

def is_windows() -> bool:
    """判断当前系统是否为Windows"""
    return sys.platform.startswith('win32')

def create_clients(config: Config):
    """创建所需的客户端实例"""
    try:
        # 初始化核心组件
        github_token = os.getenv("GITHUB_TOKEN") or config.get("github_token")
        github_client = GitHubClient(github_token=github_token) if github_token else None

        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or config.get("deepseek.api_key")
        report_generator = AIReportGenerator(config, deepseek_api_key)

        # 初始化订阅管理器时指定订阅数据路径
        sub_manager = SubscriptionManager(config, github_client) if github_client else None
        
        return sub_manager, report_generator
        
    except Exception as e:
        logger.error(f"创建客户端失败: {str(e)}")
        return None, None

def generate_daily_report():
    """生成昨天的日报"""
    logger.info("开始执行每日报告生成任务")
    
    if not config:
        logger.error("配置加载失败，无法执行任务")
        return False
    
    # 创建客户端
    sub_manager, report_generator = create_clients(config)
    if not sub_manager or not report_generator:
        logger.error("客户端创建失败，无法执行任务")
        return False
    
    # 计算时间范围（昨天00:00到今天00:00 UTC时间）
    today_utc = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    yesterday_utc = today_utc - timedelta(days=1)
    
    logger.info(f"生成时间范围: {yesterday_utc.strftime('%Y-%m-%d')} 至 {today_utc.strftime('%Y-%m-%d')}")
    
    try:
        start_time = yesterday_utc
        end_time = today_utc
        
        # 处理所有订阅
        process_results = sub_manager.process_all_subscriptions(
            custom_time_start=start_time,
            custom_time_end=end_time,
            avoid_duplicate=True
        )
        
        # 生成报告
        success_count, total_count, report_paths = report_generator.generate_all_reports()
        
        # 记录任务结果
        logger.info(
            f"定时任务完成 - "
            f"处理订阅: {len([r for r in process_results if r[0]])}/{len(process_results)} 成功, "
            f"生成报告: {success_count}/{total_count} 成功"
        )
        return True
        
    except Exception as e:
        logger.error(f"生成报告时发生错误: {str(e)}")
        return False

def run_scheduler(schedule_time: str = DEFAULT_SCHEDULE_TIME):
    """运行调度器"""
    # 首次启动时立即执行一次
    logger.info("首次启动，立即执行一次报告生成")
    generate_daily_report()
    
    # 安排每天指定时间执行
    logger.info(f"设置定时任务，每天 {schedule_time} 执行")
    schedule.every().day.at(schedule_time).do(generate_daily_report)
    
    # 运行调度循环
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("调度器被手动中断")
    except Exception as e:
        logger.error(f"调度器运行出错: {str(e)}")

def start_background():
    """在Windows上启动后台进程"""
    if os.path.exists(PID_FILE_PATH):
        logger.error(f"服务已在运行（PID文件 {PID_FILE_PATH} 已存在）")
        return False
    
    try:
        # 确定Python可执行文件路径
        python_exe = sys.executable
        
        # 构建命令行参数，使用当前脚本并传入background参数
        cmd = [
            python_exe,
            __file__,
            "background"
        ]
        
        # 在Windows上创建隐藏窗口的进程
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE  # 隐藏窗口
        
        # 启动进程
        process = subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            stdout=open("service_stdout.log", "a"),
            stderr=open("service_stderr.log", "a")
        )
        
        # 保存PID
        with open(PID_FILE_PATH, "w") as f:
            json.dump({
                "pid": process.pid,
                "start_time": datetime.now().isoformat()
            }, f)
        
        logger.info(f"服务已启动（PID: {process.pid}）")
        return True
        
    except Exception as e:
        logger.error(f"启动服务失败: {str(e)}")
        return False

def stop_background():
    """停止后台进程"""
    if not os.path.exists(PID_FILE_PATH):
        logger.error(f"服务未运行（未找到PID文件 {PID_FILE_PATH}）")
        return False
    
    try:
        # 读取PID
        with open(PID_FILE_PATH, "r") as f:
            pid_info = json.load(f)
            pid = pid_info["pid"]
        
        logger.info(f"正在停止服务（PID: {pid}）")
        
        # 终止进程
        if is_windows():
            # Windows系统终止进程
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:
            # Unix-like系统终止进程
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
        
        # 清理PID文件
        if os.path.exists(PID_FILE_PATH):
            os.remove(PID_FILE_PATH)
        
        logger.info("服务已成功停止")
        return True
        
    except subprocess.CalledProcessError:
        logger.error(f"停止进程失败，可能进程已退出")
        if os.path.exists(PID_FILE_PATH):
            os.remove(PID_FILE_PATH)
        return False
    except Exception as e:
        logger.error(f"停止服务失败: {str(e)}")
        return False

def check_status():
    """检查服务状态"""
    if not os.path.exists(PID_FILE_PATH):
        logger.info("服务未在运行")
        return False
    
    try:
        with open(PID_FILE_PATH, "r") as f:
            pid_info = json.load(f)
            pid = pid_info["pid"]
        
        # 检查进程是否存在
        if is_windows():
            # Windows检查进程是否存在
            output = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                stderr=subprocess.STDOUT,
                text=True
            )
            is_running = str(pid) in output
        else:
            # Unix-like检查进程是否存在
            os.kill(pid, 0)
            is_running = True
        
        if is_running:
            logger.info(f"服务正在运行（PID: {pid}，启动时间: {pid_info['start_time']}）")
            return True
        else:
            logger.info(f"服务已停止，但PID文件 {PID_FILE_PATH} 未被删除")
            os.remove(PID_FILE_PATH)
            return False
            
    except Exception as e:
        logger.info(f"服务未在运行: {str(e)}")
        if os.path.exists(PID_FILE_PATH):
            os.remove(PID_FILE_PATH)
        return False

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description="GitHub报告定时生成服务（兼容Windows）")
    parser.add_argument("command", choices=["start", "stop", "status", "background"],
                      help="操作命令: start(启动), stop(停止), status(状态), background(内部使用)")
    parser.add_argument("--time", default=DEFAULT_SCHEDULE_TIME,
                      help=f"定时执行时间，格式HH:MM，默认{DEFAULT_SCHEDULE_TIME}")
    
    args = parser.parse_args()
    
    # 内部使用的background命令，用于启动实际的调度器
    if args.command == "background":
        run_scheduler(args.time)
        return
    
    if args.command == "start":
        start_background()
    elif args.command == "stop":
        stop_background()
    elif args.command == "status":
        check_status()

if __name__ == "__main__":
    main()
