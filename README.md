# 社交媒體追蹤系統

一個自動化的社交媒體內容追蹤和分析系統，支持從 X (Twitter) 和 LinkedIn 收集指定帳號的貼文，使用 AI 進行重要性篩選、內容摘要和轉發內容生成，並將結果自動同步到 Google Sheets。

## 功能特點

- 🔍 **多平台支持**: 支持 X (Twitter) 和 LinkedIn 數據收集
- 🆓 **免費優先**: 優先使用 X Agent Client，備用 Nitter 服務，無需官方 API 金鑰
- 🔄 **智能切換**: 自動在 Agent → Nitter → API 間切換，確保穩定收集
- 📊 **Google Sheets 整合**: 從 Google Sheets 讀取追蹤列表，結果自動寫回
- 🤖 **AI 驅動分析**: 使用 OpenAI 或 Anthropic API 進行重要性評分、內容摘要和轉發內容生成
- 📱 **Telegram 通知**: 自動發送每日報告到 Telegram，帳號名稱可直接點擊
- ⏰ **定時任務**: 支持每日自動收集和報告推送
- 💾 **數據持久化**: 使用 SQLAlchemy 進行數據存儲和管理
- 🔧 **會話管理**: 智能 Cookie 緩存和跨進程會話共享，減少登入頻率
- 🎯 **智能優化**: 基於人工反饋自動優化 AI 評分準確性
- 🎛️ **靈活配置**: 所有 AI prompts 和系統參數都可以通過配置文件調整

## 系統架構

```
社交媒體追蹤系統/
├── clients/                    # API 客戶端
│   ├── google_sheets_client.py # Google Sheets API
│   ├── nitter_client.py       # Nitter (免費 Twitter 前端)
│   ├── x_agent_client.py      # X Agent (無需官方API)
│   ├── linkedin_client.py     # LinkedIn API
│   ├── ai_client.py           # AI 分析服務
│   └── telegram_client.py     # Telegram Bot 通知
├── services/                  # 業務邏輯
│   ├── post_collector.py      # 貼文收集服務
│   ├── scheduler.py           # 定時任務調度
│   └── report_generator.py    # Telegram 報告生成
├── models/                    # 數據模型
│   └── database.py            # 數據庫模型和管理
├── node_service/              # Node.js 服務
│   ├── twitter_cli.js         # Agent Twitter Client CLI
│   └── agent-twitter-client/  # 編譯後的 Twitter Agent
├── config.py                  # 配置管理
├── main.py                    # 主程序
├── prompt_optimizer.py        # AI Prompt 優化工具
├── sync_database_to_sheets.py # 數據庫同步工具
└── requirements.txt           # 依賴包
```

## 核心工作流程

1. **每日收集**: `main.py` 使用 X Agent Client 或 Nitter 自動收集社交媒體貼文
2. **智能切換**: 遇到限制時自動在 X Agent → Nitter → API 間切換
3. **數據處理**: 統一數據格式，修正欄位映射，確保數據庫兼容性
4. **AI 分析**: 使用 AI 評分貼文重要性（1-10分）並生成摘要
5. **數據存儲**: 結果同時寫入數據庫和 Google Sheets
6. **Telegram 報告**: 自動生成並發送每日重要貼文報告（含可點擊連結）
7. **人工反饋**: 在 Google Sheets 中提供評分和文字反饋
8. **智能優化**: `prompt_optimizer.py` 分析反饋並自動優化 AI prompt

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
# Twitter 認證客戶端配置 (推薦 - 高速且穩定)
# =============================================================================

# Twitter 帳號密碼認證 (X Agent Client) - 最佳選擇
TWITTER_USERNAME=your_twitter_username
TWITTER_PASSWORD=your_twitter_password
TWITTER_EMAIL=your_twitter_email@gmail.com              # 可選，用於 email 驗證
TWITTER_2FA_SECRET=your_totp_secret                 # 可選，用於兩步驟驗證

# 啟用認證客戶端
TWITTER_USE_AUTH_CLIENT=true

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
# 備用配置
# =============================================================================

# X (Twitter) API (最後備案 - 當 auth 和 nitter 都失敗時使用)
X_API_BEARER_TOKEN=your_twitter_api_bearer_token

# LinkedIn API (可選)
LINKEDIN_API_KEY=your_linkedin_api_key
```

**重要說明**: 

### X Agent Client 認證設置
1. **必須設定** (用於登入 Twitter):
   - `TWITTER_USERNAME`: 您的 Twitter 用戶名 (不含 @)
   - `TWITTER_PASSWORD`: 您的 Twitter 密碼

2. **可選設定**:
   - `TWITTER_EMAIL`: 如果 Twitter 要求 email 驗證時需要
   - `TWITTER_2FA_SECRET`: 如果啟用了兩步驟驗證，請提供 TOTP 密鑰

3. **2FA Secret 獲取方法**:
   - 在 Twitter 設定中啟用兩步驟驗證
   - 選擇「身份驗證應用程式」選項
   - 掃描 QR 碼時，記下顯示的密鑰字串

4. **客戶端優先順序**:
   - 第一優先：X Agent Client (推薦，最快最穩定)
   - 第二備案：Nitter 公開實例 (無需帳號，但較慢且不穩定)
   - 最後備案：官方 Twitter API (需要 Bearer Token)

### 3. Node.js 環境設置

X Agent Client 需要 Node.js 環境：

```bash
# 安裝 Node.js 18 或更高版本
node --version  # 應該 >= 18.0.0

