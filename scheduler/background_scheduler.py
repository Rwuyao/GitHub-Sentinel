import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import psutil
import schedule
from threading import Thread, Event
from subscription.manager import SubscriptionManager
from report.generator import AIReportGenerator
from core.config import Config
from core.logger import setup_logger

class BackgroundScheduler:
    """完整的定时任务后台进程管理器，支持跨平台运行"""
    
    def __init__(self, config: Config, 
                 sub_manager: SubscriptionManager, 
                 report_generator: AIReportGenerator):
        """初始化定时任务管理器"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.sub_manager = sub_manager
        self.report_generator = report_generator
        
        # 配置参数
        self.schedule_time = config.get("scheduler.daily_time", "02:00")
        self.pid_file = config.get("scheduler.pid_file", "scheduler.pid")
        self.log_file = config.get("scheduler.log_file", "scheduler.log")
        self.error_log_file = config.get("scheduler.error_log_file", "scheduler_error.log")
        self.terminate_timeout = config.get("scheduler.terminate_timeout", 10)
        self.check_interval = 5  # 进程状态检查间隔（秒）
        
        # 运行时状态
        self.thread = None
        self.stop_event = Event()
        self.background_process = None
        
        # 确保日志目录存在
        for log_path in [self.log_file, self.error_log_file]:
            log_dir = os.path.dirname(log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

    def _job(self):
        """执行定时任务的核心逻辑"""
        try:
            self.logger.info("开始执行每日定时任务...")
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            start_time = datetime.combine(yesterday, datetime.min.time())
            end_time = datetime.combine(today, datetime.min.time())
            
            # 处理所有订阅
            process_results = self.sub_manager.process_all_subscriptions(
                start_time=start_time,
                end_time=end_time,
                avoid_duplicate=True
            )
            
            # 生成报告
            success_count, total_count, report_paths = self.report_generator.generate_all_reports()
            
            # 记录任务结果
            self.logger.info(
                f"定时任务完成 - "
                f"处理订阅: {len([r for r in process_results if r[0]])}/{len(process_results)} 成功, "
                f"生成报告: {success_count}/{total_count} 成功"
            )
            
        except Exception as e:
            self.logger.error(f"定时任务执行失败: {str(e)}", exc_info=True)

    def _run_scheduler(self):
        """调度器主循环"""
        try:
            # 立即执行一次任务（可选）
            immediate_run = self.config.get("scheduler.immediate_run", False)
            if immediate_run:
                self.logger.info("执行立即运行任务...")
                self._job()
            
            # 配置定时任务
            schedule.every().day.at(self.schedule_time).do(self._job)
            self.logger.info(f"定时任务已配置：每日 {self.schedule_time} 执行")
            
            # 运行调度循环
            while not self.stop_event.is_set():
                schedule.run_pending()
                time.sleep(self.check_interval)
                
        except Exception as e:
            self.logger.error(f"调度器运行出错: {str(e)}", exc_info=True)
        finally:
            self.logger.info("调度器循环已退出")

    def start(self, run_in_background: bool = False) -> Tuple[bool, str]:
        """
        启动定时任务
        
        Args:
            run_in_background: 是否以后台进程模式运行
            
        Returns:
            (是否成功, 状态消息)
        """
        # 检查是否已在运行
        if self.is_running():
            status = self.get_status()
            return False, f"定时任务已在运行 - {status}"
        
        try:
            if run_in_background:
                return self._start_background_process()
            else:
                return self._start_foreground_thread()
        except Exception as e:
            error_msg = f"启动定时任务失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _start_foreground_thread(self) -> Tuple[bool, str]:
        """启动前台线程模式"""
        self.stop_event.clear()
        self.thread = Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info("定时任务已在前台线程启动")
        return True, f"定时任务已启动（前台模式），每日 {self.schedule_time} 执行"

    def _start_background_process(self) -> Tuple[bool, str]:
        """启动后台进程模式"""
        # 构建启动命令
        cmd = [
            sys.executable,  # 当前Python解释器
            os.path.abspath(__file__),  # 当前脚本路径
            "--config", self.config.config_path,
            "--background"
        ]
        
        # 启动后台进程
        try:
            # Windows特定配置：不显示命令窗口
            creationflags = 0
            if sys.platform.startswith('win32'):
                creationflags = subprocess.CREATE_NO_WINDOW
            
            self.background_process = subprocess.Popen(
                cmd,
                stdout=open(self.log_file, "a", encoding="utf-8"),
                stderr=open(self.error_log_file, "a", encoding="utf-8"),
                creationflags=creationflags,
                cwd=os.getcwd()
            )
            
            # 保存PID
            with open(self.pid_file, "w", encoding="utf-8") as f:
                f.write(str(self.background_process.pid))
            
            # 验证进程是否真的启动了
            time.sleep(1)
            if not psutil.pid_exists(self.background_process.pid):
                raise RuntimeError("进程启动后立即退出")
                
            self.logger.info(f"后台进程已启动，PID: {self.background_process.pid}")
            return True, f"后台进程已启动，PID: {self.background_process.pid}（日志：{self.log_file}）"
            
        except Exception as e:
            # 清理失败的启动
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            raise e

    def stop(self) -> Tuple[bool, str]:
        """
        停止定时任务
        
        Returns:
            (是否成功, 状态消息)
        """
        # 先处理后台进程
        if os.path.exists(self.pid_file):
            return self._stop_background_process()
        
        # 再处理前台线程
        if self.thread and self.thread.is_alive():
            return self._stop_foreground_thread()
        
        return False, "没有运行中的定时任务"

    def _stop_background_process(self) -> Tuple[bool, str]:
        """停止后台进程"""
        try:
            with open(self.pid_file, 'r', encoding="utf-8") as f:
                pid = int(f.read().strip())
                
            if not psutil.pid_exists(pid):
                os.remove(self.pid_file)
                return False, f"PID {pid} 对应的进程不存在，已清理PID文件"

            process = psutil.Process(pid)
            process_name = process.name()
            self.logger.info(f"开始终止进程 {pid} ({process_name})")

            # 阶段1：发送终止信号
            process.terminate()
            
            # 等待进程终止
            start_time = time.time()
            while time.time() - start_time < self.terminate_timeout:
                if not psutil.pid_exists(pid):
                    break
                time.sleep(0.5)
            
            # 阶段2：如果仍在运行，强制终止
            if psutil.pid_exists(pid):
                self.logger.warning(f"进程 {pid} 未响应终止信号，尝试强制终止")
                process.kill()
                time.sleep(1)
                
                if psutil.pid_exists(pid):
                    # 尝试操作系统级别的终止命令
                    self._os_force_terminate(pid)
                    
                    if psutil.pid_exists(pid):
                        raise RuntimeError(f"无法终止进程 {pid}，请手动终止")

            # 清理PID文件
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                
            self.logger.info(f"进程 {pid} 已成功终止")
            return True, f"后台进程 {pid} 已成功终止"
            
        except ValueError:
            os.remove(self.pid_file)
            return False, f"PID文件内容无效，已清理"
        except Exception as e:
            return False, f"终止后台进程失败: {str(e)}"

    def _stop_foreground_thread(self) -> Tuple[bool, str]:
        """停止前台线程"""
        if not (self.thread and self.thread.is_alive()):
            return False, "前台线程未在运行"
            
        self.logger.info("正在停止前台线程...")
        self.stop_event.set()
        self.thread.join(timeout=self.terminate_timeout)
        
        if self.thread.is_alive():
            schedule.clear()
            return False, "前台线程未能正常终止，请尝试重新启动程序"
            
        schedule.clear()
        self.logger.info("前台线程已成功停止")
        return True, "前台线程已成功停止"

    def _os_force_terminate(self, pid: int):
        """使用操作系统命令强制终止进程"""
        try:
            if sys.platform.startswith('win32'):
                # Windows系统使用taskkill
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                # Unix系统使用kill -9
                os.kill(pid, signal.SIGKILL)
                
            self.logger.info(f"已通过系统命令强制终止进程 {pid}")
            
        except Exception as e:
            self.logger.warning(f"系统命令强制终止进程 {pid} 失败: {str(e)}")

    def is_running(self) -> bool:
        """检查定时任务是否在运行"""
        # 检查后台进程
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r', encoding="utf-8") as f:
                    pid = int(f.read().strip())
                return psutil.pid_exists(pid)
            except:
                os.remove(self.pid_file)
        
        # 检查前台线程
        return self.thread is not None and self.thread.is_alive()

    def get_status(self) -> str:
        """获取定时任务当前状态"""
        if not self.is_running():
            return "未运行"
            
        # 检查是否为后台进程
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r', encoding="utf-8") as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    run_time = datetime.now() - datetime.fromtimestamp(process.create_time())
                    next_run = self.get_next_run_time()
                    
                    return (f"后台进程运行中 (PID: {pid}, "
                            f"运行时间: {str(run_time).split('.')[0]}, "
                            f"下次执行: {next_run or '未知'})")
            except:
                os.remove(self.pid_file)
        
        # 前台线程状态
        next_run = self.get_next_run_time()
        return f"前台线程运行中，下次执行: {next_run or '未知'}"

    def get_next_run_time(self) -> Optional[str]:
        """获取下次任务执行时间"""
        if not self.is_running():
            return None
            
        try:
            next_run = schedule.next_run()
            return next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
        except:
            return None

    def get_process_info(self) -> Optional[Dict]:
        """获取进程详细信息"""
        if not self.is_running():
            return None
            
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r', encoding="utf-8") as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    return {
                        "pid": pid,
                        "name": process.name(),
                        "status": process.status(),
                        "create_time": datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S"),
                        "cpu_percent": process.cpu_percent(interval=0.1),
                        "memory_percent": process.memory_percent(),
                        "cmdline": ' '.join(process.cmdline())
                    }
                    
        except Exception as e:
            self.logger.warning(f"获取进程信息失败: {str(e)}")
            
        return None

# 后台进程入口点
if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="GitHub Sentinel 定时任务后台进程")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--background", action="store_true", help="后台模式标记")
    args = parser.parse_args()
    
    # 初始化配置和日志
    config = Config.from_file(args.config)
    setup_logger(
        log_level=config.get("logging.level", "INFO"),
        log_file=config.get("scheduler.log_file", "scheduler.log")
    )
    
    # 初始化依赖组件
    try:
        from github.client import GitHubClient
        from subscription.manager import SubscriptionManager
        from report.generator import AIReportGenerator
        
        # 初始化GitHub客户端
        github_token = os.getenv("GITHUB_TOKEN") or config.get("github_token")
        if not github_token:
            raise ValueError("未配置GitHub Token")
        github_client = GitHubClient(github_token=github_token)
        
        # 初始化订阅管理器
        sub_manager = SubscriptionManager(config, github_client)
        
        # 初始化报告生成器
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or config.get("deepseek.api_key")
        report_generator = AIReportGenerator(config, deepseek_api_key)
        
        # 启动调度器（非后台模式，因为本身已是后台进程）
        scheduler = BackgroundScheduler(config, sub_manager, report_generator)
        success, msg = scheduler.start(run_in_background=False)
        
        # 保持进程运行
        if success:
            try:
                while True:
                    time.sleep(3600)  # 每小时检查一次
            except KeyboardInterrupt:
                scheduler.stop()
                
    except Exception as e:
        logging.error(f"后台进程初始化失败: {str(e)}", exc_info=True)
        sys.exit(1)
    