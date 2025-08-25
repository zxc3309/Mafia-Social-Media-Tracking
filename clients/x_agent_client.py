"""
Twitter Agent Client
使用 agent-twitter-client (Node.js) 的 Python 包裝器
提供不需要官方 API 的 Twitter 資料獲取功能
"""

import requests
import subprocess
import time
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class XAgentClient:
    """
    Twitter Agent 客戶端
    透過 Node.js 服務使用 agent-twitter-client 獲取 Twitter 資料
    """
    
    def __init__(self):
        """初始化 Agent 客戶端"""
        self.service_port = int(os.getenv('AGENT_SERVICE_PORT', '3456'))
        self.service_url = f"http://localhost:{self.service_port}"
        self.service_process = None
        self.max_retries = 3
        self.retry_delay = 2
        
        # 確保服務正在運行
        self._ensure_service_running()
    
    def _ensure_service_running(self):
        """確保 Node.js 服務正在運行"""
        try:
            # 檢查服務是否已經在運行
            response = requests.get(f"{self.service_url}/health", timeout=2)
            if response.status_code == 200:
                logger.info(f"Twitter Agent Service is already running on port {self.service_port}")
                return
        except requests.exceptions.RequestException:
            # 服務未運行，嘗試啟動
            logger.info("Twitter Agent Service not running, attempting to start...")
            self._start_service()
    
    def _start_service(self):
        """啟動 Node.js 服務"""
        try:
            # 檢查 node_service 目錄是否存在
            service_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'node_service')
            if not os.path.exists(service_dir):
                raise RuntimeError(f"Node service directory not found: {service_dir}")
            
            # 檢查是否已安裝依賴
            node_modules_path = os.path.join(service_dir, 'node_modules')
            agent_dist_path = os.path.join(service_dir, 'agent-twitter-client', 'dist')
            
            if not os.path.exists(node_modules_path):
                logger.info("Installing Node.js dependencies...")
                subprocess.run(['npm', 'install'], cwd=service_dir, check=True)
            
            if not os.path.exists(agent_dist_path):
                logger.info("Building agent-twitter-client...")
                subprocess.run(['npm', 'run', 'install-agent'], cwd=service_dir, check=True)
            
            # 啟動服務
            logger.info(f"Starting Twitter Agent Service on port {self.service_port}...")
            self.service_process = subprocess.Popen(
                ['node', 'twitter_service.js'],
                cwd=service_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, 'AGENT_SERVICE_PORT': str(self.service_port)}
            )
            
            # 等待服務啟動
            for i in range(30):  # 最多等待 30 秒
                time.sleep(1)
                try:
                    response = requests.get(f"{self.service_url}/health", timeout=2)
                    if response.status_code == 200:
                        logger.info("Twitter Agent Service started successfully")
                        return
                except requests.exceptions.RequestException:
                    continue
            
            raise RuntimeError("Failed to start Twitter Agent Service within timeout")
            
        except Exception as e:
            logger.error(f"Failed to start Twitter Agent Service: {e}")
            raise
    
    def test_connection(self) -> bool:
        """測試與服務的連接"""
        try:
            response = requests.get(f"{self.service_url}/test", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('success', False)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
        return False
    
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
            
            logger.info(f"Fetching tweets for @{username} (last {days_back} days) via Agent Client")
            
            # 準備請求資料
            payload = {
                'username': username,
                'days_back': days_back
            }
            
            # 重試邏輯
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        f"{self.service_url}/get_user_tweets",
                        json=payload,
                        timeout=30  # 較長的 timeout，因為可能需要登入
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            posts = data.get('tweets', [])
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
                            error_msg = data.get('error', 'Unknown error')
                            logger.error(f"Service returned error: {error_msg}")
                            
                            # 如果是認證問題，可能需要重新啟動服務
                            if 'auth' in error_msg.lower() or 'login' in error_msg.lower():
                                if attempt < self.max_retries - 1:
                                    logger.info("Authentication issue detected, retrying...")
                                    time.sleep(self.retry_delay)
                                    continue
                    else:
                        logger.error(f"Service returned status code: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    logger.error(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                except requests.exceptions.ConnectionError:
                    logger.error(f"Connection error (attempt {attempt + 1}/{self.max_retries})")
                    # 嘗試重新啟動服務
                    if attempt < self.max_retries - 1:
                        self._ensure_service_running()
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
        
        return posts
    
    def is_available(self) -> bool:
        """檢查客戶端是否可用"""
        try:
            # 檢查環境變數
            if not os.getenv('TWITTER_USERNAME') or not os.getenv('TWITTER_PASSWORD'):
                logger.warning("Twitter credentials not configured for Agent Client")
                return False
            
            # 檢查 Node.js 是否安裝
            try:
                subprocess.run(['node', '--version'], 
                             capture_output=True, 
                             check=True, 
                             timeout=2)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("Node.js not installed, Agent Client unavailable")
                return False
            
            # 檢查服務連接
            return self.test_connection()
            
        except Exception as e:
            logger.error(f"Error checking Agent Client availability: {e}")
            return False
    
    def cleanup(self):
        """清理資源"""
        if self.service_process:
            try:
                logger.info("Stopping Twitter Agent Service...")
                self.service_process.terminate()
                self.service_process.wait(timeout=5)
            except:
                self.service_process.kill()
            finally:
                self.service_process = None
    
    def __del__(self):
        """析構函數"""
        # 注意：通常不停止服務，讓它繼續運行供其他實例使用
        pass