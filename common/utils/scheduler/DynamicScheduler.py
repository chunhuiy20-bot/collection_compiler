"""
文件名: DynamicScheduler.py
作者: yangchunhui
创建日期: 2026/2/6
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/6 12:03
描述:
 全局动态定时任务调度器（可复用），配合 FastAPI 路由和 APScheduler 库实现。
 支持在程序运行时通过 API 动态控制定时任务的添加、暂停、恢复、修改和移除。
 提供间隔任务、Cron 任务、一次性任务三种触发方式。

修改历史:
2026/2/6 12:03 - yangchunhui - 初始版本

依赖:
- apscheduler: AsyncIOScheduler，异步任务调度器基类
- apscheduler.triggers: IntervalTrigger / CronTrigger / DateTrigger，三种触发器
- typing: 类型注解支持（Callable, Optional, Dict, Any, List）
- logging: 标准日志模块
- datetime: 时间处理
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from typing import Callable, Optional, Dict, Any, List
import logging
from datetime import datetime


class DynamicScheduler:
    """动态任务调度器"""

    def __init__(self, timezone: str = 'Asia/Shanghai'):
        """
        初始化调度器
        :param timezone: 时区设置
        """
        self.scheduler = AsyncIOScheduler(timezone=timezone)
        self.logger = logging.getLogger(__name__)
        self._is_running = False

    def start(self):
        """启动调度器"""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            self.logger.info("动态调度器已启动")
        else:
            self.logger.warning("调度器已经在运行中")

    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self._is_running:
            self.scheduler.shutdown(wait=wait)
            self._is_running = False
            self.logger.info("动态调度器已关闭")

    def add_interval_job(self,
                         func: Callable,
                         seconds: Optional[int] = None,
                         minutes: Optional[int] = None,
                         hours: Optional[int] = None,
                         days: Optional[int] = None,
                         job_id: Optional[str] = None,
                         args: Optional[tuple] = None,
                         kwargs: Optional[dict] = None,
                         replace_existing: bool = True) -> str:
        """
        添加间隔执行任务
        :param func: 要执行的函数
        :param seconds: 间隔秒数
        :param minutes: 间隔分钟数
        :param hours: 间隔小时数
        :param days: 间隔天数
        :param job_id: 任务ID，如果不提供则自动生成
        :param args: 函数参数
        :param kwargs: 函数关键字参数
        :param replace_existing: 是否替换已存在的同ID任务
        :return: 任务ID
        """
        if not job_id:
            job_id = f"interval_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        job = self.scheduler.add_job(
            func=func,
            trigger=IntervalTrigger(
                seconds=seconds or 0,
                minutes=minutes or 0,
                hours=hours or 0,
                days=days or 0
            ),
            id=job_id,
            args=args or (),
            kwargs=kwargs or {},
            replace_existing=replace_existing
        )

        self.logger.info(f"添加间隔任务: {job_id}, 下次执行: {job.next_run_time}")
        return job_id

    def add_cron_job(self,
                     func: Callable,
                     year: Optional[int] = None,
                     month: Optional[int] = None,
                     day: Optional[int] = None,
                     week: Optional[int] = None,
                     day_of_week: Optional[str] = None,
                     hour: Optional[int] = None,
                     minute: Optional[int] = None,
                     second: Optional[int] = None,
                     job_id: Optional[str] = None,
                     args: Optional[tuple] = None,
                     kwargs: Optional[dict] = None,
                     replace_existing: bool = True) -> str:
        """
        添加Cron定时任务
        :param func: 要执行的函数
        :param year: 年
        :param month: 月
        :param day: 日
        :param week: 周
        :param day_of_week: 星期几 (mon,tue,wed,thu,fri,sat,sun)
        :param hour: 小时
        :param minute: 分钟
        :param second: 秒
        :param job_id: 任务ID
        :param args: 函数参数
        :param kwargs: 函数关键字参数
        :param replace_existing: 是否替换已存在的同ID任务
        :return: 任务ID
        """
        if not job_id:
            job_id = f"cron_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        job = self.scheduler.add_job(
            func=func,
            trigger=CronTrigger(
                year=year,
                month=month,
                day=day,
                week=week,
                day_of_week=day_of_week,
                hour=hour,
                minute=minute,
                second=second
            ),
            id=job_id,
            args=args or (),
            kwargs=kwargs or {},
            replace_existing=replace_existing
        )

        self.logger.info(f"添加Cron任务: {job_id}, 下次执行: {job.next_run_time}")
        return job_id

    def add_date_job(self,
                     func: Callable,
                     run_date: datetime,
                     job_id: Optional[str] = None,
                     args: Optional[tuple] = None,
                     kwargs: Optional[dict] = None,
                     replace_existing: bool = True) -> str:
        """
        添加一次性定时任务
        :param func: 要执行的函数
        :param run_date: 执行时间
        :param job_id: 任务ID
        :param args: 函数参数
        :param kwargs: 函数关键字参数
        :param replace_existing: 是否替换已存在的同ID任务
        :return: 任务ID
        """
        if not job_id:
            job_id = f"date_job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        job = self.scheduler.add_job(
            func=func,
            trigger=DateTrigger(run_date=run_date),
            id=job_id,
            args=args or (),
            kwargs=kwargs or {},
            replace_existing=replace_existing
        )

        self.logger.info(f"添加一次性任务: {job_id}, 执行时间: {job.next_run_time}")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """
        移除任务
        :param job_id: 任务ID
        :return: 是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"任务 {job_id} 已移除")
            return True
        except Exception as e:
            self.logger.error(f"移除任务 {job_id} 失败: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """
        暂停任务
        :param job_id: 任务ID
        :return: 是否成功暂停
        """
        try:
            self.scheduler.pause_job(job_id)
            self.logger.info(f"任务 {job_id} 已暂停")
            return True
        except Exception as e:
            self.logger.error(f"暂停任务 {job_id} 失败: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        恢复任务
        :param job_id: 任务ID
        :return: 是否成功恢复
        """
        try:
            self.scheduler.resume_job(job_id)
            self.logger.info(f"任务 {job_id} 已恢复")
            return True
        except Exception as e:
            self.logger.error(f"恢复任务 {job_id} 失败: {e}")
            return False

    def modify_job(self, job_id: str, **changes) -> bool:
        """
        修改任务
        :param job_id: 任务ID
        :param changes: 要修改的参数
        :return: 是否成功修改
        """
        try:
            self.scheduler.modify_job(job_id, **changes)
            self.logger.info(f"任务 {job_id} 已修改")
            return True
        except Exception as e:
            self.logger.error(f"修改任务 {job_id} 失败: {e}")
            return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        获取所有任务信息
        :return: 任务列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'func': job.func.__name__,
                'trigger': str(job.trigger),
                'next_run_time': job.next_run_time,
                'args': job.args,
                'kwargs': job.kwargs
            })
        return jobs

    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定任务信息
        :param job_id: 任务ID
        :return: 任务信息
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                return {
                    'id': job.id,
                    'name': job.name,
                    'func': job.func.__name__,
                    'trigger': str(job.trigger),
                    'next_run_time': job.next_run_time,
                    'args': job.args,
                    'kwargs': job.kwargs
                }
        except Exception as e:
            self.logger.error(f"获取任务 {job_id} 信息失败: {e}")
        return None

    def clear_all_jobs(self):
        """清空所有任务"""
        self.scheduler.remove_all_jobs()
        self.logger.info("所有任务已清空")


# 创建全局实例
scheduler = DynamicScheduler()
