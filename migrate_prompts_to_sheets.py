#!/usr/bin/env python3
"""
遷移現有的 AI Prompts 從 config.py 到 Google Sheets
執行一次性資料遷移
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clients.google_sheets_client import GoogleSheetsClient
from config import (
    IMPORTANCE_FILTER_PROMPT, 
    SUMMARIZATION_PROMPT, 
    REPOST_GENERATION_PROMPT
)

def migrate_prompts():
    """將所有 prompts 遷移到 Google Sheets"""
    print("🚀 開始遷移 AI Prompts 到 Google Sheets...")
    
    try:
        # 初始化 Google Sheets 客戶端
        sheets_client = GoogleSheetsClient()
        
        # 要遷移的 prompts
        prompts_to_migrate = [
            {
                "name": "IMPORTANCE_FILTER",
                "content": IMPORTANCE_FILTER_PROMPT,
                "description": "重要性評分 prompt"
            },
            {
                "name": "SUMMARIZATION", 
                "content": SUMMARIZATION_PROMPT,
                "description": "內容摘要 prompt"
            },
            {
                "name": "REPOST_GENERATION",
                "content": REPOST_GENERATION_PROMPT, 
                "description": "轉發內容生成 prompt"
            }
        ]
        
        migration_results = []
        
        for prompt in prompts_to_migrate:
            print(f"\n📋 遷移 {prompt['name']} prompt...")
            print(f"描述: {prompt['description']}")
            
            # 檢查內容
            if not prompt['content'] or prompt['content'].strip() == "":
                print(f"❌ {prompt['name']} 內容為空，跳過遷移")
                migration_results.append(False)
                continue
                
            # 新增到 Google Sheets
            success = sheets_client.add_prompt_version(
                prompt_name=prompt['name'],
                content=prompt['content'],
                version="v1.0"
            )
            
            if success:
                print(f"✅ {prompt['name']} 遷移成功")
                migration_results.append(True)
            else:
                print(f"❌ {prompt['name']} 遷移失敗")
                migration_results.append(False)
        
        # 報告結果
        print("\n" + "="*60)
        print("📊 遷移結果統計:")
        successful = sum(migration_results)
        total = len(migration_results)
        
        print(f"   總共: {total} 個 prompts")
        print(f"   成功: {successful} 個")
        print(f"   失敗: {total - successful} 個")
        print(f"   成功率: {successful/total*100:.1f}%")
        
        if successful == total:
            print("\n✅ 所有 prompts 遷移完成！")
            print("🎯 系統現在會從 Google Sheets 讀取 prompts")
            print("💡 你可以直接在 Google Sheets 中管理和切換 prompts")
        else:
            print(f"\n⚠️  有 {total - successful} 個 prompts 遷移失敗")
            print("🔧 請檢查 Google Sheets 連接和權限設置")
            
        return successful == total
        
    except Exception as e:
        print(f"❌ 遷移過程發生錯誤: {e}")
        return False

def verify_migration():
    """驗證遷移結果"""
    print("\n🔍 驗證遷移結果...")
    
    try:
        sheets_client = GoogleSheetsClient()
        
        # 測試讀取每個 prompt
        test_prompts = ["IMPORTANCE_FILTER", "SUMMARIZATION", "REPOST_GENERATION"]
        
        for prompt_name in test_prompts:
            active_prompt = sheets_client.get_active_prompt(prompt_name)
            if active_prompt:
                print(f"✅ {prompt_name}: 讀取成功 ({len(active_prompt)} 字元)")
            else:
                print(f"❌ {prompt_name}: 讀取失敗或無活躍版本")
                
        return True
        
    except Exception as e:
        print(f"❌ 驗證過程發生錯誤: {e}")
        return False

def main():
    """主要執行函數"""
    print("🤖 AI Prompts 遷移工具")
    print("將 config.py 中的 prompts 遷移到 Google Sheets")
    print("="*60)
    
    # 執行遷移
    migration_success = migrate_prompts()
    
    if migration_success:
        # 驗證遷移結果
        verify_migration()
        
        print("\n🎉 遷移完成！")
        print("📋 接下來可以做：")
        print("   1. 檢查 Google Sheets 中的 'AI Prompts' 工作表")
        print("   2. 測試 AI 分析功能確認讀取正常")  
        print("   3. 使用 Prompt Optimizer 功能優化 prompts")
    else:
        print("\n💔 遷移未完成")
        print("🔧 請檢查錯誤訊息並重試")
        sys.exit(1)

if __name__ == "__main__":
    main()