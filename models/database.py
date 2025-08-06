from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)
    username = Column(String(255), nullable=False)
    display_name = Column(String(255))
    category = Column(String(100))
    # 移除priority欄位 - 統一為每日收集
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Account(platform='{self.platform}', username='{self.username}')>"

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)
    post_id = Column(String(255), nullable=False)
    author_username = Column(String(255), nullable=False)
    author_display_name = Column(String(255))
    original_content = Column(Text)
    post_time = Column(DateTime)
    post_url = Column(String(500))
    metrics = Column(JSON)  # 存儲點贊、分享等數據
    language = Column(String(10))
    collected_at = Column(DateTime, default=datetime.utcnow)
    
    # 唯一約束：同平台同post_id只能有一條記錄
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    def __repr__(self):
        return f"<Post(platform='{self.platform}', post_id='{self.post_id}', author='{self.author_username}')>"

class AnalyzedPost(Base):
    __tablename__ = 'analyzed_posts'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(255), nullable=False)  # 貼文 ID 字符串
    platform = Column(String(50), nullable=False)
    original_post_id = Column(String(255), nullable=False)
    author_username = Column(String(255), nullable=False)
    author_display_name = Column(String(255))
    original_content = Column(Text)
    summary = Column(Text)
    importance_score = Column(Float)
    repost_content = Column(Text)
    post_url = Column(String(500))
    post_time = Column(DateTime)
    collected_at = Column(DateTime)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    category = Column(String(100))
    status = Column(String(50), default='new')  # new, reviewed, posted, archived
    
    def __repr__(self):
        return f"<AnalyzedPost(id={self.id}, platform='{self.platform}', importance={self.importance_score})>"

class ProcessingLog(Base):
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20))  # INFO, WARNING, ERROR
    message = Column(Text)
    platform = Column(String(50))
    username = Column(String(255))
    details = Column(JSON)  # 額外的詳細信息
    
    def __repr__(self):
        return f"<ProcessingLog(timestamp='{self.timestamp}', level='{self.level}')>"

class HumanFeedback(Base):
    __tablename__ = 'human_feedback'
    
    id = Column(Integer, primary_key=True)
    analyzed_post_id = Column(Integer, nullable=False)  # 關聯到 AnalyzedPost 表
    platform = Column(String(50), nullable=False)
    original_post_id = Column(String(255), nullable=False)
    ai_score = Column(Float)  # AI給的評分
    human_score = Column(Float, nullable=False)  # 人工評分
    feedback_reason = Column(Text)  # 人工評分的原因/解釋
    feedback_category = Column(String(100))  # 反饋分類
    reviewer_notes = Column(Text)  # 審核者備註
    created_at = Column(DateTime, default=datetime.utcnow)
    prompt_version_id = Column(Integer)  # 使用的prompt版本
    
    def __repr__(self):
        return f"<HumanFeedback(id={self.id}, ai_score={self.ai_score}, human_score={self.human_score})>"

class PromptVersion(Base):
    __tablename__ = 'prompt_versions'
    
    id = Column(Integer, primary_key=True)
    version_name = Column(String(100), nullable=False)  # 版本名稱
    prompt_type = Column(String(50), nullable=False)  # importance, summary, repost
    prompt_content = Column(Text, nullable=False)  # prompt內容
    description = Column(Text)  # 版本描述/改動說明
    is_active = Column(Boolean, default=False)  # 是否為當前使用版本
    created_at = Column(DateTime, default=datetime.utcnow)
    performance_score = Column(Float)  # 根據feedback計算的性能評分
    total_feedbacks = Column(Integer, default=0)  # 總反饋次數
    avg_accuracy = Column(Float)  # 平均準確性
    
    def __repr__(self):
        return f"<PromptVersion(id={self.id}, version='{self.version_name}', type='{self.prompt_type}')>"

class TwitterUserCache(Base):
    __tablename__ = 'twitter_user_cache'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(255), nullable=False)
    display_name = Column(String(255))
    followers_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # 緩存過期時間
    
    def __repr__(self):
        return f"<TwitterUserCache(username='{self.username}', user_id='{self.user_id}')>"

class APIUsageLog(Base):
    __tablename__ = 'api_usage_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    platform = Column(String(50), nullable=False)  # twitter, linkedin
    endpoint = Column(String(100), nullable=False)  # get_user, get_users_tweets
    username = Column(String(255))  # 相關的用戶名
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    rate_limit_remaining = Column(Integer)  # 剩餘配額
    rate_limit_reset = Column(DateTime)  # 重置時間
    response_time_ms = Column(Integer)  # 響應時間
    
    def __repr__(self):
        return f"<APIUsageLog(platform='{self.platform}', endpoint='{self.endpoint}', success={self.success})>"

