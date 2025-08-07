import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote

from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup

from config import SCRAPER_CONFIG

logger = logging.getLogger(__name__)


class XScraperPublicSimple:
    """無需登入的 X/Twitter 公開內容爬蟲（簡化版）"""
    
    def __init__(self):
        self.config = SCRAPER_CONFIG
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def initialize(self):
        """初始化瀏覽器"""
        try:
            playwright = await async_playwright().start()
            
            # 瀏覽器啟動參數
            launch_args = {
                'headless': self.config.get('headless', True),
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            }
            
            self.browser = await playwright.chromium.launch(**launch_args)
            
            # 創建新頁面
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            
            self.page = await context.new_page()
            
            # 設置額外的 HTTP 標頭
            await self.page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            })
            
            logger.info("Public scraper (simple) initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize public scraper: {e}")
            raise
            
    async def close(self):
        """關閉瀏覽器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
            
    async def get_user_tweets(self, username: str, days_back: int = 7) -> List[Dict]:
        """獲取用戶的公開推文（無需登入）"""
        posts = []
        
        try:
            logger.info(f"Fetching public tweets for @{username} without login")
            
            # 直接訪問用戶頁面
            url = f"https://x.com/{username}"
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # 等待頁面加載
            await asyncio.sleep(random.uniform(3, 5))
            
            # 檢查頁面是否正常加載
            page_content = await self.page.content()
            if 'Something went wrong' in page_content:
                logger.error(f"X.com returned error page for {username}")
                return posts
            
            # 嘗試關閉可能的彈窗
            try:
                close_buttons = await self.page.query_selector_all('[aria-label="Close"]')
                for button in close_buttons:
                    await button.click()
                    await asyncio.sleep(0.5)
            except:
                pass
            
            # 滾動獲取更多內容
            scroll_count = 0
            max_scrolls = 3  # 減少滾動次數
            last_tweet_count = 0
            
            while scroll_count < max_scrolls:
                # 獲取當前頁面的推文
                tweet_elements = await self.page.query_selector_all('article')
                
                for tweet_elem in tweet_elements:
                    try:
                        # 提取推文內容
                        tweet_data = await self._extract_tweet_data_simple(tweet_elem, username)
                        if tweet_data and tweet_data['post_id'] not in [p['post_id'] for p in posts]:
                            posts.append(tweet_data)
                            
                    except Exception as e:
                        logger.debug(f"Error extracting tweet: {e}")
                        continue
                
                # 檢查是否有新推文
                current_tweet_count = len(posts)
                if current_tweet_count == last_tweet_count:
                    logger.debug("No new tweets found after scrolling")
                    break
                    
                last_tweet_count = current_tweet_count
                
                # 滾動頁面
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(random.uniform(2, 3))
                
                scroll_count += 1
                
            logger.info(f"Collected {len(posts)} public tweets from @{username}")
            
        except Exception as e:
            logger.error(f"Error fetching public tweets for {username}: {e}")
            
        return posts
        
    async def _extract_tweet_data_simple(self, tweet_elem, username: str) -> Optional[Dict]:
        """從推文元素提取數據（簡化版）"""
        try:
            # 獲取推文文本
            text_content = await tweet_elem.text_content()
            if not text_content or len(text_content) < 10:
                return None
            
            # 嘗試獲取連結以提取 ID
            links = await tweet_elem.query_selector_all('a')
            post_id = None
            post_url = None
            
            for link in links:
                href = await link.get_attribute('href')
                if href and '/status/' in href:
                    post_id = href.split('/status/')[-1].split('?')[0].split('/')[0]
                    if post_id and post_id.isdigit():
                        post_url = f"https://x.com{href}"
                        break
            
            if not post_id:
                # 生成隨機 ID
                post_id = f"pub_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # 提取時間（如果可能）
            time_elem = await tweet_elem.query_selector('time')
            created_at = datetime.utcnow().isoformat()
            if time_elem:
                datetime_str = await time_elem.get_attribute('datetime')
                if datetime_str:
                    created_at = datetime_str
            
            # 構建推文數據
            return {
                'post_id': f"{post_id}#ps",  # 添加 #ps 標記表示公開簡化爬取
                'platform': 'twitter',
                'original_post_id': post_id,
                'author_username': username,
                'author_display_name': username,
                'original_content': text_content[:500],  # 限制長度
                'created_at': created_at,
                'post_url': post_url or f"https://x.com/{username}/status/{post_id}",
                'metrics': {},
                'language': 'unknown',
                'collected_at': datetime.utcnow().isoformat(),
                'collection_method': 'public_scraper_simple'
            }
            
        except Exception as e:
            logger.debug(f"Error extracting tweet data: {e}")
            return None


async def collect_public_tweets(username: str, days_back: int = 7) -> List[Dict]:
    """便捷函數：收集公開推文"""
    try:
        async with XScraperPublicSimple() as scraper:
            return await scraper.get_user_tweets(username, days_back)
    except Exception as e:
        logger.error(f"Failed to collect public tweets: {e}")
        return []