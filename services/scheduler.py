import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from services.post_collector import PostCollector
from models.database import db_manager
from config import (
    COLLECTION_SCHEDULE_HOUR,
    COLLECTION_SCHEDULE_MINUTE,
    DATABASE_URL
)

logger = logging.getLogger(__name__)

class SocialMediaScheduler:
    def __init__(self, background_mode: bool = True):
        self.background_mode = background_mode
        self.scheduler = None
        self.post_collector = PostCollector()
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """設置調度器"""
        try:
            # 配置作業存儲
            jobstores = {
                'default': SQLAlchemyJobStore(url=DATABASE_URL)
            }
            
            # 配置執行器
            executors = {
                'default': ThreadPoolExecutor(20),
            }
            
            # 作業預設設置
            job_defaults = {
                'coalesce': False,
                'max_instances': 1,
                'misfire_grace_time': 30
            }
            
            # 選擇調度器類型
            if self.background_mode:
                self.scheduler = BackgroundScheduler(
                    jobstores=jobstores,
                    executors=executors,
                    job_defaults=job_defaults
                )
            else:
                self.scheduler = BlockingScheduler(
                    jobstores=jobstores,
                    executors=executors,
                    job_defaults=job_defaults
                )
            
            logger.info("Scheduler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup scheduler: {e}")
            raise
    
    def start(self):
        """啟動調度器"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
            else:
                logger.warning("Scheduler is already running")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self):
        """停止調度器"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Scheduler stopped successfully")
            else:
                logger.warning("Scheduler is not running")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    def add_daily_collection_job(self):
        """添加每日收集任務"""
        try:
            job_id = 'daily_post_collection'
            
            # 檢查作業是否已存在
            if self.scheduler.get_job(job_id):
                logger.info(f"Job {job_id} already exists, removing it first")
                self.scheduler.remove_job(job_id)
            
            # 添加每日定時任務
            self.scheduler.add_job(
                func=self._execute_daily_collection,
                trigger=CronTrigger(
                    hour=COLLECTION_SCHEDULE_HOUR,
                    minute=COLLECTION_SCHEDULE_MINUTE
                ),
                id=job_id,
                name='Daily Post Collection',
                replace_existing=True,
                coalesce=True,
                max_instances=1
            )
            
            logger.info(f"Daily collection job scheduled for {COLLECTION_SCHEDULE_HOUR:02d}:{COLLECTION_SCHEDULE_MINUTE:02d}")
            
        except Exception as e:
            logger.error(f"Failed to add daily collection job: {e}")
    
    def add_hourly_monitoring_job(self):
        """添加每小時監控任務（用於高頻監控重要帳號）"""
        try:
            job_id = 'hourly_monitoring'
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            self.scheduler.add_job(
                func=self._execute_priority_monitoring,
                trigger=IntervalTrigger(hours=1),
                id=job_id,
                name='Hourly Priority Monitoring',
                replace_existing=True,
                coalesce=True,
                max_instances=1
            )
            
            logger.info("Hourly monitoring job added")
            
        except Exception as e:
            logger.error(f"Failed to add hourly monitoring job: {e}")
    
    def add_manual_job(self, delay_minutes: int = 0, job_type: str = 'full_collection'):
        """添加手動執行的一次性任務"""
        try:
            job_id = f'manual_{job_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            
            run_time = datetime.now() + timedelta(minutes=delay_minutes)
            
            if job_type == 'full_collection':
                func = self._execute_daily_collection
            elif job_type == 'priority_only':
                func = self._execute_priority_monitoring
            elif job_type == 'twitter_only':
                func = lambda: self._execute_platform_collection('twitter')
            elif job_type == 'linkedin_only':
                func = lambda: self._execute_platform_collection('linkedin')
            else:
                raise ValueError(f"Unknown job type: {job_type}")
            
            self.scheduler.add_job(
                func=func,
                trigger=DateTrigger(run_date=run_time),
                id=job_id,
                name=f'Manual {job_type.replace("_", " ").title()}',
                replace_existing=True
            )
            
            logger.info(f"Manual job '{job_type}' scheduled to run at {run_time}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to add manual job: {e}")
            return None
    
    def _execute_daily_collection(self):
        """執行每日完整收集任務"""
        try:
            logger.info("Starting daily post collection")
            start_time = datetime.utcnow()
            
            # 記錄任務開始
            db_manager.log_processing(
                level='INFO',
                message='Daily collection task started',
                details={'start_time': start_time.isoformat()}
            )
            
            # 執行收集
            results = self.post_collector.collect_all_posts()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # 記錄任務完成
            db_manager.log_processing(
                level='INFO',
                message='Daily collection task completed',
                details={
                    'duration_seconds': duration,
                    'results': results
                }
            )
            
            logger.info(f"Daily collection completed in {duration:.1f} seconds")
            logger.info(f"Results: {results}")
            
        except Exception as e:
            logger.error(f"Error in daily collection: {e}")
            db_manager.log_processing(
                level='ERROR',
                message='Daily collection task failed',
                details={'error': str(e)}
            )
    
    def _execute_priority_monitoring(self):
        """執行優先帳號監控"""
        try:
            logger.info("Starting priority account monitoring")
            
            # 獲取優先級為 'high' 的帳號
            session = db_manager.get_session()
            from models.database import Account
            
            priority_accounts = session.query(Account).filter_by(
                active=True,
                priority='high'
            ).all()
            
            session.close()
            
            if not priority_accounts:
                logger.info("No high priority accounts found")
                return
            
            # 對每個優先帳號執行收集
            total_posts = 0
            for account in priority_accounts:
                try:
                    result = self.post_collector.collect_posts_by_platform(account.platform)
                    total_posts += result.get('posts_collected', 0)
                except Exception as e:
                    logger.error(f"Error monitoring {account.platform}/@{account.username}: {e}")
            
            logger.info(f"Priority monitoring completed, collected {total_posts} posts")
            
        except Exception as e:
            logger.error(f"Error in priority monitoring: {e}")
    
    def _execute_platform_collection(self, platform: str):
        """執行特定平台的收集"""
        try:
            logger.info(f"Starting {platform} collection")
            result = self.post_collector.collect_posts_by_platform(platform)
            logger.info(f"{platform} collection completed: {result}")
            
        except Exception as e:
            logger.error(f"Error in {platform} collection: {e}")
    
    def get_job_status(self) -> dict:
        """獲取調度器狀態"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return {
                'running': self.scheduler.running,
                'jobs_count': len(jobs),
                'jobs': jobs,
                'status_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                'error': str(e),
                'status_time': datetime.utcnow().isoformat()
            }
    
    def remove_job(self, job_id: str) -> bool:
        """移除指定的作業"""
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Job {job_id} removed successfully")
                return True
            else:
                logger.warning(f"Job {job_id} not found")
                return False
                
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str) -> bool:
        """暫停指定的作業"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} paused")
            return True
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """恢復指定的作業"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumed")
            return True
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False
    
    def run_blocking(self):
        """以阻塞模式運行調度器（用於獨立進程）"""
        if not self.background_mode:
            try:
                logger.info("Starting scheduler in blocking mode")
                self.scheduler.start()
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                self.stop()
        else:
            logger.error("Cannot run in blocking mode: scheduler is in background mode")

# 全局調度器實例
global_scheduler = None

def get_scheduler(background_mode: bool = True) -> SocialMediaScheduler:
    """獲取全局調度器實例"""
    global global_scheduler
    if global_scheduler is None:
        global_scheduler = SocialMediaScheduler(background_mode=background_mode)
    return global_scheduler