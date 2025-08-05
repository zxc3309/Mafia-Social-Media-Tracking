#!/usr/bin/env python3
"""
設置爬蟲環境的腳本

功能：
1. 安裝 Playwright 瀏覽器
2. 創建必要的目錄
3. 初始化配置
"""

import subprocess
import os
import sys
from pathlib import Path


def install_playwright_browsers():
    """安裝 Playwright 瀏覽器"""
    print("🔧 安裝 Playwright 瀏覽器...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Playwright Chromium 瀏覽器安裝成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 安裝失敗: {e}")
        return False
    return True


def create_directories():
    """創建必要的目錄"""
    print("📁 創建必要的目錄...")
    
    directories = [
        "scraper_cookies",  # Cookie 存儲目錄
        "logs",  # 日誌目錄
    ]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"  ✅ 創建目錄: {dir_name}")


def check_env_file():
    """檢查 .env 文件配置"""
    print("🔍 檢查環境配置...")
    
    if not os.path.exists('.env'):
        print("  ⚠️  未找到 .env 文件")
        print("  📝 請複製 .env.example 並配置以下爬蟲相關設置:")
        print("     - USE_X_SCRAPER=true (啟用爬蟲)")
        print("     - X_SCRAPER_ACCOUNTS (爬蟲帳號)")
        print("     - SCRAPER_PROXY_LIST (代理列表，可選)")
        return False
    
    print("  ✅ 找到 .env 文件")
    return True


def main():
    """主函數"""
    print("🚀 開始設置 X/Twitter 爬蟲環境")
    print("=" * 50)
    
    # 1. 安裝 Playwright 瀏覽器
    if not install_playwright_browsers():
        print("❌ 設置失敗：無法安裝瀏覽器")
        return 1
    
    # 2. 創建目錄
    create_directories()
    
    # 3. 檢查配置
    check_env_file()
    
    print("=" * 50)
    print("✅ 爬蟲環境設置完成！")
    print("\n📋 使用說明:")
    print("1. 編輯 .env 文件，設置 USE_X_SCRAPER=true")
    print("2. 添加 X_SCRAPER_ACCOUNTS 配置（格式: username:password）")
    print("3. （可選）添加代理配置 SCRAPER_PROXY_LIST")
    print("4. 運行 python main.py --run-once 測試爬蟲功能")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())