import tweepy
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from config import X_API_BEARER_TOKEN, PLATFORMS
from models.database import db_manager

logger = logging.getLogger(__name__)

class XClient:
    def __init__(self):
        self.client = None
        twitter_config = PLATFORMS.get('twitter', {})
        rate_limit = twitter_config.get('rate_limit_per_15min', 450)
        self.rate_limiter = RateLimiter(requests_per_window=rate_limit, window_minutes=15)
        self.request_delay = twitter_config.get('request_delay_seconds', 1.0)
        self.max_results = twitter_config.get('posts_per_request', 10)
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            if not X_API_BEARER_TOKEN:
                raise ValueError("X API Bearer Token not configured")
            
            self.client = tweepy.Client(
                bearer_token=X_API_BEARER_TOKEN,
                wait_on_rate_limit=True  # 自動等待 rate limit 重置
            )
            
            logger.info("X (Twitter) API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize X API client: {e}")
            raise
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """獲取指定用戶的最近貼文"""
        posts = []
        start_time = time.time()
        
        try:
            # 移除 @ 符號如果存在
            username = username.lstrip('@')
            
            # 步驟1: 獲取用戶信息（使用持久化緩存）
            cached_user = db_manager.get_twitter_user_cache(username)
            
            if cached_user:
                user_id = cached_user['user_id']
                user_display_name = cached_user['display_name']
                logger.info(f"Using cached info for {username} (ID: {user_id})")
            else:
                # 需要從 API 獲取用戶信息
                self.rate_limiter.wait_if_needed()
                time.sleep(self.request_delay)  # 添加請求間隔
                
                try:
                    api_start = time.time()
                    user = self.client.get_user(username=username)
                    api_time = int((time.time() - api_start) * 1000)
                    
                    if not user.data:
                        logger.warning(f"User {username} not found")
                        db_manager.log_api_usage(
                            platform='twitter', 
                            endpoint='get_user',
                            username=username,
                            success=False,
                            error_message='User not found',
                            response_time_ms=api_time
                        )
                        return posts
                    
                    user_id = str(user.data.id)
                    user_display_name = user.data.name
                    
                    # 保存到持久化緩存
                    user_data = {
                        'user_id': user_id,
                        'display_name': user_display_name,
                        'followers_count': user.data.public_metrics.get('followers_count', 0) if user.data.public_metrics else 0
                    }
                    db_manager.save_twitter_user_cache(username, user_data)
                    
                    # 記錄 API 使用
                    db_manager.log_api_usage(
                        platform='twitter',
                        endpoint='get_user',
                        username=username,
                        success=True,
                        response_time_ms=api_time
                    )
                    
                    logger.info(f"Found and cached user {username} with ID {user_id}")
                    
                except tweepy.TooManyRequests as e:
                    error_msg = f"Rate limit reached when getting user info for {username}"
                    logger.error(error_msg)
                    db_manager.log_api_usage(
                        platform='twitter',
                        endpoint='get_user',
                        username=username,
                        success=False,
                        error_message=error_msg
                    )
                    return posts
                except Exception as e:
                    error_msg = f"Failed to get user info for {username}: {e}"
                    logger.error(error_msg)
                    db_manager.log_api_usage(
                        platform='twitter',
                        endpoint='get_user',
                        username=username,
                        success=False,
                        error_message=str(e)
                    )
                    return posts
            
            # 步驟2: 獲取推文
            self.rate_limiter.wait_if_needed()
            time.sleep(self.request_delay)  # 添加請求間隔
            
            try:
                api_start = time.time()
                tweets_response = self.client.get_users_tweets(
                    id=user_id,
                    max_results=self.max_results,  # 使用配置的數量
                    exclude=['retweets', 'replies'],  # 排除轉推和回覆，只要原創內容
                    tweet_fields=['created_at', 'public_metrics', 'lang', 'in_reply_to_user_id', 'referenced_tweets'],
                    expansions=['referenced_tweets.id']  # 展開引用推文資訊以進行額外過濾
                )
                api_time = int((time.time() - api_start) * 1000)
                
                raw_tweets = tweets_response.data if tweets_response.data else []
                logger.info(f"Retrieved {len(raw_tweets)} raw tweets for {username}")
                
                # 手動過濾 replies（因為 API exclude 參數不完全有效）
                tweets = self._filter_replies(raw_tweets, username)
                logger.info(f"After filtering replies: {len(tweets)} original tweets for {username}")
                
                # 記錄成功的API調用
                db_manager.log_api_usage(
                    platform='twitter',
                    endpoint='get_users_tweets',
                    username=username,
                    success=True,
                    response_time_ms=api_time
                )
                
            except tweepy.TooManyRequests as e:
                error_msg = f"Rate limit reached when getting tweets for {username}"
                logger.error(error_msg)
                db_manager.log_api_usage(
                    platform='twitter',
                    endpoint='get_users_tweets',
                    username=username,
                    success=False,
                    error_message=error_msg
                )
                return posts
            except Exception as e:
                error_msg = f"Failed to get tweets for {username}: {e}"
                logger.error(error_msg)
                db_manager.log_api_usage(
                    platform='twitter',
                    endpoint='get_users_tweets',
                    username=username,
                    success=False,
                    error_message=str(e)
                )
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
    
    def _filter_replies(self, tweets, username):
        """手動過濾 replies，因為 API exclude 參數不完全有效"""
        filtered_tweets = []
        
        for tweet in tweets:
            is_reply = False
            
            # 方法 1: 檢查 in_reply_to_user_id
            if hasattr(tweet, 'in_reply_to_user_id') and tweet.in_reply_to_user_id:
                is_reply = True
                logger.debug(f"Filtered reply tweet {tweet.id} (in_reply_to_user_id: {tweet.in_reply_to_user_id})")
            
            # 方法 2: 檢查 referenced_tweets 中是否有 replied_to 類型
            if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
                for ref_tweet in tweet.referenced_tweets:
                    if ref_tweet.type == 'replied_to':
                        is_reply = True
                        logger.debug(f"Filtered reply tweet {tweet.id} (referenced_tweets.type: replied_to)")
                        break
            
            # 方法 3: 檢查推文文本是否以 @username 開頭（常見的回覆模式）
            if tweet.text and tweet.text.strip().startswith('@'):
                is_reply = True
                logger.debug(f"Filtered reply tweet {tweet.id} (starts with @mention)")
            
            if not is_reply:
                filtered_tweets.append(tweet)
            else:
                logger.info(f"Filtered out reply tweet from @{username}: {tweet.text[:50]}...")
        
        return filtered_tweets


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