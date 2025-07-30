#!/usr/bin/env python3
"""
Prompt優化引擎 - 根據Google Sheets的文字反饋優化AI分析prompt
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from datetime import datetime, timedelta
import logging
import re
from typing import Dict, List
from clients.ai_client import AIClient
from clients.google_sheets_client import GoogleSheetsClient

logger = logging.getLogger(__name__)

class PromptOptimizer:
    def __init__(self):
        self.ai_client = AIClient()
        self.sheets_client = GoogleSheetsClient()
    
    def print_separator(self, title=""):
        """打印分隔線"""
        if title:
            print(f"\n{'='*20} {title} {'='*20}")
        else:
            print("="*60)
    
    def analyze_feedback_patterns(self, days_back: int = 30) -> Dict:
        """分析反饋模式 - 從Google Sheets讀取文字反饋"""
        try:
            self.print_separator("反饋模式分析")
            
            # 從Google Sheets獲取所有已評分的貼文數據
            feedback_data = self.get_feedback_from_sheets(days_back)
            
            if not feedback_data:
                print(f"❌ 最近 {days_back} 天內沒有反饋數據")
                return {}
            
            print(f"📊 分析最近 {days_back} 天內的 {len(feedback_data)} 條反饋")
            
            # 分析偏差模式
            overrated_posts = []  # AI評分過高
            underrated_posts = []  # AI評分過低
            accurate_posts = []   # 評分準確
            text_feedback_list = []  # 所有文字反饋
            
            total_diff = 0
            for feedback in feedback_data:
                try:
                    ai_score = float(feedback['ai_score'])
                    human_score = float(feedback['human_score'])
                    diff = ai_score - human_score
                    total_diff += abs(diff)
                    
                    feedback['score_diff'] = diff
                    
                    # 收集文字反饋
                    if feedback.get('text_feedback'):
                        text_feedback_list.append({
                            'feedback': feedback['text_feedback'],
                            'score_diff': diff,
                            'ai_score': ai_score,
                            'human_score': human_score,
                            'content': feedback.get('content', '')[:100]
                        })
                    
                    if diff > 1:  # AI評分比人工高1分以上
                        overrated_posts.append(feedback)
                    elif diff < -1:  # AI評分比人工低1分以上
                        underrated_posts.append(feedback)
                    else:
                        accurate_posts.append(feedback)
                        
                except (ValueError, TypeError):
                    continue
            
            if len(feedback_data) == 0:
                print("❌ 沒有有效的評分數據")
                return {}
                
            avg_diff = total_diff / len(feedback_data)
            
            analysis = {
                'total_feedbacks': len(feedback_data),
                'avg_difference': avg_diff,
                'overrated_count': len(overrated_posts),
                'underrated_count': len(underrated_posts),
                'accurate_count': len(accurate_posts),
                'overrated_posts': overrated_posts[:5],  # 只保留前5個案例
                'underrated_posts': underrated_posts[:5],
                'accuracy_rate': len(accurate_posts) / len(feedback_data) * 100,
                'text_feedback_list': text_feedback_list
            }
            
            # 顯示分析結果
            print(f"\n📈 分析結果:")
            print(f"   平均評分差異: {avg_diff:.2f}")
            print(f"   準確率: {analysis['accuracy_rate']:.1f}%")
            print(f"   AI評分過高: {len(overrated_posts)} 次")
            print(f"   AI評分過低: {len(underrated_posts)} 次")
            print(f"   評分準確: {len(accurate_posts)} 次")
            print(f"   文字反饋數量: {len(text_feedback_list)} 條")
            
            return analysis
            
        except Exception as e:
            print(f"❌ 分析反饋模式時出錯: {e}")
            return {}
    
    def get_feedback_from_sheets(self, days_back: int = 30) -> List[Dict]:
        """從Google Sheets獲取所有已評分的貼文數據"""
        try:
            from config import OUTPUT_SPREADSHEET_NAME, ALL_POSTS_WORKSHEET_NAME
            from datetime import datetime, timedelta
            
            # 計算時間篩選範圍
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            sheet = self.sheets_client.gc.open(OUTPUT_SPREADSHEET_NAME)
            worksheet = sheet.worksheet(ALL_POSTS_WORKSHEET_NAME)
            all_values = worksheet.get_all_values()
            
            if len(all_values) <= 1:
                return []
            
            headers = all_values[0]
            
            # 找到相關列的索引
            collected_time_idx = headers.index('收集時間') if '收集時間' in headers else -1
            platform_idx = headers.index('平台') if '平台' in headers else -1
            author_idx = headers.index('發文者') if '發文者' in headers else -1
            content_idx = headers.index('原始內容') if '原始內容' in headers else -1
            ai_score_idx = headers.index('AI重要性評分') if 'AI重要性評分' in headers else -1
            human_score_idx = headers.index('人工評分') if '人工評分' in headers else -1
            text_feedback_idx = headers.index('文字反饋') if '文字反饋' in headers else -1
            url_idx = headers.index('原始貼文URL') if '原始貼文URL' in headers else -1
            
            feedback_data = []
            for row in all_values[1:]:
                # 檢查是否有人工評分
                if (len(row) > human_score_idx and 
                    human_score_idx != -1 and 
                    row[human_score_idx] and 
                    row[human_score_idx].strip()):
                    
                    # 檢查時間範圍（如果有收集時間）
                    if collected_time_idx != -1 and len(row) > collected_time_idx and row[collected_time_idx]:
                        try:
                            collected_time = datetime.strptime(row[collected_time_idx], '%Y-%m-%d %H:%M:%S')
                            if collected_time < cutoff_date:
                                continue
                        except (ValueError, TypeError):
                            pass
                    
                    feedback_item = {
                        'collected_time': row[collected_time_idx] if collected_time_idx != -1 and len(row) > collected_time_idx else '',
                        'platform': row[platform_idx] if platform_idx != -1 and len(row) > platform_idx else '',
                        'author': row[author_idx] if author_idx != -1 and len(row) > author_idx else '',
                        'content': row[content_idx] if content_idx != -1 and len(row) > content_idx else '',
                        'ai_score': row[ai_score_idx] if ai_score_idx != -1 and len(row) > ai_score_idx else '',
                        'human_score': row[human_score_idx] if human_score_idx != -1 and len(row) > human_score_idx else '',
                        'text_feedback': row[text_feedback_idx] if text_feedback_idx != -1 and len(row) > text_feedback_idx else '',
                        'url': row[url_idx] if url_idx != -1 and len(row) > url_idx else '',
                    }
                    feedback_data.append(feedback_item)
            
            return feedback_data
            
        except Exception as e:
            print(f"❌ 從Google Sheets獲取反饋數據失敗: {e}")
            return []
    
    def ai_analyze_feedback(self, analysis: Dict) -> str:
        """使用AI分析文字反饋，提取需要注意的要點"""
        try:
            if not analysis.get('text_feedback_list'):
                return "無文字反饋可供分析"
            
            # 準備文字反饋摘要
            feedback_summary = "以下是人工評分者提供的文字反饋：\n\n"
            
            # 按評分差異分組
            high_diff_feedback = []
            low_diff_feedback = []
            accurate_feedback = []
            
            for item in analysis['text_feedback_list']:
                diff = item['score_diff']
                feedback_text = f"- AI評分:{item['ai_score']}, 人工評分:{item['human_score']}, 反饋:\"{item['feedback']}\""
                
                if diff > 1:
                    high_diff_feedback.append(feedback_text)
                elif diff < -1:
                    low_diff_feedback.append(feedback_text)
                else:
                    accurate_feedback.append(feedback_text)
            
            if high_diff_feedback:
                feedback_summary += "AI評分過高的案例：\n" + "\n".join(high_diff_feedback[:5]) + "\n\n"
            
            if low_diff_feedback:
                feedback_summary += "AI評分過低的案例：\n" + "\n".join(low_diff_feedback[:5]) + "\n\n"
            
            if accurate_feedback:
                feedback_summary += "評分準確的案例：\n" + "\n".join(accurate_feedback[:3]) + "\n\n"
            
            # 構建AI分析prompt
            analysis_prompt = f"""
