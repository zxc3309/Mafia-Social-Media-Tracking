import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config import NITTER_INSTANCES

logger = logging.getLogger(__name__)


class NitterClient:
    """使用 Nitter 實例收集 Twitter 數據的客戶端"""
    
    def __init__(self):
        self.instances = NITTER_INSTANCES or []
        self.timeout = httpx.Timeout(30.0)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.working_instances = []
        self.last_instance_check = None
        self.instance_check_interval = 3600  # 每小時檢查一次
        
    def _get_working_instance(self) -> Optional[str]:
        """獲取一個可用的 Nitter 實例"""
        # 定期檢查實例可用性
        current_time = time.time()
        if (not self.working_instances or 
            not self.last_instance_check or 
            current_time - self.last_instance_check > self.instance_check_interval):
            self._check_instances()
            
        if self.working_instances:
            return random.choice(self.working_instances)
        return None
        
    def _check_instances(self):
        """檢查哪些 Nitter 實例可用"""
        logger.info("Checking Nitter instances availability...")
        self.working_instances = []
        
        for instance in self.instances:
            try:
                # 清理實例 URL
                instance = instance.strip().rstrip('/')
                
                # 測試實例是否可用
                with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
                    response = client.get(f"{instance}/Twitter", headers=self.headers)
                    if response.status_code == 200:
                        self.working_instances.append(instance)
                        logger.info(f"✓ Nitter instance working: {instance}")
                    else:
                        logger.warning(f"✗ Nitter instance returned {response.status_code}: {instance}")
            except Exception as e:
                logger.warning(f"✗ Nitter instance failed: {instance} - {e}")
                
        self.last_instance_check = time.time()
        logger.info(f"Found {len(self.working_instances)} working Nitter instances")
        
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """從 Nitter 獲取用戶推文"""
        posts = []
        username = username.lstrip('@')
        
        if not self.working_instances:
            logger.error("No working Nitter instances available")
            return posts
        
        # 嘗試所有可用的實例
        for instance in self.working_instances:
            try:
                url = f"{instance}/{username}"
                logger.info(f"Fetching tweets from Nitter: {url}")
                
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, headers=self.headers)
                    
                    if response.status_code == 404:
                        logger.warning(f"User {username} not found on Nitter")
                        return posts
                    
                    if response.status_code == 429:
                        logger.warning(f"Rate limited on {instance}, trying next instance...")
                        continue
                        
                    if response.status_code != 200:
                        logger.warning(f"Nitter {instance} returned status {response.status_code}, trying next...")
                        continue
                    
                # 解析 HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 獲取用戶信息
                user_info = self._extract_user_info(soup, username)
                
                # 獲取推文
                tweets = self._extract_tweets(soup, username, instance, days_back)
                
                for tweet_data in tweets:
                    post_data = {
                        'platform': 'twitter',
                        'post_id': tweet_data['tweet_id'],
                        'author_username': username,
                        'author_display_name': user_info.get('display_name', username),
                        'original_content': tweet_data['content'],
                        'post_time': tweet_data['timestamp'],
                        'post_url': tweet_data['url'],
                        'metrics': tweet_data.get('metrics', {}),
                        'language': 'unknown',
                        'collected_at': datetime.utcnow().isoformat(),
                        'collection_method': 'nitter'
                    }
                    posts.append(post_data)
                
                # 處理完所有推文後才記錄和返回
                logger.info(f"Collected {len(posts)} tweets from Nitter for @{username}")
                return posts  # 成功後返回
                    
            except Exception as e:
                logger.error(f"Error fetching from {instance}: {e}")
                continue  # 嘗試下一個實例
        
        # 如果所有實例都失敗，嘗試使用公開爬蟲
        logger.warning(f"All Nitter instances failed for @{username}, trying public scraper as fallback")
        
        try:
            from .x_scraper_public_simple import collect_public_tweets
            logger.info(f"Attempting to collect tweets using public scraper for @{username}")
            
            # 使用非同步運行
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            try:
                public_tweets = loop.run_until_complete(collect_public_tweets(username, days_back))
                
                if public_tweets:
                    logger.info(f"Successfully collected {len(public_tweets)} tweets via public scraper")
                    
                    # 轉換格式以匹配 Nitter 輸出
                    for tweet in public_tweets:
                        posts.append({
                            'platform': tweet['platform'],
                            'post_id': tweet['post_id'],
                            'author_username': tweet['author_username'],
                            'author_display_name': tweet['author_display_name'],
                            'original_content': tweet['original_content'],
                            'post_time': tweet['created_at'],
                            'post_url': tweet['post_url'],
                            'metrics': tweet.get('metrics', {}),
                            'language': tweet.get('language', 'unknown'),
                            'collected_at': tweet['collected_at'],
                            'collection_method': 'public_scraper_fallback'
                        })
                    
                    return posts
                else:
                    logger.warning(f"Public scraper returned no tweets for {username}")
                    
            except Exception as e:
                logger.error(f"Error running async collect_public_tweets: {e}")
                
        except Exception as e:
            logger.error(f"Public scraper also failed for {username}: {e}")
        
        logger.error(f"All collection methods (Nitter + public scraper) failed for @{username}")
        return posts
        
    def _extract_user_info(self, soup: BeautifulSoup, username: str) -> Dict[str, Any]:
        """從 Nitter 頁面提取用戶信息"""
        user_info = {'username': username}
        
        try:
            # 獲取顯示名稱
            profile_card = soup.find('div', class_='profile-card')
            if profile_card:
                name_elem = profile_card.find('a', class_='profile-card-fullname')
                if name_elem:
                    user_info['display_name'] = name_elem.get_text(strip=True)
                    
                # 獲取關注者數量
                followers_elem = profile_card.find('span', class_='profile-stat-num', 
                                                 string=lambda text: 'Followers' in text if text else False)
                if followers_elem:
                    followers_text = followers_elem.get_text(strip=True)
                    user_info['followers_count'] = self._parse_count(followers_text)
                    
        except Exception as e:
            logger.error(f"Error extracting user info: {e}")
            
        return user_info
        
    def _extract_tweets(self, soup: BeautifulSoup, username: str, instance: str, days_back: int) -> List[Dict[str, Any]]:
        """從 Nitter 頁面提取推文"""
        tweets = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            # 查找所有推文容器
            timeline_items = soup.find_all('div', class_='timeline-item')
            
            for item in timeline_items:
                try:
                    # 檢查是否是置頂推文
                    pinned_elem = item.find('div', class_='pinned')
                    if pinned_elem:
                        logger.debug(f"Skipping pinned tweet")
                        continue
                        
                    tweet_data = {}
                    
                    # 獲取推文連結和 ID
                    tweet_link = item.find('a', class_='tweet-link')
                    if tweet_link:
                        href = tweet_link.get('href', '')
                        if '/status/' in href:
                            tweet_id = href.split('/status/')[-1].split('?')[0]
                            tweet_data['tweet_id'] = tweet_id
                            # 構建原始 Twitter URL
                            tweet_data['url'] = f"https://twitter.com/{username}/status/{tweet_id}"
                        else:
                            continue
                    else:
                        continue
                        
                    # 獲取推文內容
                    content_elem = item.find('div', class_='tweet-content')
                    if content_elem:
                        tweet_data['content'] = content_elem.get_text(strip=True)
                    else:
                        tweet_data['content'] = ""
                        
                    # 獲取時間戳
                    time_elem = item.find('span', class_='tweet-date')
                    if time_elem:
                        time_link = time_elem.find('a')
                        if time_link and time_link.get('title'):
                            # Nitter 時間格式: "Jun 25, 2024 · 7:36 PM UTC"
                            time_str = time_link['title']
                            tweet_time = self._parse_nitter_time(time_str)
                            
                            # 檢查時間是否合理（不應該是未來時間）
                            if tweet_time and tweet_time > datetime.now():
                                logger.warning(f"Future timestamp detected: {time_str}, using current time")
                                tweet_time = datetime.now()
                            
                            if tweet_time and tweet_time < cutoff_date:
                                # 超過時間範圍
                                logger.debug(f"Tweet from {tweet_time} is older than cutoff {cutoff_date}, skipping")
                                continue  # 使用 continue 而不是 break，因為推文可能不是按時間順序排列
                            tweet_data['timestamp'] = tweet_time.isoformat() if tweet_time else datetime.now().isoformat()
                        else:
                            tweet_data['timestamp'] = datetime.utcnow().isoformat()
                    else:
                        tweet_data['timestamp'] = datetime.utcnow().isoformat()
                        
                    # 獲取互動指標
                    metrics = {}
                    
                    # 點贊數
                    likes_elem = item.find('div', class_='icon-heart')
                    if likes_elem:
                        parent = likes_elem.parent
                        if parent:
                            count_text = parent.get_text(strip=True)
                            metrics['likes'] = self._parse_count(count_text)
                            
                    # 轉推數
                    retweet_elem = item.find('div', class_='icon-retweet')
                    if retweet_elem:
                        parent = retweet_elem.parent
                        if parent:
                            count_text = parent.get_text(strip=True)
                            metrics['retweets'] = self._parse_count(count_text)
                            
                    # 回覆數
                    reply_elem = item.find('div', class_='icon-comment')
                    if reply_elem:
                        parent = reply_elem.parent
                        if parent:
                            count_text = parent.get_text(strip=True)
                            metrics['replies'] = self._parse_count(count_text)
                            
                    tweet_data['metrics'] = metrics
                    
                    tweets.append(tweet_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing tweet: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting tweets: {e}")
            
        return tweets
        
    def _parse_count(self, text: str) -> int:
        """解析數字（處理 K, M 等單位）"""
        if not text:
            return 0
            
        # 清理文本
        text = text.strip().upper()
        # 移除非數字字符（保留 K, M）
        text = ''.join(c for c in text if c.isdigit() or c in 'KM.')
        
        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(text) if text.isdigit() else 0
        except:
            return 0
            
    def _parse_nitter_time(self, time_str: str) -> Optional[datetime]:
        """解析 Nitter 的時間格式"""
        try:
            # 格式: "Jun 25, 2024 · 7:36 PM UTC"
            # 移除 · 和 UTC
            time_str = time_str.replace('·', '').replace('UTC', '').strip()
            
            # 嘗試不同的時間格式
            formats = [
                "%b %d, %Y %I:%M %p",
                "%B %d, %Y %I:%M %p",
                "%b %d, %Y %H:%M",
                "%B %d, %Y %H:%M"
            ]
            
            parsed_time = None
            for fmt in formats:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    break
                except:
                    continue
            
            if parsed_time:
                # 如果解析出的時間是未來時間（可能是年份錯誤），修正為今年或去年
                if parsed_time > datetime.now():
                    # 嘗試將年份改為今年
                    current_year = datetime.now().year
                    parsed_time = parsed_time.replace(year=current_year)
                    
                    # 如果還是未來時間，改為去年
                    if parsed_time > datetime.now():
                        parsed_time = parsed_time.replace(year=current_year - 1)
                
                return parsed_time
            
            # 如果都失敗，返回當前時間
            logger.warning(f"Failed to parse time: {time_str}")
            return datetime.now()
            
        except Exception as e:
            logger.error(f"Error parsing time: {e}")
            return None
            
    def test_connection(self) -> bool:
        """測試 Nitter 連接"""
        instance = self._get_working_instance()
        return instance is not None