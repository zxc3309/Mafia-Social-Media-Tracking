#!/usr/bin/env python3
"""
強制執行數據庫遷移腳本 - Railway 部署版本
這個腳本會強制執行數據庫遷移，即使在有錯誤的情況下
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def force_migrate_database():
    """強制執行數據庫遷移"""
    print("🔄 強制開始數據庫遷移...")
    print(f"DATABASE_URL: {DATABASE_URL[:50]}...")  # 只顯示前50字符
    
    try:
        # 創建數據庫連接
        engine = create_engine(DATABASE_URL)
        
        with engine.begin() as conn:  # 使用 begin() 確保事務
            # 檢查是否為 PostgreSQL
            try:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"數據庫版本: {version}")
            except Exception as e:
                print(f"⚠️  無法獲取數據庫版本: {e}")
                return False
            
            if 'PostgreSQL' in version:
                print("✅ 檢測到 PostgreSQL，開始強制遷移...")
                
                # 1. 檢查表是否存在
                try:
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'analyzed_posts'
                        )
                    """))
                    table_exists = result.fetchone()[0]
                    print(f"表 analyzed_posts 存在: {table_exists}")
                except Exception as e:
                    print(f"⚠️  檢查表存在性失敗: {e}")
                    table_exists = False
                
                if table_exists:
                    # 2. 檢查當前字段類型
                    try:
                        result = conn.execute(text("""
                            SELECT data_type, character_maximum_length
                            FROM information_schema.columns 
                            WHERE table_name = 'analyzed_posts' 
                            AND column_name = 'post_id'
                        """))
                        
                        field_info = result.fetchone()
                        if field_info:
                            data_type, max_length = field_info
                            print(f"當前 post_id 字段類型: {data_type} (長度: {max_length})")
                            
                            if data_type == 'integer':
                                print("🔧 需要修改字段類型從 INTEGER 到 VARCHAR(255)...")
                                
                                # 3. 先刪除所有數據（因為類型不兼容）
                                try:
                                    conn.execute(text("DELETE FROM analyzed_posts"))
                                    print("🗑️  清空表數據完成")
                                except Exception as e:
                                    print(f"⚠️  清空表數據失敗: {e}")
                                
                                # 4. 修改字段類型
                                try:
                                    conn.execute(text("ALTER TABLE analyzed_posts ALTER COLUMN post_id TYPE VARCHAR(255)"))
                                    print("✅ 字段類型修改完成")
                                except Exception as e:
                                    print(f"❌ 字段類型修改失敗: {e}")
                                    return False
                                    
                            elif data_type in ['character varying', 'varchar', 'text']:
                                print("✅ 字段類型已正確 (VARCHAR/TEXT)")
                            else:
                                print(f"⚠️  未知字段類型: {data_type}")
                        else:
                            print("❌ 未找到 post_id 字段")
                            return False
                            
                    except Exception as e:
                        print(f"❌ 檢查字段類型失敗: {e}")
                        return False
                        
                else:
                    print("✅ 表不存在，首次運行時會自動創建正確的結構")
                    
            elif 'SQLite' in version:
                print("✅ 檢測到 SQLite（本地開發環境），跳過遷移")
            else:
                print(f"⚠️  未知數據庫類型: {version}")
                return False
                
    except Exception as e:
        print(f"❌ 遷移失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    print("🎉 強制數據庫遷移完成！")
    return True

if __name__ == "__main__":
    success = force_migrate_database()
    if not success:
        print("❌ 遷移失敗，程序將退出")
        sys.exit(1)
    else:
        print("✅ 遷移成功，可以繼續執行主程序")
        sys.exit(0)