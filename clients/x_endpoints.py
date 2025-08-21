"""
Twitter GraphQL 端點定義和參數模板
基於 agent-twitter-client 的端點配置
"""

import json
from typing import Dict, Any, Optional
from urllib.parse import urlencode, quote


class TwitterEndpoints:
    """Twitter GraphQL 端點管理器"""
    
    # 基礎 URL
    BASE_API_URL = "https://api.x.com"
    BASE_TWITTER_URL = "https://x.com"
    GRAPHQL_URL = f"{BASE_TWITTER_URL}/i/api/graphql"
    
    # GraphQL 端點 IDs (從 agent-twitter-client 移植)
    ENDPOINTS = {
        # 用戶推文相關
        'UserTweets': {
            'id': 'V7H0Ap3_Hh2FyS75OCDO3Q',
            'url_template': f'{GRAPHQL_URL}/V7H0Ap3_Hh2FyS75OCDO3Q/UserTweets'
        },
        'UserTweetsAndReplies': {
            'id': 'E4wA5vo2sjVyvpliUffSCw', 
            'url_template': f'{GRAPHQL_URL}/E4wA5vo2sjVyvpliUffSCw/UserTweetsAndReplies'
        },
        'UserLikedTweets': {
            'id': 'eSSNbhECHHWWALkkQq-YTA',
            'url_template': f'{GRAPHQL_URL}/eSSNbhECHHWWALkkQq-YTA/Likes'
        },
        
        # 推文詳情
        'TweetDetail': {
            'id': 'xOhkmRac04YFZmOzU9PJHg',
            'url_template': f'{GRAPHQL_URL}/xOhkmRac04YFZmOzU9PJHg/TweetDetail'
        },
        'TweetResultByRestId': {
            'id': 'DJS3BdhUhcaEpZ7B7irJDg',
            'url_template': f'{GRAPHQL_URL}/DJS3BdhUhcaEpZ7B7irJDg/TweetResultByRestId'
        },
        
        # 其他功能
        'Bookmarks': {
            'id': 'cYAm3-H_HI4p2HzCM-wQvA',
            'url_template': f'{GRAPHQL_URL}/cYAm3-H_HI4p2HzCM-wQvA/Bookmarks'
        },
        'ListTweets': {
            'id': 'whF0_KH1fCkdLLoyNPMoEw',
            'url_template': f'{GRAPHQL_URL}/whF0_KH1fCkdLLoyNPMoEw/ListLatestTweetsTimeline'
        },
        
        # 用戶查詢  
        'UserByScreenName': {
            'id': 'k5XapwcSikNsEsILW5FvgA',
            'url_template': f'{GRAPHQL_URL}/k5XapwcSikNsEsILW5FvgA/UserByScreenName'
        }
    }
    
    # 認證相關端點
    AUTH_ENDPOINTS = {
        'guest_activate': f'{BASE_API_URL}/1.1/guest/activate.json',
        'onboarding_task': f'{BASE_API_URL}/1.1/onboarding/task.json',
        'verify_credentials': f'{BASE_API_URL}/1.1/account/verify_credentials.json',
        'logout': f'{BASE_API_URL}/1.1/account/logout.json'
    }
    
    @staticmethod
    def get_user_tweets_url(user_id: str, count: int = 20, cursor: str = None) -> str:
        """構建用戶推文查詢 URL"""
        variables = {
            "userId": user_id,
            "count": count,
            "includePromotedContent": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True
        }
        
        if cursor:
            variables["cursor"] = cursor
        
        features = TwitterEndpoints._get_common_features()
        field_toggles = {"withArticlePlainText": False}
        
        return TwitterEndpoints._build_graphql_url(
            'UserTweets', variables, features, field_toggles
        )
    
    @staticmethod
    def get_tweet_detail_url(tweet_id: str) -> str:
        """構建推文詳情查詢 URL"""
        variables = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True
        }
        
        features = TwitterEndpoints._get_common_features()
        field_toggles = {"withArticleRichContentState": False}
        
        return TwitterEndpoints._build_graphql_url(
            'TweetDetail', variables, features, field_toggles
        )
    
    @staticmethod
    def get_user_by_screen_name_url(screen_name: str) -> str:
        """構建用戶查詢 URL"""
        variables = {
            "screen_name": screen_name,
            "withSafetyModeUserFields": True
        }
        
        features = TwitterEndpoints._get_common_features()
        field_toggles = {"withAuxiliaryUserLabels": False}
        
        return TwitterEndpoints._build_graphql_url(
            'UserByScreenName', variables, features, field_toggles
        )
    
    @staticmethod
    def _get_common_features() -> Dict[str, Any]:
        """獲取通用的 GraphQL features 參數"""
        return {
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "articles_preview_enabled": True,
            "tweetypie_unmention_optimization_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_enhance_cards_enabled": False
        }
    
    @staticmethod
    def _build_graphql_url(endpoint_name: str, variables: Dict[str, Any], 
                          features: Dict[str, Any], field_toggles: Dict[str, Any] = None) -> str:
        """構建 GraphQL 查詢 URL"""
        endpoint = TwitterEndpoints.ENDPOINTS.get(endpoint_name)
        if not endpoint:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        
        # 構建查詢參數
        params = {
            'variables': json.dumps(variables, separators=(',', ':')),
            'features': json.dumps(features, separators=(',', ':'))
        }
        
        if field_toggles:
            params['fieldToggles'] = json.dumps(field_toggles, separators=(',', ':'))
        
        # URL 編碼
        query_string = urlencode(params, quote_via=quote)
        return f"{endpoint['url_template']}?{query_string}"


