# 社交媒體追蹤系統

一個自動化的社交媒體內容追蹤和分析系統，支持從 X (Twitter) 和 LinkedIn 收集指定帳號的貼文，使用 AI 進行重要性篩選、內容摘要和轉發內容生成，並將結果自動同步到 Google Sheets。

## 功能特點

- 🔍 **多平台支持**: 支持 X (Twitter) 和 LinkedIn 數據收集
- 📊 **Google Sheets 整合**: 從 Google Sheets 讀取追蹤列表，結果自動寫回
- 🤖 **AI 驅動分析**: 使用 OpenAI 或 Anthropic API 進行重要性評分、內容摘要和轉發內容生成
- ⏰ **定時任務**: 支持每日自動收集和優先帳號監控
- 💾 **數據持久化**: 使用 SQLAlchemy 進行數據存儲和管理
- 🎛️ **靈活配置**: 所有 AI prompts 和系統參數都可以通過配置文件調整

## 系統架構

```
社交媒體追蹤系統/
├── clients/                    # API 客戶端
│   ├── google_sheets_client.py # Google Sheets API
│   ├── x_client.py            # X (Twitter) API
│   ├── linkedin_client.py     # LinkedIn API
│   └── ai_client.py           # AI 分析服務
├── services/                  # 業務邏輯
│   ├── post_collector.py      # 貼文收集服務
│   └── scheduler.py           # 定時任務調度
├── models/                    # 數據模型
│   └── database.py            # 數據庫模型和管理
├── config.py                  # 配置管理
├── main.py                    # 主程序
└── requirements.txt           # 依賴包
```

## 安裝和設置

### 1. 環境準備

```bash
# 克隆或下載項目
cd "Mafia socia media tracking"

# 安裝依賴
pip install -r requirements.txt
```

### 2. 配置環境變量

```bash
# 複製配置文件模板
cp .env.example .env

# 編輯 .env 文件，配置以下API密鑰：
# - GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH
# - X_API_BEARER_TOKEN
# - AI_API_KEY (OpenAI 或 Anthropic)
```

### 3. Google Sheets API 設置

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 創建項目
2. 啟用 Google Sheets API 和 Google Drive API
3. 創建服務帳號並下載 JSON 憑證文件
4. 將憑證文件放在 `credentials/` 目錄
5. 與目標 Google Sheets 共享服務帳號的郵箱地址

### 4. 社交媒體 API 設置

#### X (Twitter) API
1. 在 [Twitter Developer Portal](https://developer.twitter.com/) 申請 API 訪問
2. 獲取 Bearer Token
3. 配置到 `.env` 文件

#### LinkedIn API
LinkedIn API 訪問受限，建議使用第三方服務如：
- ScrapFly
- Bright Data
- Apify

### 5. AI API 設置

支持 OpenAI 和 Anthropic API：

```bash
# OpenAI
AI_API_TYPE=openai
AI_API_KEY=your_openai_api_key

# 或 Anthropic
AI_API_TYPE=anthropic  
AI_API_KEY=your_anthropic_api_key
```

## 使用方法

### 基本命令

```bash
# 測試系統連接
python main.py --test

# 手動執行一次完整收集
python main.py --run-once

# 啟動定時任務調度器
python main.py --start-scheduler

# 只收集特定平台數據
python main.py --platform twitter
python main.py --platform linkedin

# 查看統計信息
python main.py --stats

# 查看幫助
python main.py --help
```

### Google Sheets 格式

#### 輸入表格 (帳號列表)
需要包含以下欄位：
- `platform`: 平台名稱 (twitter/linkedin)
- `username`: 用戶名
- `display_name`: 顯示名稱
- `category`: 分類
- `priority`: 優先級 (high/medium/low)
- `active`: 是否啟用 (true/false)

#### 輸出表格 (分析結果)
系統會自動創建包含以下欄位的結果表：
- 時間、平台、發文者、原始內容
- 摘要內容、重要性評分、轉發內容
- 原始貼文URL、收集時間、分類、狀態

## 配置選項

### AI Prompts 自定義

在 `.env` 文件中可以自定義 AI 分析的提示詞：

```bash
# 重要性篩選提示詞
IMPORTANCE_FILTER_PROMPT="你的自定義提示詞..."

# 摘要生成提示詞  
SUMMARIZATION_PROMPT="你的自定義提示詞..."

# 轉發內容生成提示詞
REPOST_GENERATION_PROMPT="你的自定義提示詞..."
```

### 系統參數

```bash
# 重要性篩選閾值 (1-10)
IMPORTANCE_THRESHOLD=6

# 定時任務時間
COLLECTION_SCHEDULE_HOUR=9
COLLECTION_SCHEDULE_MINUTE=0

# 日誌級別
LOG_LEVEL=INFO
```

## 定時任務

系統支持以下定時任務：

- **每日收集**: 每天指定時間執行完整的貼文收集和分析
- **優先監控**: 每小時檢查高優先級帳號的新貼文
- **手動任務**: 支持一次性手動執行任務

## 數據流程

1. **帳號同步**: 從 Google Sheets 讀取追蹤帳號列表
2. **貼文收集**: 使用各平台 API 獲取最新貼文
3. **去重處理**: 避免重複處理相同貼文
4. **AI 分析**: 
   - 重要性評分 (1-10)
   - 內容摘要生成
   - 轉發內容創建
5. **數據存儲**: 保存到本地數據庫
6. **結果輸出**: 重要貼文寫入 Google Sheets

## 監控和日誌

- 系統運行日誌保存在 `logs/` 目錄
- 數據庫記錄處理過程和錯誤信息
- 支持查看實時統計信息

## 故障排除

### 常見問題

1. **API 限制**: 各平台都有 API 調用限制，系統已實現速率控制
2. **LinkedIn 訪問**: LinkedIn API 限制較嚴，建議使用第三方服務
3. **AI API 錯誤**: 檢查 API 密鑰和餘額，系統有重試機制
4. **Google Sheets 權限**: 確保服務帳號有表格的編輯權限

### 調試模式

```bash
# 設置調試級別日誌
export LOG_LEVEL=DEBUG
python main.py --test
```

## 擴展開發

系統採用模組化設計，可以輕鬆擴展：

- 添加新的社交媒體平台支持
- 自定義 AI 分析邏輯
- 整合更多輸出格式
- 添加新的監控和警報功能

## 授權

本項目僅供學習和研究使用。使用時請遵守各平台的服務條款和 API 使用政策。

## 技術支持

如果遇到問題，請檢查：
1. 所有 API 密鑰是否正確配置
2. 網路連接是否正常
3. 相關服務是否有餘額或權限
4. 查看日誌文件獲取詳細錯誤信息