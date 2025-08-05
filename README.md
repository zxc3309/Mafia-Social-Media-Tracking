# 社交媒體追蹤系統

一個自動化的社交媒體內容追蹤和分析系統，支持從 X (Twitter) 和 LinkedIn 收集指定帳號的貼文，使用 AI 進行重要性篩選、內容摘要和轉發內容生成，並將結果自動同步到 Google Sheets。

## 功能特點

- 🔍 **多平台支持**: 支持 X (Twitter) 和 LinkedIn 數據收集
- 🆓 **免費優先**: 優先使用免費的 Nitter 服務，無需 API 金鑰
- 🔄 **智能切換**: 自動在 Nitter → Scraper → API 間切換，確保穩定收集
- 📊 **Google Sheets 整合**: 從 Google Sheets 讀取追蹤列表，結果自動寫回
- 🤖 **AI 驅動分析**: 使用 OpenAI 或 Anthropic API 進行重要性評分、內容摘要和轉發內容生成
- ⏰ **定時任務**: 支持每日自動收集
- 💾 **數據持久化**: 使用 SQLAlchemy 進行數據存儲和管理
- 🎯 **智能優化**: 基於人工反饋自動優化 AI 評分準確性
- 🎛️ **靈活配置**: 所有 AI prompts 和系統參數都可以通過配置文件調整

## 系統架構

```
社交媒體追蹤系統/
├── clients/                    # API 客戶端
│   ├── google_sheets_client.py # Google Sheets API
│   ├── nitter_client.py       # Nitter (免費 Twitter 前端)
│   ├── x_client.py            # X (Twitter) API
│   ├── x_scraper_client.py    # X 網頁爬蟲客戶端
│   ├── linkedin_client.py     # LinkedIn API
│   └── ai_client.py           # AI 分析服務
├── services/                  # 業務邏輯
│   ├── post_collector.py      # 貼文收集服務
│   └── scheduler.py           # 定時任務調度
├── models/                    # 數據模型
│   └── database.py            # 數據庫模型和管理
├── config.py                  # 配置管理
├── main.py                    # 主程序
├── prompt_optimizer.py        # AI Prompt 優化工具
├── sync_database_to_sheets.py # 數據庫同步工具
└── requirements.txt           # 依賴包
```

## 核心工作流程

1. **每日收集**: `main.py` 自動收集社交媒體貼文
2. **AI 分析**: 系統使用 AI 評分貼文重要性（1-10分）
3. **數據存儲**: 結果同時寫入數據庫和 Google Sheets
4. **人工反饋**: 在 Google Sheets 中提供評分和文字反饋
5. **智能優化**: `prompt_optimizer.py` 分析反饋並自動優化 AI prompt

## Google Sheets 工作表說明

### 1. Accounts (輸入帳號列表)
- `platform`: 平台名稱 (twitter/linkedin)
- `username`: 用戶名
- `display_name`: 顯示名稱
- `category`: 分類
- `priority`: 優先級 (high/medium/low)
- `active`: 是否啟用 (true/false)

### 2. Analyzed Posts (重要貼文結果)
系統篩選出的重要貼文（評分 ≥ 8 分），包含：
- 時間、平台、發文者、原始內容
- 摘要內容、重要性評分、轉發內容
- 原始貼文URL、收集時間、分類

### 3. All Posts & AI Scores (完整評分數據)
所有貼文及其 AI 評分，支持人工反饋：
- 收集時間、平台、發文者、內容
- AI重要性評分、人工評分、評分差異
- **文字反饋**（用於優化 AI）

### 4. Prompt Optimization History (優化歷史)
記錄 AI prompt 的優化過程和版本變更

## 安裝和設置

### 1. 環境準備

```bash
# 進入項目目錄
cd "Mafia socia media tracking"

# 安裝依賴
pip install -r requirements.txt
```

### 2. 配置環境變量

創建 `.env` 文件並配置以下設置：

```bash
# Google Sheets 服務帳號路徑
GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH=credentials/service-account.json

# Twitter 客戶端優先順序（推薦保持預設值）
TWITTER_CLIENT_PRIORITY=nitter,scraper,api

# AI API (必需)
AI_API_TYPE=openai
AI_API_KEY=your_openai_api_key

# X (Twitter) API (可選，作為最後備案)
X_API_BEARER_TOKEN=your_twitter_bearer_token

# X 爬蟲配置 (可選，當 Nitter 不可用時使用)
USE_X_SCRAPER=false
X_SCRAPER_ACCOUNTS=username1:password1,username2:password2
```

**注意**: 
- 系統現在優先使用免費的 Nitter 服務，通常無需配置 Twitter API
- 只有在 Nitter 不可用且需要爬蟲功能時才需要配置爬蟲帳號
- Twitter API 作為最後的備用方案

### 3. Google Sheets API 設置

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 創建項目
2. 啟用 Google Sheets API 和 Google Drive API
3. 創建服務帳號並下載 JSON 憑證文件
4. 將憑證文件放在 `credentials/` 目錄
5. 與目標 Google Sheets 共享服務帳號的郵箱地址