你是一個專業的AI prompt優化分析師。請分析以下人工評分者的文字反饋，並提取需要注意的要點。

{feedback_summary}

統計數據：
- 總反饋數量: {analysis['total_feedbacks']}
- AI評分過高次數: {analysis['overrated_count']} ({analysis['overrated_count']/analysis['total_feedbacks']*100:.1f}%)
- AI評分過低次數: {analysis['underrated_count']} ({analysis['underrated_count']/analysis['total_feedbacks']*100:.1f}%)
- 準確率: {analysis['accuracy_rate']:.1f}%

請基於以上反饋，總結出1-2個最重要的注意事項，這些事項將被添加到評分prompt的底部作為提醒。
請用簡潔的條列式格式回答，每條不超過20個字。

注意事項：
"""
            
            # 調用AI進行分析
            if self.ai_client.api_type == "openai":
                ai_notes = self.ai_client._call_openai(analysis_prompt, max_tokens=300)
            elif self.ai_client.api_type == "anthropic":
                ai_notes = self.ai_client._call_anthropic(analysis_prompt, max_tokens=300)
            else:
                return "AI分析失敗：不支援的API類型"
            
            return ai_notes if ai_notes else "AI分析失敗：無回應"
            
        except Exception as e:
            print(f"❌ AI分析失敗: {e}")
            return f"AI分析錯誤: {str(e)}"
    
    def generate_updated_prompt(self, ai_notes: str) -> str:
        """生成更新後的prompt，只在底部添加AI建議的注意事項"""
        try:
            from config import IMPORTANCE_FILTER_PROMPT
            
            # 保持原有的prompt結構
            base_prompt = IMPORTANCE_FILTER_PROMPT.strip()
            
            # 如果AI提供了注意事項，添加到底部
            if ai_notes and "AI分析" not in ai_notes:
                # 移除prompt中的模板變量部分
                if "{post_content}" in base_prompt:
                    # 找到"{post_content}"之前的部分
                    prompt_parts = base_prompt.split("{post_content}")
                    main_prompt = prompt_parts[0].strip()
                    
                    # 添加AI注意事項
                    updated_prompt = f"{main_prompt}\n\nAI建議注意事項：\n{ai_notes}\n\n貼文內容：\n{{post_content}}"
                    
                    # 如果原prompt有評分部分，確保保留
                    if len(prompt_parts) > 1 and "重要性評分" in prompt_parts[1]:
                        score_part = prompt_parts[1].split("重要性評分")[1]
                        updated_prompt += f"\n\n重要性評分{score_part}"
                    else:
                        updated_prompt += "\n\n重要性評分："
                else:
                    # 如果找不到模板變量，直接在底部添加
                    updated_prompt = f"{base_prompt}\n\nAI建議注意事項：\n{ai_notes}"
            else:
                updated_prompt = base_prompt
            
            return updated_prompt
            
        except Exception as e:
            print(f"❌ 生成更新prompt時出錯: {e}")
            return None
    
    def save_optimization_history(self, analysis: Dict, updated_prompt: str, ai_notes: str, is_active: bool = True) -> bool:
        """保存優化歷史到Google Sheets"""
        try:
            # 準備優化歷史數據
            optimization_data = {
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version_name': f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'total_feedbacks': analysis.get('total_feedbacks', 0),
                'avg_difference': analysis.get('avg_difference', 0),
                'overrated_ratio': analysis.get('overrated_count', 0) / analysis.get('total_feedbacks', 1),
                'underrated_ratio': analysis.get('underrated_count', 0) / analysis.get('total_feedbacks', 1),
                'accuracy_rate': analysis.get('accuracy_rate', 0),
                'main_issues': ai_notes.split('\n') if ai_notes else [],
                'optimization_method': 'AI文字反饋分析',
                'prompt_content': updated_prompt,
                'is_active': is_active,
                'description': f"基於{analysis.get('total_feedbacks', 0)}條文字反饋的優化"
            }
            
            # 寫入Google Sheets
            sheets_success = self.sheets_client.write_prompt_optimization_history(optimization_data)
            
            if sheets_success:
                print(f"✅ 優化歷史已記錄到Google Sheets")
            else:
                print(f"⚠️  無法記錄到Google Sheets")
            
            return sheets_success
            
        except Exception as e:
            print(f"❌ 保存優化歷史時出錯: {e}")
            return False
    
    def update_config_prompt(self, new_prompt: str) -> bool:
        """更新config.py中的IMPORTANCE_FILTER_PROMPT"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
            
            # 讀取config.py
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正則表達式找到IMPORTANCE_FILTER_PROMPT的定義
            # 匹配從 IMPORTANCE_FILTER_PROMPT = 開始到下一個以 """ 結束的部分
            pattern = r'(IMPORTANCE_FILTER_PROMPT\s*=\s*os\.getenv\("IMPORTANCE_FILTER_PROMPT",\s*""")(.*?)("""[^\n]*)'
            
            # 準備替換的內容，確保正確的縮排
            replacement = r'\1\n' + new_prompt + '\n\3'
            
            # 執行替換
            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            
            if new_content == content:
                print("❌ 無法找到IMPORTANCE_FILTER_PROMPT定義")
                return False
            
            # 創建備份
            backup_path = config_path + '.backup'
            import shutil
            shutil.copy2(config_path, backup_path)
            
            # 寫回config.py
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ 已更新config.py中的IMPORTANCE_FILTER_PROMPT")
            print(f"📁 原文件備份至: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ 更新config.py時出錯: {e}")
            return False
    
    def run_optimization_workflow(self, days_back: int = 30, auto_mode: bool = False):
        """運行簡化的優化工作流程"""
        print("🚀 啟動Prompt優化工作流程")
        
        # 1. 分析反饋模式
        analysis = self.analyze_feedback_patterns(days_back)
        
        if not analysis or analysis.get('total_feedbacks', 0) < 5:
            print("❌ 反饋數據不足（至少需要5條），無法進行優化")
            return
        
        # 2. 使用AI分析文字反饋
        self.print_separator("AI分析文字反饋")
        print("🤖 正在分析文字反饋...")
        
        ai_notes = self.ai_analyze_feedback(analysis)
        
        if ai_notes and "AI分析失敗" not in ai_notes:
            print(f"\n🔍 AI識別的注意事項:")
            print(ai_notes)
        else:
            print("❌ AI分析失敗")
            return
        
        # 3. 生成更新的prompt
        self.print_separator("生成優化Prompt")
        updated_prompt = self.generate_updated_prompt(ai_notes)
        
        if not updated_prompt:
            print("❌ 無法生成優化prompt")
            return
        
        print(f"\n📋 更新後的Prompt:")
        print("─" * 60)
        print(updated_prompt)
        print("─" * 60)
        
        # 4. 詢問是否保存
        if auto_mode:
            print("\n🔄 自動模式：正在保存優化結果...")
            
            # 自動保存到Google Sheets
            saved = self.save_optimization_history(analysis, updated_prompt, ai_notes)
            
            if saved:
                print("✅ 優化歷史已保存到Google Sheets")
                
                # 自動更新config.py
                print("🔄 正在更新config.py...")
                config_updated = self.update_config_prompt(updated_prompt)
                
                if config_updated:
                    print("✅ 優化workflow完成！")
                    print("🎯 新的prompt已自動應用到系統")
                else:
                    print("⚠️  優化歷史已保存，但無法自動更新config.py")
                    print("📝 請手動更新config.py中的IMPORTANCE_FILTER_PROMPT")
            else:
                print("❌ 無法保存優化歷史")
        else:
            save_input = input("\n💾 是否保存此優化歷史到Google Sheets? (y/n): ").strip().lower()
            
            if save_input == 'y':
                saved = self.save_optimization_history(analysis, updated_prompt, ai_notes)
                if saved:
                    print("✅ 優化workflow完成！")
                    
                    # 詢問是否自動更新config.py
                    update_config = input("🔄 是否自動更新config.py? (y/n): ").strip().lower()
                    if update_config == 'y':
                        if self.update_config_prompt(updated_prompt):
                            print("🎯 新的prompt已應用到系統")
                        else:
                            print("📝 請手動更新config.py中的IMPORTANCE_FILTER_PROMPT")
                    else:
                        print("📝 請手動更新config.py中的IMPORTANCE_FILTER_PROMPT以應用新prompt")
            else:
                print("📋 優化prompt已生成但未保存")

