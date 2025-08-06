#!/usr/bin/env python3
"""
本地 SQLite 數據庫遷移腳本：修復 AnalyzedPost.post_id 字段類型
從 INTEGER 改為 TEXT
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def migrate_local_database():
    """執行本地 SQLite 數據庫遷移"""
    print("🔄 開始本地數據庫遷移...")
    
    if not DATABASE_URL.startswith('sqlite'):
        print("❌ 這個腳本只適用於 SQLite 數據庫")
        return False
    
    try:
        # 創建數據庫連接
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            print("✅ SQLite 數據庫連接成功")
            
            # 檢查表是否存在
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='analyzed_posts'
            """))
            
            table_exists = result.fetchone()
            
            if table_exists:
                print("⚠️  表 analyzed_posts 已存在，需要修改字段類型...")
                
                # SQLite 不支持直接修改列類型，需要創建新表
                print("🔧 創建新表結構...")
                
                # 1. 創建新表
                conn.execute(text("""
                    CREATE TABLE analyzed_posts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        original_post_id TEXT NOT NULL,
                        author_username TEXT NOT NULL,
                        author_display_name TEXT,
                        original_content TEXT,
                        summary TEXT,
                        importance_score REAL,
                        repost_content TEXT,
                        post_url TEXT,
                        post_time TIMESTAMP,
                        collected_at TIMESTAMP,
                        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        category TEXT,
                        status TEXT DEFAULT 'new'
                    )
                """))
                print("✅ 新表創建完成")
                
                # 2. 複製數據（跳過有問題的數據）
                try:
                    conn.execute(text("""
                        INSERT INTO analyzed_posts_new 
                        SELECT 
                            id,
                            CAST(post_id AS TEXT),
                            platform,
                            original_post_id,
                            author_username,
                            author_display_name,
                            original_content,
                            summary,
                            importance_score,
                            repost_content,
                            post_url,
                            post_time,
                            collected_at,
                            analyzed_at,
                            category,
                            status
                        FROM analyzed_posts
                    """))
                    print("✅ 數據複製完成")
                except Exception as e:
                    print(f"⚠️  數據複製失敗（可能沒有舊數據）: {e}")
                
                # 3. 刪除舊表
                conn.execute(text("DROP TABLE analyzed_posts"))
                print("🗑️  舊表已刪除")
                
                # 4. 重命名新表
                conn.execute(text("ALTER TABLE analyzed_posts_new RENAME TO analyzed_posts"))
                print("✅ 新表重命名完成")
                
                # 提交更改
                conn.commit()
            else:
                print("✅ 表不存在，首次運行時會自動創建正確的結構")
                
    except Exception as e:
        print(f"❌ 遷移失敗: {e}")
        return False
        
    print("🎉 本地數據庫遷移完成！")
    return True

if __name__ == "__main__":
    success = migrate_local_database()
    sys.exit(0 if success else 1)