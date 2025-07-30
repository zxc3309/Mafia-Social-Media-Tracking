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
    priority = Column(String(20), default='medium')
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
    post_id = Column(Integer, nullable=False)  # 關聯到 Post 表
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
                    existing.priority = account_data.get('priority', existing.priority)
                    existing.active = account_data.get('active', existing.active)
                    existing.updated_at = datetime.utcnow()
                else:
                    # 創建新記錄
                    account = Account(
                        platform=account_data['platform'],
                        username=account_data['username'],
                        display_name=account_data.get('display_name'),
                        category=account_data.get('category'),
                        priority=account_data.get('priority', 'medium'),
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
                    'priority': acc.priority
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

# 全局數據庫實例
db_manager = DatabaseManager()