## Twitter 數據收集方式

系統支援三種 Twitter 數據收集方式，並按以下優先順序自動選擇：

### 1. 🆓 Nitter (首選 - 免費)
- **優點**: 完全免費、無需帳號、不會被封鎖、零風險
- **缺點**: 依賴公開 Nitter 實例的可用性
- **適用**: 大多數使用場景，推薦作為首選

### 2. 🕷️ 網頁爬蟲 (備用)
- **優點**: 不依賴官方 API、成本較低
- **缺點**: 需要 Twitter 帳號、可能被封鎖、需要維護
- **適用**: 當 Nitter 不可用且不想使用 API 時

### 3. 📡 官方 API (最後備案)
- **優點**: 最穩定可靠、官方支持
- **缺點**: 有嚴格的速率限制、需要付費（免費額度很低）
- **適用**: 需要最高穩定性的生產環境

### 自動切換邏輯
```
1. 嘗試 Nitter → 檢測可用實例 → 成功則使用
2. Nitter 失敗 → 檢查爬蟲配置 → 有配置則使用爬蟲
3. 爬蟲失敗/未配置 → 使用 Twitter API (需要有效的 Bearer Token)
```

### 自定義優先順序
可通過 `TWITTER_CLIENT_PRIORITY` 環境變量自定義：
```bash
# 預設順序
TWITTER_CLIENT_PRIORITY=nitter,scraper,api

# 只使用 API (跳過免費方案)
TWITTER_CLIENT_PRIORITY=api

# 爬蟲優先 (不推薦)
TWITTER_CLIENT_PRIORITY=scraper,nitter,api
```

## 使用方法

### 主要命令

```bash
# 手動執行一次完整收集
python main.py --run-once

# 啟動定時任務調度器（每日自動執行）
python main.py --start-scheduler

# 只收集特定平台數據
python main.py --platform twitter

# 查看統計信息
python main.py --stats

# 同步數據庫到 Google Sheets
python sync_database_to_sheets.py

# 分析人工反饋並優化 AI prompt
python prompt_optimizer.py --analyze
python prompt_optimizer.py --optimize --auto
```

### Prompt 優化工作流程

1. **提供反饋**: 在 "All Posts & AI Scores" 工作表中添加人工評分和文字反饋
2. **分析反饋**: `python prompt_optimizer.py --analyze`
3. **自動優化**: `python prompt_optimizer.py --optimize --auto`
4. **應用更新**: 優化後的 prompt 會自動更新到系統配置

## 系統配置

### 重要參數

```bash
# 重要性篩選閾值（只有 ≥ 此分數的貼文會進入 Analyzed Posts）
IMPORTANCE_THRESHOLD=8

# 定時任務時間
COLLECTION_SCHEDULE_HOUR=9
COLLECTION_SCHEDULE_MINUTE=0

# 日誌級別
LOG_LEVEL=INFO
```

### AI Prompt 自定義

系統的 AI 分析行為可以通過修改 `config.py` 中的 prompt 進行調整：
- `IMPORTANCE_FILTER_PROMPT`: 重要性評分標準
- `SUMMARIZATION_PROMPT`: 摘要生成方式
- `REPOST_GENERATION_PROMPT`: 轉發內容風格

## 監控和維護

### 日常操作

1. **查看收集結果**: 檢查 "Analyzed Posts" 工作表中的重要貼文
2. **提供反饋**: 在 "All Posts & AI Scores" 中對 AI 評分提供人工反饋
3. **優化系統**: 定期執行 prompt 優化以提高準確性
4. **檢查日誌**: 查看 `logs/social_media_tracker.log` 了解系統狀態

### 故障排除

#### Twitter 數據收集問題
1. **Nitter 無法使用**: 
   - 檢查網路連接
   - 系統會自動嘗試其他 Nitter 實例
   - 可手動更新 `NITTER_INSTANCES` 環境變量

2. **爬蟲被封鎖**: 
   - 檢查爬蟲帳號狀態
   - 調整 `SCRAPER_MIN_DELAY` 和 `SCRAPER_MAX_DELAY` 增加延遲
   - 考慮使用代理 (`SCRAPER_PROXY_ENABLED=true`)

3. **API 限制**: 
   - 檢查 Twitter API 配額和餘額
   - 調整 `posts_per_request` 和 `request_delay_seconds`

#### 其他常見問題
4. **AI API 錯誤**: 檢查 API 密鑰和餘額
5. **Google Sheets 權限**: 確保服務帳號有表格的編輯權限
6. **數據同步問題**: 使用 `sync_database_to_sheets.py` 手動同步

## 技術支持

如果遇到問題，請檢查：
1. 所有 API 密鑰是否正確配置
2. 網路連接是否正常
3. 相關服務是否有餘額或權限
4. 查看日誌文件獲取詳細錯誤信息

## 授權

本項目僅供內部使用。使用時請遵守各平台的服務條款和 API 使用政策。