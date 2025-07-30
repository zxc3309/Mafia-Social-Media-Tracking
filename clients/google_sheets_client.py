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
    OUTPUT_WORKSHEET_NAME,
    ALL_POSTS_WORKSHEET_NAME,
    PROMPT_HISTORY_WORKSHEET_NAME
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
    
    def write_all_posts_with_scores(self, posts: List[Dict[str, Any]]) -> bool:
        """將所有貼文及其AI評分寫入專門的工作表"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(ALL_POSTS_WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                # 創建新工作表
                worksheet = sheet.add_worksheet(
                    title=ALL_POSTS_WORKSHEET_NAME, 
                    rows=5000, 
                    cols=15
                )
                # 設置標題行
                headers = [
                    '收集時間', '平台', '發文者', '發文者顯示名稱', 
                    '貼文時間', '原始內容', '內容預覽', 
                    'AI重要性評分', '評分狀態', '人工評分', '評分差異', '文字反饋',
                    '原始貼文URL', 'Post ID', '分類', '備註'
                ]
                worksheet.append_row(headers)
                logger.info(f"Created new worksheet: {ALL_POSTS_WORKSHEET_NAME}")
            
            # 準備數據
            rows_to_add = []
            for post in posts:
                # 計算內容預覽（前100字符）
                content = post.get('original_content', '')
                content_preview = content[:100] + "..." if len(content) > 100 else content
                
                # 計算評分差異
                ai_score = post.get('importance_score', '')
                human_score = post.get('human_score', '')
                score_diff = ''
                if ai_score and human_score:
                    try:
                        score_diff = float(ai_score) - float(human_score)
                        score_diff = f"{score_diff:+.1f}"
                    except (ValueError, TypeError):
                        score_diff = ''
                
                row = [
                    post.get('collected_at', ''),
                    post.get('platform', ''),
                    post.get('author_username', ''),
                    post.get('author_display_name', ''),
                    post.get('post_time', ''),
                    content,
                    content_preview,
                    ai_score,
                    post.get('scoring_status', 'auto'),
                    human_score,
                    score_diff,
                    post.get('text_feedback', ''),
                    post.get('post_url', ''),
                    post.get('post_id', ''),
                    post.get('category', ''),
                    post.get('notes', '')
                ]
                rows_to_add.append(row)
            
            # 批量添加數據
            if rows_to_add:
                worksheet.append_rows(rows_to_add)
                logger.info(f"Successfully wrote {len(rows_to_add)} posts to {ALL_POSTS_WORKSHEET_NAME}")
                return True
            else:
                logger.warning("No posts to write to all posts sheet")
                return True
                
        except Exception as e:
            logger.error(f"Failed to write posts to all posts sheet: {e}")
            return False
    
    def write_prompt_optimization_history(self, optimization_data: Dict[str, Any]) -> bool:
        """將prompt優化歷史寫入專門的工作表"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(PROMPT_HISTORY_WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                # 創建新工作表
                worksheet = sheet.add_worksheet(
                    title=PROMPT_HISTORY_WORKSHEET_NAME, 
                    rows=1000, 
                    cols=12
                )
                # 設置標題行
                headers = [
                    '優化時間', '版本名稱', '分析反饋數量', '平均評分差異', 
                    'AI評分過高比例', 'AI評分過低比例', '準確率', 
                    '主要問題', '優化方法', '新Prompt內容預覽', '是否啟用', '備註'
                ]
                worksheet.append_row(headers)
                logger.info(f"Created new worksheet: {PROMPT_HISTORY_WORKSHEET_NAME}")
            
            # 準備數據
            prompt_content = optimization_data.get('prompt_content', '')
            prompt_preview = prompt_content[:200] + "..." if len(prompt_content) > 200 else prompt_content
            
            # 格式化主要問題
            main_issues = optimization_data.get('main_issues', [])
            issues_text = "; ".join(main_issues) if main_issues else ""
            
            row = [
                optimization_data.get('created_at', ''),
                optimization_data.get('version_name', ''),
                optimization_data.get('total_feedbacks', ''),
                optimization_data.get('avg_difference', ''),
                f"{optimization_data.get('overrated_ratio', 0)*100:.1f}%" if optimization_data.get('overrated_ratio') else '',
                f"{optimization_data.get('underrated_ratio', 0)*100:.1f}%" if optimization_data.get('underrated_ratio') else '',
                f"{optimization_data.get('accuracy_rate', 0):.1f}%" if optimization_data.get('accuracy_rate') else '',
                issues_text,
                optimization_data.get('optimization_method', ''),
                prompt_preview,
                '是' if optimization_data.get('is_active', False) else '否',
                optimization_data.get('description', '')
            ]
            
            worksheet.append_row(row)
            logger.info(f"Successfully wrote prompt optimization history")
            return True
                
        except Exception as e:
            logger.error(f"Failed to write prompt optimization history: {e}")
            return False
    
    def get_human_feedback_for_scoring(self, limit: int = 20) -> List[Dict[str, Any]]:
        """從All Posts工作表獲取需要人工評分的貼文"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(ALL_POSTS_WORKSHEET_NAME)
                all_values = worksheet.get_all_values()
                
                if len(all_values) <= 1:  # 只有標題行或空表
                    return []
                
                headers = all_values[0]
                
                # 找到相關列的索引
                url_col_idx = headers.index('原始貼文URL') if '原始貼文URL' in headers else -1
                ai_score_col_idx = headers.index('AI重要性評分') if 'AI重要性評分' in headers else -1
                human_score_col_idx = headers.index('人工評分') if '人工評分' in headers else -1
                text_feedback_col_idx = headers.index('文字反饋') if '文字反饋' in headers else -1
                content_col_idx = headers.index('原始內容') if '原始內容' in headers else -1
                
                if any(idx == -1 for idx in [url_col_idx, ai_score_col_idx, human_score_col_idx, content_col_idx]):
                    logger.error("Required columns not found in all posts sheet")
                    return []
                
                feedback_posts = []
                for i, row in enumerate(all_values[1:], start=2):
                    if len(row) > max(url_col_idx, ai_score_col_idx, human_score_col_idx, content_col_idx):
                        # 只選擇有AI評分但沒有人工評分的貼文
                        if (row[ai_score_col_idx] and 
                            not row[human_score_col_idx] and 
                            len(feedback_posts) < limit):
                            
                            feedback_posts.append({
                                'row_index': i,
                                'post_url': row[url_col_idx],
                                'ai_score': row[ai_score_col_idx],
                                'content': row[content_col_idx],
                                'text_feedback': row[text_feedback_col_idx] if text_feedback_col_idx != -1 and len(row) > text_feedback_col_idx else '',
                                'platform': row[headers.index('平台')] if '平台' in headers else '',
                                'author': row[headers.index('發文者')] if '發文者' in headers else ''
                            })
                
                logger.info(f"Found {len(feedback_posts)} posts needing human feedback")
                return feedback_posts
                
            except gspread.WorksheetNotFound:
                logger.info("All posts worksheet doesn't exist yet")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get posts for human feedback: {e}")
            return []
    
    def update_human_score(self, post_url: str, human_score: float, text_feedback: str = "", notes: str = "") -> bool:
        """更新貼文的人工評分"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            worksheet = sheet.worksheet(ALL_POSTS_WORKSHEET_NAME)
            
            all_values = worksheet.get_all_values()
            headers = all_values[0]
            
            # 找到相關列的索引
            url_col_idx = headers.index('原始貼文URL') + 1
            human_score_col_idx = headers.index('人工評分') + 1
            text_feedback_col_idx = headers.index('文字反饋') + 1
            notes_col_idx = headers.index('備註') + 1
            ai_score_col_idx = headers.index('AI重要性評分') + 1
            diff_col_idx = headers.index('評分差異') + 1
            
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > url_col_idx - 1 and row[url_col_idx - 1] == post_url:
                    # 更新人工評分
                    worksheet.update_cell(i, human_score_col_idx, human_score)
                    
                    # 更新文字反饋
                    if text_feedback:
                        worksheet.update_cell(i, text_feedback_col_idx, text_feedback)
                    
                    # 更新備註
                    if notes:
                        worksheet.update_cell(i, notes_col_idx, notes)
                    
                    # 計算並更新評分差異
                    ai_score = row[ai_score_col_idx - 1]
                    if ai_score:
                        try:
                            diff = float(ai_score) - float(human_score)
                            worksheet.update_cell(i, diff_col_idx, f"{diff:+.1f}")
                        except (ValueError, TypeError):
                            pass
                    
                    logger.info(f"Updated human score for post {post_url}: {human_score}")
                    return True
            
            logger.warning(f"Post with URL {post_url} not found in all posts sheet")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update human score: {e}")
            return False