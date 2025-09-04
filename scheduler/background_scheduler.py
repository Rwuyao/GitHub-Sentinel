import logging
from datetime import datetime, timedelta
from typing import Optional
import schedule
import time
from threading import Thread, Event
from subscription.manager import SubscriptionManager
from report.generator import AIReportGenerator
from core.config import Config

class BackgroundScheduler:
    """后台定时任务（每日自动处理订阅并生成报告）"""
    def __init__(self, config: Config, sub_manager: SubscriptionManager, report_generator: AIReportGenerator):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.sub_manager = sub_manager
        self.report_generator = report_generator
        # 定时配置（默认每日凌晨2点执行）
        self.schedule_time = config.get("scheduler.daily_time", "02:00")
        self.thread = None
        self.stop_event = Event()

    def _job(self):
        """定时任务执行逻辑：处理前一天订阅 + 生成报告"""
        self.logger.info("开始执行每日定时任务...")
        # 时间范围：前一天（00:00 ~ 次日00:00）
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        end_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. 处理所有订阅
        self.logger.info(f"处理所有订阅，时间范围：{start_time} ~ {end_time}")
        process_results = self.sub_manager.process_all_subscriptions(start_time, end_time)
        
        # 2. 生成所有报告
        self.logger.info("生成所有订阅的AI总结报告")
        success_count, total_count, report_paths = self.report_generator.generate_all_reports()
        
        # 日志记录结果
        self.logger.info(f"定时任务执行完成：处理订阅 {len(process_results)} 个，生成报告 {success_count}/{total_count} 个")
        for path in report_paths:
            self.logger.info(f"生成报告：{path}")

    def start(self):
        """启动定时任务（后台线程）"""
        if self.is_running():
            self.logger.warning("定时任务已在运行")
            return
        
        # 配置定时任务（每日指定时间执行）
        schedule.every().day.at(self.schedule_time).do(self._job)
        self.logger.info(f"定时任务已配置：每日 {self.schedule_time} 执行")
        
        # 启动后台线程
        self.stop_event.clear()
        self.thread = Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info("定时任务后台线程已启动")

    def _run_scheduler(self):
        """调度器运行循环"""
        while not self.stop_event.is_set():
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def stop(self):
        """停止定时任务"""
        if not self.is_running():
            self.logger.warning("定时任务未在运行")
            return
        
        self.stop_event.set()
        if self.thread:
            self.thread.join()
        schedule.clear()  # 清除所有定时任务
        self.logger.info("定时任务已停止")

    def is_running(self) -> bool:
        """检查定时任务是否在运行"""
        return self.thread and self.thread.is_alive()

    def get_next_run_time(self) -> Optional[str]:
        """获取下次执行时间"""
        if not self.is_running():
            return None
        next_run = schedule.next_run()
        return next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None