#!/usr/bin/env python3
"""
社交媒體追蹤系統主程序

功能：
1. 從Google Sheets讀取追蹤帳號列表
2. 使用X和LinkedIn API收集貼文
3. 使用AI分析貼文重要性並生成摘要和轉發內容
4. 將結果寫回Google Sheets
5. 支持定時任務和手動執行

使用方法：
python main.py --help                    # 查看幫助
python main.py --run-once                # 手動執行一次完整收集
python main.py --start-scheduler         # 啟動定時任務
python main.py --platform twitter        # 只收集Twitter數據
python main.py --stats                   # 查看統計信息
python main.py --view-data               # 查看數據庫內容
python main.py --review                  # 人工審核AI評分
python main.py --optimize-prompt         # 優化AI分析prompt
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# 添加項目根目錄到Python路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LOG_LEVEL, LOG_FILE
from services.post_collector import PostCollector
from services.scheduler import get_scheduler
from models.database import db_manager

def setup_logging():
    """設置日誌"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 減少第三方庫的日誌噪音
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('tweepy').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.INFO)

def run_once():
    """手動執行一次完整收集"""
    logger = logging.getLogger(__name__)
    logger.info("Starting manual collection...")
    
    try:
        collector = PostCollector()
        results = collector.collect_all_posts()
        
        print("\n=== 收集結果 ===")
        print(f"追蹤帳號數量: {results['total_accounts']}")
        print(f"收集到的貼文: {results['total_posts_collected']}")
        print(f"分析的貼文: {results['total_posts_analyzed']}")
        print(f"重要貼文: {results['important_posts']}")
        
        if results['errors']:
            print(f"錯誤數量: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        print(f"開始時間: {results['start_time']}")
        print(f"結束時間: {results['end_time']}")
        
        logger.info("Manual collection completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Manual collection failed: {e}")
        print(f"執行失敗: {e}")
        return False

def run_platform_only(platform: str):
    """只收集指定平台的數據"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting {platform} collection...")
    
    try:
        collector = PostCollector()
        results = collector.collect_posts_by_platform(platform)
        
        print(f"\n=== {platform.title()} 收集結果 ===")
        print(f"收集到的貼文: {results['posts_collected']}")
        print(f"分析的貼文: {results['posts_analyzed']}")
        print(f"重要貼文: {results['important_posts']}")
        
        if results['errors']:
            print(f"錯誤數量: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        logger.info(f"{platform} collection completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"{platform} collection failed: {e}")
        print(f"執行失敗: {e}")
        return False

def start_scheduler():
    """啟動定時任務調度器"""
    logger = logging.getLogger(__name__)
    
    try:
        scheduler = get_scheduler(background_mode=False)
        
        # 添加定時任務
        scheduler.add_daily_collection_job()
        
        print("定時任務調度器已啟動")
        print("每日收集時間: 每天 09:00")
        print("按 Ctrl+C 停止調度器")
        
        # 啟動調度器（阻塞模式）
        scheduler.run_blocking()
        
    except KeyboardInterrupt:
        print("\n調度器已停止")
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        print(f"調度器啟動失敗: {e}")

def show_stats():
    """顯示統計信息"""
    logger = logging.getLogger(__name__)
    
    try:
        collector = PostCollector()
        stats = collector.get_collection_stats()
        
        if 'error' in stats:
            print(f"獲取統計信息失敗: {stats['error']}")
            return False
        
        print("\n=== 系統統計信息 ===")
        print(f"總貼文數量: {stats['total_posts']}")
        print(f"已分析貼文: {stats['total_analyzed']}")
        print(f"重要貼文數量: {stats['important_posts']}")
        print(f"今日新增貼文: {stats['today_posts']}")
        
        print("\n按平台分布:")
        for platform, count in stats['platform_breakdown'].items():
            print(f"  {platform}: {count} 篇")
        
        print(f"\n最後更新: {stats['last_updated']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        print(f"獲取統計信息失敗: {e}")
        return False

def test_connections():
    """測試各個服務的連接"""
    logger = logging.getLogger(__name__)
    print("\n=== 測試系統連接 ===")
    
    # 測試數據庫連接
    try:
        session = db_manager.get_session()
        session.close()
        print("✓ 數據庫連接正常")
    except Exception as e:
        print(f"✗ 數據庫連接失敗: {e}")
    
    # 測試Google Sheets連接
    try:
        from clients.google_sheets_client import GoogleSheetsClient
        sheets_client = GoogleSheetsClient()
        accounts = sheets_client.get_accounts_to_track()
        print(f"✓ Google Sheets連接正常 (找到 {len(accounts)} 個帳號)")
    except Exception as e:
        print(f"✗ Google Sheets連接失敗: {e}")
    
    # 測試X API連接
    try:
        from clients.x_client import XClient
        from config import X_API_BEARER_TOKEN
        if X_API_BEARER_TOKEN:
            x_client = XClient()
            print("✓ X API配置正常")
        else:
            print("⚠ X API Token未配置")
    except Exception as e:
        print(f"✗ X API連接失敗: {e}")
    
    # 測試AI API連接
    try:
        from clients.ai_client import AIClient
        from config import AI_API_KEY, AI_API_TYPE
        if AI_API_KEY:
            ai_client = AIClient()
            print(f"✓ AI API配置正常 (使用 {AI_API_TYPE})")
        else:
            print("⚠ AI API Key未配置")
    except Exception as e:
        print(f"✗ AI API連接失敗: {e}")

def view_database_data():
    """查看數據庫內容"""
    logger = logging.getLogger(__name__)
    
    try:
        # 導入並使用view_database模組
        from view_database import show_statistics, view_analyzed_posts
        
        print("\n=== 數據庫內容總覽 ===")
        show_statistics()
        
        print("\n=== 最近分析結果 ===")
        view_analyzed_posts(limit=10)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to view database: {e}")
        print(f"查看數據庫失敗: {e}")
        return False

def start_review_system():
    """啟動人工審核系統"""
    logger = logging.getLogger(__name__)
    
    try:
        from review_system import ReviewSystem
        
        review_system = ReviewSystem()
        
        print("\n=== 人工審核系統 ===")
        
        # 顯示統計信息
        review_system.show_feedback_statistics()
        
        # 檢查是否有待審核的posts
        posts_for_review = review_system.db.get_posts_for_review(limit=5)
        
        if not posts_for_review:
            print("\n✅ 目前沒有需要審核的posts")
            return True
        
        print(f"\n📊 找到 {len(posts_for_review)} 篇待審核posts")
        
        # 詢問是否開始審核
        start_review = input("是否開始交互式審核? (y/n): ").strip().lower()
        
        if start_review == 'y':
            # 建議優先審核邊界分數的posts (6-9分)
            boundary_posts = review_system.db.get_posts_for_review(
                limit=10, 
                score_range=(6.0, 9.0)
            )
            
            if boundary_posts:
                print(f"\n🎯 建議優先審核邊界分數posts (6-9分): {len(boundary_posts)} 篇")
                priority_review = input("是否優先審核邊界分數posts? (y/n): ").strip().lower()
                
                if priority_review == 'y':
                    review_system.review_posts(limit=10, score_range=(6.0, 9.0))
                else:
                    review_system.review_posts(limit=10)
            else:
                review_system.review_posts(limit=10)
        else:
            print("📋 審核已取消")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to start review system: {e}")
        print(f"啟動審核系統失敗: {e}")
        return False

def show_api_stats():
    """顯示API使用統計"""
    logger = logging.getLogger(__name__)
    
    try:
        print("\n=== API 使用統計 (過去24小時) ===")
        
        # Twitter API 統計
        twitter_stats = db_manager.get_api_usage_stats('twitter', hours=24)
        if twitter_stats:
            print(f"\n🐦 Twitter API:")
            print(f"  總調用次數: {twitter_stats['total_calls']}")
            print(f"  成功調用次數: {twitter_stats['successful_calls']}")
            print(f"  失敗調用次數: {twitter_stats['failed_calls']}")
            print(f"  平均響應時間: {twitter_stats['avg_response_time']:.0f}ms")
            
            if twitter_stats['endpoints']:
                print(f"\n  按端點統計:")
                for endpoint, stats in twitter_stats['endpoints'].items():
                    success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
                    print(f"    {endpoint}: {stats['total']} 次 (成功率 {success_rate:.1f}%)")
        
        # 整體統計
        overall_stats = db_manager.get_api_usage_stats(hours=24)
        if overall_stats:
            print(f"\n📊 整體統計:")
            print(f"  總API調用: {overall_stats['total_calls']}")
            success_rate = (overall_stats['successful_calls'] / overall_stats['total_calls'] * 100) if overall_stats['total_calls'] > 0 else 0
            print(f"  成功率: {success_rate:.1f}%")
        
        # Twitter 用戶緩存統計
        session = db_manager.get_session()
        try:
            from models.database import TwitterUserCache
            cache_count = session.query(TwitterUserCache).count()
            print(f"\n💾 緩存統計:")
            print(f"  Twitter 用戶緩存數量: {cache_count}")
        finally:
            session.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to show API stats: {e}")
        print(f"顯示API統計失敗: {e}")
        return False

def optimize_ai_prompt():
    """優化AI分析prompt"""
    logger = logging.getLogger(__name__)
    
    try:
        from prompt_optimizer import PromptOptimizer
        
        optimizer = PromptOptimizer()
        
        print("\n=== AI Prompt優化系統 ===")
        
        # 檢查是否有足夠的反饋數據
        feedback_stats = optimizer.db.get_feedback_statistics()
        
        if feedback_stats.get('total_feedback', 0) < 5:
            print("❌ 反饋數據不足 (至少需要5條反饋)")
            print("💡 請先使用 --review 進行人工審核，累積足夠的反饋數據")
            return False
        
        print(f"📊 找到 {feedback_stats['total_feedback']} 條反饋數據")
        print(f"📈 當前準確率: {feedback_stats['accuracy_rate']:.1f}%")
        
        # 詢問是否運行優化工作流
        run_optimization = input("\n是否運行prompt優化工作流? (y/n): ").strip().lower()
        
        if run_optimization == 'y':
            # 運行優化工作流
            optimizer.run_optimization_workflow(days_back=30, auto_save=False)
        else:
            # 只顯示分析結果
            optimizer.analyze_feedback_patterns(days_back=30)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to optimize prompt: {e}")
        print(f"優化prompt失敗: {e}")
        return False

def main():
    """主函數"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(
        description='社交媒體追蹤系統',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python main.py --run-once              # 手動執行一次完整收集
  python main.py --start-scheduler       # 啟動定時任務
  python main.py --platform twitter      # 只收集Twitter數據
  python main.py --platform linkedin     # 只收集LinkedIn數據
  python main.py --stats                 # 查看統計信息
  python main.py --api-stats             # 查看API使用統計
  python main.py --test                  # 測試系統連接
  python main.py --view-data             # 查看數據庫內容和AI評分
  python main.py --review                # 人工審核AI評分系統
  python main.py --optimize-prompt       # 優化AI分析prompt
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run-once', action='store_true', help='手動執行一次完整收集')
    group.add_argument('--start-scheduler', action='store_true', help='啟動定時任務調度器')
    group.add_argument('--platform', choices=['twitter', 'linkedin'], help='只收集指定平台的數據')
    group.add_argument('--stats', action='store_true', help='顯示統計信息')
    group.add_argument('--api-stats', action='store_true', help='查看API使用統計')
    group.add_argument('--test', action='store_true', help='測試系統連接')
    group.add_argument('--view-data', action='store_true', help='查看數據庫內容和AI評分')
    group.add_argument('--review', action='store_true', help='人工審核AI評分系統')
    group.add_argument('--optimize-prompt', action='store_true', help='優化AI分析prompt')
    
    args = parser.parse_args()
    
    # 檢查環境文件（雲端部署時通過環境變數配置，不需要 .env 文件）
    # 檢查是否在雲端環境（Railway 會設定 DATABASE_URL 環境變數）
    is_cloud_deployment = os.getenv('DATABASE_URL', '').startswith('postgres')
    
    if not os.path.exists('.env') and not is_cloud_deployment:
        print("警告: 未找到 .env 文件，請複製 .env.example 並配置相關API密鑰")
        print("執行: cp .env.example .env")
        return 1
    
    logger.info(f"Starting Social Media Tracker with args: {args}")
    
    try:
        if args.run_once:
            success = run_once()
            return 0 if success else 1
            
        elif args.start_scheduler:
            start_scheduler()
            return 0
            
        elif args.platform:
            success = run_platform_only(args.platform)
            return 0 if success else 1
            
        elif args.stats:
            success = show_stats()
            return 0 if success else 1
            
        elif getattr(args, 'api_stats', False):
            success = show_api_stats()
            return 0 if success else 1
            
        elif args.test:
            test_connections()
            return 0
        
        elif args.view_data:
            success = view_database_data()
            return 0 if success else 1
        
        elif args.review:
            success = start_review_system()
            return 0 if success else 1
        
        elif args.optimize_prompt:
            success = optimize_ai_prompt()
            return 0 if success else 1
            
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        print("\n程序已停止")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"程序執行出錯: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())