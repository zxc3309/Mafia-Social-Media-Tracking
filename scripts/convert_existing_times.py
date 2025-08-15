#!/usr/bin/env python3
"""
一次性腳本：將 Google Sheets 中的現有時間轉換為台灣時間
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.google_sheets_client import GoogleSheetsClient
from config import OUTPUT_SPREADSHEET_NAME, OUTPUT_WORKSHEET_NAME, ALL_POSTS_WORKSHEET_NAME
import pytz
from datetime import datetime
from dateutil import parser
import json
import argparse

class TimeConverter:
    def __init__(self):
        self.client = GoogleSheetsClient()
        self.taiwan_tz = pytz.timezone('Asia/Taipei')
        self.utc_tz = pytz.UTC
        self.conversion_log = []
        
    def parse_and_convert_time(self, time_str):
        """解析並轉換時間字串為台灣時間"""
        if not time_str or time_str.strip() == '':
            return ''
        
        original = time_str
        try:
            # 檢查是否已經包含 +8 時區標記
            if '+8' in time_str or 'GMT+8' in time_str or '台灣' in time_str:
                # 已經是台灣時間，只需要標準化格式
                # 移除時區標記來解析
                clean_time = time_str.replace('+8', '').replace('GMT+8', '').replace('(台灣時間)', '').strip()
                dt = parser.parse(clean_time)
                if dt.tzinfo is None:
                    dt = self.taiwan_tz.localize(dt)
                result = dt.strftime('%Y-%m-%d %H:%M:%S')
                self.conversion_log.append(f"標準化台灣時間: {original} -> {result}")
                return result
            
            # 嘗試解析時間
            dt = parser.parse(time_str)
            
            # 如果沒有時區信息，假設是 UTC
            if dt.tzinfo is None:
                dt = self.utc_tz.localize(dt)
                self.conversion_log.append(f"假設 UTC: {original}")
            
            # 轉換為台灣時間
            taiwan_time = dt.astimezone(self.taiwan_tz)
            result = taiwan_time.strftime('%Y-%m-%d %H:%M:%S')
            self.conversion_log.append(f"轉換: {original} -> {result}")
            return result
            
        except Exception as e:
            self.conversion_log.append(f"錯誤: 無法轉換 '{original}' - {e}")
            return time_str  # 返回原始值
    
    def convert_worksheet(self, worksheet_name, time_columns, dry_run=True):
        """轉換工作表中的時間欄位"""
        print(f"\n{'='*60}")
        print(f"處理工作表: {worksheet_name}")
        print(f"{'='*60}")
        
        try:
            sheet = self.client.gc.open(OUTPUT_SPREADSHEET_NAME)
            worksheet = sheet.worksheet(worksheet_name)
            
            # 獲取所有資料
            all_values = worksheet.get_all_values()
            
            if len(all_values) <= 1:
                print("工作表沒有資料需要轉換")
                return
            
            headers = all_values[0]
            data_rows = all_values[1:]
            
            # 找出時間欄位的索引
            time_col_indices = []
            for col_name in time_columns:
                if col_name in headers:
                    idx = headers.index(col_name)
                    time_col_indices.append((idx, col_name))
                    print(f"找到時間欄位: {col_name} (索引: {idx})")
            
            if not time_col_indices:
                print("未找到指定的時間欄位")
                return
            
            # 轉換每一行的時間
            updated_rows = []
            changes_made = 0
            
            for row_idx, row in enumerate(data_rows, start=2):  # 從第2行開始（跳過標題）
                row_copy = row.copy()
                row_changed = False
                
                for col_idx, col_name in time_col_indices:
                    if col_idx < len(row_copy):
                        original_value = row_copy[col_idx]
                        new_value = self.parse_and_convert_time(original_value)
                        
                        if new_value != original_value:
                            row_changed = True
                            changes_made += 1
                            print(f"Row {row_idx}, {col_name}: '{original_value}' -> '{new_value}'")
                            row_copy[col_idx] = new_value
                
                updated_rows.append(row_copy)
            
            print(f"\n總計需要更新 {changes_made} 個時間欄位")
            
            if not dry_run and changes_made > 0:
                # 備份原始資料
                backup_filename = f"backup_{worksheet_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(f"scripts/{backup_filename}", 'w', encoding='utf-8') as f:
                    json.dump({
                        'worksheet': worksheet_name,
                        'headers': headers,
                        'original_data': data_rows,
                        'timestamp': datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                print(f"已備份原始資料到: scripts/{backup_filename}")
                
                # 清除工作表（保留標題）
                worksheet.clear()
                
                # 寫回標題和更新後的資料
                all_updated_values = [headers] + updated_rows
                worksheet.update(all_updated_values)
                
                print(f"✅ 成功更新 {worksheet_name} 工作表")
            elif dry_run:
                print("\n🔍 乾跑模式 - 不會實際更新資料")
                print("如果要執行實際轉換，請使用 --execute 參數")
            else:
                print("沒有需要更新的資料")
                
        except Exception as e:
            print(f"❌ 處理工作表時發生錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self, dry_run=True):
        """執行轉換"""
        print("開始轉換 Google Sheets 時間為台灣時間")
        print(f"模式: {'乾跑測試' if dry_run else '實際執行'}")
        
        # 定義每個工作表的時間欄位
        worksheets_config = [
            {
                'name': OUTPUT_WORKSHEET_NAME,
                'time_columns': ['時間', '收集時間']
            },
            {
                'name': ALL_POSTS_WORKSHEET_NAME,
                'time_columns': ['收集時間', '貼文時間']
            }
        ]
        
        for config in worksheets_config:
            self.convert_worksheet(
                config['name'],
                config['time_columns'],
                dry_run=dry_run
            )
        
        # 顯示轉換日誌摘要
        if self.conversion_log:
            print(f"\n{'='*60}")
            print("轉換日誌摘要（前20條）:")
            print(f"{'='*60}")
            for log in self.conversion_log[:20]:
                print(f"  {log}")
            if len(self.conversion_log) > 20:
                print(f"  ... 還有 {len(self.conversion_log) - 20} 條日誌")

def main():
    parser = argparse.ArgumentParser(description='轉換 Google Sheets 中的時間為台灣時間')
    parser.add_argument('--execute', action='store_true', 
                      help='執行實際轉換（預設為乾跑模式）')
    args = parser.parse_args()
    
    converter = TimeConverter()
    converter.run(dry_run=not args.execute)
    
    if not args.execute:
        print("\n" + "="*60)
        print("提示：這是乾跑模式，沒有實際修改資料")
        print("如果確認要執行轉換，請運行：")
        print("  python scripts/convert_existing_times.py --execute")
        print("="*60)

if __name__ == '__main__':
    main()