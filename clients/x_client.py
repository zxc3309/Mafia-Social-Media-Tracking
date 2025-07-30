import tweepy
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from config import X_API_BEARER_TOKEN, PLATFORMS

logger = logging.getLogger(__name__)

class XClient:
    def __init__(self):
        self.client = None
        self.user_cache = {}  # 緩存用戶信息 {username: {id, name}}
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            if not X_API_BEARER_TOKEN:
                raise ValueError("X API Bearer Token not configured")
            
            self.client = tweepy.Client(
                bearer_token=X_API_BEARER_TOKEN,
                wait_on_rate_limit=False  # 不要無限等待，立即失敗
            )
            
            logger.info("X (Twitter) API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize X API client: {e}")
            raise
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """獲取指定用戶的最近貼文"""
        posts = []
        
        try:
            # 移除 @ 符號如果存在
            username = username.lstrip('@')
            
            # 步驟1: 獲取用戶信息（使用緩存）
            if username in self.user_cache:
                user_id = self.user_cache[username]['id']
                user_display_name = self.user_cache[username]['name']
                logger.info(f"Using cached info for {username} (ID: {user_id})")
            else:
                try:
                    user = self.client.get_user(username=username)
                    if not user.data:
                        logger.warning(f"User {username} not found")
                        return posts
                    
                    user_id = user.data.id
                    user_display_name = user.data.name
                    
                    # 緩存用戶信息
                    self.user_cache[username] = {
                        'id': user_id,
                        'name': user_display_name
                    }
                    logger.info(f"Found and cached user {username} with ID {user_id}")
                    
                except tweepy.TooManyRequests:
                    logger.error(f"Rate limit reached when getting user info for {username}")
                    return posts
                except Exception as e:
                    logger.error(f"Failed to get user info for {username}: {e}")
                    return posts
            
            # 步驟2: 獲取推文 - 使用與測試腳本相同的簡單邏輯
            try:
                tweets_response = self.client.get_users_tweets(
                    id=user_id,
                    max_results=10,  # 大幅減少數量，與測試腳本一致
                    exclude=['retweets', 'replies']  # 排除轉推和回覆，只要原創內容
                )
                tweets = tweets_response.data if tweets_response.data else []
                logger.info(f"Retrieved {len(tweets)} tweets for {username}")
                
            except tweepy.TooManyRequests:
                logger.error(f"Rate limit reached when getting tweets for {username}")
                return posts
            except Exception as e:
                logger.error(f"Failed to get tweets for {username}: {e}")
                tweets = []
            
            for tweet in tweets:
                post_data = {
                    'platform': 'twitter',
                    'post_id': str(tweet.id),
                    'author_username': username,
                    'author_display_name': user_display_name,
                    'original_content': tweet.text,
                    'post_time': tweet.created_at.isoformat() if tweet.created_at else '',
                    'post_url': f"https://twitter.com/{username}/status/{tweet.id}",
                    'metrics': {
                        'likes': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                        'retweets': tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                        'replies': tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                        'quotes': tweet.public_metrics.get('quote_count', 0) if tweet.public_metrics else 0
                    },
                    'language': tweet.lang if hasattr(tweet, 'lang') else 'unknown',
                    'collected_at': datetime.utcnow().isoformat()
                }
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} tweets from @{username}")
            
        except tweepy.TooManyRequests:
            logger.warning(f"Rate limit reached for user {username}")
        except tweepy.NotFound:
            logger.warning(f"User {username} not found")
        except tweepy.Unauthorized:
            logger.error(f"Unauthorized access for user {username}")
        except Exception as e:
            logger.error(f"Error getting tweets for {username}: {e}")
        
        return posts
    
    def search_recent_tweets(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """搜索最近的推文"""
        posts = []
        
        try:
            # Tweepy 會自動處理速率限制 (wait_on_rate_limit=True)
            
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang'],
                user_fields=['name', 'username']
            )
            
            if not tweets.data:
                logger.info(f"No tweets found for query: {query}")
                return posts
            
            # 創建用戶信息映射
            users = {user.id: user for user in tweets.includes.get('users', [])} if tweets.includes else {}
            
            for tweet in tweets.data:
                author = users.get(tweet.author_id)
                author_username = author.username if author else 'unknown'
                author_display_name = author.name if author else 'unknown'
                
                post_data = {
                    'platform': 'twitter',
                    'post_id': str(tweet.id),
                    'author_username': author_username,
                    'author_display_name': author_display_name,
                    'original_content': tweet.text,
                    'post_time': tweet.created_at.isoformat() if tweet.created_at else '',
                    'post_url': f"https://twitter.com/{author_username}/status/{tweet.id}",
                    'metrics': {
                        'likes': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                        'retweets': tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                        'replies': tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                        'quotes': tweet.public_metrics.get('quote_count', 0) if tweet.public_metrics else 0
                    },
                    'language': tweet.lang if hasattr(tweet, 'lang') else 'unknown',
                    'collected_at': datetime.utcnow().isoformat(),
                    'search_query': query
                }
                posts.append(post_data)
            
            logger.info(f"Retrieved {len(posts)} tweets for query: {query}")
            
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
        
        return posts
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """獲取用戶基本信息"""
        try:
            username = username.lstrip('@')
            user = self.client.get_user(
                username=username,
                user_fields=['public_metrics', 'description', 'location', 'verified']
            )
            
            if not user.data:
                return None
            
            return {
                'id': str(user.data.id),
                'username': user.data.username,
                'display_name': user.data.name,
                'description': user.data.description,
                'location': user.data.location,
                'verified': getattr(user.data, 'verified', False),
                'followers_count': user.data.public_metrics.get('followers_count', 0) if user.data.public_metrics else 0,
                'following_count': user.data.public_metrics.get('following_count', 0) if user.data.public_metrics else 0,
                'tweet_count': user.data.public_metrics.get('tweet_count', 0) if user.data.public_metrics else 0,
                'listed_count': user.data.public_metrics.get('listed_count', 0) if user.data.public_metrics else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user info for {username}: {e}")
            return None


class RateLimiter:
    def __init__(self, requests_per_window: int, window_minutes: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_minutes * 60
        self.requests = []
    
    def wait_if_needed(self):
        now = time.time()
        
        # 移除過期的請求記錄
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window_seconds]
        
        # 如果已達到限制，等待
        if len(self.requests) >= self.requests_per_window:
            sleep_time = self.window_seconds - (now - self.requests[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.requests = []
        
        # 記錄這次請求
        self.requests.append(now)