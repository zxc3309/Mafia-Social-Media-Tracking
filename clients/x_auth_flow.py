"""
Twitter 認證流程處理模組
基於 agent-twitter-client 的登入流程實現
"""

import json
import time
import logging
import asyncio
import random
from typing import Dict, Any, Optional, List
import pyotp

from .x_http_session import TwitterHTTPSession
from .x_endpoints import TwitterEndpoints

logger = logging.getLogger(__name__)


class TwitterAuthFlow:
    """Twitter 認證流程管理器"""
    
    def __init__(self, session: TwitterHTTPSession, bearer_token: str):
        self.session = session
        self.bearer_token = bearer_token
        self.endpoints = TwitterEndpoints()
        self.guest_token = None
        self.flow_token = None
    
    async def authenticate_guest(self) -> str:
        """獲取 guest token"""
        try:
            # 設置基本 Twitter 請求頭
            self.session.set_twitter_headers(self.bearer_token)
            
            # 請求 guest token
            response = self.session.post(
                self.endpoints.AUTH_ENDPOINTS['guest_activate'],
                headers={
                    'authorization': f'Bearer {self.bearer_token}'
                }
            )
            
            if not response.ok:
                raise Exception(f"Failed to get guest token: {response.status_code} {response.text}")
            
            data = response.json()
            guest_token = data.get('guest_token')
            
            if not guest_token:
                raise Exception("No guest_token in response")
            
            self.guest_token = guest_token
            
            # 更新會話頭部
            self.session.set_twitter_headers(self.bearer_token, guest_token)
            
            logger.info("Successfully obtained guest token")
            return guest_token
            
        except Exception as e:
            logger.error(f"Guest authentication failed: {e}")
            raise
    
    async def login_user(self, username: str, password: str, email: str = None, 
                        totp_secret: str = None) -> bool:
        """用戶登入流程"""
        try:
            # 會話預熱 - 模擬正常瀏覽器行為
            await self._warm_up_session()
            
            # 首先獲取 guest token
            if not self.guest_token:
                await self.authenticate_guest()
            
            # 初始化登入流程
            flow_result = await self._init_login_flow()
            
            # 處理各種 subtasks
            while flow_result.get('status') == 'continue' and flow_result.get('subtask'):
                subtask = flow_result['subtask']
                subtask_id = subtask.get('subtask_id')
                
                logger.debug(f"Processing subtask: {subtask_id}")
                
                # 添加人類思考延遲 (模擬真實用戶行為)
                thinking_delay = random.uniform(1.5, 4.0)
                await asyncio.sleep(thinking_delay)
                
                if subtask_id == 'LoginJsInstrumentationSubtask':
                    flow_result = await self._handle_js_instrumentation(flow_result)
                    
                elif subtask_id == 'LoginEnterUserIdentifierSSO':
                    # 模擬輸入用戶名的時間
                    await asyncio.sleep(random.uniform(0.8, 2.0))
                    flow_result = await self._handle_enter_username(flow_result, username)
                    
                elif subtask_id == 'LoginEnterAlternateIdentifierSubtask':
                    # 模擬輸入替代識別的時間
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    # 嘗試不同的驗證方式
                    if email:
                        flow_result = await self._handle_enter_email(flow_result, email)
                    else:
                        # 如果沒有 email，嘗試使用用戶名作為替代驗證
                        flow_result = await self._handle_enter_email(flow_result, username)
                    
                elif subtask_id == 'LoginEnterPassword':
                    # 模擬輸入密碼的時間 (通常較慢)
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                    flow_result = await self._handle_enter_password(flow_result, password)
                    
                elif subtask_id == 'AccountDuplicationCheck':
                    flow_result = await self._handle_duplication_check(flow_result)
                    
                elif subtask_id == 'LoginTwoFactorAuthChallenge':
                    if not totp_secret:
                        raise Exception("TOTP secret required for 2FA")
                    flow_result = await self._handle_2fa(flow_result, totp_secret)
                    
                elif subtask_id == 'LoginAcid':
                    if not email:
                        raise Exception("Email required for LoginAcid")
                    flow_result = await self._handle_acid(flow_result, email)
                    
                elif subtask_id == 'LoginSuccessSubtask':
                    flow_result = await self._handle_success(flow_result)
                    
                else:
                    raise Exception(f"Unknown subtask: {subtask_id}")
            
            if flow_result.get('status') == 'success':
                logger.info(f"Successfully logged in as {username}")
                return True
            else:
                raise Exception(f"Login failed: {flow_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"User login failed: {e}")
            raise
    
    async def _init_login_flow(self) -> Dict[str, Any]:
        """初始化登入流程"""
        # 清除特定的會話 cookies
        cookies_to_clear = [
            'twitter_ads_id', 'ads_prefs', '_twitter_sess', 'zipbox_forms_auth_token',
            'lang', 'bouncer_reset_cookie', 'twid', 'twitter_ads_idb', 'email_uid',
            'external_referer', 'ct0', 'aa_u', '__cf_bm'
        ]
        
        for cookie_name in cookies_to_clear:
            # 簡單的清除方式，直接從會話中刪除
            self.session.session.cookies.pop(cookie_name, None)
        
        # 構建初始化請求數據
        request_data = {
            "flow_name": "login",
            "input_flow_data": {
                "flow_context": {
                    "debug_overrides": {},
                    "start_location": {
                        "location": "unknown"
                    }
                }
            },
            "subtask_versions": self._get_subtask_versions()
        }
        
        return await self._execute_flow_task(request_data)
    
    def _get_subtask_versions(self) -> Dict[str, int]:
        """獲取 subtask 版本配置"""
        return {
            "action_list": 2,
            "alert_dialog": 1,
            "app_download_cta": 1,
            "check_logged_in_account": 1,
            "choice_selection": 3,
            "contacts_live_sync_permission_prompt": 0,
            "cta": 7,
            "email_verification": 2,
            "end_flow": 1,
            "enter_date": 1,
            "enter_email": 2,
            "enter_password": 5,
            "enter_phone": 2,
            "enter_recaptcha": 1,
            "enter_text": 5,
            "enter_username": 2,
            "generic_urt": 3,
            "in_app_notification": 1,
            "interest_picker": 3,
            "js_instrumentation": 1,
            "menu_dialog": 1,
            "notifications_permission_prompt": 2,
            "open_account": 2,
            "open_home_timeline": 1,
            "open_link": 1,
            "phone_verification": 4,
            "privacy_options": 1,
            "security_key": 3,
            "select_avatar": 4,
            "select_banner": 2,
            "settings_list": 7,
            "show_code": 1,
            "sign_up": 2,
            "sign_up_review": 4,
            "tweet_selection_urt": 1,
            "update_users": 1,
            "upload_media": 1,
            "user_recommendations_list": 4,
            "user_recommendations_urt": 1,
            "wait_spinner": 3,
            "web_modal": 1
        }
    
    async def _handle_js_instrumentation(self, prev_result: Dict[str, Any]) -> Dict[str, Any]:
        """處理 JS instrumentation subtask"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": [{
                "subtask_id": "LoginJsInstrumentationSubtask",
                "js_instrumentation": {
                    "response": "{}",
                    "link": "next_link"
                }
            }]
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _handle_enter_username(self, prev_result: Dict[str, Any], username: str) -> Dict[str, Any]:
        """處理用戶名輸入"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": [{
                "subtask_id": "LoginEnterUserIdentifierSSO",
                "settings_list": {
                    "setting_responses": [{
                        "key": "user_identifier",
                        "response_data": {
                            "text_data": {"result": username}
                        }
                    }],
                    "link": "next_link"
                }
            }]
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _handle_enter_email(self, prev_result: Dict[str, Any], email: str) -> Dict[str, Any]:
        """處理 email 輸入"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": [{
                "subtask_id": "LoginEnterAlternateIdentifierSubtask",
                "enter_text": {
                    "text": email,
                    "link": "next_link"
                }
            }]
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _handle_enter_password(self, prev_result: Dict[str, Any], password: str) -> Dict[str, Any]:
        """處理密碼輸入"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": [{
                "subtask_id": "LoginEnterPassword",
                "enter_password": {
                    "password": password,
                    "link": "next_link"
                }
            }]
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _handle_duplication_check(self, prev_result: Dict[str, Any]) -> Dict[str, Any]:
        """處理帳號重複檢查"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": [{
                "subtask_id": "AccountDuplicationCheck",
                "check_logged_in_account": {
                    "link": "AccountDuplicationCheck_false"
                }
            }]
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _handle_2fa(self, prev_result: Dict[str, Any], totp_secret: str) -> Dict[str, Any]:
        """處理兩步驟驗證"""
        # 生成 TOTP 代碼
        totp = pyotp.TOTP(totp_secret)
        
        # 重試機制，因為 TOTP 可能因時間問題失敗
        for attempt in range(3):
            try:
                totp_code = totp.now()
                
                request_data = {
                    "flow_token": prev_result['flow_token'],
                    "subtask_inputs": [{
                        "subtask_id": "LoginTwoFactorAuthChallenge",
                        "enter_text": {
                            "link": "next_link",
                            "text": totp_code
                        }
                    }]
                }
                
                result = await self._execute_flow_task(request_data)
                
                # 如果成功或者不是因為 2FA 失敗，返回結果
                if result.get('status') != 'error' or '2fa' not in result.get('error', '').lower():
                    return result
                    
                # 等待下一個時間窗口 (增加隨機性)
                await asyncio.sleep(random.uniform(3.0, 6.0) * (attempt + 1))
                
            except Exception as e:
                if attempt == 2:  # 最後一次嘗試
                    raise
                await asyncio.sleep(random.uniform(2.0, 4.0) * (attempt + 1))
        
        raise Exception("2FA authentication failed after 3 attempts")
    
    async def _handle_acid(self, prev_result: Dict[str, Any], email: str) -> Dict[str, Any]:
        """處理 LoginAcid (email 驗證)"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": [{
                "subtask_id": "LoginAcid",
                "enter_text": {
                    "text": email,
                    "link": "next_link"
                }
            }]
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _handle_success(self, prev_result: Dict[str, Any]) -> Dict[str, Any]:
        """處理登入成功"""
        request_data = {
            "flow_token": prev_result['flow_token'],
            "subtask_inputs": []
        }
        
        return await self._execute_flow_task(request_data)
    
    async def _execute_flow_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行 flow task 請求"""
        try:
            # 構建 URL
            url = self.endpoints.AUTH_ENDPOINTS['onboarding_task']
            if 'flow_name' in request_data:
                url += f"?flow_name={request_data['flow_name']}"
            
            # 設置完整的請求頭
            headers = {
                'authorization': f'Bearer {self.bearer_token}',
                'content-type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Nokia G20) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.88 Mobile Safari/537.36',
                'x-guest-token': self.guest_token,
                'x-twitter-auth-type': 'OAuth2Client',
                'x-twitter-active-user': 'yes',
                'x-twitter-client-language': 'en'
            }
            
            # 發送請求
            response = self.session.post(
                url,
                data=json.dumps(request_data),
                headers=headers
            )
            
            if not response.ok:
                return {
                    'status': 'error',
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
            
            data = response.json()
            
            # 檢查錯誤
            if data.get('errors'):
                errors = data.get('errors', [])
                error_messages = []
                for error in errors:
                    code = error.get('code')
                    message = error.get('message', 'Unknown error')
                    error_messages.append(f"Code {code}: {message}")
                    
                    # 記錄詳細錯誤信息以便調試
                    logger.error(f"Twitter API Error - Code: {code}, Message: {message}")
                
                return {
                    'status': 'error',
                    'error': '; '.join(error_messages),
                    'error_codes': [e.get('code') for e in errors]
                }
            
            flow_token = data.get('flow_token')
            if not flow_token:
                return {
                    'status': 'error',
                    'error': 'No flow_token in response'
                }
            
            self.flow_token = flow_token
            
            # 獲取下一個 subtask
            subtasks = data.get('subtasks', [])
            subtask = subtasks[0] if subtasks else None
            
            # 檢查是否為拒絕登入
            if subtask and subtask.get('subtask_id') == 'DenyLoginSubtask':
                return {
                    'status': 'error',
                    'error': 'Login denied by Twitter'
                }
            
            # 檢查是否登入成功
            if not subtask or subtask.get('subtask_id') == 'LoginSuccessSubtask':
                return {
                    'status': 'success',
                    'flow_token': flow_token
                }
            
            return {
                'status': 'continue',
                'flow_token': flow_token,
                'subtask': subtask
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _warm_up_session(self):
        """模擬正常瀏覽器行為預熱會話 (降低安全限制風險)"""
        try:
            logger.debug("Warming up session with normal browsing behavior")
            
            # 1. 訪問 Twitter 首頁 (模擬正常用戶訪問)
            response = self.session.get('https://x.com', timeout=10)
            if response.ok:
                logger.debug("Visited Twitter homepage successfully")
            
            # 隨機延遲 2-4 秒
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # 2. 訪問登入頁 (模擬用戶點擊登入)
            response = self.session.get('https://x.com/i/flow/login', timeout=10)
            if response.ok:
                logger.debug("Visited login page successfully")
            
            # 隨機延遲 1-3 秒 (模擬用戶閱讀登入頁的時間)
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            logger.debug("Session warm-up completed")
            
        except Exception as e:
            logger.warning(f"Session warm-up failed, continuing anyway: {e}")
            # 預熱失敗不應該阻止認證流程
            pass
    
    async def verify_login(self) -> bool:
        """驗證登入狀態"""
        try:
            response = self.session.get(self.endpoints.AUTH_ENDPOINTS['verify_credentials'])
            
            if response.ok:
                data = response.json()
                return not data.get('errors')
            
            return False
            
        except Exception:
            return False
    
    async def logout(self) -> bool:
        """登出"""
        try:
            response = self.session.post(self.endpoints.AUTH_ENDPOINTS['logout'])
            
            if response.ok:
                # 清除 cookies
                self.session.clear_cookies()
                self.guest_token = None
                self.flow_token = None
                return True
            
            return False
            
        except Exception:
            return False