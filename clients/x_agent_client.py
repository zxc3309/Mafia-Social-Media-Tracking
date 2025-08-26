"""
Twitter Agent Client
使用 agent-twitter-client (Node.js) 的 Python 包裝器
提供不需要官方 API 的 Twitter 資料獲取功能
"""

import subprocess
import json
import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class TwitterFallbackRequired(Exception):
    """當遇到需要 fallback 到其他客戶端的 Twitter 錯誤時拋出"""
    pass


class XAgentClient:
    """
    Twitter Agent 客戶端
    透過 Node.js CLI 工具使用 agent-twitter-client 獲取 Twitter 資料
    """
    
    def __init__(self):
        """初始化 Agent 客戶端"""
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 60  # 60 seconds timeout for CLI calls
        
        # 找到 Node.js CLI 工具的路徑
        self.cli_script = self._find_cli_script()
        
        # 驗證 Node.js 是否可用
        self._check_node_availability()
    
    def _find_cli_script(self):
        """找到 Node.js CLI 腳本的路徑"""
        # 嘗試不同的可能路徑
        base_dir = Path(__file__).parent.parent
        possible_paths = [
            base_dir / 'node_service' / 'twitter_cli.js',
            Path('/app/node_service/twitter_cli.js'),  # Railway 路徑
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found CLI script at: {path}")
                return str(path)
        
        raise RuntimeError(f"Twitter CLI script not found. Searched paths: {[str(p) for p in possible_paths]}")
    
    def _check_node_availability(self):
        """檢查 Node.js 是否可用"""
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                logger.info(f"Node.js available: {result.stdout.strip()}")
                return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        raise RuntimeError("Node.js not found or not executable")
    
    def _call_cli(self, username: str, days_back: int) -> Dict[str, Any]:
        """調用 Node.js CLI 工具"""
        try:
            # 準備命令
            cmd = ['node', self.cli_script, username, str(days_back)]
            
            # 設置環境變數
            env = {
                **os.environ,
                'TWITTER_USERNAME': os.getenv('TWITTER_USERNAME', ''),
                'TWITTER_PASSWORD': os.getenv('TWITTER_PASSWORD', ''),
                'TWITTER_EMAIL': os.getenv('TWITTER_EMAIL', ''),
                'TWITTER_2FA_SECRET': os.getenv('TWITTER_2FA_SECRET', ''),
            }
            
            logger.debug(f"Calling CLI: {' '.join(cmd)}")
            
            # 執行 CLI 工具
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                cwd=Path(self.cli_script).parent
            )
            
            # 解析 JSON 輸出
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    return data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse CLI output as JSON: {e}")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")
            
            # 如果沒有 stdout 或解析失敗，返回錯誤
            return {
                'success': False,
                'error': f"CLI execution failed. STDERR: {result.stderr}",
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"CLI call timed out after {self.timeout} seconds")
            return {'success': False, 'error': 'Request timeout'}
        except Exception as e:
            logger.error(f"CLI call failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        獲取指定用戶的推文
        
        Args:
            username: Twitter 用戶名（不含 @）
            days_back: 獲取過去幾天的推文
            
        Returns:
            推文列表
        """
        posts = []
        
        try:
            # 移除 @ 符號如果存在
            username = username.lstrip('@')
            
            logger.info(f"Fetching tweets for @{username} (last {days_back} days) via Agent CLI")
            
            # 重試邏輯
            for attempt in range(self.max_retries):
                try:
                    # 調用 CLI 工具
                    result = self._call_cli(username, days_back)
                    
                    if result.get('success'):
                        posts = result.get('tweets', [])
                        logger.info(f"Successfully fetched {len(posts)} tweets for @{username}")
                        
                        # 確保時間格式正確
                        for post in posts:
                            if post.get('post_time'):
                                try:
                                    # 確保是 ISO 格式字串
                                    if isinstance(post['post_time'], str):
                                        # 驗證格式
                                        datetime.fromisoformat(post['post_time'].replace('Z', '+00:00'))
                                    else:
                                        # 如果不是字串，轉換為 ISO 格式
                                        post['post_time'] = datetime.utcnow().isoformat()
                                except:
                                    post['post_time'] = datetime.utcnow().isoformat()
                        
                        break
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.error(f"CLI returned error: {error_msg}")
                        
                        # 檢查是否是需要 fallback 的錯誤
                        if self._is_fallback_error(error_msg):
                            logger.warning(f"Detected fallback-required error for @{username}: {error_msg}")
                            # 拋出特殊異常以觸發 fallback
                            raise TwitterFallbackRequired(f"Twitter Error 399 or similar detected: {error_msg}")
                        
                        # 如果是認證問題，重試
                        if 'auth' in error_msg.lower() or 'login' in error_msg.lower():
                            if attempt < self.max_retries - 1:
                                logger.info("Authentication issue detected, retrying...")
                                time.sleep(self.retry_delay)
                                continue
                        
                        # 其他錯誤也重試
                        if attempt < self.max_retries - 1:
                            logger.info(f"Retrying in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                            continue
                        
                except Exception as e:
                    logger.error(f"CLI call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
            
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
        
        return posts
    
    def _is_fallback_error(self, error_msg: str) -> bool:
        """檢查錯誤是否需要 fallback 到其他客戶端"""
        error_msg_lower = error_msg.lower()
        
        # Twitter Error 399 和相關的反機器人保護錯誤
        fallback_patterns = [
            'error 399',
            'incorrect. please try again',
            'authorization required',
            'not authorized',
            'suspended',
            'account suspended',
            'blocked',
            'rate limit exceeded',
            'too many requests',
            'challenge required',
            'phone verification',
            'verify your identity',
            'automation detected',
            'unusual activity'
        ]
        
        return any(pattern in error_msg_lower for pattern in fallback_patterns)
    
    def is_available(self) -> bool:
        """檢查客戶端是否可用"""
        try:
            # 檢查環境變數
            if not os.getenv('TWITTER_USERNAME') or not os.getenv('TWITTER_PASSWORD'):
                logger.warning("Twitter credentials not configured for Agent Client")
                return False
            
            # 檢查 Node.js 是否安裝
            try:
                self._check_node_availability()
            except RuntimeError:
                logger.warning("Node.js not available, Agent Client unavailable")
                return False
            
            # 檢查 CLI 腳本是否存在
            try:
                if not Path(self.cli_script).exists():
                    logger.warning("CLI script not found, Agent Client unavailable")
                    return False
            except:
                logger.warning("CLI script not accessible, Agent Client unavailable")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking Agent Client availability: {e}")
            return False
    
    def cleanup(self):
        """清理資源"""
        # CLI 模式不需要清理常駐進程
        pass
    
    def __del__(self):
        """析構函數"""
        # CLI 模式不需要清理
        pass