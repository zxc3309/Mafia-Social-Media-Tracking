# 社交媒體追蹤系統 - 使用指南

## 快速開始

### 1. 基本設置

```bash
# 1. 進入專案目錄
cd "/Users/weilinchen/Documents/Mafia socia media tracking"

# 2. 執行安裝腳本
python3 setup.py

# 3. 配置 API 密鑰
cp .env.example .env
vim .env  # 編輯配置文件
```

### 2. 必要配置

編輯 `.env` 文件，至少需要配置：

```bash
# Google Sheets 服務帳號憑證路徑
GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH=credentials/service-account.json

# X (Twitter) API Bearer Token
X_API_BEARER_TOKEN=your_twitter_bearer_token

# AI API 配置
AI_API_TYPE=openai  # 或 anthropic
AI_API_KEY=your_api_key

# Google Sheets 表格名稱
INPUT_SPREADSHEET_NAME="Social Media Tracking - Accounts"
OUTPUT_SPREADSHEET_NAME="Social Media Tracking - Results"
```

### 3. Google Sheets 設置

#### 創建輸入表格
創建一個Google Sheets表格，包含以下欄位：

| platform | username | display_name | category | priority | active |
|----------|----------|--------------|----------|----------|--------|
| twitter  | elonmusk | Elon Musk    | tech     | high     | true   |
| twitter  | naval    | Naval        | business | medium   | true   |
| linkedin | satyanadella | Satya Nadella | tech | high | true |

#### 設置服務帳號權限
1. 下載Google Cloud服務帳號JSON文件
2. 放置在 `credentials/service-account.json`
3. 與表格共享服務帳號的郵箱地址（編輯權限）

## 基本使用

### 測試系統連接

```bash
python3 main.py --test
```

預期輸出：
```
=== 測試系統連接 ===
✓ 數據庫連接正常
✓ Google Sheets連接正常 (找到 3 個帳號)
✓ X API配置正常
✓ AI API配置正常 (使用 openai)
```

### 手動執行收集

```bash
python3 main.py --run-once
```

預期輸出：
```
=== 收集結果 ===
追蹤帳號數量: 3
收集到的貼文: 15
分析的貼文: 15
重要貼文: 6
開始時間: 2024-01-20T10:00:00
結束時間: 2024-01-20T10:05:00
```

### 啟動定時任務

```bash
python3 main.py --start-scheduler
```

系統會：
- 每天上午9點執行完整收集
- 每小時檢查高優先級帳號
- 按 Ctrl+C 停止

### 查看統計信息

```bash
python3 main.py --stats
```

預期輸出：
```
=== 系統統計信息 ===
總貼文數量: 150
已分析貼文: 150
重要貼文數量: 45
今日新增貼文: 12

按平台分布:
  twitter: 120 篇
  linkedin: 30 篇

最後更新: 2024-01-20T15:30:00
```

### 單平台收集

```bash
# 只收集 Twitter 數據
python3 main.py --platform twitter

# 只收集 LinkedIn 數據
python3 main.py --platform linkedin
```

## 高級配置

### 自定義 AI Prompts

在 `.env` 文件中自定義分析提示詞：

```bash
# 重要性篩選提示詞
IMPORTANCE_FILTER_PROMPT="請評估以下貼文的商業價值，1-10評分：\n{post_content}\n\n評分："

# 摘要生成提示詞
SUMMARIZATION_PROMPT="請用一句話總結以下內容的核心觀點：\n{post_content}\n\n摘要："

# 轉發內容生成提示詞
REPOST_GENERATION_PROMPT="基於以下內容，寫一個適合商業帳號轉發的短文：\n{post_content}\n\n轉發內容："
```

### 調整篩選閾值

```bash
# 只有評分6以上的貼文會被標記為重要
IMPORTANCE_THRESHOLD=6

# 調整為更嚴格的篩選（8分以上）
IMPORTANCE_THRESHOLD=8
```

### 修改定時任務時間

```bash
# 改為每天下午2點執行
COLLECTION_SCHEDULE_HOUR=14
COLLECTION_SCHEDULE_MINUTE=0
```

## 數據管理

### 查看本地數據庫

系統使用SQLite數據庫存儲數據：

```bash
# 安裝SQLite客戶端
brew install sqlite3  # macOS

# 查看數據庫
sqlite3 social_media_tracking.db

# 查看表格
.tables

# 查看最近的貼文
SELECT * FROM posts ORDER BY collected_at DESC LIMIT 10;

# 查看重要貼文
SELECT * FROM analyzed_posts WHERE importance_score >= 6;
```

### 備份數據

```bash
# 備份數據庫
cp social_media_tracking.db backup/social_media_tracking_$(date +%Y%m%d).db

# 備份配置
cp .env backup/env_$(date +%Y%m%d).backup
```

## 故障排除

### 常見錯誤及解決方案

#### 1. Google Sheets 權限錯誤
```
Error: 沒有權限訪問 Google Sheets
```

解決方案：
1. 確認服務帳號JSON文件路徑正確
2. 檢查是否與表格共享了服務帳號郵箱
3. 確認表格名稱與配置一致

#### 2. X API 限制
```
Error: Twitter API rate limit reached
```

解決方案：
1. 等待15分鐘後重試
2. 檢查API套餐限制
3. 考慮升級API套餐

#### 3. AI API 錯誤
```
Error: OpenAI API error: Insufficient credits
```

解決方案：
1. 檢查API餘額
2. 確認API密鑰正確
3. 嘗試切換到Anthropic API

#### 4. LinkedIn 數據收集失敗
```
Warning: LinkedIn API access is restricted
```

解決方案：
1. LinkedIn API限制嚴格，屬正常情況
2. 考慮使用第三方服務
3. 或專注於Twitter數據收集

### 調試模式

```bash
# 設置詳細日誌
export LOG_LEVEL=DEBUG

# 運行測試
python3 main.py --test

# 查看日誌文件
tail -f logs/social_media_tracker.log
```

### 性能優化

#### 1. 減少API調用
- 適當增加重要性閾值
- 減少追蹤帳號數量
- 調整收集頻率

#### 2. 優化批次處理
```bash
# 在 .env 中調整批次大小
AI_BATCH_SIZE=3  # 減少同時處理的貼文數量
```

#### 3. 數據庫維護
```bash
# 定期清理舊數據
sqlite3 social_media_tracking.db "DELETE FROM posts WHERE collected_at < datetime('now', '-30 days');"
```

## 部署建議

### 在伺服器上運行

```bash
# 使用 screen 在後台運行
screen -S social_tracker
python3 main.py --start-scheduler

# 離開 screen (Ctrl+A, D)
# 重新連接: screen -r social_tracker
```

### 使用 systemd 服務

創建服務文件 `/etc/systemd/system/social-tracker.service`：

```ini
[Unit]
Description=Social Media Tracker
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/social-tracker
ExecStart=/usr/bin/python3 main.py --start-scheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

啟動服務：
```bash
sudo systemctl enable social-tracker
sudo systemctl start social-tracker
```

## 最佳實踐

1. **定期備份數據和配置**
2. **監控API使用量和餘額**
3. **定期檢查和更新追蹤帳號列表**
4. **適當調整重要性閾值避免信息過載**
5. **使用版本控制管理配置變更**
6. **設置監控和警報機制**

## 擴展功能

系統支持以下擴展：

1. **添加新平台支持**
2. **整合更多AI服務**
3. **支持多種輸出格式**
4. **添加實時通知功能**
5. **整合數據可視化工具**

如需要客製化功能，請參考系統架構文檔進行開發。