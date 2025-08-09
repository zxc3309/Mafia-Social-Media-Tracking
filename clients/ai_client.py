import openai
import anthropic
import time
import logging
from typing import Optional, Dict, Any
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
    
    def analyze_importance(self, post_content: str, author: str = "", max_retries: int = 3) -> Optional[float]:
        """
        分析貼文重要性，返回1-10的評分
        """
        # 優先從數據庫獲取活躍的prompt版本
        prompt_template = self._get_active_importance_prompt()
        prompt = prompt_template.format(post_content=post_content, author=author)
        
        for attempt in range(max_retries):
            try:
                if self.api_type == "openai":
                    response = self._call_openai(prompt, max_tokens=50)
                elif self.api_type == "anthropic":
                    response = self._call_anthropic(prompt, max_tokens=50)
                else:
                    logger.error(f"Unsupported API type: {self.api_type}")
                    return None
                
                # 從回應中提取數字評分
                logger.debug(f"AI response (length={len(response) if response else 0}): {response}")
                score = self._extract_score(response)
                if score is not None:
                    logger.debug(f"Importance score: {score} for content preview: {post_content[:50]}...")
                    return score
                else:
                    logger.warning(f"Could not extract score from response (length={len(response) if response else 0}): {response}")
                    
            except Exception as e:
                logger.error(f"Error analyzing importance (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指數退避
                
        return None
    
    def summarize_content(self, post_content: str, max_retries: int = 3) -> Optional[str]:
        """
        摘要貼文內容
        """
        prompt = SUMMARIZATION_PROMPT.format(post_content=post_content)
        
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
        prompt = REPOST_GENERATION_PROMPT.format(post_content=post_content)
        
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
        """調用OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except openai.RateLimitError:
            logger.warning("OpenAI rate limit reached, waiting...")
            time.sleep(60)
            raise
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}")
            raise
    
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
    
    def _extract_score(self, response: str) -> Optional[float]:
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
        """獲取活躍的重要性分析prompt"""
        try:
            from models.database import db_manager
            
            # 嘗試從數據庫獲取活躍的prompt
            active_prompt = db_manager.get_active_prompt('importance')
            
            if active_prompt and active_prompt.prompt_content:
                logger.info(f"Using active prompt version: {active_prompt.version_name}")
                return active_prompt.prompt_content
            else:
                logger.info("No active prompt version found, using default from config")
                return IMPORTANCE_FILTER_PROMPT
                
        except Exception as e:
            logger.warning(f"Failed to get active prompt from database: {e}, using default")
            return IMPORTANCE_FILTER_PROMPT
    
    def batch_analyze(self, posts: list, batch_size: int = 5) -> list:
        """
        批量分析貼文
        """
        analyzed_posts = []
        
        for i in range(0, len(posts), batch_size):
            batch = posts[i:i + batch_size]
            
            for post in batch:
                try:
                    content = post.get('original_content', '')
                    # 優先使用 display_name，如果沒有則使用 username
                    author = post.get('author_display_name', '') or post.get('author_username', '')
                    if not content:
                        logger.warning(f"Empty content for post {post.get('post_id')}")
                        continue
                    
                    # 分析重要性（包含作者信息）
                    importance_score = self.analyze_importance(content, author)
                    
                    # 如果重要性評分失敗，跳過這篇貼文
                    if importance_score is None:
                        logger.error(f"Failed to get importance score for post {post.get('post_id')}")
                        continue
                    
                    # 準備分析後的貼文數據
                    analyzed_post = post.copy()
                    analyzed_post['importance_score'] = importance_score
                    
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
                    
                    analyzed_posts.append(analyzed_post)
                    
                    # 避免API調用過於頻繁
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error analyzing post {post.get('post_id', 'unknown')}: {e}")
                    continue
            
            # 批次間稍作暫停
            if i + batch_size < len(posts):
                time.sleep(2)
        
        logger.info(f"Analyzed {len(analyzed_posts)} out of {len(posts)} posts")
        return analyzed_posts