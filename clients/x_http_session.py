"""
HTTP Session 和 Cookie 管理模組
用於 XAuthClient 的會話管理和持久化
"""

import os
import json
import time
import pickle
import logging
import random
from pathlib import Path
from typing import Dict, Optional, Any
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# 真實瀏覽器指紋池 (降低自動化檢測風險)
REAL_BROWSER_PROFILES = [
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec_ch_ua_platform': '"Windows"',
        'sec_ch_ua_mobile': '?0'
    },
    {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'sec_ch_ua': '"Not_A Brand";v="8", "Safari";v="17"',
        'sec_ch_ua_platform': '"macOS"',
        'sec_ch_ua_mobile': '?0'
    },
    {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'sec_ch_ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec_ch_ua_platform': '"macOS"',
        'sec_ch_ua_mobile': '?0'
    },
    {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'sec_ch_ua': None,  # Firefox 不使用 sec-ch-ua
        'sec_ch_ua_platform': None,
        'sec_ch_ua_mobile': None
    }
]


class TwitterHTTPSession:
    """
    Twitter HTTP 會話管理器
    處理 Cookie 持久化、CSRF token 管理和請求頭設置
    """
    
    def __init__(self, username: str = None, cookie_cache_days: int = 7):
        self.username = username
        self.cookie_cache_days = cookie_cache_days
        self.session = requests.Session()
        self.cookies_dir = Path("twitter_cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        
        # 設置重試策略
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 設置基本請求頭
        self._setup_headers()
        
        # 載入已保存的 cookies
        if username:
            self._load_cookies()
    
    def _setup_headers(self):
        """設置完整的瀏覽器請求頭 (使用隨機真實瀏覽器指紋)"""
        # 隨機選擇一個真實的瀏覽器配置
        browser_profile = random.choice(REAL_BROWSER_PROFILES)
        
        headers = {
            'User-Agent': browser_profile['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-TW,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # 添加瀏覽器特定的頭部 (如果存在)
        if browser_profile['sec_ch_ua']:
            headers['sec-ch-ua'] = browser_profile['sec_ch_ua']
        if browser_profile['sec_ch_ua_platform']:
            headers['sec-ch-ua-platform'] = browser_profile['sec_ch_ua_platform']
        if browser_profile['sec_ch_ua_mobile']:
            headers['sec-ch-ua-mobile'] = browser_profile['sec_ch_ua_mobile']
        
        self.session.headers.update(headers)
        logger.debug(f"Using browser profile: {browser_profile['user_agent'][:50]}...")
    
    def set_twitter_headers(self, bearer_token: str, guest_token: str = None):
        """設置 Twitter 特定的請求頭"""
        headers = {
            'authorization': f'Bearer {bearer_token}',
            'x-twitter-auth-type': 'OAuth2Client',
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
            'content-type': 'application/json',
            'Referer': 'https://x.com/',
            'Origin': 'https://x.com'
        }
        
        if guest_token:
            headers['x-guest-token'] = guest_token
            
        self.session.headers.update(headers)
        
        # 設置 CSRF token
        self._update_csrf_token()
    
    def _update_csrf_token(self):
        """從 cookies 中提取並設置 CSRF token"""
        ct0_cookie = self.session.cookies.get('ct0')
        if ct0_cookie:
            self.session.headers['x-csrf-token'] = ct0_cookie
            logger.debug(f"Updated CSRF token: {ct0_cookie[:10]}...")
    
    def get_cookie_file_path(self) -> Path:
        """獲取 cookie 文件路徑"""
        if not self.username:
            return self.cookies_dir / "guest_cookies.json"
        return self.cookies_dir / f"{self.username}_cookies.json"
    
    def _load_cookies(self) -> bool:
        """載入保存的 cookies"""
        cookie_file = self.get_cookie_file_path()
        
        if not cookie_file.exists():
            logger.info(f"No cached cookies found for {self.username or 'guest'}")
            return False
            
        try:
            # 檢查文件年齡
            file_age_days = (time.time() - cookie_file.stat().st_mtime) / 86400
            if file_age_days > self.cookie_cache_days:
                logger.info(f"Cookie cache expired ({file_age_days:.1f} days old)")
                cookie_file.unlink()
                return False
            
            with open(cookie_file, 'r') as f:
                cookies_data = json.load(f)
            
            # 恢復 cookies
            for cookie_data in cookies_data:
                self.session.cookies.set(
                    cookie_data['name'],
                    cookie_data['value'],
                    domain=cookie_data.get('domain'),
                    path=cookie_data.get('path', '/')
                )
            
            logger.info(f"Loaded {len(cookies_data)} cached cookies for {self.username or 'guest'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
    
    def save_cookies(self):
        """保存當前的 cookies"""
        if not self.username:
            return
            
        try:
            cookie_file = self.get_cookie_file_path()
            cookies_data = []
            
            for cookie in self.session.cookies:
                cookies_data.append({
                    'name': cookie.name,
                    'value': cookie.value,
                    'domain': cookie.domain,
                    'path': cookie.path,
                    'secure': cookie.secure,
                    'expires': cookie.expires
                })
            
            with open(cookie_file, 'w') as f:
                json.dump(cookies_data, f, indent=2)
                
            logger.info(f"Saved {len(cookies_data)} cookies for {self.username}")
            
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
    
    def clear_cookies(self):
        """清除所有 cookies"""
        self.session.cookies.clear()
        
        if self.username:
            cookie_file = self.get_cookie_file_path()
            if cookie_file.exists():
                cookie_file.unlink()
                logger.info(f"Cleared cached cookies for {self.username}")
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        發送 HTTP 請求
        自動處理 CSRF token 和錯誤重試
        """
        # 在每次請求前更新 CSRF token
        self._update_csrf_token()
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # 保存 cookies (如果是成功的請求)
            if response.status_code < 400 and self.username:
                self.save_cookies()
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET 請求"""
        return self.request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST 請求"""
        return self.request('POST', url, **kwargs)
    
    def is_logged_in(self) -> bool:
        """檢查是否已登入 (基於 cookies)"""
        # 檢查是否有關鍵的登入 cookies
        required_cookies = ['auth_token', 'ct0']
        
        for cookie_name in required_cookies:
            if not self.session.cookies.get(cookie_name):
                return False
                
        return True
    
    def get_guest_token(self) -> Optional[str]:
        """從 cookies 中獲取 guest token"""
        return self.session.cookies.get('gt')
    
    def close(self):
        """關閉會話"""
        if self.username:
            self.save_cookies()
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CookieManager:
    """Cookie 管理輔助類"""
    
    @staticmethod
    def cleanup_old_cookies(cookies_dir: Path, max_age_days: int = 30):
        """清理過期的 cookie 文件"""
        if not cookies_dir.exists():
            return
            
        current_time = time.time()
        cleaned_count = 0
        
        for cookie_file in cookies_dir.glob("*.json"):
            file_age_days = (current_time - cookie_file.stat().st_mtime) / 86400
            
            if file_age_days > max_age_days:
                try:
                    cookie_file.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned old cookie file: {cookie_file.name}")
                except Exception as e:
                    logger.error(f"Failed to clean {cookie_file.name}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned {cleaned_count} old cookie files")
    
    @staticmethod
    def list_cached_users(cookies_dir: Path) -> list:
        """列出所有有緩存的用戶"""
        if not cookies_dir.exists():
            return []
            
        users = []
        for cookie_file in cookies_dir.glob("*_cookies.json"):
            username = cookie_file.stem.replace('_cookies', '')
            if username != 'guest':
                users.append(username)
                
        return users