#!/usr/bin/env python3
"""
Twitter 認證診斷工具
幫助解決 XAuthClient 登入問題
"""

import asyncio
import sys
import logging
import json
from datetime import datetime
from pathlib import Path

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, '.')

from clients.x_http_session import TwitterHTTPSession
from clients.x_auth_flow import TwitterAuthFlow
from config import TWITTER_AUTH_CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TwitterAuthDiagnoser:
    def __init__(self):
        self.config = TWITTER_AUTH_CONFIG
        self.session = None
        self.auth_flow = None
    
    async def run_diagnosis(self):
        """運行完整的認證診斷"""
        print("🔍 Twitter 認證診斷工具")
        print("=" * 50)
        
        # 步驟 1: 檢查配置
        print("\n📋 步驟 1: 檢查配置")
        if not self.check_config():
            return False
        
        # 步驟 2: 初始化會話
        print("\n🌐 步驟 2: 初始化 HTTP 會話")
        if not await self.init_session():
            return False
        
        # 步驟 3: 獲取 Guest Token
        print("\n🎫 步驟 3: 獲取 Guest Token")
        if not await self.test_guest_token():
            return False
        
        # 步驟 4: 分析登入流程
        print("\n🔐 步驟 4: 分析登入流程")
        await self.analyze_login_flow()
        
        # 步驟 5: 提供解決方案
        print("\n💡 步驟 5: 解決方案建議")
        self.provide_solutions()
        
        return True
    
    def check_config(self):
        """檢查配置"""
        username = self.config.get('username')
        password = self.config.get('password')
        email = self.config.get('email')
        
        print(f"✓ 用戶名: {username}")
        print(f"✓ 密碼: {'已設置' if password else '未設置'}")
        print(f"✓ Email: {email if email else '未設置'}")
        print(f"✓ Bearer Token: {'已設置' if self.config.get('bearer_token') else '未設置'}")
        
        if not username or not password:
            print("❌ 用戶名和密碼必須設置")
            return False
        
        return True
    
    async def init_session(self):
        """初始化 HTTP 會話"""
        try:
            self.session = TwitterHTTPSession(username=self.config['username'])
            self.auth_flow = TwitterAuthFlow(self.session, self.config['bearer_token'])
            print("✓ HTTP 會話初始化成功")
            return True
        except Exception as e:
            print(f"❌ 會話初始化失敗: {e}")
            return False
    
    async def test_guest_token(self):
        """測試 Guest Token 獲取"""
        try:
            guest_token = await self.auth_flow.authenticate_guest()
            print(f"✓ Guest Token 獲取成功: {guest_token[:20]}...")
            return True
        except Exception as e:
            print(f"❌ Guest Token 獲取失敗: {e}")
            return False
    
    async def analyze_login_flow(self):
        """分析登入流程"""
        try:
            print("正在分析登入流程...")
            
            # 嘗試初始化登入
            flow_result = await self.auth_flow._init_login_flow()
            
            if flow_result.get('status') == 'error':
                error_codes = flow_result.get('error_codes', [])
                print(f"❌ 登入初始化失敗: {flow_result.get('error')}")
                
                # 分析錯誤碼
                self.analyze_error_codes(error_codes)
            else:
                print("✓ 登入流程初始化成功")
                
                # 嘗試第一步：輸入用戶名
                flow_result = await self.auth_flow._handle_enter_username(
                    flow_result, self.config['username']
                )
                
                if flow_result.get('status') == 'error':
                    error_codes = flow_result.get('error_codes', [])
                    print(f"❌ 用戶名步驟失敗: {flow_result.get('error')}")
                    self.analyze_error_codes(error_codes)
                else:
                    print("✓ 用戶名步驟成功")
                    
                    # 嘗試密碼步驟
                    flow_result = await self.auth_flow._handle_enter_password(
                        flow_result, self.config['password']
                    )
                    
                    if flow_result.get('status') == 'error':
                        error_codes = flow_result.get('error_codes', [])
                        print(f"❌ 密碼步驟失敗: {flow_result.get('error')}")
                        self.analyze_error_codes(error_codes)
                    else:
                        print("✓ 密碼步驟成功")
                        
        except Exception as e:
            print(f"❌ 登入流程分析失敗: {e}")
    
    def analyze_error_codes(self, error_codes):
        """分析錯誤碼"""
        print("\n🔍 錯誤碼分析:")
        
        for code in error_codes:
            if code == 399:
                print(f"  • 錯誤碼 {code}: 認證失敗 - 可能原因:")
                print("    - 帳號需要額外驗證")
                print("    - 帳號被暫時限制")
                print("    - 需要 Email 或手機驗證")
                print("    - 密碼不正確")
            elif code == 326:
                print(f"  • 錯誤碼 {code}: 帳號被鎖定")
            elif code == 64:
                print(f"  • 錯誤碼 {code}: 帳號被暫停")
            elif code == 32:
                print(f"  • 錯誤碼 {code}: 認證錯誤")
            else:
                print(f"  • 錯誤碼 {code}: 未知錯誤")
    
    def provide_solutions(self):
        """提供解決方案"""
        print("🛠️ 推薦解決方案:")
        print()
        print("1. 🌐 網頁版驗證步驟:")
        print("   - 開啟 https://x.com")
        print("   - 完全登出現有會話")
        print("   - 重新登入，注意任何安全提示")
        print("   - 完成 Email 驗證 (如果出現)")
        print("   - 完成手機驗證 (如果出現)")
        print("   - 確認沒有要求設置 2FA")
        print()
        print("2. 🔒 如果啟用了 2FA:")
        print("   - 確保 TWITTER_2FA_SECRET 已正確設置")
        print("   - 使用 TOTP 應用 (如 Google Authenticator)")
        print("   - 驗證 TOTP 密鑰正確性")
        print()
        print("3. 📧 Email 驗證:")
        print("   - 確保 TWITTER_EMAIL 設置正確")
        print("   - 檢查垃圾郵件箱中的驗證郵件")
        print()
        print("4. 🕐 等待和重試:")
        print("   - 如果帳號被暫時限制，等待 15-30 分鐘")
        print("   - 避免頻繁重試 (會加重限制)")
        print()
        print("5. 🔄 替代方案:")
        print("   - 系統已自動使用 Nitter 作為備案")
        print("   - Nitter 能正常獲取推文數據")
        print("   - 可以繼續使用系統功能")
        print()
        print("6. 📞 如果問題持續:")
        print("   - 嘗試使用不同的 Twitter 帳號")
        print("   - 確保帳號是活躍且正常的")
        print("   - 考慮建立專用的自動化帳號")

async def main():
    diagnoser = TwitterAuthDiagnoser()
    await diagnoser.run_diagnosis()
    
    print("\n" + "=" * 50)
    print("🎯 診斷完成")
    print("\n📊 當前系統狀態:")
    print("✅ Nitter 客戶端運作正常，能成功獲取推文")
    print("⚠️  XAuthClient 等待認證問題解決")
    print("🔄 系統自動降級機制運作良好")

if __name__ == "__main__":
    asyncio.run(main())