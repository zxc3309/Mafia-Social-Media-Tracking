"""
Twitter HTTP 認證客戶端
基於 agent-twitter-client 技術的 Python 實現
使用帳號密碼登入，提供高速的 GraphQL API 訪問
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

from .x_http_session import TwitterHTTPSession
from .x_auth_flow import TwitterAuthFlow
from .x_endpoints import TwitterEndpoints, TwitterQueryBuilder, TwitterResponseParser
from config import TWITTER_AUTH_CONFIG
from models.database import db_manager

logger = logging.getLogger(__name__)


class XAuthClient:
    """
    Twitter HTTP 認證客戶端
    提供與 XScraperClient 相同的介面，但使用 HTTP 請求而非瀏覽器
    """
    
    def __init__(self):
        self.config = TWITTER_AUTH_CONFIG
        self.session = None
        self.auth_flow = None
        self.query_builder = TwitterQueryBuilder()
        self.response_parser = TwitterResponseParser()
        self.is_authenticated = False
        self.username = self.config.get('username')
        self.password = self.config.get('password')
        self.email = self.config.get('email')
        self.totp_secret = self.config.get('totp_secret')
        
        if not self.username or not self.password:
            raise ValueError("Twitter username and password must be configured")
    
    async def __aenter__(self):
        """異步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器出口"""
        await self.close()
    
    async def initialize(self):
        """初始化客戶端並嘗試登入"""
        try:
            # 創建 HTTP 會話
            self.session = TwitterHTTPSession(
                username=self.username,
                cookie_cache_days=self.config.get('cookie_cache_days', 7)
            )
            
            # 創建認證流程管理器
            self.auth_flow = TwitterAuthFlow(
                session=self.session,
                bearer_token=self.config['bearer_token']
            )
            
            # 檢查是否已經登入 (基於緩存的 cookies)
            if self.session.is_logged_in():
                # 驗證登入狀態
                if await self.auth_flow.verify_login():
                    self.is_authenticated = True
                    logger.info(f"Already authenticated as {self.username}")
                    return
                else:
                    logger.info("Cached login expired, re-authenticating...")
                    self.session.clear_cookies()
            
            # 執行登入流程
            await self._login()
            
        except Exception as e:
            logger.error(f"Failed to initialize XAuthClient: {e}")
            raise
    
    async def close(self):
        """關閉客戶端"""
        if self.session:
            self.session.close()
    
    async def _login(self):
        """執行登入流程"""
        try:
            success = await self.auth_flow.login_user(
                username=self.username,
                password=self.password,
                email=self.email,
                totp_secret=self.totp_secret
            )
            
            if success:
                self.is_authenticated = True
                logger.info(f"Successfully authenticated as {self.username}")
            else:
                raise Exception("Login failed")
                
        except Exception as e:
            logger.error(f"Login failed for {self.username}: {e}")
            raise
    
    async def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        獲取用戶推文 (與現有介面兼容)
        
        Args:
            username: Twitter 用戶名 (不含 @)
            days_back: 獲取多少天內的推文
            
        Returns:
            List[Dict]: 推文數據列表
        """
        posts = []
        
        try:
            # 確保已認證
            if not self.is_authenticated:
                await self._login()
            
            # 移除 @ 符號
            username = username.lstrip('@')
            
            # 獲取用戶 ID
            user_id = await self._get_user_id(username)
            if not user_id:
                logger.warning(f"Could not find user ID for {username}")
                return posts
            
            # 獲取用戶信息
            user_info = await self._get_user_info(username, user_id)
            
            # 獲取推文
            tweets = await self._fetch_user_tweets(user_id, days_back)
            
            # 轉換為標準格式
            for tweet_data in tweets:
                post_data = self._convert_tweet_to_post(tweet_data, username, user_info)
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} tweets from @{username}")
            
            # 保存用戶信息到緩存
            if user_info:
                db_manager.save_twitter_user_cache(username, {
                    'user_id': user_id,
                    'display_name': user_info.get('name', username),
                    'followers_count': user_info.get('followers_count', 0)
                })
            
            return posts
            
        except Exception as e:
            logger.error(f"Error getting tweets for {username}: {e}")
            return posts
    
    async def _get_user_id(self, username: str) -> Optional[str]:
        """獲取用戶 ID"""
        try:
            # 先檢查緩存
            cached_user = db_manager.get_twitter_user_cache(username)
            if cached_user:
                return cached_user.get('user_id')
            
            # 調用 UserByScreenName GraphQL 查詢
            query_url = TwitterEndpoints.get_user_by_screen_name_url(username)
            response = self.session.get(query_url)
            
            if not response.ok:
                logger.error(f"User lookup failed: {response.status_code} {response.text}")
                return None
            
            data = response.json()
            user_data = self.response_parser.parse_user_by_screen_name_response(data)
            
            if user_data and user_data.get('user_id'):
                # 緩存用戶信息
                db_manager.save_twitter_user_cache(username, {
                    'user_id': user_data['user_id'],
                    'display_name': user_data.get('name', username),
                    'followers_count': user_data.get('followers_count', 0)
                })
                
                logger.info(f"Successfully looked up user ID for @{username}: {user_data['user_id']}")
                return user_data['user_id']
            else:
                logger.warning(f"User @{username} not found")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get user ID for {username}: {e}")
            return None
    
    async def _get_user_info(self, username: str, user_id: str) -> Optional[Dict[str, Any]]:
        """獲取用戶詳細信息"""
        try:
            # 先檢查緩存
            cached_user = db_manager.get_twitter_user_cache(username)
            if cached_user:
                return {
                    'name': cached_user.get('display_name', username),
                    'screen_name': username,
                    'followers_count': cached_user.get('followers_count', 0)
                }
            
            # 實際實現需要調用相應的 GraphQL 查詢
            # 這裡返回基礎信息
            return {
                'name': username,
                'screen_name': username,
                'followers_count': 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get user info for {username}: {e}")
            return None
    
    async def _fetch_user_tweets(self, user_id: str, days_back: int) -> List[Dict[str, Any]]:
        """獲取用戶推文"""
        tweets = []
        cursor = None
        cutoff_date = datetime.now() - timedelta(days=days_back)
        max_requests = 5  # 限制最大請求次數
        request_count = 0
        
        try:
            while request_count < max_requests:
                request_count += 1
                
                # 構建查詢 URL
                query_url = TwitterEndpoints.get_user_tweets_url(
                    user_id=user_id,
                    count=20,
                    cursor=cursor
                )
                
                # 發送請求
                response = self.session.get(query_url)
                
                if not response.ok:
                    logger.error(f"GraphQL request failed: {response.status_code} {response.text}")
                    break
                
                data = response.json()
                
                # 解析響應
                parsed_data = self.response_parser.parse_user_tweets_response(data)
                
                new_tweets = parsed_data.get('tweets', [])
                if not new_tweets:
                    break
                
                # 檢查推文時間
                for tweet in new_tweets:
                    tweet_time = self._parse_twitter_time(tweet.get('created_at', ''))
                    
                    if tweet_time and tweet_time < cutoff_date:
                        # 已經超過時間範圍，停止獲取
                        return tweets
                    
                    tweets.append(tweet)
                
                # 獲取下一頁游標
                cursor = parsed_data.get('cursor')
                if not cursor or not parsed_data.get('has_more'):
                    break
                
                # 添加隨機延遲避免速率限制 (人類級別的延遲)
                delay = random.uniform(3.0, 7.0)
                await asyncio.sleep(delay)
            
            return tweets
            
        except Exception as e:
            logger.error(f"Failed to fetch user tweets: {e}")
            return tweets
    
    def _parse_twitter_time(self, time_string: str) -> Optional[datetime]:
        """解析 Twitter 時間格式"""
        try:
            if not time_string:
                return None
            
            # Twitter 時間格式示例: "Wed Oct 05 19:45:12 +0000 2022"
            return datetime.strptime(time_string, "%a %b %d %H:%M:%S %z %Y")
            
        except Exception:
            try:
                # ISO 格式: "2022-10-05T19:45:12.000Z"
                return datetime.fromisoformat(time_string.replace('Z', '+00:00'))
            except Exception:
                return None
    
    def _convert_tweet_to_post(self, tweet_data: Dict[str, Any], username: str, 
                              user_info: Dict[str, Any]) -> Dict[str, Any]:
        """將 Twitter API 響應轉換為標準的 post 格式"""
        try:
            tweet_id = tweet_data.get('id') or tweet_data.get('rest_id', '')
            created_at = tweet_data.get('created_at', '')
            full_text = tweet_data.get('full_text', '')
            
            # 構建 post URL
            post_url = f"https://x.com/{username}/status/{tweet_id}" if tweet_id else ""
            
            # 解析時間
            post_time = self._parse_twitter_time(created_at)
            post_time_iso = post_time.isoformat() if post_time else datetime.utcnow().isoformat()
            
            # 構建指標數據
            metrics = {
                'likes': tweet_data.get('favorite_count', 0),
                'retweets': tweet_data.get('retweet_count', 0),
                'replies': tweet_data.get('reply_count', 0),
                'quotes': tweet_data.get('quote_count', 0),
                'views': tweet_data.get('view_count', 0)
            }
            
            # 用戶信息
            user_display_name = user_info.get('name', username) if user_info else username
            
            return {
                'platform': 'twitter',
                'post_id': tweet_id,
                'author_username': username,
                'author_display_name': user_display_name,
                'original_content': full_text,
                'post_time': post_time_iso,
                'post_url': post_url,
                'metrics': metrics,
                'language': tweet_data.get('lang', 'unknown'),
                'collected_at': datetime.utcnow().isoformat(),
                'collection_method': 'x_auth_client'
            }
            
        except Exception as e:
            logger.error(f"Failed to convert tweet to post format: {e}")
            # 返回基礎格式
            return {
                'platform': 'twitter',
                'post_id': tweet_data.get('id', ''),
                'author_username': username,
                'author_display_name': username,
                'original_content': tweet_data.get('full_text', ''),
                'post_time': datetime.utcnow().isoformat(),
                'post_url': '',
                'metrics': {},
                'language': 'unknown',
                'collected_at': datetime.utcnow().isoformat(),
                'collection_method': 'x_auth_client'
            }
    
    def is_available(self) -> bool:
        """檢查客戶端是否可用"""
        # 基本配置檢查
        if not (self.config.get('enabled', True) and
                self.config.get('username') and
                self.config.get('password')):
            return False
        
        # 嘗試簡單的初始化測試
        try:
            session = TwitterHTTPSession(username=None)  # 不需要保存 cookies 的測試
            return True
        except Exception:
            return False


# 同步包裝器，方便在現有代碼中使用
class XAuthClientSync:
    """XAuthClient 的同步包裝器"""
    
    def __init__(self):
        self.async_client = XAuthClient()
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """同步版本的 get_user_tweets"""
        try:
            # 檢查是否已有運行中的事件循環
            loop = asyncio.get_running_loop()
            # 如果有運行中的循環，使用 asyncio.create_task()
            import concurrent.futures
            import threading
            
            def run_in_thread():
                return asyncio.run(self._get_user_tweets(username, days_back))
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
                
        except RuntimeError:
            # 沒有運行中的事件循環，直接使用 asyncio.run()
            return asyncio.run(self._get_user_tweets(username, days_back))
    
    async def _get_user_tweets(self, username: str, days_back: int) -> List[Dict[str, Any]]:
        """內部異步實現"""
        async with self.async_client as client:
            return await client.get_user_tweets(username, days_back)
    
    def is_available(self) -> bool:
        """檢查客戶端是否可用"""
        return self.async_client.is_available()