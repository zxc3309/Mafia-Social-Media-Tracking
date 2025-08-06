#!/usr/bin/env python3
"""
數據庫架構驗證腳本
用於驗證 Railway 部署後的數據庫架構是否正確
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def verify_schema():
    """驗證數據庫架構"""
    print("🔍 開始驗證數據庫架構...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 檢查數據庫版本
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"📊 數據庫版本: {version[:50]}...")
            
            # 檢查所有表
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 找到 {len(tables)} 個表: {', '.join(tables)}")
            
            # 重點檢查 analyzed_posts 表
            if 'analyzed_posts' in tables:
                print("\n🎯 檢查 analyzed_posts 表結構:")
                result = conn.execute(text("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'analyzed_posts' 
                    ORDER BY ordinal_position
                """))
                
                post_id_type = None
                for col_name, data_type, max_len, nullable in result.fetchall():
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    if col_name == 'post_id':
                        post_id_type = data_type
                        if data_type == 'character varying':
                            print(f"   ✅ {col_name}: {data_type}({max_len}) {nullable_str}")
                        else:
                            print(f"   ❌ {col_name}: {data_type} {nullable_str} (應該是 character varying)")
                    else:
                        length_info = f"({max_len})" if max_len else ""
                        print(f"   📝 {col_name}: {data_type}{length_info} {nullable_str}")
                
                # 測試插入功能
                if post_id_type == 'character varying':
                    print("\n🧪 測試數據插入...")
                    test_post_id = f"verify_test_{__import__('time').time()}_#m"
                    
                    try:
                        # 測試插入
                        conn.execute(text("""
                            INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
                            VALUES (:post_id, 'twitter', :post_id, 'verify_test')
                        """), {"post_id": test_post_id})
                        
                        # 驗證插入
                        result = conn.execute(text("""
                            SELECT post_id FROM analyzed_posts WHERE post_id = :post_id
                        """), {"post_id": test_post_id})
                        
                        if result.fetchone():
                            print("   ✅ 插入測試成功")
                            
                            # 清理測試數據
                            conn.execute(text("DELETE FROM analyzed_posts WHERE post_id = :post_id"), 
                                       {"post_id": test_post_id})
                            conn.commit()
                            print("   🧹 測試數據已清理")
                        else:
                            print("   ❌ 插入測試失敗：找不到插入的數據")
                            return False
                            
                    except Exception as e:
                        print(f"   ❌ 插入測試失敗: {e}")
                        return False
                else:
                    print(f"   ❌ post_id 字段類型錯誤: {post_id_type}")
                    return False
            else:
                print("❌ 未找到 analyzed_posts 表")
                return False
            
            print("\n🎉 數據庫架構驗證成功！")
            return True
            
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)