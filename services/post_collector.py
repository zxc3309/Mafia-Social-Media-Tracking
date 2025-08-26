import logging
import os
from typing import List, Dict, Any
from datetime import datetime
from clients.google_sheets_client import GoogleSheetsClient
from clients.linkedin_client import LinkedInClient
from clients.ai_client import AIClient
from models.database import db_manager
from config import PLATFORMS, IMPORTANCE_THRESHOLD, NITTER_INSTANCES, TWITTER_CLIENT_PRIORITY, OUTPUT_WORKSHEET_NAME, ALL_POSTS_WORKSHEET_NAME

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
                elif client_type == "agent":
                    if self._try_agent_client():
                        return
                else:
                    logger.warning(f"Unknown client type: {client_type}")
            except Exception as e:
                logger.error(f"Failed to initialize {client_type} client: {e}")
                continue
        
        # 如果所有客戶端都失敗，記錄錯誤
        logger.error("All configured Twitter clients failed")
        logger.warning("No Twitter client available - Twitter functionality will be disabled")
        self.x_client = None
    
    
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
    
    def _try_agent_client(self) -> bool:
        """嘗試初始化 agent-twitter-client"""
        try:
            from clients.x_agent_client import XAgentClient
            
            # 檢查配置
            if not os.getenv('TWITTER_USERNAME') or not os.getenv('TWITTER_PASSWORD'):
                logger.info("Twitter credentials not configured for Agent Client, skipping")
                return False
            
            agent_client = XAgentClient()
            
            # 測試連接
            if agent_client.is_available():
                self.x_client = agent_client
                logger.info("✓ X (Twitter) Agent client initialized successfully")
                logger.info(f"Using agent-twitter-client with account: {os.getenv('TWITTER_USERNAME')}")
                return True
            else:
                logger.warning("✗ Agent client not available")
                return False
                
        except Exception as e:
            logger.warning(f"Agent client initialization failed: {e}")
            return False
    
    
    
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
            
            # 3. 獲取已存在的貼文，用於去重
            # 同時檢查 URL 和 post_id
            existing_urls = set(self.sheets_client.get_existing_post_urls())
            
            # 從兩個工作表獲取已存在的 post_ids
            existing_post_ids_output = self.sheets_client.get_existing_post_ids(OUTPUT_WORKSHEET_NAME)
            existing_post_ids_all = self.sheets_client.get_existing_post_ids(ALL_POSTS_WORKSHEET_NAME)
            
            # 合併所有已存在的 post_ids
            all_existing_post_ids = {}
            for platform in set(list(existing_post_ids_output.keys()) + list(existing_post_ids_all.keys())):
                all_existing_post_ids[platform] = set()
                if platform in existing_post_ids_output:
                    all_existing_post_ids[platform].update(existing_post_ids_output[platform])
                if platform in existing_post_ids_all:
                    all_existing_post_ids[platform].update(existing_post_ids_all[platform])
            
            logger.info(f"Total existing posts - URLs: {len(existing_urls)}, Post IDs: {sum(len(ids) for ids in all_existing_post_ids.values())}")
            
            # 4. 收集所有平台的貼文
            all_posts = []
            
            for account in accounts:
                if not account.get('active', True):
                    continue
                
                platform = account['platform'].lower()
                username = account['username']
                
                try:
                    posts = self._collect_posts_for_account(platform, username)
                    
                    # 去重：同時檢查 URL 和 post_id
                    new_posts = []
                    url_duplicates = 0
                    id_duplicates = 0
                    
                    for post in posts:
                        post_url = post.get('post_url')
                        post_id = post.get('post_id')
                        post_platform = post.get('platform', '').lower()
                        
                        # 檢查 URL 重複
                        if post_url and post_url in existing_urls:
                            url_duplicates += 1
                            logger.debug(f"Skipping duplicate URL: {post_url}")
                            continue
                        
                        # 檢查 post_id 重複
                        if post_id and post_platform in all_existing_post_ids and post_id in all_existing_post_ids[post_platform]:
                            id_duplicates += 1
                            logger.debug(f"Skipping duplicate post_id: {post_platform}/{post_id}")
                            continue
                        
                        new_posts.append(post)
                    
                    if new_posts:
                        all_posts.extend(new_posts)
                        logger.info(f"Collected {len(new_posts)} new posts from {platform}/@{username} (filtered {url_duplicates} URL duplicates, {id_duplicates} ID duplicates)")
                    else:
                        if url_duplicates > 0 or id_duplicates > 0:
                            logger.info(f"No new posts from {platform}/@{username} (all {url_duplicates + id_duplicates} posts were duplicates)")
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
            
            # Send Telegram report if enabled and there are important posts
            try:
                if results.get('important_posts', 0) > 0:
                    from services.report_generator import ReportGenerator
                    report_generator = ReportGenerator()
                    report_generator.send_daily_report(results)
            except Exception as e:
                logger.error(f"Failed to send Telegram report: {e}")
                # Don't fail the main process if Telegram fails
        
        return results
    
    def _collect_posts_for_account(self, platform: str, username: str) -> List[Dict[str, Any]]:
        """為單個帳號收集貼文"""
        posts = []
        
        try:
            if platform in ['twitter', 'x']:
                posts = self._collect_twitter_posts_with_fallback(username)
                        
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
    
    def _collect_twitter_posts_with_fallback(self, username: str) -> List[Dict[str, Any]]:
        """使用 fallback 機制收集 Twitter 貼文"""
        posts = []
        
        # 首先嘗試當前客戶端
        if self.x_client:
            current_client_type = type(self.x_client).__name__
            logger.info(f"Trying primary client {current_client_type} for @{username}")
            
            try:
                posts = self.x_client.get_user_tweets(username, days_back=1)
                if posts:
                    logger.info(f"✓ Successfully got {len(posts)} posts from {current_client_type}")
                    return posts
                else:
                    logger.warning(f"Primary client {current_client_type} returned no posts for @{username}")
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Primary client {current_client_type} failed for @{username}: {e}")
                
                # 檢查是否是 TwitterFallbackRequired 異常
                if "twitterfallbackrequired" in str(type(e)).lower() or "twitter error 399" in error_msg:
                    logger.info("Twitter Error 399 or similar detected, immediate fallback required...")
                elif self._should_fallback(error_msg):
                    logger.info("Error indicates need for fallback, trying alternative client...")
                else:
                    logger.info("Attempting fallback due to general error...")
        
        # Fallback: 嘗試其他可用的客戶端
        logger.info(f"Attempting fallback for @{username}")
        return self._try_fallback_clients(username)
    
    def _should_fallback(self, error_msg: str) -> bool:
        """判斷錯誤是否需要 fallback"""
        fallback_indicators = [
            'error 399',
            'incorrect. please try again',
            'authentication',
            'auth',
            'login',
            'blocked',
            'suspended',
            'rate limit',
            'timeout',
            'connection',
            'network'
        ]
        
        return any(indicator in error_msg for indicator in fallback_indicators)
    
    def _try_fallback_clients(self, username: str) -> List[Dict[str, Any]]:
        """嘗試 fallback 客戶端"""
        posts = []
        current_client_type = type(self.x_client).__name__ if self.x_client else "None"
        
        # 根據當前客戶端類型決定 fallback 順序
        if current_client_type == "XAgentClient":
            # 如果當前是 Agent Client，fallback 到 Nitter
            logger.info("Attempting fallback to Nitter...")
            posts = self._try_nitter_fallback(username)
        elif current_client_type == "NitterClient":
            # 如果當前是 Nitter，嘗試 Agent Client（如果有配置）
            logger.info("Attempting fallback to Agent Client...")
            posts = self._try_agent_fallback(username)
        else:
            # 沒有主要客戶端，按優先順序嘗試
            logger.info("No primary client, trying all available clients...")
            for client_type in TWITTER_CLIENT_PRIORITY:
                client_type = client_type.strip().lower()
                if client_type == "agent":
                    posts = self._try_agent_fallback(username)
                elif client_type == "nitter":
                    posts = self._try_nitter_fallback(username)
                
                if posts:
                    break
        
        return posts
    
    def _try_nitter_fallback(self, username: str) -> List[Dict[str, Any]]:
        """嘗試使用 Nitter 作為 fallback"""
        try:
            if not NITTER_INSTANCES:
                logger.info("No Nitter instances configured for fallback")
                return []
            
            from clients.nitter_client import NitterClient
            nitter_client = NitterClient()
            
            if nitter_client.test_connection():
                logger.info("✓ Nitter fallback client available, fetching posts...")
                posts = nitter_client.get_user_tweets(username, days_back=1)
                if posts:
                    logger.info(f"✓ Nitter fallback successful: got {len(posts)} posts for @{username}")
                    return posts
                else:
                    logger.warning("Nitter fallback returned no posts")
            else:
                logger.warning("Nitter fallback unavailable - no working instances")
                
        except Exception as e:
            logger.error(f"Nitter fallback failed for @{username}: {e}")
        
        return []
    
    def _try_agent_fallback(self, username: str) -> List[Dict[str, Any]]:
        """嘗試使用 Agent Client 作為 fallback"""
        try:
            if not os.getenv('TWITTER_USERNAME') or not os.getenv('TWITTER_PASSWORD'):
                logger.info("Twitter credentials not configured, cannot use Agent fallback")
                return []
            
            from clients.x_agent_client import XAgentClient
            agent_client = XAgentClient()
            
            if agent_client.is_available():
                logger.info("✓ Agent fallback client available, fetching posts...")
                posts = agent_client.get_user_tweets(username, days_back=1)
                if posts:
                    logger.info(f"✓ Agent fallback successful: got {len(posts)} posts for @{username}")
                    return posts
                else:
                    logger.warning("Agent fallback returned no posts")
            else:
                logger.warning("Agent fallback unavailable")
                
        except Exception as e:
            logger.error(f"Agent fallback failed for @{username}: {e}")
        
        return []
    
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
            
            # 獲取已存在的 post_ids
            existing_post_ids_output = self.sheets_client.get_existing_post_ids(OUTPUT_WORKSHEET_NAME)
            existing_post_ids_all = self.sheets_client.get_existing_post_ids(ALL_POSTS_WORKSHEET_NAME)
            
            # 合併已存在的 post_ids
            all_existing_post_ids = {}
            for plat in set(list(existing_post_ids_output.keys()) + list(existing_post_ids_all.keys())):
                all_existing_post_ids[plat] = set()
                if plat in existing_post_ids_output:
                    all_existing_post_ids[plat].update(existing_post_ids_output[plat])
                if plat in existing_post_ids_all:
                    all_existing_post_ids[plat].update(existing_post_ids_all[plat])
            
            for account in accounts:
                username = account['username']
                try:
                    posts = self._collect_posts_for_account(platform, username)
                    
                    # 去重：同時檢查 URL 和 post_id
                    new_posts = []
                    for post in posts:
                        post_url = post.get('post_url')
                        post_id = post.get('post_id')
                        post_platform = post.get('platform', '').lower()
                        
                        # 檢查重複
                        if post_url and post_url in existing_urls:
                            continue
                        if post_id and post_platform in all_existing_post_ids and post_id in all_existing_post_ids[post_platform]:
                            continue
                        
                        new_posts.append(post)
                    
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