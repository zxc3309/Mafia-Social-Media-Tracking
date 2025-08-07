#!/usr/bin/env python3
"""
Railway 資訊獲取工具
用於獲取正確的 Railway project/service IDs
"""

import subprocess
import json
import sys

def run_command(cmd):
    """執行命令並返回結果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Exception: {str(e)}"

def main():
    print("🚂 Railway 資訊獲取工具")
    print("=" * 40)
    
    # 檢查 Railway CLI 是否安裝
    print("1. 檢查 Railway CLI...")
    cli_check = run_command("railway --version")
    print(f"   Railway CLI: {cli_check}")
    
    if "Error" in cli_check or "Exception" in cli_check:
        print("\n❌ Railway CLI 未安裝，請先安裝：")
        print("   npm install -g @railway/cli")
        return
    
    # 檢查登錄狀態
    print("\n2. 檢查登錄狀態...")
    whoami = run_command("railway whoami")
    print(f"   登錄狀態: {whoami}")
    
    # 獲取項目資訊
    print("\n3. 獲取項目資訊...")
    
    # 列出所有項目
    projects = run_command("railway projects")
    print(f"   可用項目:\n{projects}")
    
    # 獲取當前項目資訊（如果已連結）
    print("\n4. 當前項目狀態...")
    status = run_command("railway status")
    print(f"   狀態: {status}")
    
    # 嘗試獲取環境變數（需要先 link 到項目）
    print("\n5. 環境資訊...")
    env_info = run_command("railway variables")
    if "Error" not in env_info:
        print(f"   環境變數預覽: {env_info[:200]}...")
    else:
        print(f"   環境變數: {env_info}")
    
    print("\n" + "=" * 40)
    print("📋 設置 GitHub Secrets 所需資訊：")
    print("1. RAILWAY_TOKEN: 到 https://railway.app/account/tokens 創建")
    print("2. RAILWAY_SERVICE_ID: 從上面的狀態資訊獲取")
    print("3. 或使用 RAILWAY_ENVIRONMENT_ID 替代")
    
    # 提供手動命令
    print("\n🔧 手動獲取命令：")
    print("railway login")
    print("railway link  # 選擇你的項目")
    print("railway status  # 獲取 project/service ID")

if __name__ == "__main__":
    main()