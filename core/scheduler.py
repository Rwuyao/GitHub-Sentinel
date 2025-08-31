import logging
from datetime import time, datetime
from typing import Callable
import schedule
import time as time_module

class Scheduler:
    """任务调度器，负责安排和执行定期任务"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.running = False
    
    def add_daily_task(self, task: Callable, time_str: str = None):
        """添加每日任务"""
        run_time = time_str or self.config.daily_time
        try:
            hour, minute = map(int, run_time.split(':'))
            schedule.every().day.at(time(hour, minute)).do(task)
            self.logger.info(f"Added daily task to run at {run_time}")
        except ValueError:
            self.logger.error(f"Invalid time format: {run_time}. Using default time.")
            schedule.every().day.at(self.config.daily_time).do(task)
    
    def add_weekly_task(self, task: Callable, day: str = None, time_str: str = None):
        """添加每周任务"""
        day_of_week = day or self.config.weekly_day
        run_time = time_str or self.config.daily_time
        
        try:
            hour, minute = map(int, run_time.split(':'))
            # 获取星期几的调度对象
            day_scheduler = getattr(schedule.every(), day_of_week.lower())
            day_scheduler.at(time(hour, minute)).do(task)
            self.logger.info(f"Added weekly task to run every {day_of_week} at {run_time}")
        except AttributeError:
            self.logger.error(f"Invalid day of week: {day_of_week}. Using default day.")
            default_day_scheduler = getattr(schedule.every(), self.config.weekly_day.lower())
            default_day_scheduler.at(self.config.daily_time).do(task)
        except ValueError:
            self.logger.error(f"Invalid time format: {run_time}. Using default time.")
            day_scheduler = getattr(schedule.every(), day_of_week.lower())
            day_scheduler.at(self.config.daily_time).do(task)
    
    def add_interval_task(self, task: Callable, hours: int = 1):
        """添加间隔任务（每N小时执行一次）"""
        schedule.every(hours).hours.do(task)
        self.logger.info(f"Added interval task to run every {hours} hours")
    
    def start(self):
        """启动调度器"""
        self.running = True
        self.logger.info("Scheduler started. Running pending tasks...")
        
        while self.running:
            schedule.run_pending()
            time_module.sleep(60)  # 每分钟检查一次
    
    def shutdown(self):
        """关闭调度器"""
        self.running = False
        self.logger.info("Scheduler shut down.")
