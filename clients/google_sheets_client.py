import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
import os
import json
import base64
import pytz
from datetime import datetime
from config import (
    GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH,
    INPUT_SPREADSHEET_NAME,
    OUTPUT_SPREADSHEET_NAME,
    INPUT_WORKSHEET_NAME,
    OUTPUT_WORKSHEET_NAME,
    ALL_POSTS_WORKSHEET_NAME,
    PROMPT_HISTORY_WORKSHEET_NAME,
    PROMPTS_WORKSHEET_NAME
)

logger = logging.getLogger(__name__)

class GoogleSheetsClient:
    def __init__(self):
        self.gc = None
        self.taiwan_tz = pytz.timezone('Asia/Taipei')
        self.utc_tz = pytz.UTC
        self._initialize_client()
    
    def _initialize_client(self):
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # 優先從環境變數讀取憑證
            google_creds_base64 = os.getenv('GOOGLE_SHEETS_CREDENTIALS_BASE64')
            
            if google_creds_base64:
                # 從 base64 環境變數解碼憑證
                try:
                    creds_json = base64.b64decode(google_creds_base64).decode('utf-8')
                    creds_dict = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(
                        creds_dict,
                        scopes=scopes
                    )
                    logger.info("Google Sheets credentials loaded from environment variable")
                except Exception as e:
                    logger.error(f"Failed to load credentials from environment variable: {e}")
                    raise
            else:
                # 從文件讀取憑證（本地開發）
                if os.path.exists(GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH):
                    creds = Credentials.from_service_account_file(
                        GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH, 
                        scopes=scopes
                    )
                    logger.info("Google Sheets credentials loaded from file")
                else:
                    raise FileNotFoundError(
                        f"Service account file not found at {GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH} "
                        "and GOOGLE_SHEETS_CREDENTIALS_BASE64 environment variable not set"
                    )
            
            self.gc = gspread.authorize(creds)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise
    
    def convert_to_taiwan_time(self, time_input: Any) -> str:
        """將時間轉換為台灣時間字串
        
        Args:
            time_input: 可以是 datetime object、ISO format string、或其他時間格式
            
        Returns:
            格式化的台灣時間字串 (YYYY-MM-DD HH:MM:SS)
        """
        if not time_input:
            return ''
        
        try:
            # 如果是字串，嘗試解析
            if isinstance(time_input, str):
                # 處理常見的 ISO 格式
                if 'T' in time_input:
                    # 移除毫秒部分（如果有）
                    if '.' in time_input:
                        time_input = time_input.split('.')[0] + 'Z' if time_input.endswith('Z') else time_input.split('.')[0]
                    
                    # 替換 Z 為 +00:00 以便 fromisoformat 可以解析
                    if time_input.endswith('Z'):
                        time_input = time_input[:-1] + '+00:00'
                    
                    # 解析 ISO 格式
                    dt = datetime.fromisoformat(time_input)
                else:
                    # 嘗試其他常見格式
                    from dateutil import parser
                    dt = parser.parse(time_input)
            elif isinstance(time_input, datetime):
                dt = time_input
            else:
                return str(time_input)
            
            # 如果沒有時區信息，假設是 UTC
            if dt.tzinfo is None:
                dt = self.utc_tz.localize(dt)
            
            # 轉換為台灣時間
            taiwan_time = dt.astimezone(self.taiwan_tz)
            
            # 格式化輸出
            return taiwan_time.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            logger.warning(f"Failed to convert time to Taiwan timezone: {e}, input: {time_input}")
            # 如果轉換失敗，返回原始值的字串形式
            return str(time_input)
    
    def get_taiwan_now(self) -> str:
        """獲取當前台灣時間的格式化字串"""
        now = datetime.now(self.taiwan_tz)
        return now.strftime('%Y-%m-%d %H:%M:%S')
    
    def group_posts_by_thread(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        將貼文按 Thread 分組並格式化為 Thread 顯示
        
        Args:
            posts: 分析後的貼文列表
            
        Returns:
            Thread 列表，每個 Thread 為一個整合的顯示項目
        """
        if not posts:
            return []
        
        # 按 thread_id 分組
        threads_map = {}
        for post in posts:
            thread_id = post.get('thread_id')
            if not thread_id:
                # 如果沒有 thread_id，使用 post_id 作為唯一的 thread_id
                # 這樣確保每個沒有 thread_id 的貼文都是獨立的
                thread_id = f"single_{post.get('platform', 'unknown')}_{post.get('post_id', 'unknown')}"
            
            if thread_id not in threads_map:
                threads_map[thread_id] = []
            threads_map[thread_id].append(post)
        
        thread_displays = []
        
        for thread_id, thread_posts in threads_map.items():
            if len(thread_posts) == 1:
                # 單一貼文，確保設置正確的 thread_id
                single_post = thread_posts[0].copy()
                single_post['thread_id'] = thread_id
                single_post['thread_posts_count'] = 1
                thread_displays.append(single_post)
            else:
                # 多個貼文的 Thread，需要整合
                thread_display = self._create_thread_display(thread_posts)
                thread_display['thread_id'] = thread_id  # 確保設置正確的 thread_id
                thread_displays.append(thread_display)
        
        return thread_displays
    
    def _create_thread_display(self, thread_posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """創建 Thread 整合顯示"""
        if not thread_posts:
            return {}
        
        # 按時間排序
        sorted_posts = sorted(thread_posts, key=lambda x: x.get('post_time', ''))
        first_post = sorted_posts[0]
        last_post = sorted_posts[-1]
        
        # 整合內容
        thread_content_parts = []
        for i, post in enumerate(sorted_posts, 1):
            content = post.get('original_content', '').strip()
            if content:
                thread_content_parts.append(f"{i}/{len(sorted_posts)}: {content}")
        
        merged_content = "\n".join(thread_content_parts)
        
        # 計算時間範圍
        start_time = self.convert_to_taiwan_time(first_post.get('post_time', ''))
        end_time = self.convert_to_taiwan_time(last_post.get('post_time', ''))
        
        if start_time == end_time:
            time_display = start_time
        else:
            time_display = f"{start_time} ~ {end_time}"
        
        # 創建 Thread 顯示項目
        thread_display = first_post.copy()
        thread_display.update({
            'original_content': f"【Thread - {len(thread_posts)} 則貼文】\n{merged_content}",
            'post_time': time_display,
            'thread_count': len(thread_posts),
            'is_thread_display': True,
            'thread_posts_count': len(thread_posts)
        })
        
        return thread_display
    
    def _ensure_thread_id_columns(self, worksheet):
        """確保工作表包含Thread ID相關欄位"""
        try:
            # 獲取現有的標題行
            if worksheet.row_count == 0:
                logger.info("工作表為空，將添加標題行")
                headers = [
                    '時間', '平台', '發文者', '發文者顯示名稱', 
                    '原始內容', '摘要內容', '重要性評分', '轉發內容',
                    '原始貼文URL', '收集時間', '分類', '狀態', 'Post ID', 'Thread ID', 'Thread數量'
                ]
                worksheet.append_row(headers)
                return

            headers = worksheet.row_values(1)
            logger.info(f"現有標題行: {headers}")
            
            # 檢查是否需要添加Thread ID欄位
            needs_thread_id = 'Thread ID' not in headers
            needs_thread_count = 'Thread數量' not in headers
            
            if needs_thread_id or needs_thread_count:
                logger.info("需要更新標題行以包含Thread相關欄位")
                
                # 準備完整的標題行
                new_headers = [
                    '時間', '平台', '發文者', '發文者顯示名稱', 
                    '原始內容', '摘要內容', '重要性評分', '轉發內容',
                    '原始貼文URL', '收集時間', '分類', '狀態', 'Post ID', 'Thread ID', 'Thread數量'
                ]
                
                # 確保工作表有足夠的列
                if worksheet.col_count < len(new_headers):
                    worksheet.resize(worksheet.row_count, len(new_headers))
                
                # 更新第一行
                worksheet.update('1:1', [new_headers])
                logger.info("已更新標題行包含Thread ID和Thread數量欄位")
            else:
                logger.info("標題行已包含所需的Thread欄位")
                
        except Exception as e:
            logger.error(f"檢查/更新標題行時發生錯誤: {e}")
    
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
        """將重要的分析後貼文數據寫入 Google Sheets（Thread已整合，直接顯示）"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(OUTPUT_WORKSHEET_NAME)
                
                # 檢查現有工作表的標題行，確保包含Thread ID欄位
                self._ensure_thread_id_columns(worksheet)
                
                # 獲取現有的 post_ids 用於去重
                existing_post_ids = self.get_existing_post_ids(OUTPUT_WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                # 如果工作表不存在，創建一個新的
                worksheet = sheet.add_worksheet(
                    title=OUTPUT_WORKSHEET_NAME, 
                    rows=1000, 
                    cols=16  # 增加到16列以容納AI評分邏輯欄位
                )
                # 設置標題行（加入 Thread ID、Thread 數量和AI評分邏輯）
                headers = [
                    '時間', '平台', '發文者', '發文者顯示名稱', 
                    '原始內容', '摘要內容', '重要性評分', 'AI評分邏輯', '轉發內容',
                    '原始貼文URL', '收集時間', '分類', '狀態', 'Post ID', 'Thread ID', 'Thread數量'
                ]
                worksheet.append_row(headers)
                existing_post_ids = {}
            
            # 1. 輸入的posts已經是分析並整合過的結果，直接使用
            logger.info(f"Processing {len(posts)} analyzed items for Analyzed Posts sheet")
            
            # 2. 準備數據，過濾重複的 thread
            rows_to_add = []
            duplicates_count = 0
            
            for analyzed_item in posts:
                platform = analyzed_item.get('platform', '').lower()
                thread_id = analyzed_item.get('thread_id', analyzed_item.get('post_id', ''))
                
                # 檢查是否已存在（使用 thread_id 檢查重複）
                if platform in existing_post_ids and thread_id in existing_post_ids[platform]:
                    duplicates_count += 1
                    logger.debug(f"Skipping duplicate thread: {platform}/{thread_id}")
                    continue
                
                # 格式化時間
                time_display = analyzed_item.get('post_time', '')
                # 對於Thread，可能已經是合併的時間範圍格式
                if analyzed_item.get('is_thread', False) and analyzed_item.get('post_time_range'):
                    # Thread有時間範圍，格式化顯示
                    start_time = self.convert_to_taiwan_time(analyzed_item['post_time_range'].get('start', ''))
                    end_time = self.convert_to_taiwan_time(analyzed_item['post_time_range'].get('end', ''))
                    if start_time == end_time:
                        time_display = start_time
                    else:
                        time_display = f"{start_time} ~ {end_time}"
                else:
                    # 單一貼文，正常轉換
                    time_display = self.convert_to_taiwan_time(time_display)
                
                row = [
                    time_display,
                    analyzed_item.get('platform', ''),
                    analyzed_item.get('author_username', ''),
                    analyzed_item.get('author_display_name', ''),
                    analyzed_item.get('original_content', ''),
                    analyzed_item.get('summary', ''),
                    analyzed_item.get('importance_score', ''),
                    analyzed_item.get('importance_reasoning', ''),  # 新增AI評分邏輯
                    analyzed_item.get('repost_content', ''),
                    analyzed_item.get('post_url', ''),
                    self.convert_to_taiwan_time(analyzed_item.get('collected_at', '')),
                    analyzed_item.get('category', ''),
                    analyzed_item.get('status', 'new'),
                    analyzed_item.get('post_id', ''),  # Post ID (對Thread而言是主要貼文的ID)
                    thread_id,  # Thread ID
                    analyzed_item.get('thread_count', 1)  # Thread 內貼文數量
                ]
                rows_to_add.append(row)
            
            # 3. 批量添加數據
            if rows_to_add:
                worksheet.append_rows(rows_to_add)
                logger.info(f"Successfully wrote {len(rows_to_add)} thread displays to Google Sheets (filtered {duplicates_count} duplicates)")
                return True
            else:
                if duplicates_count > 0:
                    logger.info(f"No new threads to write (all {duplicates_count} threads were duplicates)")
                else:
                    logger.warning("No threads to write")
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
    
    def get_existing_post_ids(self, worksheet_name: str) -> Dict[str, set]:
        """獲取已存在的貼文ID和Thread ID列表，按平台分組，用於去重
        
        Returns:
            Dict[str, set]: 格式為 {'platform': set(post_ids_and_thread_ids)}
        """
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(worksheet_name)
                all_values = worksheet.get_all_values()
                
                if len(all_values) <= 1:  # 只有標題行或空表
                    return {}
                
                headers = all_values[0]
                
                # 找到必要的列索引
                post_id_col_idx = -1
                thread_id_col_idx = -1
                platform_col_idx = -1
                
                # 嘗試不同的列名
                for idx, header in enumerate(headers):
                    if header in ['Post ID', 'post_id', '貼文ID']:
                        post_id_col_idx = idx
                    elif header in ['Thread ID', 'thread_id', 'Thread識別碼']:
                        thread_id_col_idx = idx
                    elif header in ['平台', 'platform', 'Platform']:
                        platform_col_idx = idx
                
                if platform_col_idx == -1:
                    logger.warning(f"Platform column not found in {worksheet_name}")
                    return {}
                
                # 按平台分組收集 post_id 和 thread_id
                existing_ids = {}
                for row in all_values[1:]:
                    if len(row) > platform_col_idx:
                        platform = row[platform_col_idx].lower() if row[platform_col_idx] else ''
                        
                        if platform:
                            if platform not in existing_ids:
                                existing_ids[platform] = set()
                            
                            # 添加 Post ID（如果存在）
                            if post_id_col_idx != -1 and len(row) > post_id_col_idx and row[post_id_col_idx]:
                                existing_ids[platform].add(row[post_id_col_idx])
                            
                            # 添加 Thread ID（如果存在）
                            if thread_id_col_idx != -1 and len(row) > thread_id_col_idx and row[thread_id_col_idx]:
                                existing_ids[platform].add(row[thread_id_col_idx])
                
                total_count = sum(len(ids) for ids in existing_ids.values())
                logger.info(f"Found {total_count} existing IDs (Post ID + Thread ID) in {worksheet_name}")
                for platform, ids in existing_ids.items():
                    logger.info(f"  {platform}: {len(ids)} IDs")
                
                return existing_ids
                
            except gspread.WorksheetNotFound:
                logger.info(f"Worksheet {worksheet_name} doesn't exist yet")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get existing IDs from {worksheet_name}: {e}")
            return {}
    
    def write_all_posts_with_scores(self, posts: List[Dict[str, Any]]) -> bool:
        """將所有貼文及其AI評分寫入專門的工作表（展開Thread顯示每個原始貼文）"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(ALL_POSTS_WORKSHEET_NAME)
                # 獲取現有的 post_ids 用於去重
                existing_post_ids = self.get_existing_post_ids(ALL_POSTS_WORKSHEET_NAME)
            except gspread.WorksheetNotFound:
                # 創建新工作表
                worksheet = sheet.add_worksheet(
                    title=ALL_POSTS_WORKSHEET_NAME, 
                    rows=5000, 
                    cols=18  # 增加Thread相關欄位和AI評分邏輯欄位
                )
                # 設置標題行（添加Thread相關欄位和AI評分邏輯）
                headers = [
                    '收集時間', '平台', '發文者', '發文者顯示名稱', 
                    '貼文時間', '原始內容', '內容預覽', 
                    'AI重要性評分', 'AI評分邏輯', '評分狀態', '人工評分', '評分差異', '文字反饋',
                    '原始貼文URL', 'Post ID', 'Thread ID', '是否Thread的一部分', '分類', '備註'
                ]
                worksheet.append_row(headers)
                logger.info(f"Created new worksheet: {ALL_POSTS_WORKSHEET_NAME}")
                existing_post_ids = {}
            
            # 展開分析結果，將Thread中的每個貼文都作為獨立行
            all_individual_posts = []
            for analyzed_item in posts:
                if analyzed_item.get('is_thread', False) and 'individual_posts_for_all_sheet' in analyzed_item:
                    # 這是一個Thread，展開為個別貼文
                    individual_posts = analyzed_item['individual_posts_for_all_sheet']
                    all_individual_posts.extend(individual_posts)
                    logger.info(f"Expanded thread {analyzed_item.get('thread_id')} into {len(individual_posts)} individual posts")
                else:
                    # 這是單獨貼文，直接添加
                    all_individual_posts.append(analyzed_item)
            
            logger.info(f"Total individual posts to write: {len(all_individual_posts)}")
            
            # 準備數據，過濾重複的 post_id
            rows_to_add = []
            duplicates_count = 0
            
            for post in all_individual_posts:
                platform = post.get('platform', '').lower()
                post_id = post.get('post_id', '')
                
                # 檢查是否已存在
                if platform in existing_post_ids and post_id in existing_post_ids[platform]:
                    duplicates_count += 1
                    logger.debug(f"Skipping duplicate post in All Posts: {platform}/{post_id}")
                    continue
                
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
                    self.convert_to_taiwan_time(post.get('collected_at', '')),
                    post.get('platform', ''),
                    post.get('author_username', ''),
                    post.get('author_display_name', ''),
                    self.convert_to_taiwan_time(post.get('post_time', '')),
                    content,
                    content_preview,
                    ai_score,
                    post.get('importance_reasoning', ''),  # 新增AI評分邏輯
                    post.get('scoring_status', 'auto'),
                    human_score,
                    score_diff,
                    post.get('text_feedback', ''),
                    post.get('post_url', ''),
                    post.get('post_id', ''),
                    post.get('thread_id', ''),  # Thread ID
                    '是' if post.get('is_part_of_thread', False) else '否',  # 是否Thread的一部分
                    post.get('category', ''),
                    post.get('notes', '')
                ]
                rows_to_add.append(row)
            
            # 批量添加數據
            if rows_to_add:
                worksheet.append_rows(rows_to_add)
                logger.info(f"Successfully wrote {len(rows_to_add)} new posts to {ALL_POSTS_WORKSHEET_NAME} (filtered {duplicates_count} duplicates)")
                return True
            else:
                if duplicates_count > 0:
                    logger.info(f"No new posts to write to All Posts (all {duplicates_count} posts were duplicates)")
                else:
                    logger.warning("No posts to write to all posts sheet")
                return True
                
        except Exception as e:
            logger.error(f"Failed to write posts to all posts sheet: {e}")
            return False
    
    def get_prompt_by_name(self, prompt_name: str) -> Optional[str]:
        """
        Get a specific prompt from the AI Prompts worksheet
        
        Args:
            prompt_name: Name of the prompt to retrieve (e.g., "TELEGRAM_SUMMARY")
            
        Returns:
            Prompt content if found, None otherwise
        """
        try:
            input_spreadsheet = self.gc.open(INPUT_SPREADSHEET_NAME)
            
            # Check if AI Prompts worksheet exists
            try:
                prompts_sheet = input_spreadsheet.worksheet(PROMPTS_WORKSHEET_NAME)
            except gspread.exceptions.WorksheetNotFound:
                logger.debug(f"Worksheet '{PROMPTS_WORKSHEET_NAME}' not found")
                return None
                
            # Get all records
            records = prompts_sheet.get_all_records()
            
            # Look for the specific prompt
            for record in records:
                if record.get('Prompt Name') == prompt_name:
                    # Check if prompt is active
                    if str(record.get('Active', 'TRUE')).upper() == 'TRUE':
                        return record.get('Prompt Content')
                        
            logger.debug(f"Prompt '{prompt_name}' not found in sheets")
            return None
            
        except Exception as e:
            logger.error(f"Error getting prompt from sheets: {e}")
            return None
            
    def ensure_prompts_worksheet_exists(self) -> bool:
        """
        Ensure the AI Prompts worksheet exists with proper structure
        
        Returns:
            True if worksheet exists or was created successfully
        """
        try:
            input_spreadsheet = self.gc.open(INPUT_SPREADSHEET_NAME)
            
            # Check if worksheet exists
            try:
                prompts_sheet = input_spreadsheet.worksheet(PROMPTS_WORKSHEET_NAME)
                logger.info(f"Worksheet '{PROMPTS_WORKSHEET_NAME}' already exists")
                return True
            except gspread.exceptions.WorksheetNotFound:
                # Create the worksheet
                logger.info(f"Creating worksheet '{PROMPTS_WORKSHEET_NAME}'")
                prompts_sheet = input_spreadsheet.add_worksheet(
                    title=PROMPTS_WORKSHEET_NAME,
                    rows=100,
                    cols=10
                )
                
                # Set headers
                headers = [
                    'Prompt Name',
                    'Prompt Content', 
                    'Last Updated',
                    'Active',
                    'Description'
                ]
                prompts_sheet.update('A1:E1', [headers])
                
                # Add default prompts
                default_prompts = [
                    [
                        'TELEGRAM_SUMMARY',
                        'Organize these important social media posts into a concise English summary:\n\n{posts_list}\n\nGroup by account if needed. Keep it brief and highlight key information.',
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'TRUE',
                        'Prompt for generating Telegram daily report summaries'
                    ]
                ]
                
                if default_prompts:
                    prompts_sheet.update('A2:E2', default_prompts)
                    
                logger.info(f"Created '{PROMPTS_WORKSHEET_NAME}' worksheet with default prompts")
                return True
                
        except Exception as e:
            logger.error(f"Error ensuring prompts worksheet exists: {e}")
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
                self.convert_to_taiwan_time(optimization_data.get('created_at', '')),
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
    
    def get_active_prompt(self, prompt_name: str) -> str:
        """從 Google Sheets 獲取活躍的 prompt"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            # 檢查是否存在 AI Prompts 工作表
            try:
                worksheet = sheet.worksheet(PROMPTS_WORKSHEET_NAME)
            except:
                logger.warning(f"AI Prompts worksheet not found, creating it...")
                self._create_prompts_worksheet(sheet)
                worksheet = sheet.worksheet(PROMPTS_WORKSHEET_NAME)
            
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:  # 只有標題行或空
                logger.warning(f"No prompt data found for {prompt_name}")
                return ""
            
            headers = all_values[0]
            prompt_name_idx = headers.index('prompt_name') if 'prompt_name' in headers else -1
            prompt_content_idx = headers.index('prompt_content') if 'prompt_content' in headers else -1
            is_active_idx = headers.index('is_active') if 'is_active' in headers else -1
            
            if prompt_name_idx == -1 or prompt_content_idx == -1 or is_active_idx == -1:
                logger.error("Required columns not found in AI Prompts sheet")
                return ""
            
            # 找到活躍的 prompt
            for row in all_values[1:]:
                if (len(row) > max(prompt_name_idx, prompt_content_idx, is_active_idx) and
                    row[prompt_name_idx] == prompt_name and 
                    row[is_active_idx].upper() == 'TRUE'):
                    
                    logger.info(f"Using active prompt for {prompt_name}")
                    return row[prompt_content_idx]
            
            logger.warning(f"No active prompt found for {prompt_name}")
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get active prompt for {prompt_name}: {e}")
            return ""
    
    def add_prompt_version(self, prompt_name: str, content: str, version: str) -> bool:
        """新增 prompt 版本並設為活躍，將其他版本設為非活躍"""
        try:
            sheet = self.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            # 檢查是否存在 AI Prompts 工作表
            try:
                worksheet = sheet.worksheet(PROMPTS_WORKSHEET_NAME)
            except:
                logger.info(f"Creating AI Prompts worksheet...")
                self._create_prompts_worksheet(sheet)
                worksheet = sheet.worksheet(PROMPTS_WORKSHEET_NAME)
            
            # 先將同名的所有 prompt 設為 inactive
            all_values = worksheet.get_all_values()
            if len(all_values) > 1:  # 有資料
                headers = all_values[0]
                prompt_name_idx = headers.index('prompt_name') if 'prompt_name' in headers else -1
                is_active_idx = headers.index('is_active') if 'is_active' in headers else -1
                
                if prompt_name_idx != -1 and is_active_idx != -1:
                    for i, row in enumerate(all_values[1:], start=2):  # 從第2行開始
                        if (len(row) > max(prompt_name_idx, is_active_idx) and 
                            row[prompt_name_idx] == prompt_name):
                            worksheet.update_cell(i, is_active_idx + 1, "FALSE")
            
            # 新增新版本
            new_row = [
                prompt_name,
                content,
                version,
                "TRUE",  # is_active
                self.get_taiwan_now()
            ]
            
            worksheet.append_row(new_row)
            logger.info(f"Added new active prompt version {version} for {prompt_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add prompt version: {e}")
            return False
    
    def _create_prompts_worksheet(self, sheet):
        """創建 AI Prompts 工作表"""
        try:
            worksheet = sheet.add_worksheet(
                title=PROMPTS_WORKSHEET_NAME,
                rows=1000,
                cols=10
            )
            
            # 設置標題行
            headers = [
                'prompt_name',
                'prompt_content', 
                'version',
                'is_active',
                'created_date'
            ]
            worksheet.append_row(headers)
            logger.info("Created AI Prompts worksheet with headers")
            
        except Exception as e:
            logger.error(f"Failed to create AI Prompts worksheet: {e}")
            raise