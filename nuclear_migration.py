#!/usr/bin/env python3
"""
核心選項數據庫遷移腳本 - 完全重建表結構
當標準遷移失敗時使用這個腳本
"""

import os
import sys
import traceback
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def log_message(level, message):
    """統一日誌輸出格式"""
    timestamp = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [NUCLEAR-{level}] {message}")
    sys.stdout.flush()

def nuclear_migration():
    """核心選項：完全重建數據庫結構"""
    log_message("WARNING", "🚨 核心選項：完全重建數據庫開始...")
    
    # 環境檢查
    is_railway = os.getenv('RAILWAY_ENVIRONMENT_NAME') is not None
    is_postgres = DATABASE_URL.startswith('postgres')
    
    if not (is_railway and is_postgres):
        log_message("ERROR", "❌ 核心選項只能在 Railway PostgreSQL 環境使用")
        return False
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.begin() as conn:
            log_message("INFO", "步驟 1/4: 檢查數據庫連接...")
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            log_message("SUCCESS", f"✅ 連接成功: PostgreSQL")
            
            log_message("WARNING", "步驟 2/4: 刪除所有現有表...")
            
            # 刪除所有相關表（按依賴順序）
            tables_to_drop = [
                'human_feedback',
                'analyzed_posts', 
                'posts',
                'api_usage_logs',
                'processing_logs',
                'prompt_versions',
                'twitter_user_cache',
                'accounts'
            ]
            
            for table in tables_to_drop:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    log_message("INFO", f"  - 刪除表: {table}")
                except Exception as e:
                    log_message("WARNING", f"  - 刪除表 {table} 失敗 (可能不存在): {e}")
            
            log_message("SUCCESS", "✅ 所有表已刪除")
            
            log_message("INFO", "步驟 3/4: 重新創建表結構...")
            
            # 創建 accounts 表
            conn.execute(text("""
                CREATE TABLE accounts (
                    id SERIAL PRIMARY KEY,
                    platform VARCHAR(50) NOT NULL,
                    username VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255),
                    category VARCHAR(100),
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            log_message("INFO", "  - 創建表: accounts")
            
            # 創建 posts 表
            conn.execute(text("""
                CREATE TABLE posts (
                    id SERIAL PRIMARY KEY,
                    platform VARCHAR(50) NOT NULL,
                    post_id VARCHAR(255) NOT NULL,
                    author_username VARCHAR(255) NOT NULL,
                    author_display_name VARCHAR(255),
                    original_content TEXT,
                    post_time TIMESTAMP,
                    post_url VARCHAR(500),
                    metrics JSONB,
                    language VARCHAR(10),
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            log_message("INFO", "  - 創建表: posts")
            
            # 創建 analyzed_posts 表 (最重要的表)
            conn.execute(text("""
                CREATE TABLE analyzed_posts (
                    id SERIAL PRIMARY KEY,
                    post_id VARCHAR(255) NOT NULL,
                    platform VARCHAR(50) NOT NULL,
                    original_post_id VARCHAR(255) NOT NULL,
                    author_username VARCHAR(255) NOT NULL,
                    author_display_name VARCHAR(255),
                    original_content TEXT,
                    summary TEXT,
                    importance_score REAL,
                    repost_content TEXT,
                    post_url VARCHAR(500),
                    post_time TIMESTAMP,
                    collected_at TIMESTAMP,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    category VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'new'
                )
            """))
            log_message("SUCCESS", "  - ✅ 創建表: analyzed_posts (VARCHAR post_id)")
            
            # 創建其他必要表
            other_tables = [
                ("processing_logs", """
                    CREATE TABLE processing_logs (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        level VARCHAR(20),
                        message TEXT,
                        platform VARCHAR(50),
                        username VARCHAR(255),
                        details JSONB
                    )
                """),
                ("human_feedback", """
                    CREATE TABLE human_feedback (
                        id SERIAL PRIMARY KEY,
                        analyzed_post_id INTEGER NOT NULL,
                        platform VARCHAR(50) NOT NULL,
                        original_post_id VARCHAR(255) NOT NULL,
                        ai_score REAL,
                        human_score REAL NOT NULL,
                        feedback_reason TEXT,
                        feedback_category VARCHAR(100),
                        reviewer_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        prompt_version_id INTEGER
                    )
                """),
                ("prompt_versions", """
                    CREATE TABLE prompt_versions (
                        id SERIAL PRIMARY KEY,
                        version_name VARCHAR(100) NOT NULL,
                        prompt_type VARCHAR(50) NOT NULL,
                        prompt_content TEXT NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        performance_score REAL,
                        total_feedbacks INTEGER DEFAULT 0,
                        avg_accuracy REAL
                    )
                """),
                ("twitter_user_cache", """
                    CREATE TABLE twitter_user_cache (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        user_id VARCHAR(255) NOT NULL,
                        display_name VARCHAR(255),
                        followers_count INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """),
                ("api_usage_logs", """
                    CREATE TABLE api_usage_logs (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        platform VARCHAR(50) NOT NULL,
                        endpoint VARCHAR(100) NOT NULL,
                        username VARCHAR(255),
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT,
                        rate_limit_remaining INTEGER,
                        rate_limit_reset TIMESTAMP,
                        response_time_ms INTEGER
                    )
                """)
            ]
            
            for table_name, create_sql in other_tables:
                conn.execute(text(create_sql))
                log_message("INFO", f"  - 創建表: {table_name}")
            
            log_message("SUCCESS", "✅ 所有表已重新創建")
            
            log_message("INFO", "步驟 4/4: 驗證表結構...")
            
            # 驗證 analyzed_posts 表結構
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'analyzed_posts' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            post_id_correct = False
            
            for col_name, data_type, max_len in columns:
                if col_name == 'post_id':
                    if data_type == 'character varying':
                        post_id_correct = True
                        log_message("SUCCESS", f"  - ✅ post_id: {data_type}({max_len})")
                    else:
                        log_message("ERROR", f"  - ❌ post_id: {data_type} (應該是 character varying)")
                else:
                    log_message("INFO", f"  - {col_name}: {data_type}")
            
            if not post_id_correct:
                log_message("ERROR", "❌ post_id 字段類型不正確")
                return False
            
            # 最終測試
            test_post_id = "nuclear_test_1234567890123456789#m"
            conn.execute(text("""
                INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
                VALUES (:post_id, 'twitter', :post_id, 'nuclear_test')
            """), {"post_id": test_post_id})
            
            conn.execute(text("DELETE FROM analyzed_posts WHERE post_id = :post_id"), {"post_id": test_post_id})
            
            log_message("SUCCESS", "✅ 測試插入成功")
            
    except Exception as e:
        log_message("ERROR", f"❌ 核心遷移失敗: {e}")
        traceback.print_exc()
        return False
        
    log_message("SUCCESS", "🎉 核心選項遷移完成！數據庫已完全重建")
    return True

if __name__ == "__main__":
    log_message("WARNING", "🚨 開始執行核心選項數據庫遷移...")
    success = nuclear_migration()
    
    if success:
        log_message("SUCCESS", "✅ 核心遷移成功")
        sys.exit(0)
    else:
        log_message("ERROR", "❌ 核心遷移失敗")
        sys.exit(1)