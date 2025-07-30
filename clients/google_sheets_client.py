import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import List, Dict, Any
import logging
from config import (
    GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH,
    INPUT_SPREADSHEET_NAME,
    OUTPUT_SPREADSHEET_NAME,
    INPUT_WORKSHEET_NAME,
    OUTPUT_WORKSHEET_NAME
)

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    def __init__(self):
        self.gc = None
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH, 
                scopes=scopes
            )
            self.gc = gspread.authorize(creds)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise
    
    def get_accounts_to_track(self) -> List[Dict[str, Any]]:
        """從 Google Sheets 讀取要追蹤的帳號列表"""
        try:
            sheet = self.gc.open(INPUT_SPREADSHEET_NAME)
            worksheet = sheet.worksheet(INPUT_WORKSHEET_NAME)
            
            # 獲取所有數據
            data = worksheet.get_all_records()
            
            accounts = []
            for row in data:
                if row.get('platform') and row.get('username'):
                    accounts.append({
                        'platform': row.get('platform', '').lower(),
                        'username': row.get('username', ''),
                        'display_name': row.get('display_name', ''),
                        'category': row.get('category', ''),
                        'priority': row.get('priority', 'medium'),
                        'active': row.get('active', 'true').lower() == 'true'
                    })
            
            logger.info(f"Retrieved {len(accounts)} accounts to track")
            return accounts
            
        except Exception as e:
            logger.error(f"Failed to get accounts from Google Sheets: {e}")
            return []
    
    def write_analyzed_posts(self, posts: List[Dict[str, Any]]) -> bool:
        """將分析後的貼文數據寫入 Google Sheets"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(OUTPUT_WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                # 如果工作表不存在，創建一個新的
                worksheet = sheet.add_worksheet(
                    title=OUTPUT_WORKSHEET_NAME, 
                    rows=1000, 
                    cols=12
                )
                # 設置標題行
                headers = [
                    '時間', '平台', '發文者', '發文者顯示名稱', 
                    '原始內容', '摘要內容', '重要性評分', '轉發內容',
                    '原始貼文URL', '收集時間', '分類', '狀態'
                ]
                worksheet.append_row(headers)
            
            # 準備數據
            rows_to_add = []
            for post in posts:
                row = [
                    post.get('post_time', ''),
                    post.get('platform', ''),
                    post.get('author_username', ''),
                    post.get('author_display_name', ''),
                    post.get('original_content', ''),
                    post.get('summary', ''),
                    post.get('importance_score', ''),
                    post.get('repost_content', ''),
                    post.get('post_url', ''),
                    post.get('collected_at', ''),
                    post.get('category', ''),
                    post.get('status', 'new')
                ]
                rows_to_add.append(row)
            
            # 批量添加數據
            if rows_to_add:
                worksheet.append_rows(rows_to_add)
                logger.info(f"Successfully wrote {len(rows_to_add)} posts to Google Sheets")
                return True
            else:
                logger.warning("No posts to write")
                return True
                
        except Exception as e:
            logger.error(f"Failed to write posts to Google Sheets: {e}")
            return False
    
    def update_post_status(self, post_url: str, status: str) -> bool:
        """更新特定貼文的狀態"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            worksheet = sheet.worksheet(OUTPUT_WORKSHEET_NAME)
            
            # 找到對應的行
            all_values = worksheet.get_all_values()
            headers = all_values[0]
            
            # 找到 URL 和狀態列的索引
            url_col_idx = headers.index('原始貼文URL') + 1
            status_col_idx = headers.index('狀態') + 1
            
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > url_col_idx - 1 and row[url_col_idx - 1] == post_url:
                    worksheet.update_cell(i, status_col_idx, status)
                    logger.info(f"Updated status for post {post_url} to {status}")
                    return True
            
            logger.warning(f"Post with URL {post_url} not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update post status: {e}")
            return False
    
    def get_existing_post_urls(self) -> List[str]:
        """獲取已存在的貼文URL列表，用於去重"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(OUTPUT_WORKSHEET_NAME)
                all_values = worksheet.get_all_values()
                
                if len(all_values) <= 1:  # 只有標題行或空表
                    return []
                
                headers = all_values[0]
                url_col_idx = headers.index('原始貼文URL')
                
                existing_urls = []
                for row in all_values[1:]:
                    if len(row) > url_col_idx and row[url_col_idx]:
                        existing_urls.append(row[url_col_idx])
                
                logger.info(f"Found {len(existing_urls)} existing post URLs")
                return existing_urls
                
            except gspread.WorksheetNotFound:
                logger.info("Output worksheet doesn't exist yet")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get existing post URLs: {e}")
            return []