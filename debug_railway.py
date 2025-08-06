#!/usr/bin/env python3
"""
Railway 部署調試腳本
用於檢查 Railway 環境和數據庫連接狀態
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text

def log_debug(message):
    """調試日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [DEBUG] {message}")
    sys.stdout.flush()

def debug_railway_environment():
    """檢查 Railway 環境"""
    log_debug("🔍 開始 Railway 環境檢查...")
    
    # 檢查環境變數
    env_vars = [
        'RAILWAY_ENVIRONMENT_NAME',
        'DATABASE_URL',
        'RAILWAY_PROJECT_ID',
        'RAILWAY_SERVICE_NAME',
        'AI_API_KEY',
        'GOOGLE_SHEETS_CREDENTIALS_BASE64'
    ]
    
    log_debug("📋 環境變數檢查:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'CREDENTIALS' in var or 'DATABASE_URL' in var:
                # 隱藏敏感信息
                display_value = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "***"
            else:
                display_value = value
            log_debug(f"  ✅ {var}: {display_value}")
        else:
            log_debug(f"  ❌ {var}: 未設置")
    
    # 檢查 Railway 環境
    is_railway = os.getenv('RAILWAY_ENVIRONMENT_NAME') is not None
    log_debug(f"🚂 Railway 環境: {is_railway}")
    
    return is_railway

def debug_database_connection():
    """檢查數據庫連接"""
    log_debug("🔌 開始數據庫連接檢查...")
    
    try:
        from config import DATABASE_URL
        log_debug(f"📊 DATABASE_URL 開頭: {DATABASE_URL[:50]}...")
        
        # 檢查 URL 格式
        if DATABASE_URL.startswith('postgres'):
            log_debug("✅ PostgreSQL URL 格式正確")
        elif DATABASE_URL.startswith('sqlite'):
            log_debug("⚠️  SQLite URL (本地環境)")
        else:
            log_debug(f"❌ 未知 DATABASE_URL 格式: {DATABASE_URL[:20]}...")
            return False
        
        # 測試連接
        log_debug("🔗 嘗試連接數據庫...")
        engine = create_engine(DATABASE_URL, connect_args={'connect_timeout': 10})
        
        with engine.connect() as conn:
            # 獲取版本
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            log_debug(f"✅ 數據庫連接成功")
            log_debug(f"📋 數據庫版本: {version[:100]}...")
            
            # 檢查表存在
            if 'PostgreSQL' in version:
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result.fetchall()]
                log_debug(f"📊 找到 {len(tables)} 個表: {', '.join(tables)}")
                
                # 檢查 analyzed_posts 表結構
                if 'analyzed_posts' in tables:
                    result = conn.execute(text("""
                        SELECT column_name, data_type, character_maximum_length
                        FROM information_schema.columns 
                        WHERE table_name = 'analyzed_posts'
                        AND column_name = 'post_id'
                    """))
                    
                    field_info = result.fetchone()
                    if field_info:
                        col_name, data_type, max_len = field_info
                        log_debug(f"🎯 post_id 字段: {data_type}({max_len if max_len else 'N/A'})")
                        if data_type == 'integer':
                            log_debug("❌ post_id 仍為 INTEGER 類型！需要遷移")
                            return False
                        elif data_type == 'character varying':
                            log_debug("✅ post_id 已為 VARCHAR 類型")
                            return True
                        else:
                            log_debug(f"⚠️  post_id 未知類型: {data_type}")
                    else:
                        log_debug("❌ 未找到 post_id 字段")
                        return False
                else:
                    log_debug("❌ 未找到 analyzed_posts 表")
                    return False
            else:
                log_debug("✅ SQLite 數據庫（本地環境）")
                return True
                
    except Exception as e:
        log_debug(f"❌ 數據庫連接失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_migration_requirements():
    """檢查遷移需求"""
    log_debug("🔧 檢查遷移需求...")
    
    try:
        # 檢查遷移腳本是否存在
        migration_scripts = [
            'force_migration.py',
            'nuclear_migration.py',
            'migrate_database.py'
        ]
        
        for script in migration_scripts:
            if os.path.exists(script):
                log_debug(f"✅ 遷移腳本存在: {script}")
            else:
                log_debug(f"❌ 遷移腳本不存在: {script}")
        
        # 檢查權限
        log_debug(f"🔐 當前工作目錄: {os.getcwd()}")
        log_debug(f"📁 目錄內容: {os.listdir('.')[:10]}...")  # 前10個文件
        
        return True
        
    except Exception as e:
        log_debug(f"❌ 遷移需求檢查失敗: {e}")
        return False

def main():
    """主函數"""
    log_debug("🚀 開始 Railway 調試...")
    
    # 環境檢查
    is_railway = debug_railway_environment()
    
    # 數據庫連接檢查  
    db_ok = debug_database_connection()
    
    # 遷移需求檢查
    migration_ok = debug_migration_requirements()
    
    # 總結
    log_debug("📊 調試總結:")
    log_debug(f"  Railway 環境: {'✅' if is_railway else '❌'}")
    log_debug(f"  數據庫連接: {'✅' if db_ok else '❌'}")
    log_debug(f"  遷移需求: {'✅' if migration_ok else '❌'}")
    
    if db_ok:
        log_debug("✅ 數據庫已正確配置，無需遷移")
        return True
    else:
        log_debug("❌ 需要執行數據庫遷移")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)