class TwitterQueryBuilder:
    """Twitter GraphQL 查詢構建器"""
    
    def __init__(self):
        self.endpoints = TwitterEndpoints()
    
    def build_user_tweets_query(self, user_id: str, count: int = 20, 
                               cursor: str = None) -> Dict[str, Any]:
        """構建用戶推文查詢"""
        return {
            'url': self.endpoints.get_user_tweets_url(user_id, count, cursor),
            'method': 'GET',
            'params': {
                'userId': user_id,
                'count': count,
                'cursor': cursor
            }
        }
    
    def build_tweet_detail_query(self, tweet_id: str) -> Dict[str, Any]:
        """構建推文詳情查詢"""
        return {
            'url': self.endpoints.get_tweet_detail_url(tweet_id),
            'method': 'GET',
            'params': {
                'tweetId': tweet_id
            }
        }
    
    def build_search_query(self, query: str, count: int = 20, 
                          cursor: str = None) -> Dict[str, Any]:
        """構建搜索查詢 (待實現)"""
        # TODO: 實現搜索查詢構建
        pass


class TwitterResponseParser:
    """Twitter API 響應解析器"""
    
    @staticmethod
    def parse_user_tweets_response(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析用戶推文響應"""
        try:
            data = response_data.get('data', {})
            user = data.get('user', {})
            result = user.get('result', {})
            timeline = result.get('timeline_v2', {}).get('timeline', {})
            instructions = timeline.get('instructions', [])
            
            tweets = []
            cursor = None
            
            for instruction in instructions:
                if instruction.get('type') == 'TimelineAddEntries':
                    entries = instruction.get('entries', [])
                    
                    for entry in entries:
                        entry_id = entry.get('entryId', '')
                        
                        # 解析推文條目
                        if entry_id.startswith('tweet-'):
                            tweet_data = TwitterResponseParser._extract_tweet_from_entry(entry)
                            if tweet_data:
                                tweets.append(tweet_data)
                        
                        # 解析游標
                        elif entry_id.startswith('cursor-bottom-'):
                            cursor = entry.get('content', {}).get('value')
            
            return {
                'tweets': tweets,
                'cursor': cursor,
                'has_more': cursor is not None
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse user tweets response: {e}")
    
    @staticmethod
    def _extract_tweet_from_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """從時間線條目中提取推文數據"""
        try:
            content = entry.get('content', {})
            item_content = content.get('itemContent', {})
            tweet_results = item_content.get('tweet_results', {})
            result = tweet_results.get('result', {})
            
            if not result or result.get('__typename') != 'Tweet':
                return None
            
            # 基本推文信息
            tweet_data = {
                'id': result.get('rest_id'),
                'created_at': result.get('legacy', {}).get('created_at'),
                'full_text': result.get('legacy', {}).get('full_text', ''),
                'user_id': result.get('legacy', {}).get('user_id_str'),
                'conversation_id': result.get('legacy', {}).get('conversation_id_str'),
                'lang': result.get('legacy', {}).get('lang'),
                'reply_count': result.get('legacy', {}).get('reply_count', 0),
                'retweet_count': result.get('legacy', {}).get('retweet_count', 0),
                'favorite_count': result.get('legacy', {}).get('favorite_count', 0),
                'quote_count': result.get('legacy', {}).get('quote_count', 0),
                'view_count': result.get('views', {}).get('count')
            }
            
            # 用戶信息
            user_result = result.get('core', {}).get('user_results', {}).get('result', {})
            if user_result:
                tweet_data['user'] = {
                    'screen_name': user_result.get('legacy', {}).get('screen_name'),
                    'name': user_result.get('legacy', {}).get('name'),
                    'followers_count': user_result.get('legacy', {}).get('followers_count', 0)
                }
            
            # 媒體信息 (如果有)
            entities = result.get('legacy', {}).get('entities', {})
            media = entities.get('media', [])
            if media:
                tweet_data['media'] = []
                for media_item in media:
                    tweet_data['media'].append({
                        'type': media_item.get('type'),
                        'media_url': media_item.get('media_url_https'),
                        'url': media_item.get('url')
                    })
            
            return tweet_data
            
        except Exception as e:
            return None
    
    @staticmethod
    def parse_user_by_screen_name_response(response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析用戶查詢響應"""
        try:
            data = response_data.get('data', {})
            user = data.get('user', {})
            result = user.get('result', {})
            
            if not result or result.get('__typename') != 'User':
                return None
            
            legacy = result.get('legacy', {})
            
            return {
                'user_id': result.get('rest_id'),
                'screen_name': legacy.get('screen_name'),
                'name': legacy.get('name'),
                'description': legacy.get('description'),
                'followers_count': legacy.get('followers_count', 0),
                'following_count': legacy.get('friends_count', 0),
                'statuses_count': legacy.get('statuses_count', 0),
                'verified': legacy.get('verified', False),
                'created_at': legacy.get('created_at'),
                'profile_image_url': legacy.get('profile_image_url_https')
            }
            
        except Exception as e:
            return None
    
    @staticmethod
    def parse_error_response(response_data: Dict[str, Any]) -> str:
        """解析錯誤響應"""
        errors = response_data.get('errors', [])
        if errors:
            error_messages = [error.get('message', 'Unknown error') for error in errors]
            return '; '.join(error_messages)
        return 'Unknown error occurred'