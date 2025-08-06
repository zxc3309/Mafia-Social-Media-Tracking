#!/usr/bin/env python3
"""
數據庫遷移腳本：修復 AnalyzedPost.post_id 字段類型
從 INTEGER 改為 VARCHAR(255)
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def migrate_database():
    """執行數據庫遷移"""
    print("🔄 開始數據庫遷移...")
    
    try:
        # 創建數據庫連接
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 檢查是否為 PostgreSQL
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"數據庫版本: {version}")
            
            if 'PostgreSQL' in version:
                print("✅ 檢測到 PostgreSQL，開始遷移...")
                
                # 1. 檢查表是否存在
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'analyzed_posts'
                    )
                """))
                
                table_exists = result.fetchone()[0]
                
                if table_exists:
                    print("⚠️  表 analyzed_posts 已存在，需要修改字段類型...")
                    
                    # 2. 檢查當前字段類型
                    result = conn.execute(text("""
                        SELECT data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'analyzed_posts' 
                        AND column_name = 'post_id'
                    """))
                    
                    current_type = result.fetchone()
                    if current_type:
                        print(f"當前 post_id 字段類型: {current_type[0]}")
                        
                        if current_type[0] == 'integer':
                            print("🔧 修改字段類型從 INTEGER 到 VARCHAR(255)...")
                            
                            # 先刪除所有數據（因為類型不兼容）
                            conn.execute(text("DELETE FROM analyzed_posts"))
                            print("🗑️  清空表數據")
                            
                            # 修改字段類型
                            conn.execute(text("ALTER TABLE analyzed_posts ALTER COLUMN post_id TYPE VARCHAR(255)"))
                            print("✅ 字段類型修改完成")
                            
                            # 提交更改
                            conn.commit()
                        else:
                            print("✅ 字段類型已正確")
                    else:
                        print("⚠️  未找到 post_id 字段")
                else:
                    print("✅ 表不存在，首次運行時會自動創建正確的結構")
                    
            elif 'SQLite' in version:
                print("✅ 檢測到 SQLite（本地開發環境），跳過遷移")
            else:
                print(f"⚠️  未知數據庫類型: {version}")
                
    except Exception as e:
        print(f"❌ 遷移失敗: {e}")
        return False
        
    print("🎉 數據庫遷移完成！")
    return True

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)