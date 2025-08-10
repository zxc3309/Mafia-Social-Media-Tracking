import logging
from typing import List, Dict, Any
from datetime import datetime
from clients.google_sheets_client import GoogleSheetsClient
from clients.x_client import XClient
from clients.linkedin_client import LinkedInClient
from clients.ai_client import AIClient
from models.database import db_manager
from config import PLATFORMS, IMPORTANCE_THRESHOLD, SCRAPER_CONFIG, NITTER_INSTANCES, TWITTER_CLIENT_PRIORITY

logger = logging.getLogger(__name__)

class PostCollector:
    def __init__(self):
        self.sheets_client = GoogleSheetsClient()
        self.x_client = None
        self.linkedin_client = None
        self.ai_client = AIClient()
        
        # 初始化社交媒體客戶端
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化社交媒體客戶端"""
        try:
            if PLATFORMS.get('twitter', {}).get('enabled'):
                self._initialize_twitter_client()
            
            if PLATFORMS.get('linkedin', {}).get('enabled'):
                self.linkedin_client = LinkedInClient()
                logger.info("LinkedIn client initialized")
                
        except Exception as e:
            logger.error(f"Error initializing social media clients: {e}")
            
    def _initialize_twitter_client(self):
        """根據配置的優先順序初始化 Twitter 客戶端"""
        logger.info(f"Twitter client priority order: {TWITTER_CLIENT_PRIORITY}")
        
        for client_type in TWITTER_CLIENT_PRIORITY:
            client_type = client_type.strip().lower()
            
            try:
                if client_type == "nitter":
                    if self._try_nitter_client():
                        return
                elif client_type == "scraper":
                    if self._try_scraper_client():
                        return
                elif client_type == "api":
                    if self._try_api_client():
                        return
                else:
                    logger.warning(f"Unknown client type: {client_type}")
            except Exception as e:
                logger.error(f"Failed to initialize {client_type} client: {e}")
                continue
        
        # 如果所有客戶端都失敗，使用 API 作為最後備案
        logger.error("All Twitter clients failed, using API as last resort")
        self.x_client = XClient()
        logger.info("X (Twitter) API client initialized (emergency fallback)")
    
    def _try_nitter_client(self) -> bool:
        """嘗試初始化 Nitter 客戶端"""
        if not NITTER_INSTANCES:
            logger.info("No Nitter instances configured, skipping")
            return False
            
        from clients.nitter_client import NitterClient
        nitter_client = NitterClient()
        if nitter_client.test_connection():
            self.x_client = nitter_client
            logger.info("✓ X (Twitter) Nitter client initialized successfully")
            logger.info(f"Using {len(nitter_client.working_instances)} working Nitter instances")
            return True
        else:
            logger.warning("✗ No working Nitter instances available")
            return False
    
    def _try_scraper_client(self) -> bool:
        """嘗試初始化 Scraper 客戶端"""
        if not SCRAPER_CONFIG.get('use_scraper', False):
            logger.info("Scraper not enabled in config, skipping")
            return False
            
        if not SCRAPER_CONFIG.get('accounts'):
            logger.warning("No scraper accounts configured, skipping")
            return False
            
        from clients.x_scraper_client import XScraperClientSync
        self.x_client = XScraperClientSync()
        logger.info("✓ X (Twitter) scraper client initialized successfully")
        logger.info(f"Using {len(SCRAPER_CONFIG.get('accounts', []))} scraper accounts")
        return True
    
    def _try_api_client(self) -> bool:
        """嘗試初始化 API 客戶端"""
        from config import X_API_BEARER_TOKEN
        if not X_API_BEARER_TOKEN:
            logger.warning("No X API bearer token configured, skipping")
            return False
            
        self.x_client = XClient()
        logger.info("✓ X (Twitter) API client initialized successfully")
        return True
    
    def collect_all_posts(self) -> Dict[str, Any]:
        """
        收集所有帳號的貼文並進行AI分析
        """
        results = {
            'total_accounts': 0,
            'total_posts_collected': 0,
            'total_posts_analyzed': 0,
            'important_posts': 0,
            'errors': [],
            'start_time': datetime.utcnow().isoformat(),
            'end_time': None
        }
        
        try:
            # 1. 從Google Sheets獲取要追蹤的帳號列表
            accounts = self.sheets_client.get_accounts_to_track()
            results['total_accounts'] = len(accounts)
            
            if not accounts:
                logger.warning("No accounts to track found")
                return results
            
            # 2. 同步帳號到數據庫
            db_manager.save_accounts(accounts)
            
            # 3. 獲取已存在的貼文URL，用於去重
            existing_urls = set(self.sheets_client.get_existing_post_urls())
            
            # 4. 收集所有平台的貼文
            all_posts = []
            
            for account in accounts:
                if not account.get('active', True):
                    continue
                
                platform = account['platform'].lower()
                username = account['username']
                
                try:
                    posts = self._collect_posts_for_account(platform, username)
                    
                    # 去重：過濾已存在的貼文
                    new_posts = [post for post in posts if post.get('post_url') not in existing_urls]
                    
                    if new_posts:
                        all_posts.extend(new_posts)
                        logger.info(f"Collected {len(new_posts)} new posts from {platform}/@{username}")
                    else:
                        logger.info(f"No new posts from {platform}/@{username}")
                        
                except Exception as e:
                    error_msg = f"Error collecting posts from {platform}/@{username}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            results['total_posts_collected'] = len(all_posts)
            
            # 5. 保存原始貼文到數據庫
            if all_posts:
                db_manager.save_posts(all_posts)
            
            # 6. AI分析貼文
            if all_posts:
                analyzed_posts = self._analyze_posts(all_posts)
                results['total_posts_analyzed'] = len(analyzed_posts)
                
                # 7. 統計重要貼文
                important_posts = [post for post in analyzed_posts 
                                 if post.get('importance_score', 0) >= IMPORTANCE_THRESHOLD]
                results['important_posts'] = len(important_posts)
                
                # 8. 保存分析結果到數據庫
                if analyzed_posts:
                    db_manager.save_analyzed_posts(analyzed_posts)
                
                # 9. 將重要貼文寫入Google Sheets
                if important_posts:
                    success = self.sheets_client.write_analyzed_posts(important_posts)
                    if not success:
                        results['errors'].append("Failed to write results to Google Sheets")
                
                # 10. 將所有分析過的貼文寫入All Posts工作表
                if analyzed_posts:
                    all_success = self.sheets_client.write_all_posts_with_scores(analyzed_posts)
                    if not all_success:
                        results['errors'].append("Failed to write all posts to Google Sheets")
                
                logger.info(f"Processing complete: {len(analyzed_posts)} posts analyzed, {len(important_posts)} important posts")
            
        except Exception as e:
            error_msg = f"Critical error in post collection: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        finally:
            results['end_time'] = datetime.utcnow().isoformat()
        
        return results
    
    def _collect_posts_for_account(self, platform: str, username: str) -> List[Dict[str, Any]]:
        """為單個帳號收集貼文"""
        posts = []
        
        try:
            if platform in ['twitter', 'x'] and self.x_client:
                # 記錄是否使用爬蟲
                collection_method = 'scraper' if SCRAPER_CONFIG.get('use_scraper', False) else 'api'
                logger.info(f"Collecting posts for @{username} using {collection_method}")
                
                posts = self.x_client.get_user_tweets(username, days_back=1)
                
                # 為爬蟲收集的貼文添加標記
                if collection_method == 'scraper':
                    for post in posts:
                        post['collection_method'] = 'scraper'
                        
            elif platform == 'linkedin' and self.linkedin_client:
                posts = self.linkedin_client.get_user_posts(username, days_back=1)
            else:
                logger.warning(f"No client available for platform: {platform}")
            
            # 為每個貼文添加帳號分類信息
            for post in posts:
                post['category'] = self._get_account_category(platform, username)
                
        except Exception as e:
            logger.error(f"Error collecting posts for {platform}/@{username}: {e}")
        
        return posts
    
    def _get_account_category(self, platform: str, username: str) -> str:
        """獲取帳號分類"""
        try:
            accounts = db_manager.get_active_accounts(platform)
            for account in accounts:
                if account['username'] == username:
                    return account.get('category', 'general')
        except Exception as e:
            logger.error(f"Error getting account category: {e}")
        
        return 'general'
    
    def _analyze_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用AI分析貼文"""
        try:
            logger.info(f"Starting AI analysis for {len(posts)} posts")
            analyzed_posts = self.ai_client.batch_analyze(posts)
            logger.info(f"AI analysis completed: {len(analyzed_posts)} posts analyzed")
            return analyzed_posts
        
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return []
    
    def collect_posts_by_platform(self, platform: str) -> Dict[str, Any]:
        """收集特定平台的貼文"""
        results = {
            'platform': platform,
            'posts_collected': 0,
            'posts_analyzed': 0,
            'important_posts': 0,
            'errors': []
        }
        
        try:
            # 獲取該平台的活躍帳號
            accounts = db_manager.get_active_accounts(platform)
            
            if not accounts:
                logger.warning(f"No active accounts found for platform: {platform}")
                return results
            
            all_posts = []
            existing_urls = set(self.sheets_client.get_existing_post_urls())
            
            for account in accounts:
                username = account['username']
                try:
                    posts = self._collect_posts_for_account(platform, username)
                    new_posts = [post for post in posts if post.get('post_url') not in existing_urls]
                    all_posts.extend(new_posts)
                    
                except Exception as e:
                    error_msg = f"Error collecting from {username}: {e}"
                    results['errors'].append(error_msg)
            
            results['posts_collected'] = len(all_posts)
            
            if all_posts:
                # 保存到數據庫
                db_manager.save_posts(all_posts)
                
                # AI分析
                analyzed_posts = self._analyze_posts(all_posts)
                results['posts_analyzed'] = len(analyzed_posts)
                
                # 統計重要貼文
                important_posts = [post for post in analyzed_posts 
                                 if post.get('importance_score', 0) >= IMPORTANCE_THRESHOLD]
                results['important_posts'] = len(important_posts)
                
                # 保存分析結果
                if analyzed_posts:
                    db_manager.save_analyzed_posts(analyzed_posts)
                
                # 寫入Google Sheets
                if important_posts:
                    self.sheets_client.write_analyzed_posts(important_posts)
                
                # 同時寫入所有分析過的貼文到All Posts工作表
                if analyzed_posts:
                    self.sheets_client.write_all_posts_with_scores(analyzed_posts)
        
        except Exception as e:
            error_msg = f"Error in platform collection for {platform}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def manual_analyze_post(self, post_url: str) -> Dict[str, Any]:
        """手動分析單個貼文"""
        result = {
            'success': False,
            'post_url': post_url,
            'analysis': None,
            'error': None
        }
        
        try:
            # 這裡可以實現根據URL獲取貼文內容並分析的邏輯
            # 由於API限制，暫時返回佔位符
            logger.info(f"Manual analysis requested for: {post_url}")
            result['success'] = True
            result['analysis'] = "Manual analysis feature to be implemented"
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error in manual analysis: {e}")
        
        return result
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """獲取收集統計信息"""
        try:
            session = db_manager.get_session()
            
            from models.database import Post, AnalyzedPost
            from sqlalchemy import func
            
            # 基本統計
            total_posts = session.query(Post).count()
            total_analyzed = session.query(AnalyzedPost).count()
            
            # 按平台統計
            platform_stats = session.query(
                Post.platform,
                func.count(Post.id).label('count')
            ).group_by(Post.platform).all()
            
            # 重要貼文統計
            important_posts = session.query(AnalyzedPost).filter(
                AnalyzedPost.importance_score >= IMPORTANCE_THRESHOLD
            ).count()
            
            # 今日統計
            from datetime import date
            today = date.today()
            today_posts = session.query(Post).filter(
                func.date(Post.collected_at) == today
            ).count()
            
            # 同時查詢 posts 和 analyzed_posts 表，取最新的
            last_post = session.query(Post).order_by(Post.collected_at.desc()).first()
            last_analyzed = session.query(AnalyzedPost).order_by(AnalyzedPost.collected_at.desc()).first()
            
            # 比較兩個表，使用最新的記錄
            if last_post and last_analyzed:
                if last_post.collected_at > last_analyzed.collected_at:
                    last_collection = last_post.collected_at.isoformat()
                    logger.info(f"📊 Using last collection from posts table: {last_collection}")
                else:
                    last_collection = last_analyzed.collected_at.isoformat()
                    logger.info(f"📊 Using last collection from analyzed_posts table: {last_collection}")
            elif last_analyzed:
                last_collection = last_analyzed.collected_at.isoformat()
                logger.info(f"📊 Only analyzed_posts has data: {last_collection}")
            elif last_post:
                last_collection = last_post.collected_at.isoformat()
                logger.info(f"📊 Only posts table has data: {last_collection}")
            else:
                last_collection = None
                logger.warning("📊 No data in either posts or analyzed_posts tables")
            
            # 獲取最新貼文的發布時間（用於參考）
            latest_post_time = last_post.post_time.isoformat() if (last_post and last_post.post_time) else None
            
            session.close()
            
            return {
                'total_posts': total_posts,
                'total_analyzed': total_analyzed,
                'important_posts': important_posts,
                'today_posts': today_posts,
                'platform_breakdown': {stat.platform: stat.count for stat in platform_stats},
                'last_collection': last_collection,
                'latest_post_time': latest_post_time,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                'error': str(e),
                'last_updated': datetime.utcnow().isoformat()
            }