# 社交媒體追蹤系統

一個自動化的社交媒體內容追蹤和分析系統，支持從 X (Twitter) 和 LinkedIn 收集指定帳號的貼文，使用 AI 進行重要性篩選、內容摘要和轉發內容生成，並將結果自動同步到 Google Sheets。

## 功能特點

- 🔍 **多平台支持**: 支持 X (Twitter) 和 LinkedIn 數據收集
- 🔄 **智能切換**: 自動在 Apify → Nitter 間切換，確保穩定收集
- 📊 **Google Sheets 整合**: 從 Google Sheets 讀取追蹤列表，結果自動寫回
- 🤖 **AI 驅動分析**: 使用 OpenAI 或 Anthropic API 進行重要性評分、內容摘要和轉發內容生成
- 📱 **Telegram 通知**: 自動發送每日報告到 Telegram，帳號名稱可直接點擊
- ⏰ **定時任務**: 支持每日自動收集和報告推送
- 💾 **數據持久化**: 使用 SQLAlchemy 進行數據存儲和管理
- 🎯 **智能優化**: 基於人工反饋自動優化 AI 評分準確性
- 🎛️ **靈活配置**: 所有 AI prompts 和系統參數都可以通過配置文件調整

## 系統架構

```
社交媒體追蹤系統/
├── clients/                    # API 客戶端
│   ├── apify_twitter_client.py # Apify Twitter 爬蟲 (主要)
│   ├── nitter_client.py       # Nitter (免費備用)
│   ├── google_sheets_client.py # Google Sheets API
│   ├── linkedin_client.py     # LinkedIn API
│   ├── ai_client.py           # AI 分析服務
│   └── telegram_client.py     # Telegram Bot 通知
├── services/                  # 業務邏輯
│   ├── post_collector.py      # 貼文收集服務
│   ├── scheduler.py           # 定時任務調度
│   └── report_generator.py    # Telegram 報告生成
├── models/                    # 數據模型
│   └── database.py            # 數據庫模型和管理
├── app.py                     # Web 服務 (Railway 部署用)
├── config.py                  # 配置管理
├── main.py                    # CLI 主程序
└── requirements.txt           # Python 依賴包
```

## 核心工作流程

1. **每日收集**: `main.py` 使用 Apify 自動收集社交媒體貼文
2. **智能切換**: 遇到限制時自動在 Apify → Nitter 間切換
3. **數據處理**: 統一數據格式，修正欄位映射，確保數據庫兼容性
4. **AI 分析**: 使用 AI 評分貼文重要性（1-10分）並生成摘要
5. **數據存儲**: 結果同時寫入數據庫和 Google Sheets
6. **Telegram 報告**: 自動生成並發送每日重要貼文報告（含可點擊連結）
7. **人工反饋**: 在 Google Sheets 中提供評分和文字反饋

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
# =============================================================================
# 機密資訊 - 必須設定
# =============================================================================

# AI API 配置 (必需)
AI_API_KEY=your_openai_api_key

# Google Sheets 服務帳號路徑
GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH=credentials/service-account.json

# =============================================================================
# Telegram Bot 配置 (可選 - 用於每日報告)
# =============================================================================

# Telegram Bot Token (從 @BotFather 獲取)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Telegram Chat ID (您的聊天 ID 或群組 ID)
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 是否啟用 Telegram 通知
TELEGRAM_ENABLED=true

# =============================================================================
# Apify 配置 (推薦 - 穩定可靠)
# =============================================================================

# Apify API Token (從 apify.com 獲取)
APIFY_API_TOKEN=your_apify_api_token

# =============================================================================
# 備用配置
# =============================================================================

# LinkedIn API (可選)
LINKEDIN_API_KEY=your_linkedin_api_key
```

**重要說明**: 

### Apify 配置 (推薦)
1. 前往 [Apify](https://apify.com) 註冊帳號
2. 在 Settings → Integrations 獲取 API Token
3. 設定 `APIFY_API_TOKEN` 環境變數
4. 系統會自動使用 Apify 作為首選 Twitter 數據來源

**客戶端優先順序** (可在 `config.py` 的 `TWITTER_CLIENT_PRIORITY` 調整):
   - 第一優先：Apify (推薦，穩定可靠)
   - 第二備案：Nitter 公開實例 (免費，但可能不穩定)

### 3. Google Sheets API 設置

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 創建項目
2. 啟用 Google Sheets API 和 Google Drive API
3. 創建服務帳號並下載 JSON 憑證文件
4. 將憑證文件放在 `credentials/` 目錄
5. 與目標 Google Sheets 共享服務帳號的郵箱地址

### 5. Telegram Bot 設置 (可選)

如果您想接收每日報告，可以設置 Telegram Bot：

1. 在 Telegram 中找到 @BotFather
2. 使用 `/newbot` 命令創建新 Bot
3. 獲取 Bot Token 並設置到 `TELEGRAM_BOT_TOKEN`
4. 獲取您的 Chat ID 並設置到 `TELEGRAM_CHAT_ID`
5. 設置 `TELEGRAM_ENABLED=true`

## Twitter 數據收集方式

系統支援兩種 Twitter 數據收集方式，並按以下優先順序自動選擇：

### 1. 🚀 Apify Twitter Scraper (首選 - 穩定可靠)
- **優點**: 穩定可靠、支援批次查詢、無需維護帳號登入
- **缺點**: 需要 Apify API Token，按使用量計費
- **適用**: 推薦作為首選，特別適用於生產環境
- **配置**: 設定 `APIFY_API_TOKEN` 環境變數

### 2. 🆓 Nitter (備用 - 免費)
- **優點**: 完全免費、無需帳號、不會被封鎖、零風險
- **缺點**: 依賴公開 Nitter 實例的可用性，速度較慢
- **適用**: Apify 不可用時的免費備用方案

### 智能切換邏輯
```
1. Apify → 檢查 API Token → 有效則使用
2. Apify 失敗 → Fallback 到 Nitter → 檢測可用實例 → 成功則使用

