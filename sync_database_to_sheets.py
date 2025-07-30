#!/usr/bin/env python3
"""
數據庫同步工具 - 將數據庫中的已分析貼文同步到Google Sheets
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import db_manager, AnalyzedPost, HumanFeedback
from clients.google_sheets_client import GoogleSheetsClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
import argparse
from datetime import datetime

class DatabaseSyncTool:
    def __init__(self):
        self.db = db_manager
        self.sheets_client = GoogleSheetsClient()
    
    def get_analyzed_posts_from_db(self, limit: int = None) -> list:
        """從數據庫獲取已分析的貼文"""
        session = self.db.get_session()
        try:
            print("🔍 從數據庫獲取已分析的貼文...")
            
            query = session.query(AnalyzedPost).order_by(AnalyzedPost.analyzed_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            analyzed_posts = query.all()
            
            print(f"📊 找到 {len(analyzed_posts)} 條記錄")
            
            # 轉換為字典格式
            posts_data = []
            for post in analyzed_posts:
                post_data = {
                    'collected_at': post.collected_at.strftime('%Y-%m-%d %H:%M:%S') if post.collected_at else '',
                    'platform': post.platform,
                    'author_username': post.author_username,
                    'author_display_name': post.author_display_name or '',
                    'post_time': post.post_time.strftime('%Y-%m-%d %H:%M:%S') if post.post_time else '',
                    'original_content': post.original_content or '',
                    'importance_score': post.importance_score,
                    'scoring_status': 'auto',
                    'human_score': '',  # 從HumanFeedback表中獲取
                    'post_url': post.post_url or '',
                    'post_id': post.original_post_id or str(post.id),
                    'category': post.category or '',
                    'notes': ''
                }
                posts_data.append(post_data)
            
            return posts_data
            
        except Exception as e:
            print(f"❌ 從數據庫獲取數據失敗: {e}")
            return []
        finally:
            session.close()
    
    def get_human_feedback_from_db(self) -> dict:
        """從數據庫獲取人工反饋數據"""
        session = self.db.get_session()
        try:
            feedbacks = session.query(HumanFeedback).all()
            
            # 建立 analyzed_post_id 到 human_score 的映射
            feedback_map = {}
            for feedback in feedbacks:
                feedback_map[feedback.analyzed_post_id] = {
                    'human_score': feedback.human_score,
                    'notes': feedback.reviewer_notes or feedback.feedback_reason or ''
                }
            
            print(f"📝 找到 {len(feedback_map)} 條人工反饋記錄")
            return feedback_map
            
        except Exception as e:
            print(f"⚠️  獲取人工反饋失敗: {e}")
            return {}
        finally:
            session.close()
    
    def merge_feedback_data(self, posts_data: list, feedback_map: dict) -> list:
        """合併貼文數據和反饋數據"""
        session = self.db.get_session()
        try:
            # 建立 post_url 到 analyzed_post_id 的映射
            analyzed_posts = session.query(AnalyzedPost).all()
            url_to_id_map = {post.post_url: post.id for post in analyzed_posts if post.post_url}
            
            # 合併數據
            for post_data in posts_data:
                post_url = post_data.get('post_url', '')
                if post_url in url_to_id_map:
                    analyzed_post_id = url_to_id_map[post_url]
                    if analyzed_post_id in feedback_map:
                        feedback = feedback_map[analyzed_post_id]
                        post_data['human_score'] = feedback['human_score']
                        post_data['notes'] = feedback['notes']
                        post_data['scoring_status'] = 'reviewed'
            
            return posts_data
            
        except Exception as e:
            print(f"⚠️  合併反饋數據失敗: {e}")
            return posts_data
        finally:
            session.close()
    
    def get_existing_urls_from_sheets(self) -> set:
        """獲取Google Sheets中已存在的URL"""
        try:
            from config import OUTPUT_SPREADSHEET_NAME, ALL_POSTS_WORKSHEET_NAME
            sheet = self.sheets_client.gc.open(OUTPUT_SPREADSHEET_NAME)
            
            try:
                worksheet = sheet.worksheet(ALL_POSTS_WORKSHEET_NAME)
                all_values = worksheet.get_all_values()
                
                if len(all_values) <= 1:
                    return set()
                
                headers = all_values[0]
                url_col_idx = headers.index('原始貼文URL') if '原始貼文URL' in headers else -1
                
                if url_col_idx == -1:
                    return set()
                
                existing_urls = set()
                for row in all_values[1:]:
                    if len(row) > url_col_idx and row[url_col_idx]:
                        existing_urls.add(row[url_col_idx])
                
                print(f"📊 Google Sheets中已有 {len(existing_urls)} 條記錄")
                return existing_urls
                
            except Exception as e:
                print(f"⚠️  獲取現有URL失敗: {e}")
                return set()
                
        except Exception as e:
            print(f"❌ 連接Google Sheets失敗: {e}")
            return set()

    def sync_to_sheets(self, limit: int = None, force_overwrite: bool = False):
        """同步數據到Google Sheets"""
        try:
            print("🚀 開始同步數據到Google Sheets...")
            
            # 1. 獲取數據庫中的已分析貼文
            posts_data = self.get_analyzed_posts_from_db(limit)
            
            if not posts_data:
                print("❌ 沒有找到可同步的數據")
                return
            
            # 2. 獲取人工反饋數據
            feedback_map = self.get_human_feedback_from_db()
            
            # 3. 合併數據
            merged_data = self.merge_feedback_data(posts_data, feedback_map)
            
            # 4. 如果不是強制覆寫，過濾掉已存在的數據
            if not force_overwrite:
                existing_urls = self.get_existing_urls_from_sheets()
                if existing_urls:
                    original_count = len(merged_data)
                    merged_data = [post for post in merged_data if post.get('post_url') not in existing_urls]
                    filtered_count = original_count - len(merged_data)
                    print(f"🔍 過濾掉 {filtered_count} 條已存在的記錄，剩餘 {len(merged_data)} 條新記錄")
                    
                    if not merged_data:
                        print("✅ 沒有新數據需要同步")
                        return
            else:
                print("⚠️  強制覆寫模式：將清空現有工作表數據")
                # 這裡可以添加清空工作表的邏輯
                # self.clear_all_posts_sheet()
            
            # 5. 寫入Google Sheets
            print(f"📤 正在寫入 {len(merged_data)} 條新記錄到Google Sheets...")
            success = self.sheets_client.write_all_posts_with_scores(merged_data)
            
            if success:
                print("✅ 數據同步成功！")
                print(f"📊 已同步 {len(merged_data)} 條記錄")
                
                # 統計信息
                with_human_feedback = sum(1 for post in merged_data if post.get('human_score'))
                with_ai_scores = sum(1 for post in merged_data if post.get('importance_score'))
                
                print(f"📈 統計信息:")
                print(f"   有AI評分的貼文: {with_ai_scores}")
                print(f"   有人工評分的貼文: {with_human_feedback}")
                print(f"   需要人工評分的貼文: {with_ai_scores - with_human_feedback}")
                
            else:
                print("❌ 數據同步失敗")
                
        except Exception as e:
            print(f"❌ 同步過程中出錯: {e}")
    
    def preview_data(self, limit: int = 5):
        """預覽將要同步的數據"""
        print("👀 數據預覽模式")
        
        posts_data = self.get_analyzed_posts_from_db(limit)
        feedback_map = self.get_human_feedback_from_db()
        merged_data = self.merge_feedback_data(posts_data, feedback_map)
        
        if not merged_data:
            print("❌ 沒有找到數據")
            return
        
        print(f"\n📋 將同步以下 {len(merged_data)} 條記錄的預覽:\n")
        
        for i, post in enumerate(merged_data, 1):
            print(f"{i}. 【{post['platform']}】@{post['author_username']}")
            print(f"   時間: {post['post_time']}")
            print(f"   AI評分: {post['importance_score']}")
            print(f"   人工評分: {post['human_score'] or '未評分'}")
            print(f"   內容預覽: {post['original_content'][:100]}...")
            print(f"   URL: {post['post_url']}")
            print("-" * 80)
    
    def check_sheets_connection(self):
        """檢查Google Sheets連接"""
        try:
            print("🔗 檢查Google Sheets連接...")
            
            # 嘗試獲取現有數據
            existing_posts = self.sheets_client.get_human_feedback_for_scoring(1)
            print("✅ Google Sheets連接正常")
            return True
            
        except Exception as e:
            print(f"❌ Google Sheets連接失敗: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='數據庫同步工具')
    parser.add_argument('--sync', action='store_true', help='同步數據到Google Sheets')
    parser.add_argument('--preview', action='store_true', help='預覽將要同步的數據')
    parser.add_argument('--check-connection', action='store_true', help='檢查Google Sheets連接')
    parser.add_argument('--limit', type=int, help='限制同步的記錄數量')
    parser.add_argument('--force', action='store_true', help='強制覆寫現有數據')
    
    args = parser.parse_args()
    
    sync_tool = DatabaseSyncTool()
    
    if args.check_connection:
        sync_tool.check_sheets_connection()
    elif args.preview:
        sync_tool.preview_data(args.limit or 5)
    elif args.sync:
        sync_tool.sync_to_sheets(args.limit, args.force)
    else:
        print("📊 數據庫同步工具")
        print("\n📋 可用命令:")
        print("   --check-connection  檢查Google Sheets連接")
        print("   --preview          預覽將要同步的數據")
        print("   --sync             同步數據到Google Sheets")
        print("   --limit N          限制處理的記錄數量")
        print("   --force            強制覆寫現有數據")
        print("\n💡 建議工作流程:")
        print("   1. python sync_database_to_sheets.py --check-connection")
        print("   2. python sync_database_to_sheets.py --preview")
        print("   3. python sync_database_to_sheets.py --sync")

if __name__ == "__main__":
    main()