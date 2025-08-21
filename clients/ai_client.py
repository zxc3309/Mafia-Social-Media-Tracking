import openai
import anthropic
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from config import (
    AI_API_KEY, 
    AI_API_TYPE,
    IMPORTANCE_FILTER_PROMPT,
    SUMMARIZATION_PROMPT,
    REPOST_GENERATION_PROMPT
)

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.api_type = AI_API_TYPE.lower()
        self.openai_client = None
        self.anthropic_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化AI客戶端"""
        try:
            if not AI_API_KEY or AI_API_KEY == "your_openai_or_anthropic_api_key_here":
                raise ValueError("AI API key not configured")
            
            if self.api_type == "openai":
                self.openai_client = openai.OpenAI(api_key=AI_API_KEY)
                logger.info("OpenAI client initialized successfully")
            elif self.api_type == "anthropic":
                self.anthropic_client = anthropic.Anthropic(api_key=AI_API_KEY)
                logger.info("Anthropic client initialized successfully")
            else:
                raise ValueError(f"Unsupported AI API type: {self.api_type}")
                
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
            raise
    
    def detect_and_group_threads(self, posts: List[Dict[str, Any]], time_threshold_minutes: int = 5) -> List[List[Dict[str, Any]]]:
        """
        檢測並分組 Thread
        
        Args:
            posts: 貼文列表
            time_threshold_minutes: 時間閾值（分鐘）
            
        Returns:
            List of thread groups, each containing related posts
        """
        if not posts:
            return []
        
        # 按作者和時間排序
        sorted_posts = sorted(posts, key=lambda x: (
            x.get('author_username', ''),
            self._parse_post_time(x.get('post_time', ''))
        ))
        
        threads = []
        current_thread = []
        last_author = None
        last_time = None
        
        for post in sorted_posts:
            author = post.get('author_username', '')
            post_time = self._parse_post_time(post.get('post_time', ''))
            
            # 檢查是否開始新的 Thread
            if (last_author != author or 
                not last_time or 
                not post_time or
                abs((post_time - last_time).total_seconds()) > time_threshold_minutes * 60):
                
                # 保存上一個 Thread（如果有的話）
                if current_thread:
                    threads.append(current_thread)
                
                # 開始新的 Thread
                current_thread = [post]
            else:
                # 添加到當前 Thread
                current_thread.append(post)
            
            last_author = author
            last_time = post_time
        
        # 添加最後一個 Thread
        if current_thread:
            threads.append(current_thread)
        
        logger.info(f"Detected {len(threads)} threads from {len(posts)} posts")
        return threads
    
    def _parse_post_time(self, time_str: str) -> Optional[datetime]:
        """解析貼文時間字串為 datetime 對象"""
        if not time_str:
            return None
        
        try:
            # 嘗試不同的時間格式
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format with microseconds and Z
                '%Y-%m-%dT%H:%M:%SZ',     # ISO format without microseconds but with Z
                '%Y-%m-%dT%H:%M:%S.%f',   # ISO format with microseconds, no timezone
                '%Y-%m-%dT%H:%M:%S',      # ISO format without timezone
                '%Y-%m-%d %H:%M:%S',      # Simple format
                '%Y-%m-%dT%H:%M:%S+00:00',# ISO with timezone
                '%Y-%m-%d %H:%M:%S.%f',   # Simple format with microseconds
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            logger.warning(f"Unable to parse time: {time_str}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing time {time_str}: {e}")
            return None
    
    def generate_thread_id(self, thread_posts: List[Dict[str, Any]]) -> str:
        """為 Thread 生成唯一的 ID"""
        if not thread_posts:
            return ""
        
        first_post = thread_posts[0]
        author = first_post.get('author_username', '')
        platform = first_post.get('platform', '')
        post_time = first_post.get('post_time', '')
        
        # 使用平台、作者、時間的組合生成 hash
        unique_string = f"{platform}_{author}_{post_time}_{len(thread_posts)}"
        thread_id = hashlib.md5(unique_string.encode()).hexdigest()[:16]
        
        return f"{platform}_{author}_{thread_id}"
    
    def merge_thread_content(self, thread_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合併 Thread 內容
        
        Args:
            thread_posts: Thread 內的貼文列表
            
        Returns:
            合併後的 Thread 資料
        """
        if not thread_posts:
            return {}
        
        if len(thread_posts) == 1:
            # 單一貼文，直接返回
            return thread_posts[0]
        
        # 排序貼文（按時間）
        sorted_posts = sorted(thread_posts, key=lambda x: self._parse_post_time(x.get('post_time', '')) or datetime.min)
        
        first_post = sorted_posts[0]
        last_post = sorted_posts[-1]
        
        # 合併內容
        merged_content_parts = []
        for i, post in enumerate(sorted_posts, 1):
            content = post.get('original_content', '').strip()
            if content:
                merged_content_parts.append(f"{i}/{len(sorted_posts)}: {content}")
        
        merged_content = "\n".join(merged_content_parts)
        
        # 創建合併後的貼文資料
        merged_post = first_post.copy()
        merged_post.update({
            'original_content': merged_content,
            'is_thread': True,
            'thread_count': len(thread_posts),
            'thread_posts': thread_posts,  # 保留原始貼文列表
            'post_time_range': {
                'start': first_post.get('post_time', ''),
                'end': last_post.get('post_time', '')
            }
        })
        
        return merged_post
    
    def analyze_importance(self, post_content: str, author: str = "", max_retries: int = 3) -> tuple[Optional[float], Optional[str]]:
        """
        分析貼文重要性，返回1-10的評分和評分理由
        
        Returns:
            tuple[score, reasoning]: (評分, 評分理由)
        """
        # 優先從數據庫獲取活躍的prompt版本
        prompt_template = self._get_active_importance_prompt()
        
        # 安全地格式化 prompt
        try:
            prompt = prompt_template.format(post_content=post_content, author=author)
        except KeyError as e:
            logger.warning(f"Format error in prompt template: {e}, using string replacement")
            # 使用字符串替換作為備用方案
            prompt = prompt_template.replace("{post_content}", post_content).replace("{author}", author)
        
        for attempt in range(max_retries):
            try:
                if self.api_type == "openai":
                    response = self._call_openai(prompt, max_tokens=300)  # 增加 token 限制以獲取完整理由
                elif self.api_type == "anthropic":
                    response = self._call_anthropic(prompt, max_tokens=300)
                else:
                    logger.error(f"Unsupported API type: {self.api_type}")
                    return None, None
                
                # 先嘗試解析 JSON 格式的回應
                logger.debug(f"AI response (length={len(response) if response else 0}): {response}")
                score, reasoning = self._extract_score_and_reasoning(response)
                
                if score is not None:
                    logger.debug(f"Importance score: {score}, reasoning: {reasoning[:50]}... for content preview: {post_content[:50]}...")
                    return score, reasoning
                else:
                    logger.warning(f"Could not extract score from response (length={len(response) if response else 0}): {response}")
                    
            except Exception as e:
                logger.error(f"Error analyzing importance (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                
        return None, None
    
    def summarize_content(self, post_content: str, max_retries: int = 3) -> Optional[str]:
        """
        摘要貼文內容
        """
        prompt_template = self._get_active_summarization_prompt()
        prompt = prompt_template.format(post_content=post_content)
        
        for attempt in range(max_retries):
            try:
                if self.api_type == "openai":
                    response = self._call_openai(prompt, max_tokens=200)
                elif self.api_type == "anthropic":
                    response = self._call_anthropic(prompt, max_tokens=200)
                else:
                    logger.error(f"Unsupported API type: {self.api_type}")
                    return None
                
                if response and response.strip():
                    logger.debug(f"Generated summary for content preview: {post_content[:50]}...")
                    return response.strip()
                else:
                    logger.warning("Empty summary response")
                    
            except Exception as e:
                logger.error(f"Error generating summary (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                
        return None
    
    def generate_repost_content(self, post_content: str, max_retries: int = 3) -> Optional[str]:
        """
        生成轉發內容
        """
        prompt_template = self._get_active_repost_prompt()
        prompt = prompt_template.format(post_content=post_content)
        
        for attempt in range(max_retries):
            try:
                if self.api_type == "openai":
                    response = self._call_openai(prompt, max_tokens=300)
                elif self.api_type == "anthropic":
                    response = self._call_anthropic(prompt, max_tokens=300)
                else:
                    logger.error(f"Unsupported API type: {self.api_type}")
                    return None
                
                if response and response.strip():
                    logger.debug(f"Generated repost content for: {post_content[:50]}...")
                    return response.strip()
                else:
                    logger.warning("Empty repost content response")
                    
            except Exception as e:
                logger.error(f"Error generating repost content (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                
        return None
    
    
    def _call_openai(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """調用 OpenAI Response API with web search"""
        try:
            logger.debug("Using Response API with web search")
            return self._call_openai_response_api(prompt, max_tokens)
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def _call_openai_response_api(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """調用 OpenAI Response API（GPT-5 minimal reasoning，無 web search）"""
        try:
            # GPT-5 使用 minimal reasoning 以提升速度，不使用 web_search
            response = self.openai_client.responses.create(
                model="gpt-5",
                input=prompt,
                reasoning={
                    "effort": "minimal"  # 最快速度
                }
                # 移除 web_search 工具以支援 minimal reasoning
            )
            
            # 提取文本內容
            text_content = self._extract_text_from_response(response)
            return text_content
            
        except openai.RateLimitError:
            logger.warning("OpenAI rate limit reached, waiting...")
            time.sleep(60)
            raise
        except openai.APIError as e:
            logger.error(f"OpenAI Response API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI Response API: {e}")
            raise
    
    def _extract_text_from_response(self, response) -> Optional[str]:
        """從 Response API 回應中提取文本內容（支援 GPT-5 推理結構）"""
        try:
            for output_item in response.output:
                # GPT-5: 查找 ResponseOutputMessage 類型的輸出
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                return content_item.text
                
                # GPT-4o: 向後兼容舊結構
                elif hasattr(output_item, 'content') and output_item.content:
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            return content_item.text
            
            return None
        except Exception as e:
            logger.error(f"提取 Response API 文本失敗: {e}")
            return None
    
    
    def _call_anthropic(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """調用Anthropic API"""
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text if response.content else None
            
        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit reached, waiting...")
            time.sleep(60)
            raise
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Anthropic: {e}")
            raise
    
    def _extract_score_and_reasoning(self, response: str) -> tuple[Optional[float], Optional[str]]:
        """從AI回應中提取評分和理由"""
        if not response:
            return None, None
            
        import json
        import re
        
        # 首先嘗試解析 JSON 格式
        try:
            # 清理回應，移除可能的前後文本
            json_match = re.search(r'\{[^{}]*"score"[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                score = result.get('score')
                reasoning = result.get('reasoning', '')
                
                if score is not None:
                    score = float(score)
                    if 1 <= score <= 10:
                        return score, reasoning
                        
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.debug(f"JSON parsing failed: {e}")
        
        # 備用方案：使用舊的數字提取方法
        score = self._extract_score_fallback(response)
        return score, "" if score else (None, None)
    
    def _extract_score_fallback(self, response: str) -> Optional[float]:
        """從AI回應中提取數字評分"""
        if not response:
            return None
        
        import re
        
        # 尋找數字
        numbers = re.findall(r'\b([0-9](?:\.[0-9])?|10(?:\.0)?)\b', response)
        
        if numbers:
            try:
                score = float(numbers[0])
                # 確保評分在1-10範圍內
                if 1 <= score <= 10:
                    return score
                else:
                    logger.warning(f"Score {score} out of range 1-10")
                    return max(1, min(10, score))  # 強制在範圍內
            except ValueError:
                logger.warning(f"Could not convert {numbers[0]} to float")
        
        # 如果找不到有效數字，嘗試其他模式
        if "重要" in response or "高" in response or "10" in response:
            return 8.0
        elif "一般" in response or "中" in response or "5" in response:
            return 5.0
        elif "不重要" in response or "低" in response or "1" in response:
            return 2.0
        
        return None
    
    def _get_active_importance_prompt(self) -> str:
        """從 Google Sheets 獲取活躍的重要性分析 prompt"""
        try:
            from clients.google_sheets_client import GoogleSheetsClient
            sheets_client = GoogleSheetsClient()
            
            # 從 Google Sheets 獲取活躍的 prompt
            active_prompt = sheets_client.get_active_prompt("IMPORTANCE_FILTER")
            
            if active_prompt:
                logger.info("Using active IMPORTANCE_FILTER prompt from Google Sheets")
                return active_prompt
            else:
                logger.warning("No active IMPORTANCE_FILTER prompt found in Sheets, using config default")
                return IMPORTANCE_FILTER_PROMPT
                
        except Exception as e:
            logger.warning(f"Failed to get active prompt from Google Sheets: {e}, using config default")
            return IMPORTANCE_FILTER_PROMPT
    
    def _get_active_summarization_prompt(self) -> str:
        """從 Google Sheets 獲取活躍的摘要 prompt"""
        try:
            from clients.google_sheets_client import GoogleSheetsClient
            sheets_client = GoogleSheetsClient()
            
            # 從 Google Sheets 獲取活躍的 prompt
            active_prompt = sheets_client.get_active_prompt("SUMMARIZATION")
            
            if active_prompt:
                logger.info("Using active SUMMARIZATION prompt from Google Sheets")
                return active_prompt
            else:
                logger.warning("No active SUMMARIZATION prompt found in Sheets, using config default")
                return SUMMARIZATION_PROMPT
                
        except Exception as e:
            logger.warning(f"Failed to get active summarization prompt from Google Sheets: {e}, using config default")
            return SUMMARIZATION_PROMPT
    
    def _get_active_repost_prompt(self) -> str:
        """從 Google Sheets 獲取活躍的轉發 prompt"""
        try:
            from clients.google_sheets_client import GoogleSheetsClient
            sheets_client = GoogleSheetsClient()
            
            # 從 Google Sheets 獲取活躍的 prompt
            active_prompt = sheets_client.get_active_prompt("REPOST_GENERATION")
            
            if active_prompt:
                logger.info("Using active REPOST_GENERATION prompt from Google Sheets")
                return active_prompt
            else:
                logger.warning("No active REPOST_GENERATION prompt found in Sheets, using config default")
                return REPOST_GENERATION_PROMPT
                
        except Exception as e:
            logger.warning(f"Failed to get active repost prompt from Google Sheets: {e}, using config default")
            return REPOST_GENERATION_PROMPT
    

    def batch_analyze(self, posts: list, batch_size: int = 5) -> list:
        """
        批量分析貼文（支援 Thread 整合）
        
        Returns:
            list: 分析後的結果，Thread 只返回一個整合的項目
        """
        analyzed_results = []
        
        # 1. 檢測並分組 Threads
        threads = self.detect_and_group_threads(posts)
        logger.info(f"Processing {len(threads)} threads (from {len(posts)} posts)")
        
        # 2. 處理每個 Thread
        for thread_posts in threads:
            try:
                # 生成 thread_id
                thread_id = self.generate_thread_id(thread_posts)
                
                if len(thread_posts) == 1:
                    # 單一貼文，直接分析
                    post = thread_posts[0]
                    post['thread_id'] = thread_id
                    analyzed_post = self._analyze_single_post(post)
                    if analyzed_post:
                        analyzed_results.append(analyzed_post)
                else:
                    # Thread 分析：合併內容後分析，返回一個整合的結果
                    merged_thread = self.merge_thread_content(thread_posts)
                    merged_thread['thread_id'] = thread_id
                    
                    # 分析合併後的 Thread
                    thread_analysis = self._analyze_single_post(merged_thread)
                    
                    if thread_analysis:
                        # 為 Thread 添加原始貼文資訊，但只返回一個整合的結果
                        thread_analysis.update({
                            'is_thread': True,
                            'thread_count': len(thread_posts),
                            'thread_posts': thread_posts,  # 保留原始貼文列表供後續使用
                            'individual_posts_for_all_sheet': self._prepare_individual_posts_for_thread(
                                thread_posts, thread_id, thread_analysis
                            )
                        })
                        analyzed_results.append(thread_analysis)
                
                # 避免API調用過於頻繁
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing thread: {e}")
                continue
        
        logger.info(f"Successfully analyzed {len(analyzed_results)} items from {len(threads)} threads")
        return analyzed_results
    
    def _prepare_individual_posts_for_thread(self, thread_posts: List[Dict[str, Any]], 
                                           thread_id: str, thread_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """為 Thread 中的每個貼文準備個別的資料（用於 All Posts sheet）"""
        individual_posts = []
        
        for post in thread_posts:
            individual_post = post.copy()
            individual_post.update({
                'thread_id': thread_id,
                'importance_score': thread_analysis['importance_score'],
                'importance_reasoning': thread_analysis.get('importance_reasoning', ''),
                'summary': thread_analysis.get('summary', ''),
                'repost_content': thread_analysis.get('repost_content', ''),
                'is_part_of_thread': True,
                'thread_count': len(thread_posts)
            })
            individual_posts.append(individual_post)
        
        return individual_posts
    
    def _analyze_single_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分析單個貼文（或合併的 Thread）"""
        try:
            content = post.get('original_content', '')
            # 優先使用 display_name，如果沒有則使用 username
            author = post.get('author_display_name', '') or post.get('author_username', '')
            
            if not content:
                logger.warning(f"Empty content for post {post.get('post_id')}")
                return None
            
            # 分析重要性（包含作者信息和理由）
            importance_score, importance_reasoning = self.analyze_importance(content, author)
            
            # 如果重要性評分失敗，跳過這篇貼文
            if importance_score is None:
                logger.error(f"Failed to get importance score for post {post.get('post_id')}")
                return None
            
            # 準備分析後的貼文數據
            analyzed_post = post.copy()
            analyzed_post['importance_score'] = importance_score
            analyzed_post['importance_reasoning'] = importance_reasoning or ""
            
            # 只對重要的貼文進行摘要和轉發內容生成
            from config import IMPORTANCE_THRESHOLD
            if importance_score >= IMPORTANCE_THRESHOLD:
                # 生成摘要
                summary = self.summarize_content(content)
                analyzed_post['summary'] = summary if summary else "摘要生成失敗"
                
                # 生成轉發內容
                repost_content = self.generate_repost_content(content)
                analyzed_post['repost_content'] = repost_content if repost_content else "轉發內容生成失敗"
            else:
                analyzed_post['summary'] = "重要性不足，未生成摘要"
                analyzed_post['repost_content'] = "重要性不足，未生成轉發內容"
            
            return analyzed_post
            
        except Exception as e:
            logger.error(f"Error analyzing post {post.get('post_id', 'unknown')}: {e}")
            return None
