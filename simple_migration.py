#!/usr/bin/env python3
"""
簡化版數據庫遷移腳本
直接使用 SQL 命令，避免複雜的 SQLAlchemy 操作
"""

import os
import sys
import psycopg2
from datetime import datetime

def log_msg(level, message):
    """日誌輸出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [SIMPLE-{level}] {message}")
    sys.stdout.flush()

def simple_migration():
    """簡化版遷移"""
    log_msg("INFO", "🔄 開始簡化版數據庫遷移...")
    
    # 檢查環境
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        log_msg("ERROR", "❌ DATABASE_URL 環境變數未設置")
        return False
    
    # 檢查是否為 PostgreSQL
    if not database_url.startswith('postgres'):
        log_msg("INFO", "✅ 非 PostgreSQL 環境，跳過遷移")
        return True
    
    log_msg("INFO", f"🐘 PostgreSQL URL: {database_url[:50]}...")
    
    try:
        # 直接使用 psycopg2 連接
        log_msg("INFO", "📡 嘗試連接 PostgreSQL...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = False  # 使用事務
        cursor = conn.cursor()
        
        log_msg("SUCCESS", "✅ PostgreSQL 連接成功")
        
        # 檢查 analyzed_posts 表是否存在
        log_msg("INFO", "🔍 檢查 analyzed_posts 表...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'analyzed_posts'
            )
        """)
        table_exists = cursor.fetchone()[0]
        log_msg("INFO", f"📊 表存在: {table_exists}")
        
        if table_exists:
            # 檢查 post_id 字段類型
            log_msg("INFO", "🔍 檢查 post_id 字段類型...")
            cursor.execute("""
                SELECT data_type, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'analyzed_posts' 
                AND column_name = 'post_id'
            """)
            
            field_info = cursor.fetchone()
            if field_info:
                data_type, max_length = field_info
                log_msg("INFO", f"📋 當前類型: {data_type}({max_length})")
                
                if data_type == 'integer':
                    log_msg("WARNING", "⚠️  需要修改 INTEGER → VARCHAR(255)")
                    
                    # 開始遷移事務
                    log_msg("INFO", "🔄 開始遷移事務...")
                    
                    # 步驟 1: 清空表數據（避免類型轉換問題）
                    log_msg("INFO", "🗑️  步驟1: 清空現有數據...")
                    cursor.execute("DELETE FROM analyzed_posts")
                    deleted_count = cursor.rowcount
                    log_msg("INFO", f"已刪除 {deleted_count} 條記錄")
                    
                    # 步驟 2: 修改字段類型
                    log_msg("INFO", "🔧 步驟2: 修改字段類型...")
                    cursor.execute("ALTER TABLE analyzed_posts ALTER COLUMN post_id TYPE VARCHAR(255)")
                    log_msg("SUCCESS", "✅ 字段類型修改完成")
                    
                    # 步驟 3: 驗證修改
                    log_msg("INFO", "✅ 步驟3: 驗證修改...")
                    cursor.execute("""
                        SELECT data_type, character_maximum_length
                        FROM information_schema.columns 
                        WHERE table_name = 'analyzed_posts' 
                        AND column_name = 'post_id'
                    """)
                    
                    new_field_info = cursor.fetchone()
                    if new_field_info:
                        new_type, new_length = new_field_info
                        log_msg("SUCCESS", f"✅ 新類型: {new_type}({new_length})")
                        
                        if new_type == 'character varying':
                            # 步驟 4: 測試插入
                            log_msg("INFO", "🧪 步驟4: 測試插入...")
                            test_id = "test_migration_123456789#m"
                            cursor.execute("""
                                INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
                                VALUES (%s, 'twitter', %s, 'test_migration')
                            """, (test_id, test_id))
                            
                            # 驗證插入
                            cursor.execute("SELECT post_id FROM analyzed_posts WHERE post_id = %s", (test_id,))
                            if cursor.fetchone():
                                log_msg("SUCCESS", "✅ 測試插入成功")
                                
                                # 清理測試數據
                                cursor.execute("DELETE FROM analyzed_posts WHERE post_id = %s", (test_id,))
                                log_msg("INFO", "🧹 清理測試數據")
                                
                                # 提交事務
                                conn.commit()
                                log_msg("SUCCESS", "🎉 遷移事務提交成功！")
                                
                            else:
                                log_msg("ERROR", "❌ 測試插入驗證失敗")
                                conn.rollback()
                                return False
                        else:
                            log_msg("ERROR", f"❌ 字段類型仍不正確: {new_type}")
                            conn.rollback()
                            return False
                    else:
                        log_msg("ERROR", "❌ 無法驗證字段修改")
                        conn.rollback()
                        return False
                        
                elif data_type == 'character varying':
                    log_msg("SUCCESS", "✅ 字段類型已正確")
                else:
                    log_msg("WARNING", f"⚠️  未知字段類型: {data_type}")
            else:
                log_msg("ERROR", "❌ 未找到 post_id 字段")
                return False
        else:
            log_msg("SUCCESS", "✅ 表不存在，首次部署時會自動創建")
        
        # 關閉連接
        cursor.close()
        conn.close()
        log_msg("SUCCESS", "🔌 數據庫連接已關閉")
        
        return True
        
    except psycopg2.Error as e:
        log_msg("ERROR", f"❌ PostgreSQL 錯誤: {e}")
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False
        
    except Exception as e:
        log_msg("ERROR", f"❌ 未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    log_msg("INFO", "🚀 啟動簡化版數據庫遷移...")
    success = simple_migration()
    
    if success:
        log_msg("SUCCESS", "✅ 簡化版遷移完成")
        sys.exit(0)
    else:
        log_msg("ERROR", "❌ 簡化版遷移失敗")
        sys.exit(1)