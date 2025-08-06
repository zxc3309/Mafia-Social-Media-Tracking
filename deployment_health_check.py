#!/usr/bin/env python3
"""
部署健康檢查腳本
驗證部署後系統的核心功能是否正常工作
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

def log_health(level, message):
    """健康檢查日誌"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [HEALTH-{level}] {message}")
    sys.stdout.flush()

def check_database_health():
    """檢查數據庫健康狀態"""
    log_health("INFO", "🏥 開始數據庫健康檢查...")
    
    try:
        from config import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 基本連接測試
            result = conn.execute(text("SELECT 1 as health_check"))
            if result.fetchone()[0] == 1:
                log_health("SUCCESS", "✅ 數據庫基本連接正常")
            else:
                log_health("ERROR", "❌ 數據庫基本連接測試失敗")
                return False
            
            # 檢查必要表是否存在
            required_tables = ['accounts', 'posts', 'analyzed_posts']
            
            if DATABASE_URL.startswith('postgres'):
                # PostgreSQL 環境
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = ANY(%(tables)s)
                """), {"tables": required_tables})
                
                existing_tables = [row[0] for row in result.fetchall()]
                log_health("INFO", f"📊 找到表: {existing_tables}")
                
                for table in required_tables:
                    if table in existing_tables:
                        log_health("SUCCESS", f"✅ 表存在: {table}")
                    else:
                        log_health("ERROR", f"❌ 缺少表: {table}")
                        return False
                
                # 重點檢查 analyzed_posts 的 post_id 字段
                result = conn.execute(text("""
                    SELECT data_type, character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_name = 'analyzed_posts' 
                    AND column_name = 'post_id'
                """))
                
                field_info = result.fetchone()
                if field_info:
                    data_type, max_length = field_info
                    if data_type == 'character varying' and max_length >= 255:
                        log_health("SUCCESS", f"✅ post_id 字段正確: {data_type}({max_length})")
                    else:
                        log_health("ERROR", f"❌ post_id 字段不正確: {data_type}({max_length})")
                        return False
                else:
                    log_health("ERROR", "❌ 未找到 post_id 字段")
                    return False
                
                # 測試實際數據插入
                log_health("INFO", "🧪 測試數據插入功能...")
                test_post_id = f"health_check_{int(datetime.now().timestamp())}#m"
                
                try:
                    conn.execute(text("""
                        INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username, analyzed_at)
                        VALUES (:post_id, 'twitter', :post_id, 'health_check', :now)
                    """), {
                        "post_id": test_post_id,
                        "now": datetime.now()
                    })
                    
                    # 驗證插入
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM analyzed_posts WHERE post_id = :post_id
                    """), {"post_id": test_post_id})
                    
                    if result.fetchone()[0] == 1:
                        log_health("SUCCESS", "✅ 數據插入測試成功")
                        
                        # 清理測試數據
                        conn.execute(text("DELETE FROM analyzed_posts WHERE post_id = :post_id"), 
                                   {"post_id": test_post_id})
                        conn.commit()
                        log_health("INFO", "🧹 清理測試數據完成")
                    else:
                        log_health("ERROR", "❌ 數據插入測試失敗")
                        return False
                        
                except Exception as e:
                    log_health("ERROR", f"❌ 數據插入測試錯誤: {e}")
                    return False
            
            else:
                # SQLite 環境（本地開發）
                log_health("INFO", "✅ SQLite 環境（本地開發）")
            
            return True
            
    except Exception as e:
        log_health("ERROR", f"❌ 數據庫健康檢查失敗: {e}")
        return False

def check_environment_health():
    """檢查環境配置健康狀態"""
    log_health("INFO", "🌍 開始環境配置健康檢查...")
    
    # 檢查關鍵環境變數
    required_env_vars = {
        'DATABASE_URL': '數據庫連接',
        'AI_API_KEY': 'AI API 密鑰',
    }
    
    optional_env_vars = {
        'GOOGLE_SHEETS_CREDENTIALS_BASE64': 'Google Sheets 憑證',
        'X_API_BEARER_TOKEN': 'X API Token',
        'RAILWAY_ENVIRONMENT_NAME': 'Railway 環境名稱'
    }
    
    all_good = True
    
    for var, desc in required_env_vars.items():
        if os.getenv(var):
            log_health("SUCCESS", f"✅ {desc} 已配置")
        else:
            log_health("ERROR", f"❌ {desc} 未配置 ({var})")
            all_good = False
    
    for var, desc in optional_env_vars.items():
        if os.getenv(var):
            log_health("INFO", f"📋 {desc} 已配置")
        else:
            log_health("WARNING", f"⚠️  {desc} 未配置 ({var})")
    
    return all_good

def check_application_health():
    """檢查應用程式功能健康狀態"""
    log_health("INFO", "🚀 開始應用程式健康檢查...")
    
    try:
        # 測試導入核心模組
        from clients.ai_client import AIClient
        from models.database import db_manager
        from services.post_collector import PostCollector
        
        log_health("SUCCESS", "✅ 核心模組導入成功")
        
        # 測試 AI 客戶端初始化
        try:
            ai_client = AIClient()
            log_health("SUCCESS", "✅ AI 客戶端初始化成功")
        except Exception as e:
            log_health("WARNING", f"⚠️  AI 客戶端初始化失敗: {e}")
        
        # 測試數據庫管理器
        try:
            session = db_manager.get_session()
            session.close()
            log_health("SUCCESS", "✅ 數據庫管理器正常")
        except Exception as e:
            log_health("ERROR", f"❌ 數據庫管理器錯誤: {e}")
            return False
        
        return True
        
    except Exception as e:
        log_health("ERROR", f"❌ 應用程式健康檢查失敗: {e}")
        return False

def main():
    """主健康檢查函數"""
    log_health("INFO", "🏥 開始部署健康檢查...")
    
    # 環境配置檢查
    env_health = check_environment_health()
    
    # 數據庫健康檢查
    db_health = check_database_health()
    
    # 應用程式健康檢查
    app_health = check_application_health()
    
    # 總結
    log_health("INFO", "📊 健康檢查總結:")
    log_health("INFO", f"  環境配置: {'✅ 健康' if env_health else '❌ 不健康'}")
    log_health("INFO", f"  數據庫: {'✅ 健康' if db_health else '❌ 不健康'}")
    log_health("INFO", f"  應用程式: {'✅ 健康' if app_health else '❌ 不健康'}")
    
    overall_health = env_health and db_health and app_health
    
    if overall_health:
        log_health("SUCCESS", "🎉 系統整體健康狀況良好，準備就緒！")
        return True
    else:
        log_health("ERROR", "❌ 系統健康檢查發現問題，需要修復")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)