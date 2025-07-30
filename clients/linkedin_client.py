import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from bs4 import BeautifulSoup
import json
import re
from config import LINKEDIN_API_KEY, PLATFORMS

logger = logging.getLogger(__name__)

class LinkedInClient:
    def __init__(self):
        self.api_key = LINKEDIN_API_KEY
        self.session = requests.Session()
        self.rate_limiter = RateLimiter(
            requests_per_day=PLATFORMS['linkedin']['rate_limit_per_day']
        )
        self._setup_session()
    
    def _setup_session(self):
        """設置請求會話"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def get_user_posts(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        獲取LinkedIn用戶的貼文
        注意：由於LinkedIn API限制，這裡使用替代方案
        在實際部署時，建議使用正式的LinkedIn API或第三方服務
        """
        posts = []
        
        try:
            # 由於LinkedIn的API限制，這裡提供一個框架
            # 實際實現需要使用LinkedIn Partner API或第三方服務
            
            logger.warning("LinkedIn API access is restricted. Using placeholder implementation.")
            
            # 這是一個示例結構，實際需要根據可用的API進行調整
            if self.api_key:
                posts = self._fetch_posts_via_api(username, days_back)
            else:
                logger.info("No LinkedIn API key configured, skipping LinkedIn data collection")
            
        except Exception as e:
            logger.error(f"Error getting LinkedIn posts for {username}: {e}")
        
        return posts
    
    def _fetch_posts_via_api(self, username: str, days_back: int) -> List[Dict[str, Any]]:
        """
        通過API獲取貼文（需要適當的API訪問權限）
        """
        posts = []
        
        try:
            # 等待速率限制
            self.rate_limiter.wait_if_needed()
            
            # 這裡需要實現實際的LinkedIn API調用
            # 由於LinkedIn API的限制，建議使用以下替代方案：
            # 1. LinkedIn Partner API (需要申請合作夥伴資格)
            # 2. 第三方服務如ScrapFly, Bright Data等
            # 3. 使用專門的LinkedIn數據服務
            
            # 示例API調用結構（需要根據實際API調整）
            # response = self.session.get(
            #     f"https://api.linkedin.com/v2/people/{username}/posts",
            #     headers={'Authorization': f'Bearer {self.api_key}'}
            # )
            
            # 臨時返回空列表，避免實際API調用
            logger.info(f"LinkedIn API call placeholder for user: {username}")
            
        except Exception as e:
            logger.error(f"API call failed for {username}: {e}")
        
        return posts
    
    def get_company_posts(self, company_id: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """獲取公司頁面的貼文"""
        posts = []
        
        try:
            # 等待速率限制
            self.rate_limiter.wait_if_needed()
            
            # 公司貼文API調用
            # 同樣需要適當的API權限
            logger.info(f"LinkedIn company API call placeholder for: {company_id}")
            
        except Exception as e:
            logger.error(f"Error getting company posts: {e}")
        
        return posts
    
    def search_posts(self, keywords: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """搜索LinkedIn貼文"""
        posts = []
        
        try:
            # 等待速率限制
            self.rate_limiter.wait_if_needed()
            
            # 搜索API調用
            logger.info(f"LinkedIn search API call placeholder for: {keywords}")
            
        except Exception as e:
            logger.error(f"Error searching LinkedIn posts: {e}")
        
        return posts
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """獲取用戶基本信息"""
        try:
            # 等待速率限制
            self.rate_limiter.wait_if_needed()
            
            # 用戶信息API調用
            logger.info(f"LinkedIn user info API call placeholder for: {username}")
            
            # 返回示例結構
            return {
                'username': username,
                'display_name': 'Unknown',
                'headline': '',
                'location': '',
                'connections': 0,
                'followers': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting LinkedIn user info: {e}")
            return None
    
    def _create_post_data(self, post_content: dict, author_info: dict) -> Dict[str, Any]:
        """創建標準化的貼文數據結構"""
        return {
            'platform': 'linkedin',
            'post_id': post_content.get('id', ''),
            'author_username': author_info.get('username', ''),
            'author_display_name': author_info.get('display_name', ''),
            'original_content': post_content.get('text', ''),
            'post_time': post_content.get('created_at', ''),
            'post_url': post_content.get('url', ''),
            'metrics': {
                'likes': post_content.get('likes', 0),
                'comments': post_content.get('comments', 0),
                'shares': post_content.get('shares', 0)
            },
            'language': 'unknown',
            'collected_at': datetime.utcnow().isoformat()
        }


class RateLimiter:
    def __init__(self, requests_per_day: int):
        self.requests_per_day = requests_per_day
        self.requests_today = []
        self.last_reset = datetime.now().date()
    
    def wait_if_needed(self):
        today = datetime.now().date()
        
        # 重置日計數器
        if today > self.last_reset:
            self.requests_today = []
            self.last_reset = today
        
        # 檢查是否達到日限制
        if len(self.requests_today) >= self.requests_per_day:
            # 計算到第二天的等待時間
            tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
            wait_seconds = (tomorrow - datetime.now()).total_seconds()
            
            if wait_seconds > 0:
                logger.info(f"Daily rate limit reached, waiting until tomorrow ({wait_seconds/3600:.1f} hours)")
                time.sleep(min(wait_seconds, 3600))  # 最多等待1小時，避免程序長時間掛起
                return
        
        # 記錄請求
        self.requests_today.append(datetime.now())


class LinkedInScrapingClient:
    """
    使用第三方服務進行LinkedIn數據抓取的客戶端
    這是一個更實用的替代方案
    """
    def __init__(self, service_api_key: str = None):
        self.service_api_key = service_api_key
        self.session = requests.Session()
    
    def get_posts_via_service(self, profile_url: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        通過第三方服務獲取LinkedIn貼文
        可以整合如ScrapFly, Bright Data, Apify等服務
        """
        posts = []
        
        try:
            if not self.service_api_key:
                logger.warning("No third-party service API key configured")
                return posts
            
            # 這裡可以整合第三方服務的API
            # 例如：
            # - ScrapFly API
            # - Bright Data API  
            # - Apify API
            
            logger.info(f"Third-party service call placeholder for: {profile_url}")
            
        except Exception as e:
            logger.error(f"Third-party service call failed: {e}")
        
        return posts