class DatabaseManager:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化數據庫連接"""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # 設置為 True 可以看到 SQL 語句
                pool_pre_ping=True
            )
            
            # 創建所有表
            Base.metadata.create_all(bind=self.engine)
            
            # 創建會話工廠
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self):
        """獲取數據庫會話"""
        return self.SessionLocal()
    
    def save_accounts(self, accounts: list):
        """保存帳號信息到數據庫"""
        session = self.get_session()
        try:
            for account_data in accounts:
                # 檢查是否已存在
                existing = session.query(Account).filter_by(
                    platform=account_data['platform'],
                    username=account_data['username']
                ).first()
                
                if existing:
                    # 更新現有記錄
                    existing.display_name = account_data.get('display_name', existing.display_name)
                    existing.category = account_data.get('category', existing.category)
                    # 移除priority更新
                    existing.active = account_data.get('active', existing.active)
                    existing.updated_at = datetime.utcnow()
                else:
                    # 創建新記錄
                    account = Account(
                        platform=account_data['platform'],
                        username=account_data['username'],
                        display_name=account_data.get('display_name'),
                        category=account_data.get('category'),
                        # 移除priority設定
                        active=account_data.get('active', True)
                    )
                    session.add(account)
            
            session.commit()
            logger.info(f"Saved {len(accounts)} accounts to database")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save accounts: {e}")
            raise
        finally:
            session.close()
    
    def save_posts(self, posts: list):
        """保存貼文到數據庫"""
        session = self.get_session()
        try:
            saved_count = 0
            for post_data in posts:
                # 檢查是否已存在（避免重複）
                existing = session.query(Post).filter_by(
                    platform=post_data['platform'],
                    post_id=post_data['post_id']
                ).first()
                
                if not existing:
                    post = Post(
                        platform=post_data['platform'],
                        post_id=post_data['post_id'],
                        author_username=post_data['author_username'],
                        author_display_name=post_data.get('author_display_name'),
                        original_content=post_data.get('original_content'),
                        post_time=datetime.fromisoformat(post_data['post_time'].replace('Z', '+00:00')) if post_data.get('post_time') else None,
                        post_url=post_data.get('post_url'),
                        metrics=post_data.get('metrics'),
                        language=post_data.get('language'),
                        collected_at=datetime.fromisoformat(post_data['collected_at'].replace('Z', '+00:00')) if post_data.get('collected_at') else datetime.utcnow()
                    )
                    session.add(post)
                    saved_count += 1
            
            session.commit()
            logger.info(f"Saved {saved_count} new posts to database")
            return saved_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save posts: {e}")
            raise
        finally:
            session.close()
    
    def save_analyzed_posts(self, analyzed_posts: list):
        """保存分析後的貼文到數據庫"""
        session = self.get_session()
        try:
            for post_data in analyzed_posts:
                analyzed_post = AnalyzedPost(
                    post_id=post_data.get('post_id', 0),
                    platform=post_data['platform'],
                    original_post_id=post_data['post_id'],
                    author_username=post_data['author_username'],
                    author_display_name=post_data.get('author_display_name'),
                    original_content=post_data.get('original_content'),
                    summary=post_data.get('summary'),
                    importance_score=post_data.get('importance_score'),
                    repost_content=post_data.get('repost_content'),
                    post_url=post_data.get('post_url'),
                    post_time=datetime.fromisoformat(post_data['post_time'].replace('Z', '+00:00')) if post_data.get('post_time') else None,
                    collected_at=datetime.fromisoformat(post_data['collected_at'].replace('Z', '+00:00')) if post_data.get('collected_at') else datetime.utcnow(),
                    category=post_data.get('category'),
                    status=post_data.get('status', 'new')
                )
                session.add(analyzed_post)
            
            session.commit()
            logger.info(f"Saved {len(analyzed_posts)} analyzed posts to database")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save analyzed posts: {e}")
            raise
        finally:
            session.close()
    
    def get_active_accounts(self, platform: str = None):
        """獲取活躍的帳號列表"""
        session = self.get_session()
        try:
            query = session.query(Account).filter_by(active=True)
            if platform:
                query = query.filter_by(platform=platform)
            
            accounts = query.all()
            return [
                {
                    'platform': acc.platform,
                    'username': acc.username,
                    'display_name': acc.display_name,
                    'category': acc.category,
                    # 移除priority回傳
                }
                for acc in accounts
            ]
            
        except Exception as e:
            logger.error(f"Failed to get active accounts: {e}")
            return []
        finally:
            session.close()
    
    def log_processing(self, level: str, message: str, platform: str = None, username: str = None, details: dict = None):
        """記錄處理日誌"""
        session = self.get_session()
        try:
            log_entry = ProcessingLog(
                level=level,
                message=message,
                platform=platform,
                username=username,
                details=details
            )
            session.add(log_entry)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save processing log: {e}")
        finally:
            session.close()
    
    def save_human_feedback(self, feedback_data: dict):
        """保存人工反饋"""
        session = self.get_session()
        try:
            feedback = HumanFeedback(
                analyzed_post_id=feedback_data['analyzed_post_id'],
                platform=feedback_data['platform'],
                original_post_id=feedback_data['original_post_id'],
                ai_score=feedback_data.get('ai_score'),
                human_score=feedback_data['human_score'],
                feedback_reason=feedback_data.get('feedback_reason'),
                feedback_category=feedback_data.get('feedback_category'),
                reviewer_notes=feedback_data.get('reviewer_notes'),
                prompt_version_id=feedback_data.get('prompt_version_id')
            )
            session.add(feedback)
            session.commit()
            logger.info(f"Saved human feedback for post {feedback_data['original_post_id']}")
            return feedback.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save human feedback: {e}")
            raise
        finally:
            session.close()
    
    def get_posts_for_review(self, limit: int = 20, score_range: tuple = None):
        """獲取需要審核的posts"""
        session = self.get_session()
        try:
            # 獲取還沒有人工反饋的分析結果
            query = session.query(AnalyzedPost).outerjoin(
                HumanFeedback, 
                AnalyzedPost.id == HumanFeedback.analyzed_post_id
            ).filter(HumanFeedback.id == None)  # 沒有反饋的
            
            # 如果指定了評分範圍
            if score_range:
                min_score, max_score = score_range
                if min_score is not None:
                    query = query.filter(AnalyzedPost.importance_score >= min_score)
                if max_score is not None:
                    query = query.filter(AnalyzedPost.importance_score <= max_score)
            
            posts = query.order_by(AnalyzedPost.analyzed_at.desc()).limit(limit).all()
            return posts
            
        except Exception as e:
            logger.error(f"Failed to get posts for review: {e}")
            return []
        finally:
            session.close()
    
    def save_prompt_version(self, version_data: dict):
        """保存prompt版本"""
        session = self.get_session()
        try:
            # 如果設為活躍版本，先將其他同類型版本設為非活躍
            if version_data.get('is_active', False):
                session.query(PromptVersion).filter_by(
                    prompt_type=version_data['prompt_type'],
                    is_active=True
                ).update({'is_active': False})
            
            prompt_version = PromptVersion(
                version_name=version_data['version_name'],
                prompt_type=version_data['prompt_type'],
                prompt_content=version_data['prompt_content'],
                description=version_data.get('description'),
                is_active=version_data.get('is_active', False)
            )
            session.add(prompt_version)
            session.commit()
            logger.info(f"Saved prompt version {version_data['version_name']}")
            return prompt_version.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save prompt version: {e}")
            raise
        finally:
            session.close()
    
    def get_active_prompt(self, prompt_type: str):
        """獲取當前活躍的prompt"""
        session = self.get_session()
        try:
            prompt = session.query(PromptVersion).filter_by(
                prompt_type=prompt_type,
                is_active=True
            ).first()
            return prompt
            
        except Exception as e:
            logger.error(f"Failed to get active prompt: {e}")
            return None
        finally:
            session.close()
    
    def get_feedback_statistics(self):
        """獲取反饋統計信息"""
        session = self.get_session()
        try:
            from sqlalchemy import func
            
            # 總反饋數
            total_feedback = session.query(HumanFeedback).count()
            
            # 平均差異
            avg_diff_query = session.query(
                func.avg(func.abs(HumanFeedback.ai_score - HumanFeedback.human_score)).label('avg_diff')
            ).first()
            
            avg_difference = avg_diff_query.avg_diff if avg_diff_query.avg_diff else 0
            
            # 準確性分析（差異在1分以內算準確）
            accurate_count = session.query(HumanFeedback).filter(
                func.abs(HumanFeedback.ai_score - HumanFeedback.human_score) <= 1.0
            ).count()
            
            accuracy_rate = (accurate_count / total_feedback * 100) if total_feedback > 0 else 0
            
            # 按分類統計
            category_stats = session.query(
                HumanFeedback.feedback_category,
                func.count(HumanFeedback.id).label('count')
            ).group_by(HumanFeedback.feedback_category).all()
            
            return {
                'total_feedback': total_feedback,
                'avg_difference': avg_difference,
                'accuracy_rate': accuracy_rate,
                'accurate_count': accurate_count,
                'category_stats': dict(category_stats) if category_stats else {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get feedback statistics: {e}")
            return {}
        finally:
            session.close()
    
    def get_twitter_user_cache(self, username: str):
        """獲取 Twitter 用戶緩存"""
        session = self.get_session()
        try:
            from datetime import datetime
            now = datetime.utcnow()
            
            cache = session.query(TwitterUserCache).filter_by(username=username).first()
            
            # 檢查緩存是否過期
            if cache and cache.expires_at and cache.expires_at > now:
                return {
                    'user_id': cache.user_id,
                    'display_name': cache.display_name,
                    'followers_count': cache.followers_count
                }
            elif cache and cache.expires_at and cache.expires_at <= now:
                # 緩存過期，刪除
                session.delete(cache)
                session.commit()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Twitter user cache: {e}")
            return None
        finally:
            session.close()
    
    def save_twitter_user_cache(self, username: str, user_data: dict, cache_days: int = 30):
        """保存 Twitter 用戶緩存"""
        session = self.get_session()
        try:
            from datetime import datetime, timedelta
            
            # 檢查是否已存在
            existing = session.query(TwitterUserCache).filter_by(username=username).first()
            
            expires_at = datetime.utcnow() + timedelta(days=cache_days)
            
            if existing:
                # 更新現有記錄
                existing.user_id = user_data['user_id']
                existing.display_name = user_data.get('display_name')
                existing.followers_count = user_data.get('followers_count')
                existing.updated_at = datetime.utcnow()
                existing.expires_at = expires_at
            else:
                # 創建新記錄
                cache = TwitterUserCache(
                    username=username,
                    user_id=user_data['user_id'],
                    display_name=user_data.get('display_name'),
                    followers_count=user_data.get('followers_count'),
                    expires_at=expires_at
                )
                session.add(cache)
            
            session.commit()
            logger.info(f"Saved Twitter user cache for {username}")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save Twitter user cache: {e}")
        finally:
            session.close()
    
    def log_api_usage(self, platform: str, endpoint: str, username: str = None, 
                     success: bool = True, error_message: str = None,
                     rate_limit_remaining: int = None, rate_limit_reset = None,
                     response_time_ms: int = None):
        """記錄 API 使用情況"""
        session = self.get_session()
        try:
            usage_log = APIUsageLog(
                platform=platform,
                endpoint=endpoint,
                username=username,
                success=success,
                error_message=error_message,
                rate_limit_remaining=rate_limit_remaining,
                rate_limit_reset=rate_limit_reset,
                response_time_ms=response_time_ms
            )
            session.add(usage_log)
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log API usage: {e}")
        finally:
            session.close()
    
    def get_api_usage_stats(self, platform: str = None, hours: int = 24):
        """獲取 API 使用統計"""
        session = self.get_session()
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(APIUsageLog).filter(APIUsageLog.timestamp >= cutoff_time)
            if platform:
                query = query.filter(APIUsageLog.platform == platform)
            
            logs = query.all()
            
            stats = {
                'total_calls': len(logs),
                'successful_calls': len([log for log in logs if log.success]),
                'failed_calls': len([log for log in logs if not log.success]),
                'endpoints': {},
                'avg_response_time': 0
            }
            
            # 按端點統計
            for endpoint_name in set(log.endpoint for log in logs):
                endpoint_logs = [log for log in logs if log.endpoint == endpoint_name]
                stats['endpoints'][endpoint_name] = {
                    'total': len(endpoint_logs),
                    'successful': len([log for log in endpoint_logs if log.success]),
                    'failed': len([log for log in endpoint_logs if not log.success])
                }
            
            # 平均響應時間
            response_times = [log.response_time_ms for log in logs if log.response_time_ms]
            if response_times:
                stats['avg_response_time'] = sum(response_times) / len(response_times)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get API usage stats: {e}")
            return {}
        finally:
            session.close()

# 全局數據庫實例
db_manager = DatabaseManager()