def main():
    parser = argparse.ArgumentParser(description='Prompt優化引擎 - 基於文字反饋')
    parser.add_argument('--analyze', action='store_true', help='分析反饋模式')
    parser.add_argument('--optimize', action='store_true', help='運行優化工作流程')
    parser.add_argument('--days', type=int, default=30, help='分析天數 (預設30天)')
    parser.add_argument('--auto', action='store_true', help='自動模式，不詢問是否保存')
    
    args = parser.parse_args()
    
    optimizer = PromptOptimizer()
    
    if args.analyze:
        optimizer.analyze_feedback_patterns(days_back=args.days)
    
    elif args.optimize:
        optimizer.run_optimization_workflow(days_back=args.days, auto_mode=args.auto)
    
    else:
        # 如果沒有指定參數，顯示幫助
        print("🤖 Prompt優化引擎 - 基於文字反饋")
        print("\n📋 可用命令:")
        print("   --analyze      分析反饋模式")
        print("   --optimize     運行優化工作流程")
        print("   --days N       設定分析天數（預設30天）")
        print("\n💡 使用範例:")
        print("   python prompt_optimizer.py --analyze")
        print("   python prompt_optimizer.py --optimize")
        print("   python prompt_optimizer.py --optimize --days 7")

if __name__ == "__main__":
    main()