特殊情況處理：
- API 錯誤或超時 → 自動切換到 Nitter
- 所有客戶端都失敗 → 記錄錯誤並繼續處理其他帳號
```

## 使用方法

### 主要命令

```bash
# 手動執行一次完整收集（含 AI 分析和 Telegram 報告）
python main.py --run-once

# 啟動定時任務調度器（每日自動執行）
python main.py --start-scheduler

# 啟動 Web 服務器（用於 Railway 部署）
python main.py --web-server

# 只收集特定平台數據
python main.py --platform twitter

# 測試 Telegram Bot 連接和報告功能
python main.py --test-telegram

# 查看統計信息
python main.py --stats

# 查看 API 使用統計
python main.py --api-stats

# 測試系統連接
python main.py --test
```

## Railway 雲端部署

系統支援部署到 Railway 雲端平台，實現每天自動執行：

### 🚀 快速部署

1. **準備憑證**: 將 Google Service Account JSON 轉為 base64
   ```bash
   base64 -i credentials/service-account.json | tr -d '\n'
   ```

2. **Railway 部署**: 
   - 前往 [Railway](https://railway.app)
   - 選擇從 GitHub 部署此倉庫
   - 添加 PostgreSQL 數據庫插件

3. **配置環境變數**:
   ```bash
   GOOGLE_SHEETS_CREDENTIALS_BASE64=<base64編碼的憑證>
   AI_API_KEY=<OpenAI或Anthropic API Key>
   # 其他必要的API Keys...
   ```

4. **設定 GitHub Actions 定時執行**:
   - 在 GitHub 倉庫設定 Railway API Token
   - 系統會每天早上 9:00 CST 自動執行

### 📋 詳細說明

請參考 [Railway 部署指南](RAILWAY_DEPLOYMENT.md) 獲取完整的部署說明。

### ✨ 雲端部署優勢

- 🕘 **自動定時執行**: 每天 9:00 自動收集數據
- 💾 **PostgreSQL 數據持久化**: 資料安全保存
- 📊 **即時監控**: Railway 控制台查看執行狀態  
- 🆓 **免費額度**: 每月 500 小時免費運行時間
- 🔄 **自動重啟**: 失敗時自動重試

### Prompt 優化工作流程

1. **提供反饋**: 在 "All Posts & AI Scores" 工作表中添加人工評分和文字反饋
2. **分析反饋**: `python prompt_optimizer.py --analyze`
3. **自動優化**: `python prompt_optimizer.py --optimize --auto`
4. **應用更新**: 優化後的 prompt 會自動更新到系統配置

## 新增功能介紹

### 📱 Telegram 智能報告

- **每日自動報告**: 收集完成後自動發送重要貼文摘要到 Telegram
- **可點擊連結**: 帳號名稱 @username 變成可點擊的 Twitter 連結
- **AI 智能摘要**: 使用 AI 生成簡潔的重點摘要
- **統計數據**: 包含收集成功率、重要貼文數量等統計
- **自動分割**: 超過 Telegram 字數限制時自動分割發送

### 🔍 數據收集功能

- **數據驗證**: 在數據庫儲存前驗證必要欄位，防止錯誤
- **容错機制**: 缺少欄位時使用預設值進行填補
- **一致格式**: 所有收集方法使用統一的數據格式

### 🌐 雲端部署優化

- **Railway 支援**: 完整支援 Railway PostgreSQL 部署
- **環境變數檢測**: 自動檢測雲端和本地環境
- **資料庫遷移**: 自動處理資料庫架構更新
- **日誌優化**: 雲端環境下的日誌和監控優化

## 系統配置

### 重要參數

```bash
# 重要性篩選闾值（只有 ≥ 此分數的貼文會進入 Analyzed Posts）
IMPORTANCE_THRESHOLD=8

# 定時任務時間 (CST 時區)
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
3. **檢查日誌**: 查看 `logs/social_media_tracker.log` 了解系統狀態

### 常見問題排除

#### 🚀 Apify 問題
1. **API Token 無效**:
   - 檢查 `APIFY_API_TOKEN` 是否正確設定
   - 確認 Apify 帳號餘額充足

2. **請求超時**:
   - 系統會自動 Fallback 到 Nitter
   - 可調整 `APIFY_TIMEOUT` 參數

#### 🆓 Nitter 問題
3. **Nitter 實例不可用**:
   - 系統會自動測試多個實例並選擇最佳的
   - 可在 `config.py` 中更新 Nitter 實例列表

#### 📱 Telegram 問題
5. **Telegram 報告未收到**:
   - 使用 `python main.py --test-telegram` 測試連接
   - 檢查 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 設定
   - 確認 Bot 已被添加到指定的聊天或群組

6. **連結無法點擊**:
   - 確認 Telegram 客戶端支援 HTML 格式
   - 檢查是否有特殊字元導致 HTML 解析錯誤

#### 其他問題
7. **AI API 錯誤**: 檢查 API 密鑰和餘額
8. **Google Sheets 權限**: 確保服務帳號有表格的編輯權限
9. **數據同步問題**: 檢查 `logs/social_media_tracker.log` 了解詳細錯誤

## 技術支持

如果遇到問題，請檢查：
1. 所有 API 密鑰是否正確配置
2. 網路連接是否正常
3. 相關服務是否有餘額或權限
4. 查看日誌文件獲取詳細錯誤信息

## 授權

本項目僅供內部使用。使用時請遵守各平台的服務條款和 API 使用政策。