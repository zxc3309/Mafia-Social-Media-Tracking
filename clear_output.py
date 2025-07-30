#!/usr/bin/env python3
"""
清理 Google Sheets 輸出工作表的腳本
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients.google_sheets_client import GoogleSheetsClient

def clear_output_sheet():
    try:
        print("🧹 清理 Google Sheets 輸出數據...")
        
        client = GoogleSheetsClient()
        
        # 獲取現有的 URLs 看看有什麼測試數據
        existing_urls = client.get_existing_post_urls()
        print(f"找到 {len(existing_urls)} 條現有記錄")
        
        if existing_urls:
            print("現有記錄:")
            for i, url in enumerate(existing_urls[:5], 1):  # 只顯示前5條
                print(f"  {i}. {url}")
            if len(existing_urls) > 5:
                print(f"  ... 還有 {len(existing_urls) - 5} 條")
        
        # 創建新的乾淨工作表
        import gspread
        from google.oauth2.service_account import Credentials
        from config import (
            GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH,
            OUTPUT_SPREADSHEET_NAME,
            OUTPUT_WORKSHEET_NAME
        )
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH, 
            scopes=scopes
        )
        gc = gspread.authorize(creds)
        
        sheet = gc.open(OUTPUT_SPREADSHEET_NAME)
        
        try:
            worksheet = sheet.worksheet(OUTPUT_WORKSHEET_NAME)
            # 清除所有數據但保留標題
            worksheet.clear()
            
            # 重新添加標題行
            headers = [
                '時間', '平台', '發文者', '發文者顯示名稱', 
                '原始內容', '摘要內容', '重要性評分', '轉發內容',
                '原始貼文URL', '收集時間', '分類', '狀態'
            ]
            worksheet.append_row(headers)
            
            print("✅ 成功清理並重設標題行")
            
        except gspread.WorksheetNotFound:
            print("⚠️ 輸出工作表不存在，將在首次寫入時自動創建")
        
    except Exception as e:
        print(f"❌ 清理失敗: {e}")

if __name__ == "__main__":
    clear_output_sheet()