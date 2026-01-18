import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from apify_client import ApifyClient

from config import APIFY_API_TOKEN, APIFY_MAX_ITEMS, APIFY_TIMEOUT

logger = logging.getLogger(__name__)


class ApifyTwitterClient:
    """使用 Apify twitter-scraper-lite actor 收集 Twitter 數據"""

    def __init__(self):
        """初始化 Apify 客戶端"""
        self.api_token = APIFY_API_TOKEN
        self.max_items = APIFY_MAX_ITEMS
        self.timeout = APIFY_TIMEOUT
        self.client = None

        if self.api_token:
            try:
                self.client = ApifyClient(self.api_token)
                logger.info("Apify client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Apify client: {e}")
                self.client = None

    def is_available(self) -> bool:
        """檢查 Apify 客戶端是否可用"""
        return self.client is not None and self.api_token is not None

    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        獲取指定用戶的推文

        Args:
            username: Twitter 用戶名（不含 @）
            days_back: 獲取過去幾天的推文

        Returns:
            標準化的推文列表
        """
        if not self.is_available():
            logger.error("Apify client is not available")
            return []

        try:
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # 構建 Twitter 高級搜索查詢
            # 只獲取原創推文，在 API 端排除 RT/Reply/Quote
            search_query = f"from:{username} -filter:nativeretweets -filter:replies -filter:quote"

            # 準備 Apify actor 輸入
            run_input = {
                "searchTerms": [search_query],  # 使用搜索語法代替 twitterHandles
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            }

            logger.info(f"Calling Apify actor for @{username} (past {days_back} days) with query: {search_query}")

            # 調用 Apify actor
            run = self.client.actor('apidojo/twitter-scraper-lite').call(
                run_input=run_input,
                timeout_secs=self.timeout
            )

            if not run or run.get('status') != 'SUCCEEDED':
                logger.error(f"Apify actor run failed: {run.get('status') if run else 'No run info'}")
                return []

            # 獲取結果
            dataset_id = run.get('defaultDatasetId')
            if not dataset_id:
                logger.error("No dataset ID in Apify run result")
                return []

            # 從 dataset 獲取數據
            dataset_items = self.client.dataset(dataset_id).list_items().items

            logger.info(f"Retrieved {len(dataset_items)} items from Apify for @{username}")

            # 調試：打印第一條數據的結構
            if dataset_items:
                logger.info(f"Sample data keys: {list(dataset_items[0].keys())}")
                logger.debug(f"Sample data: {dataset_items[0]}")

            # 映射到標準格式
            # API 已經過濾了 RT/Reply/Quote，直接映射即可
            standardized_tweets = []

            for item in dataset_items:
                try:
                    tweet = self._map_apify_to_standard(item, expected_username=username)
                    if tweet:
                        standardized_tweets.append(tweet)
                except Exception as e:
                    logger.warning(f"Failed to map tweet {item.get('id', 'unknown')}: {e}")
                    continue

            # 驗證 API 過濾效果（可選，用於調試）
            if dataset_items:
                retweet_count = sum(1 for item in dataset_items if item.get('isRetweet'))
                reply_count = sum(1 for item in dataset_items if item.get('isReply'))
                quote_count = sum(1 for item in dataset_items if item.get('isQuote'))

                if retweet_count > 0 or reply_count > 0 or quote_count > 0:
                    logger.warning(f"API filtering incomplete: {retweet_count} RTs, {reply_count} replies, {quote_count} quotes still present")

            # 客戶端日期篩選：確保所有推文都在指定時間範圍內
            filtered_tweets = []
            out_of_range_count = 0
            for tweet in standardized_tweets:
                if self._is_within_date_range(tweet['post_time'], start_date, end_date):
                    filtered_tweets.append(tweet)
                else:
                    out_of_range_count += 1
                    logger.debug(f"Filtered out-of-range tweet: {tweet['post_id']} at {tweet['post_time']}")

            if out_of_range_count > 0:
                logger.warning(f"Filtered {out_of_range_count} tweets outside date range ({start_date.date()} to {end_date.date()}) for @{username}")

            logger.info(f"Successfully mapped {len(filtered_tweets)} tweets for @{username} (filtered {out_of_range_count} out-of-range)")
            return filtered_tweets

        except Exception as e:
            logger.error(f"Error fetching tweets from Apify for @{username}: {e}")
            return []

    def get_batch_tweets(self, usernames: List[str], days_back: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """
        批次獲取多個用戶的推文（一次 API 調用）

        Args:
            usernames: Twitter 用戶名列表（不含 @）
            days_back: 獲取過去幾天的推文

        Returns:
            字典 {username: [tweets]}，按用戶分組的推文列表
        """
        if not self.is_available():
            logger.error("Apify client is not available")
            return {}

        if not usernames:
            logger.warning("No usernames provided for batch fetch")
            return {}

        try:
            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # 構建批次搜索查詢（使用用戶提供的格式）
            search_terms = []
            for username in usernames:
                # 注意：使用 -filter:retweets 而不是 -filter:nativeretweets
                query = f"from:{username} since:{start_date.strftime('%Y-%m-%d')} until:{end_date.strftime('%Y-%m-%d')} -filter:replies -filter:retweets"
                search_terms.append(query)

            # 準備 Apify actor 輸入
            run_input = {
                "searchTerms": search_terms,
                "maxItems": len(usernames) * 100,  # 每個用戶預估最多 100 條
                "sort": "Latest"
            }

            logger.info(f"Calling Apify actor for {len(usernames)} users in batch (single API call)")
            logger.debug(f"Batch query: {len(search_terms)} search terms")

            # 調用 Apify actor（一次 API 調用）
            run = self.client.actor('apidojo/twitter-scraper-lite').call(
                run_input=run_input,
                timeout_secs=self.timeout
            )

            if not run or run.get('status') != 'SUCCEEDED':
                logger.error(f"Apify batch run failed: {run.get('status') if run else 'No run info'}")
                return {}

            # 獲取結果
            dataset_id = run.get('defaultDatasetId')
            if not dataset_id:
                logger.error("No dataset ID in Apify batch run result")
                return {}

            # 從 dataset 獲取數據
            dataset_items = self.client.dataset(dataset_id).list_items().items
            logger.info(f"Retrieved {len(dataset_items)} total items from Apify batch call")

            # 按用戶分組結果
            results_by_user = {username: [] for username in usernames}
            unmatched_count = 0
            out_of_range_count = 0

            for item in dataset_items:
                try:
                    # 提取作者用戶名
                    author = item.get('author', {})
                    if isinstance(author, dict):
                        author_username = author.get('userName') or author.get('username')

                        if author_username and author_username in usernames:
                            # 映射推文並驗證用戶名
                            tweet = self._map_apify_to_standard(item, expected_username=author_username)
                            if tweet:
                                # 客戶端日期篩選：確保推文在指定時間範圍內
                                if self._is_within_date_range(tweet['post_time'], start_date, end_date):
                                    results_by_user[author_username].append(tweet)
                                else:
                                    out_of_range_count += 1
                                    logger.debug(f"Filtered out-of-range tweet: {tweet['post_id']} at {tweet['post_time']}")
                        else:
                            unmatched_count += 1
                            if author_username:
                                logger.debug(f"Unmatched tweet from @{author_username} (not in target list)")
                except Exception as e:
                    logger.warning(f"Failed to process batch item: {e}")
                    continue

            # 記錄統計
            total_tweets = sum(len(tweets) for tweets in results_by_user.values())
            logger.info(f"Batch fetch results: {total_tweets} tweets from {len([u for u, t in results_by_user.items() if t])} users")
            for username, tweets in results_by_user.items():
                if tweets:
                    logger.info(f"  @{username}: {len(tweets)} tweets")

            if unmatched_count > 0:
                logger.info(f"Filtered out {unmatched_count} tweets from non-target users")

            if out_of_range_count > 0:
                logger.warning(f"Filtered {out_of_range_count} tweets outside date range ({start_date.date()} to {end_date.date()})")

            return results_by_user

        except Exception as e:
            logger.error(f"Error in batch fetch: {e}")
            return {}

    def _is_within_date_range(self, post_time_str: str, start_date: datetime, end_date: datetime) -> bool:
        """
        檢查貼文時間是否在指定的日期範圍內

        Args:
            post_time_str: ISO 8601 格式的時間字串
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            True 如果在範圍內，False 如果超出範圍
        """
        try:
            # 解析 ISO 8601 時間字串
            post_time = datetime.fromisoformat(post_time_str.replace('Z', '+00:00'))

            # 確保 start_date 和 end_date 是 timezone-aware
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=post_time.tzinfo)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=post_time.tzinfo)

            return start_date <= post_time <= end_date
        except Exception as e:
            logger.warning(f"Failed to parse post time '{post_time_str}' for date range check: {e}")
            # 如果無法解析時間，保守地保留這個貼文
            return True

    def _map_apify_to_standard(self, apify_tweet: Dict, expected_username: str = None) -> Optional[Dict[str, Any]]:
        """
        將 Apify 返回的推文映射到系統標準格式

        Args:
            apify_tweet: Apify actor 返回的推文數據
            expected_username: 預期的用戶名（可選，用於過濾非目標用戶）

        Returns:
            標準化的推文字典，如果缺少必填字段則返回 None
        """
        try:
            # 檢查必填字段
            tweet_id = apify_tweet.get('id')

            # 從 author 對象中提取用戶名
            author = apify_tweet.get('author', {})
            if isinstance(author, dict):
                author_username = author.get('userName') or author.get('username')
                author_display_name = author.get('name') or author.get('displayName') or author_username
            else:
                author_username = None
                author_display_name = None

            if not tweet_id or not author_username:
                logger.warning(f"Missing required fields in tweet: id={tweet_id}, author_username={author_username}")
                return None

            # 用戶名驗證：如果提供了 expected_username，只保留目標用戶的推文
            if expected_username and author_username.lower() != expected_username.lower():
                logger.debug(f"Skipping tweet from @{author_username} (expected @{expected_username})")
                return None

            # 構建推文 URL
            post_url = apify_tweet.get('url') or apify_tweet.get('twitterUrl')
            if not post_url:
                # 如果沒有 URL，手動構建
                post_url = f"https://twitter.com/{author_username}/status/{tweet_id}"

            # 處理時間戳
            created_at = apify_tweet.get('createdAt', '')
            try:
                # 確保時間格式為 ISO 8601
                if created_at:
                    # Apify 可能返回不同格式的時間戳
                    # 格式1: ISO 8601 (如 "2026-01-06T10:51:51Z")
                    # 格式2: Twitter 格式 (如 "Tue Jan 06 06:34:34 +0000 2026")
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except ValueError:
                        # 嘗試解析 Twitter 時間格式
                        from datetime import datetime as dt_class
                        dt = dt_class.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
                    post_time = dt.isoformat()
                else:
                    post_time = datetime.utcnow().isoformat()
            except Exception as e:
                logger.warning(f"Failed to parse timestamp {created_at}: {e}")
                post_time = datetime.utcnow().isoformat()

            # 獲取推文文本（優先使用 fullText）
            tweet_text = apify_tweet.get('fullText') or apify_tweet.get('text', '')

            # 構建標準化的推文對象
            standardized = {
                'platform': 'twitter',
                'post_id': str(tweet_id),
                'author_username': author_username,
                'author_display_name': author_display_name,
                'original_content': tweet_text,
                'post_time': post_time,
                'post_url': post_url,
                'metrics': {
                    'retweet_count': apify_tweet.get('retweetCount', 0),
                    'favorite_count': apify_tweet.get('likeCount', 0),
                    'reply_count': apify_tweet.get('replyCount', 0),
                    'quote_count': apify_tweet.get('quoteCount', 0),
                    'view_count': apify_tweet.get('viewCount', 0)
                },
                'language': apify_tweet.get('lang', 'unknown'),
                'thread_id': apify_tweet.get('conversationId'),
                'collected_at': datetime.utcnow().isoformat(),
                'collection_method': 'apify'
            }

            return standardized

        except Exception as e:
            logger.error(f"Error mapping Apify tweet to standard format: {e}")
            return None