# 進入 node_service 目錄安裝依賴
cd node_service
npm install
```

### 4. Google Sheets API 設置

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

系統支援三種 Twitter 數據收集方式，並按以下優先順序自動選擇：

### 1. 🔄 X Agent Client (首選 - 高效穩定)
- **優點**: 高速穩定、智能會話管理、跨進程狀態共享、減少登入頻率
- **缺點**: 需要 Twitter 帳號密碼，可能遇到反機器人檢測
- **適用**: 推薦作為首選，特別適用於高頻率收集
- **功能**: 24小時會話持續、Cookie 緩存、會話狀態檔案共享

### 2. 🆓 Nitter (備用 - 免費)
- **優點**: 完全免費、無需帳號、不會被封鎖、零風險
- **缺點**: 依賴公開 Nitter 實例的可用性，速度較慢
- **適用**: Agent Client 不可用時的穩定備用方案

### 3. 📡 官方 API (最後備案)
- **優點**: 最穩定可靠、官方支持
- **缺點**: 有嚴格的速率限制、需要付費（免費額度很低）
- **適用**: 其他所有方案都不可用時的最終備案

### 智能切換邏輯
```
1. X Agent Client → 檢查認證配置 → 登入成功則使用
2. Agent 失敗 → Fallback 到 Nitter → 檢測可用實例 → 成功則使用
3. Nitter 失敗 → 使用 Twitter API (需要有效的 Bearer Token)

特殊情況處理：
- Twitter Error 399 或反機器人檢測 → 自動 Fallback 到 Nitter
- 會話過期或認證失敗 → 自動重新登入
- 多個帳號同時收集 → 共享會話狀態，減少登入次數
```

### 會話管理功能
新版 X Agent Client 具備智能會話管理：

- **Cookie 緩存**: 登入成功後自動保存 Cookie，下次使用時直接加載
- **會話狀態共享**: 使用 JSON 檔案在不同 CLI 進程間共享登入狀態
- **24小時持續**: 會話有效期 24 小時，適合雲端部署
- **智能重試**: 遇到認證錯誤時自動清理狀態並重新登入
- **分散式部署**: 支持多個 Railway 實例同時使用相同帳號

## 使用方法

### 主要命令

```bash
# 手動執行一次完整收集（含 AI 分析和 Telegram 報告）
python main.py --run-once

# 啟動定時任務調度器（每日自動執行）
python main.py --start-scheduler

# 只收集特定平台數據
python main.py --platform twitter

# 測試 Telegram Bot 連接和報告功能
python main.py --test-telegram

# 查看統計信息
python main.py --stats

# 查看 API 使用統計
python main.py --api-stats

# 同步數據庫到 Google Sheets
python sync_database_to_sheets.py

# 分析人工反饋並優化 AI prompt
python prompt_optimizer.py --analyze
python prompt_optimizer.py --optimize --auto

# 直接測試 X Agent Client 功能
node node_service/twitter_cli.js username 1
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

### 🔧 進階會話管理

- **跨進程狀態共享**: 多個帳號收集時共享相同登入會話
- **24小時會話保持**: 優化為雲端部署環境，減少登入頻率
- **智能重試機制**: 遇到 Error 399 或認證錯誤時自動切換客戶端
- **Cookie 持久化**: 自動保存和加載 Cookie，提高登入效率

### 🔍 改進的數據收集

- **欄位映射修復**: 解決 X Agent Client 數據格式不一致問題
- **數據驗證**: 在數據庫儲存前驗證必要欄位，防止錯誤
- **容错機制**: 缺少欄位時使用預設值進行填補
- **整合進度**: 所有收集方法現在使用一致的數據格式

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

# Twitter 會話管理
TWITTER_COOKIE_CACHE_DAYS=7                         # Cookie 緩存天數
TWITTER_AUTO_REFRESH_SESSION=true                   # 自動刷新會話

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

### 常見問題排除

#### 🔄 X Agent Client 問題
1. **登入失敗 (Login verification failed)**:
   - 檢查 `TWITTER_USERNAME` 和 `TWITTER_PASSWORD` 是否正確
   - 確認帳號未被凍結或限制
   - 如啟用 2FA，檢查 `TWITTER_2FA_SECRET` 設定
   - 系統會自動清理會話狀態並重試

2. **Error 399 或反機器人檢測**:
   - 系統已自動處理，會自動 Fallback 到 Nitter
   - 無需手動介入，等待系統自動復原

3. **post_id 欄位錯誤**:
   - 已修復，系統現在會自動映射欄位名稱
   - 如仍有問題，檢查 Node.js 版本是否 >= 18

#### 🆓 Nitter 問題
4. **Nitter 實例不可用**:
   - 系統會自動測試多個實例並選擇最佳的
   - 如所有實例都失效，會自動切換到 X Agent Client

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
9. **數據同步問題**: 使用 `sync_database_to_sheets.py` 手動同步

## 技術支持

如果遇到問題，請檢查：
1. 所有 API 密鑰是否正確配置
2. 網路連接是否正常
3. 相關服務是否有餘額或權限
4. 查看日誌文件獲取詳細錯誤信息

## 授權

本項目僅供內部使用。使用時請遵守各平台的服務條款和 API 使用政策。