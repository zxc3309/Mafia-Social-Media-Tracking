#!/usr/bin/env python3
"""
強制執行數據庫遷移腳本 - Railway 部署版本
這個腳本會強制執行數據庫遷移，即使在有錯誤的情況下
版本 2.0 - 增強版本，解決 Railway 部署問題
"""

import os
import sys
import traceback
from sqlalchemy import create_engine, text, inspect
from config import DATABASE_URL

def log_message(level, message):
    """統一日誌輸出格式"""
    timestamp = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()  # 確保立即輸出

def force_migrate_database():
    """強制執行數據庫遷移"""
    log_message("INFO", "🔄 強制開始數據庫遷移...")
    log_message("INFO", f"DATABASE_URL 開頭: {DATABASE_URL[:50]}...")
    
    # 檢查環境
    is_railway = os.getenv('RAILWAY_ENVIRONMENT_NAME') is not None
    is_cloud = DATABASE_URL.startswith('postgres')
    log_message("INFO", f"Railway環境: {is_railway}, PostgreSQL: {is_cloud}")
    
    try:
        log_message("INFO", "正在建立數據庫連接...")
        # 創建數據庫連接
        engine = create_engine(DATABASE_URL, echo=True if is_railway else False)
        
        log_message("INFO", "測試數據庫連接...")
        # 先測試連接
        with engine.connect() as test_conn:
            log_message("SUCCESS", "✅ 數據庫連接成功")
        
        # 開始遷移事務
        log_message("INFO", "開始遷移事務...")
        with engine.begin() as conn:
            # 檢查是否為 PostgreSQL
            try:
                log_message("INFO", "檢查數據庫版本...")
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                log_message("INFO", f"數據庫版本: {version[:100]}...")
            except Exception as e:
                log_message("ERROR", f"⚠️  無法獲取數據庫版本: {e}")
                traceback.print_exc()
                return False
            
            if 'PostgreSQL' in version:
                log_message("SUCCESS", "✅ 檢測到 PostgreSQL，開始強制遷移...")
                
                # 1. 檢查表是否存在
                try:
                    log_message("INFO", "檢查 analyzed_posts 表是否存在...")
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'analyzed_posts'
                        )
                    """))
                    table_exists = result.fetchone()[0]
                    log_message("INFO", f"表 analyzed_posts 存在: {table_exists}")
                except Exception as e:
                    log_message("ERROR", f"⚠️  檢查表存在性失敗: {e}")
                    traceback.print_exc()
                    table_exists = False
                
                if table_exists:
                    # 2. 檢查當前字段類型
                    try:
                        log_message("INFO", "檢查 post_id 字段類型...")
                        result = conn.execute(text("""
                            SELECT data_type, character_maximum_length
                            FROM information_schema.columns 
                            WHERE table_name = 'analyzed_posts' 
                            AND column_name = 'post_id'
                        """))
                        
                        field_info = result.fetchone()
                        if field_info:
                            data_type, max_length = field_info
                            log_message("INFO", f"當前 post_id 字段類型: {data_type} (長度: {max_length})")
                            
                            if data_type == 'integer':
                                log_message("WARNING", "🔧 需要修改字段類型從 INTEGER 到 VARCHAR(255)...")
                                
                                # 核心選項：直接刪除表並重建
                                log_message("WARNING", "採用核心選項：刪除並重建表...")
                                try:
                                    log_message("INFO", "步驟 1/3: 刪除現有表...")
                                    conn.execute(text("DROP TABLE IF EXISTS analyzed_posts CASCADE"))
                                    log_message("SUCCESS", "✅ 表已刪除")
                                    
                                    log_message("INFO", "步驟 2/3: 重新創建表結構...")
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
                                    log_message("SUCCESS", "✅ 表重新創建完成")
                                    
                                    log_message("INFO", "步驟 3/3: 驗證表結構...")
                                    result = conn.execute(text("""
                                        SELECT data_type FROM information_schema.columns 
                                        WHERE table_name = 'analyzed_posts' AND column_name = 'post_id'
                                    """))
                                    new_type = result.fetchone()[0]
                                    log_message("SUCCESS", f"✅ 驗證成功，新字段類型: {new_type}")
                                    
                                except Exception as e:
                                    log_message("ERROR", f"❌ 表重建失敗: {e}")
                                    traceback.print_exc()
                                    return False
                                    
                            elif data_type in ['character varying', 'varchar', 'text']:
                                log_message("SUCCESS", "✅ 字段類型已正確 (VARCHAR/TEXT)")
                            else:
                                log_message("WARNING", f"⚠️  未知字段類型: {data_type}")
                        else:
                            log_message("ERROR", "❌ 未找到 post_id 字段")
                            return False
                            
                    except Exception as e:
                        log_message("ERROR", f"❌ 檢查字段類型失敗: {e}")
                        traceback.print_exc()
                        return False
                        
                else:
                    log_message("SUCCESS", "✅ 表不存在，首次運行時會自動創建正確的結構")
                    
            elif 'SQLite' in version:
                log_message("INFO", "✅ 檢測到 SQLite（本地開發環境），跳過遷移")
            else:
                log_message("WARNING", f"⚠️  未知數據庫類型: {version}")
                return False
                
    except Exception as e:
        log_message("ERROR", f"❌ 遷移失敗: {e}")
        traceback.print_exc()
        return False
        
    log_message("SUCCESS", "🎉 強制數據庫遷移完成！")
    return True

def verify_migration():
    """驗證遷移是否成功"""
    try:
        log_message("INFO", "開始驗證遷移結果...")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 檢查表和字段
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'analyzed_posts' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            log_message("INFO", f"找到 {len(columns)} 個字段:")
            for col_name, data_type, max_len in columns:
                log_message("INFO", f"  - {col_name}: {data_type}({max_len if max_len else 'N/A'})")
            
            # 測試插入一條測試記錄
            test_post_id = "test_1234567890#m"
            try:
                conn.execute(text("""
                    INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
                    VALUES (:post_id, 'twitter', :post_id, 'test_user')
                """), {"post_id": test_post_id})
                
                # 立即刪除測試記錄
                conn.execute(text("DELETE FROM analyzed_posts WHERE post_id = :post_id"), {"post_id": test_post_id})
                conn.commit()
                
                log_message("SUCCESS", "✅ 測試插入成功，post_id 字段可以接受字符串值")
                return True
                
            except Exception as e:
                log_message("ERROR", f"❌ 測試插入失敗: {e}")
                return False
                
    except Exception as e:
        log_message("ERROR", f"❌ 驗證失敗: {e}")
        return False

if __name__ == "__main__":
    log_message("INFO", "開始執行數據庫遷移腳本...")
    success = force_migrate_database()
    
    if success:
        # 驗證遷移結果
        verify_success = verify_migration()
        if verify_success:
            log_message("SUCCESS", "✅ 遷移和驗證都成功，可以繼續執行主程序")
            sys.exit(0)
        else:
            log_message("ERROR", "❌ 遷移成功但驗證失敗")
            sys.exit(1)
    else:
        log_message("ERROR", "❌ 遷移失敗，程序將退出")
        sys.exit(1)