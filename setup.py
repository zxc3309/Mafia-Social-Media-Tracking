#!/usr/bin/env python3
"""
社交媒體追蹤系統安裝腳本
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def print_step(step, message):
    print(f"\n{'='*60}")
    print(f"步驟 {step}: {message}")
    print('='*60)

def check_python_version():
    """檢查Python版本"""
    if sys.version_info < (3, 8):
        print("錯誤: 需要 Python 3.8 或更高版本")
        sys.exit(1)
    print(f"✓ Python 版本: {sys.version}")

def install_requirements():
    """安裝依賴包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ 依賴包安裝完成")
        return True
    except subprocess.CalledProcessError:
        print("✗ 依賴包安裝失敗")
        return False

def setup_directories():
    """創建必要的目錄"""
    directories = ['credentials', 'logs', 'data']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ 創建目錄: {directory}")

def setup_config_file():
    """設置配置文件"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy('.env.example', '.env')
            print("✓ 創建 .env 配置文件")
            print("⚠ 請編輯 .env 文件配置您的API密鑰")
        else:
            print("✗ 找不到 .env.example 文件")
            return False
    else:
        print("✓ .env 配置文件已存在")
    
    return True

def test_imports():
    """測試核心模組導入"""
    try:
        import gspread
        import tweepy
        import openai
        import anthropic
        import sqlalchemy
        import apscheduler
        print("✓ 核心模組導入測試通過")
        return True
    except ImportError as e:
        print(f"✗ 模組導入失敗: {e}")
        return False

def create_sample_sheets_template():
    """創建Google Sheets模板說明"""
    template_content = """
# Google Sheets 模板設置

## 輸入表格 (追蹤帳號列表)

請創建一個包含以下欄位的Google Sheets表格：

| platform | username | display_name | category | priority | active |
|----------|----------|--------------|----------|----------|--------|
| twitter  | elonmusk | Elon Musk    | tech     | high     | true   |
| twitter  | naval    | Naval        | business | medium   | true   |
| linkedin | satyanadella | Satya Nadella | tech | high | true |

欄位說明：
- platform: 平台名稱 (twitter/linkedin)
- username: 用戶名 (不含@符號)
- display_name: 顯示名稱
- category: 分類標籤
- priority: 優先級 (high/medium/low)
- active: 是否啟用追蹤 (true/false)

## 輸出表格 (分析結果)

系統會自動創建輸出表格，包含以下欄位：
- 時間: 貼文發布時間
- 平台: 來源平台
- 發文者: 用戶名
- 發文者顯示名稱: 顯示名稱
- 原始內容: 貼文原始內容
- 摘要內容: AI生成的摘要
- 重要性評分: 1-10的重要性評分
- 轉發內容: AI生成的轉發內容
- 原始貼文URL: 貼文鏈接
- 收集時間: 數據收集時間
- 分類: 帳號分類
- 狀態: 處理狀態

## 設置步驟

1. 創建Google Sheets文檔
2. 設置輸入表格（按上述格式）
3. 與服務帳號郵箱共享編輯權限
4. 在config.py中配置表格名稱
"""
    
    with open('SHEETS_TEMPLATE.md', 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print("✓ 創建 Google Sheets 模板說明文件")

def main():
    """主安裝流程"""
    print("社交媒體追蹤系統 - 安裝腳本")
    print(f"當前目錄: {os.getcwd()}")
    
    # 步驟1: 檢查Python版本
    print_step(1, "檢查Python版本")
    check_python_version()
    
    # 步驟2: 創建目錄結構
    print_step(2, "創建目錄結構")
    setup_directories()
    
    # 步驟3: 安裝依賴包
    print_step(3, "安裝Python依賴包")
    if not install_requirements():
        print("安裝失敗，請手動執行: pip install -r requirements.txt")
        return False
    
    # 步驟4: 設置配置文件
    print_step(4, "設置配置文件")
    if not setup_config_file():
        return False
    
    # 步驟5: 測試模組導入
    print_step(5, "測試核心模組")
    if not test_imports():
        print("模組測試失敗，請檢查依賴包安裝")
        return False
    
    # 步驟6: 創建模板文件
    print_step(6, "創建模板和說明文件")
    create_sample_sheets_template()
    
    # 完成
    print("\n" + "="*60)
    print("🎉 安裝完成！")
    print("="*60)
    
    print("\n下一步操作：")
    print("1. 編輯 .env 文件，配置API密鑰")
    print("2. 設置 Google Sheets 服務帳號憑證")
    print("3. 創建並配置 Google Sheets 表格")
    print("4. 運行測試: python main.py --test")
    print("5. 執行收集: python main.py --run-once")
    
    print("\n參考文件：")
    print("- README.md: 詳細使用說明")  
    print("- SHEETS_TEMPLATE.md: Google Sheets 設置指南")
    print("- .env.example: 配置文件範例")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n安裝被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n安裝過程中出錯: {e}")
        sys.exit(1)