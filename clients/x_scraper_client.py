import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async
from fake_useragent import UserAgent
from bs4 import BeautifulSoup

from config import SCRAPER_CONFIG, NITTER_INSTANCES
from models.database import db_manager

logger = logging.getLogger(__name__)


class XScraperClient:
    def __init__(self):
        self.config = SCRAPER_CONFIG
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.current_account = None
        self.daily_requests = 0
        self.last_request_time = None
        self.ua = UserAgent()
        self.cookies_dir = Path(self.config['cookies_dir'])
        self.cookies_dir.mkdir(exist_ok=True)
        self.proxy_index = 0
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def initialize(self):
        """初始化瀏覽器和上下文"""
        try:
            playwright = await async_playwright().start()
            
            # 瀏覽器啟動參數
            launch_args = {
                'headless': self.config['headless'],
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                ]
            }
            
            # 如果啟用代理，添加代理配置
            if self.config['proxy_enabled'] and self.config['proxy_list']:
                proxy = self._get_next_proxy()
                if proxy:
                    launch_args['proxy'] = {'server': proxy}
                    logger.info(f"Using proxy: {proxy}")
            
            self.browser = await playwright.chromium.launch(**launch_args)
            
            # 創建瀏覽器上下文，加入反檢測措施
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': self._get_random_user_agent(),
                'locale': 'en-US',
                'timezone_id': 'America/New_York',
                'permissions': ['geolocation'],
                'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},  # New York
                'color_scheme': 'light',
                'device_scale_factor': 1,
                'has_touch': False,
                'java_script_enabled': True,
                'accept_downloads': False,
                'bypass_csp': True,
                'ignore_https_errors': True,
            }
            
            self.context = await self.browser.new_context(**context_options)
            
            # 添加額外的反檢測腳本
            await self.context.add_init_script("""
                // 覆蓋 navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // 覆蓋 chrome
                window.chrome = {
                    runtime: {},
                };
                
                // 覆蓋 permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // 覆蓋 plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // 覆蓋 languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            # 創建頁面
            self.page = await self.context.new_page()
            
            # 應用 stealth 插件
            await stealth_async(self.page)
            
            # 設置額外的請求頭
            await self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            logger.info("Browser initialized with anti-detection measures")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
            
    async def close(self):
        """關閉瀏覽器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
            
    def _get_random_user_agent(self) -> str:
        """獲取隨機的 User Agent"""
        # 如果有自定義的 user agents 文件
        if os.path.exists(self.config['user_agents_file']):
            with open(self.config['user_agents_file'], 'r') as f:
                agents = f.read().strip().split('\n')
                return random.choice(agents)
        # 否則使用 fake-useragent
        return self.ua.random
        
    def _get_next_proxy(self) -> Optional[str]:
        """獲取下一個代理"""
        if not self.config['proxy_list']:
            return None
        proxy = self.config['proxy_list'][self.proxy_index % len(self.config['proxy_list'])]
        self.proxy_index += 1
        return proxy.strip() if proxy else None
        
    async def _random_delay(self):
        """隨機延遲"""
        delay = random.uniform(self.config['min_delay'], self.config['max_delay'])
        await asyncio.sleep(delay)
        
    async def _human_like_scroll(self):
        """模擬人類滾動行為"""
        # 隨機滾動幾次
        scroll_times = random.randint(3, 7)
        for _ in range(scroll_times):
            # 隨機滾動距離
            scroll_distance = random.randint(300, 700)
            await self.page.evaluate(f'window.scrollBy(0, {scroll_distance})')
            # 隨機停留時間
            await asyncio.sleep(random.uniform(0.5, 2))
            
    async def _human_like_mouse_movement(self):
        """模擬人類鼠標移動"""
        # 獲取視窗大小
        viewport = self.page.viewport_size
        if viewport:
            # 隨機移動鼠標幾次
            for _ in range(random.randint(2, 5)):
                x = random.randint(0, viewport['width'])
                y = random.randint(0, viewport['height'])
                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
    async def _check_rate_limit(self) -> bool:
        """檢查是否超過速率限制"""
        # 檢查每日限制
        if self.daily_requests >= self.config['daily_limit']:
            logger.warning(f"Daily limit reached: {self.daily_requests}/{self.config['daily_limit']}")
            return False
            
        # 檢查請求間隔
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.config['min_delay']:
                await asyncio.sleep(self.config['min_delay'] - elapsed)
                
        return True
        
    async def _save_cookies(self, username: str):
        """保存 cookies"""
        cookies = await self.context.cookies()
        cookie_file = self.cookies_dir / f"{username}_cookies.json"
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"Saved cookies for {username}")
        
    async def _load_cookies(self, username: str) -> bool:
        """加載 cookies"""
        cookie_file = self.cookies_dir / f"{username}_cookies.json"
        if cookie_file.exists():
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
            await self.context.add_cookies(cookies)
            logger.info(f"Loaded cookies for {username}")
            return True
        return False
        
    async def login(self, username: str, password: str) -> bool:
        """登入 X/Twitter"""
        try:
            logger.info(f"Attempting to login as {username}")
            
            # 嘗試加載已保存的 cookies
            if await self._load_cookies(username):
                # 檢查是否仍然登入
                await self.page.goto('https://x.com/home', wait_until='networkidle')
                await self._random_delay()
                
                # 檢查是否在首頁
                if await self.page.query_selector('[data-testid="primaryColumn"]'):
                    logger.info(f"Already logged in as {username}")
                    self.current_account = username
                    return True
                    
            # 需要重新登入
            await self.page.goto('https://x.com/login', wait_until='networkidle')
            await self._random_delay()
            
            # 輸入用戶名
            username_input = await self.page.wait_for_selector('input[autocomplete="username"]', timeout=30000)
            await username_input.click()
            await username_input.type(username, delay=random.randint(50, 150))
            await self._random_delay()
            
            # 點擊下一步
            next_button = await self.page.query_selector('text=Next')
            if next_button:
                await next_button.click()
                await self._random_delay()
                
            # 輸入密碼
            password_input = await self.page.wait_for_selector('input[type="password"]', timeout=30000)
            await password_input.click()
            await password_input.type(password, delay=random.randint(50, 150))
            await self._random_delay()
            
            # 點擊登入
            login_button = await self.page.query_selector('text=Log in')
            if login_button:
                await login_button.click()
                await self.page.wait_for_load_state('networkidle')
                
            # 檢查是否登入成功
            await asyncio.sleep(5)  # 等待頁面完全加載
            if await self.page.query_selector('[data-testid="primaryColumn"]'):
                logger.info(f"Successfully logged in as {username}")
                self.current_account = username
                await self._save_cookies(username)
                return True
            else:
                logger.error(f"Login failed for {username}")
                return False
                
        except Exception as e:
            logger.error(f"Login error for {username}: {e}")
            return False
            
    async def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """獲取用戶推文"""
        posts = []
        
        try:
            # 檢查速率限制
            if not await self._check_rate_limit():
                return posts
                
            # 移除 @ 符號
            username = username.lstrip('@')
            
            # 訪問用戶頁面
            user_url = f"https://x.com/{username}"
            await self.page.goto(user_url, wait_until='networkidle')
            await self._random_delay()
            
            # 檢查用戶是否存在  
            if await self.page.query_selector("text=This account doesn't exist"):
                logger.warning(f"User {username} not found")
                return posts
                
            # 獲取用戶信息
            user_info = await self._extract_user_info(username)
            if user_info:
                # 保存到緩存
                db_manager.save_twitter_user_cache(username, {
                    'user_id': user_info.get('user_id', username),
                    'display_name': user_info.get('display_name', username),
                    'followers_count': user_info.get('followers_count', 0)
                })
                
            # 模擬人類行為
            await self._human_like_scroll()
            await self._human_like_mouse_movement()
            
            # 獲取推文
            tweets = await self._extract_tweets(username, days_back)
            
            # 處理推文數據
            for tweet_data in tweets:
                post_data = {
                    'platform': 'twitter',
                    'post_id': tweet_data['tweet_id'],
                    'author_username': username,
                    'author_display_name': user_info.get('display_name', username) if user_info else username,
                    'original_content': tweet_data['content'],
                    'post_time': tweet_data['timestamp'],
                    'post_url': tweet_data['url'],
                    'metrics': tweet_data.get('metrics', {}),
                    'language': 'unknown',  # 爬蟲難以準確獲取語言
                    'collected_at': datetime.utcnow().isoformat(),
                    'collection_method': 'scraper'
                }
                posts.append(post_data)
                
            logger.info(f"Scraped {len(posts)} tweets from @{username}")
            
            # 更新請求計數
            self.daily_requests += 1
            self.last_request_time = time.time()
            
        except Exception as e:
            logger.error(f"Error scraping tweets for {username}: {e}")
            
        return posts
        
    async def _extract_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """提取用戶信息"""
        try:
            # 等待用戶信息加載
            await self.page.wait_for_selector('[data-testid="UserName"]', timeout=10000)
            
            user_info = {}
            
            # 獲取顯示名稱
            display_name_elem = await self.page.query_selector('[data-testid="UserName"] > div > div > div > span')
            if display_name_elem:
                user_info['display_name'] = await display_name_elem.text_content()
                
            # 獲取關注者數量（需要更精確的選擇器）
            followers_elem = await self.page.query_selector('a[href$="/followers"] span')
            if followers_elem:
                followers_text = await followers_elem.text_content()
                # 轉換 K, M 等單位
                user_info['followers_count'] = self._parse_metric_count(followers_text)
                
            return user_info
            
        except Exception as e:
            logger.error(f"Error extracting user info: {e}")
            return None
            
    async def _extract_tweets(self, username: str, days_back: int) -> List[Dict[str, Any]]:
        """提取推文數據"""
        tweets = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            # 滾動加載更多推文
            max_scrolls = 10
            no_new_tweets_count = 0
            
            for scroll_count in range(max_scrolls):
                # 獲取當前所有推文元素
                tweet_elements = await self.page.query_selector_all('article[data-testid="tweet"]')
                
                for elem in tweet_elements:
                    try:
                        tweet_data = await self._parse_tweet_element(elem, username)
                        if tweet_data:
                            # 檢查時間
                            tweet_time = datetime.fromisoformat(tweet_data['timestamp'].replace('Z', '+00:00'))
                            if tweet_time < cutoff_date:
                                # 已經超過時間範圍，停止
                                return tweets
                                
                            # 檢查是否已經存在
                            if not any(t['tweet_id'] == tweet_data['tweet_id'] for t in tweets):
                                tweets.append(tweet_data)
                                
                    except Exception as e:
                        logger.error(f"Error parsing tweet: {e}")
                        continue
                        
                # 檢查是否有新推文
                current_count = len(tweets)
                if scroll_count > 0 and current_count == len(tweets):
                    no_new_tweets_count += 1
                    if no_new_tweets_count >= 3:
                        # 連續3次沒有新推文，停止
                        break
                else:
                    no_new_tweets_count = 0
                    
                # 滾動加載更多
                await self._human_like_scroll()
                await self._random_delay()
                
        except Exception as e:
            logger.error(f"Error extracting tweets: {e}")
            
        return tweets
        
    async def _parse_tweet_element(self, element, username: str) -> Optional[Dict[str, Any]]:
        """解析單個推文元素"""
        try:
            tweet_data = {}
            
            # 獲取推文連結和ID
            link_elem = await element.query_selector(f'a[href*="/{username}/status/"]')
            if link_elem:
                href = await link_elem.get_attribute('href')
                tweet_id = href.split('/')[-1]
                tweet_data['tweet_id'] = tweet_id
                tweet_data['url'] = f"https://x.com{href}"
            else:
                return None
                
            # 獲取推文內容
            content_elem = await element.query_selector('[data-testid="tweetText"]')
            if content_elem:
                tweet_data['content'] = await content_elem.text_content()
            else:
                tweet_data['content'] = ""
                
            # 獲取時間戳
            time_elem = await element.query_selector('time')
            if time_elem:
                datetime_str = await time_elem.get_attribute('datetime')
                tweet_data['timestamp'] = datetime_str
            else:
                tweet_data['timestamp'] = datetime.utcnow().isoformat()
                
            # 獲取互動指標
            metrics = {}
            
            # 點贊數
            like_elem = await element.query_selector('[data-testid="like"] span')
            if like_elem:
                like_text = await like_elem.text_content()
                metrics['likes'] = self._parse_metric_count(like_text)
                
            # 轉推數
            retweet_elem = await element.query_selector('[data-testid="retweet"] span')
            if retweet_elem:
                retweet_text = await retweet_elem.text_content()
                metrics['retweets'] = self._parse_metric_count(retweet_text)
                
            # 回覆數
            reply_elem = await element.query_selector('[data-testid="reply"] span')
            if reply_elem:
                reply_text = await reply_elem.text_content()
                metrics['replies'] = self._parse_metric_count(reply_text)
                
            tweet_data['metrics'] = metrics
            
            return tweet_data
            
        except Exception as e:
            logger.error(f"Error parsing tweet element: {e}")
            return None
            
    def _parse_metric_count(self, text: str) -> int:
        """解析指標數字（處理 K, M 等單位）"""
        if not text:
            return 0
            
        text = text.strip().upper()
        
        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(text.replace(',', ''))
        except:
            return 0
            
    async def use_nitter_fallback(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """使用 Nitter 作為備用方案"""
        posts = []
        
        if not NITTER_INSTANCES:
            logger.warning("No Nitter instances configured")
            return posts
            
        # 隨機選擇一個 Nitter 實例
        nitter_instance = random.choice(NITTER_INSTANCES).strip()
        
        try:
            username = username.lstrip('@')
            url = f"{nitter_instance}/{username}"
            
            await self.page.goto(url, wait_until='networkidle')
            await self._random_delay()
            
            # 解析 Nitter 頁面（需要根據實際 Nitter HTML 結構調整）
            # 這裡提供基本框架，實際實現需要根據 Nitter 實例的具體結構
            
            logger.info(f"Attempted to use Nitter fallback at {nitter_instance}")
            
        except Exception as e:
            logger.error(f"Nitter fallback failed: {e}")
            
        return posts


# 同步包裝器，方便在現有代碼中使用
class XScraperClientSync:
    def __init__(self):
        self.async_client = XScraperClient()
        
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """同步版本的 get_user_tweets"""
        return asyncio.run(self._get_user_tweets(username, days_back))
        
    async def _get_user_tweets(self, username: str, days_back: int) -> List[Dict[str, Any]]:
        async with self.async_client as client:
            # 如果配置了帳號，嘗試登入
            if client.config['accounts'] and not client.current_account:
                account = random.choice(client.config['accounts'])
                await client.login(account['username'], account['password'])
                
            return await client.get_user_tweets(username, days_back)