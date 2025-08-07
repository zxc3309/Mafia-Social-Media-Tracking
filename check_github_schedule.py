#!/usr/bin/env python3
"""
GitHub Actions 自動執行檢查工具
檢查 workflow schedule 設定和執行狀態
"""

import datetime
import pytz

def check_cron_schedule():
    """檢查 cron 排程設定"""
    print("📅 GitHub Actions Cron 排程檢查")
    print("=" * 50)
    
    # 當前時間
    utc_now = datetime.datetime.now(pytz.UTC)
    taipei_tz = pytz.timezone('Asia/Taipei')
    taipei_now = utc_now.astimezone(taipei_tz)
    
    print(f"當前 UTC 時間: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"當前台北時間: {taipei_now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 分析 cron 設定
    print(f"\n🕘 Cron 設定分析:")
    print(f"設定: '0 1 * * *' = 每天 UTC 1:00")
    print(f"對應台北時間: 每天 09:00")
    
    # 計算下次執行時間
    today_utc = utc_now.replace(hour=1, minute=0, second=0, microsecond=0)
    if utc_now.hour >= 1:
        next_run_utc = today_utc + datetime.timedelta(days=1)
    else:
        next_run_utc = today_utc
    
    next_run_taipei = next_run_utc.astimezone(taipei_tz)
    
    print(f"\n⏰ 下次預定執行:")
    print(f"UTC: {next_run_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"台北時間: {next_run_taipei.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 時間差計算
    time_until = next_run_utc - utc_now
    hours = int(time_until.total_seconds() // 3600)
    minutes = int((time_until.total_seconds() % 3600) // 60)
    print(f"距離下次執行: {hours} 小時 {minutes} 分鐘")

def check_github_actions_limitations():
    """檢查 GitHub Actions 限制"""
    print(f"\n⚠️  GitHub Actions Cron 限制:")
    print(f"1. 最多延遲 15 分鐘執行")
    print(f"2. 如果 repository 長時間無活動，可能暫停 cron")
    print(f"3. 需要在 default branch (main) 上")
    print(f"4. 免費帳戶每月有執行時間限制")
    
    print(f"\n✅ 確保自動執行的方法:")
    print(f"1. Repository 必須有定期 commit 活動")
    print(f"2. Workflow 文件必須在 main branch")
    print(f"3. 等待首次執行（可能需要 1-2 天）")
    print(f"4. 檢查 GitHub Actions 頁面的執行歷史")

def generate_test_schedule():
    """生成測試用的更頻繁排程"""
    print(f"\n🧪 測試建議:")
    print(f"建議先設定一個更頻繁的測試排程來驗證:")
    
    utc_now = datetime.datetime.now(pytz.UTC)
    test_time = utc_now + datetime.timedelta(minutes=10)
    
    print(f"例如設定為每 15 分鐘執行一次（僅測試用）:")
    print(f"schedule:")
    print(f"  - cron: '*/15 * * * *'")
    print(f"")
    print(f"測試成功後再改回每日執行:")
    print(f"schedule:")
    print(f"  - cron: '0 1 * * *'")

def main():
    print("🔍 GitHub Actions 自動執行診斷工具")
    print("=" * 60)
    
    check_cron_schedule()
    check_github_actions_limitations()
    generate_test_schedule()
    
    print(f"\n📋 檢查清單:")
    print(f"□ 檢查 GitHub Actions 頁面是否有執行記錄")
    print(f"□ 確認 workflow 文件在 main branch")
    print(f"□ 確認 repository 最近有 commit 活動")
    print(f"□ 檢查 GitHub Actions 額度是否足夠")
    
    print(f"\n💡 立即檢查方法:")
    print(f"1. 到 GitHub → Actions → 查看執行歷史")
    print(f"2. 確認有沒有 'Schedule' 觸發的執行記錄")
    print(f"3. 如果沒有，設定測試排程驗證系統")

if __name__ == "__main__":
    main()