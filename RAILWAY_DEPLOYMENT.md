# 🚀 Railway 部署指南

## 概述

本指南將幫助您將社交媒體追蹤系統部署到 Railway，並設定每天早上 9:00 自動執行。

## 準備工作

### 1. 準備 Google Service Account 憑證

1. 將 `credentials/service-account.json` 內容轉換為 base64：
   ```bash
   base64 -i credentials/service-account.json | tr -d '\n'
   ```
2. 複製輸出的 base64 字符串，後面會用到

### 2. 準備必要的 API Keys

確保您有以下 API 憑證：
- Google Sheets 服務帳號憑證 (已轉為 base64)
- OpenAI API Key
- Twitter API Bearer Token (可選)
- Anthropic API Key (可選，如果使用 Claude)

## Railway 部署步驟

### 步驟 1: 創建 Railway 項目

1. 前往 [Railway](https://railway.app)
2. 點擊 "New Project" 
3. 選擇 "Deploy from GitHub repo"
4. 選擇您的 GitHub 倉庫

### 步驟 2: 添加 PostgreSQL 數據庫

1. 在 Railway 項目面板中，點擊 "+ New"
2. 選擇 "Database"
3. 選擇 "PostgreSQL"
4. 等待數據庫創建完成

### 步驟 3: 配置環境變數

在 Railway 項目的 Variables 標籤中添加以下環境變數：

#### 必需的環境變數

```bash
# Google Sheets 憑證 (Base64 編碼)
GOOGLE_SHEETS_CREDENTIALS_BASE64=<your_base64_encoded_service_account_json>

# AI API 配置
AI_API_KEY=<your_openai_or_anthropic_api_key>
AI_API_TYPE=openai

# Twitter API (可選)
X_API_BEARER_TOKEN=<your_twitter_bearer_token>

# LinkedIn API (可選)
LINKEDIN_API_KEY=<your_linkedin_api_key>

# Google Sheets 表格名稱 (如果與預設不同)
INPUT_SPREADSHEET_NAME=Social Media Tracking
OUTPUT_SPREADSHEET_NAME=Social Media Tracking

# 日誌等級 (可選)
LOG_LEVEL=INFO
```

#### 自動配置的環境變數

以下變數由 Railway 自動配置，無需手動設定：
- `DATABASE_URL` - PostgreSQL 連接字符串

### 步驟 4: 設定 GitHub Actions 定時執行

#### 📌 重要：必需的 GitHub Secrets

在 GitHub 倉庫設定中，前往 "Settings" > "Secrets and variables" > "Actions"，添加以下 **必需的** Repository Secrets：

| Secret 名稱 | 說明 | 是否必需 | 獲取方式 |
|------------|------|---------|---------|
| `RAILWAY_TOKEN` | Railway API Token | ✅ 必需 | 見下方說明 |
| `RAILWAY_PROJECT_ID` | Railway 項目 ID | ✅ 必需 | 見下方說明 |
| `RAILWAY_SERVICE_ID` | Railway 服務 ID | ⚠️ 強烈建議 | 見下方說明 |

#### 獲取 Railway API Token

1. 前往 [Railway Account Settings](https://railway.app/account/tokens)
2. 點擊 "Create Token"
3. 給 Token 一個描述性名稱（如 "GitHub Actions"）
4. 複製生成的 Token
5. ⚠️ **重要**：Token 只會顯示一次，請立即保存

#### 獲取 Project ID

1. 打開您的 Railway 項目
2. 點擊項目設置（Settings）
3. 在 URL 中找到項目 ID，格式如：
   ```
   https://railway.app/project/[PROJECT_ID]/settings
   ```
   或在設置頁面的 "Project ID" 欄位中複製

#### 獲取 Service ID

1. 在 Railway 項目中，點擊您部署的服務
2. 點擊服務設置（Settings）
3. 在 "Service ID" 欄位中複製
4. 或使用測試工作流程自動列出所有服務 ID：
   ```bash
   # 在 GitHub Actions 中運行 test-railway-connection.yml
   # 它會列出所有可用的服務及其 ID
   ```

#### 驗證配置

使用提供的測試工作流程驗證配置：

1. 前往 GitHub 倉庫的 "Actions" 標籤
2. 選擇 "Test Railway Connection" 工作流
3. 點擊 "Run workflow"
4. 檢查輸出以確認所有 secrets 都已正確配置

## 部署驗證

### 1. 手動執行測試

部署完成後，您可以：

1. 在 Railway 控制台查看部署日誌
2. 使用 GitHub Actions 手動觸發執行：
   - 前往 GitHub 倉庫的 "Actions" 標籤
   - 選擇 "Daily Social Media Collection" 工作流
   - 點擊 "Run workflow"

### 2. 檢查執行結果

執行完成後檢查：
- Railway 日誌中的執行狀態
- Google Sheets 中是否有新數據
- PostgreSQL 數據庫中的記錄

## 定時執行設定

系統配置為每天早上 9:00 CST 自動執行：

- GitHub Actions 使用 cron: `'0 1 * * *'` (UTC 1:00 = CST 9:00)
- 可在 `.github/workflows/daily-collection.yml` 中修改時間

## 故障排除

### 常見問題及解決方案

#### 1. **"Project Token not found" 錯誤**
**症狀**：GitHub Actions 中 Railway CLI 報告 "Project Token not found"

**原因**：Railway CLI 無法找到項目認證信息

**解決方案**：
- 確保 `RAILWAY_TOKEN` 和 `RAILWAY_PROJECT_ID` 都已設置為 GitHub Secrets
- 運行 test-railway-connection.yml 工作流程驗證配置
- 確認 Token 沒有過期或被撤銷

#### 2. **Railway API "Problem processing request" 錯誤**
**症狀**：使用 Railway API 時收到錯誤響應

**原因**：API 請求格式錯誤或缺少必要參數

**解決方案**：
- 確保 `RAILWAY_SERVICE_ID` 已正確設置
- 驗證 Service ID 是否對應實際存在的服務
- 使用測試工作流程列出所有可用服務

#### 3. **Dockerfile CMD 執行失敗**
**症狀**：Railway 部署成功但執行失敗

**原因**：Dockerfile 中引用了不存在的文件

**解決方案**：
- 已修復：移除了對不存在的遷移腳本的引用
- 確保 main.py 可以正常執行

#### 4. **Google Sheets 憑證錯誤**
**症狀**：無法訪問 Google Sheets

**解決方案**：
- 確保 base64 編碼正確：
  ```bash
  base64 -i credentials/service-account.json | tr -d '\n'
  ```
- 檢查服務帳號是否有權限訪問指定的表格
- 在 Railway 環境變數中設置 `GOOGLE_SHEETS_CREDENTIALS_BASE64`

#### 5. **數據庫連接失敗**
**症狀**：程序無法連接到 PostgreSQL

**解決方案**：
- 確保 PostgreSQL 插件已在 Railway 項目中添加
- 檢查 `DATABASE_URL` 環境變數是否自動生成
- 確認數據庫服務正在運行

#### 6. **GitHub Actions 無法觸發**
**症狀**：定時任務不執行或手動觸發失敗

**解決方案**：
- 檢查所有必需的 GitHub Secrets：
  - `RAILWAY_TOKEN`
  - `RAILWAY_PROJECT_ID`
  - `RAILWAY_SERVICE_ID`
- 確認 cron 表達式正確（UTC 時間）
- 檢查 GitHub Actions 是否在倉庫中啟用

### 查看日誌

- **Railway 日誌**: Railway 控制台 > Deploy > View Logs
- **GitHub Actions 日誌**: GitHub 倉庫 > Actions > 選擇執行記錄

## 成本考量

### Railway 免費額度

- 每月 500 小時運行時間
- 每月 100GB 出站流量
- 1GB RAM / 1 vCPU

### 預估使用量

每日執行一次，每次約 5-10 分鐘：
- 月運行時間：~5 小時
- 在免費額度內

## 監控和維護

### 推薦監控項目

1. **每日執行狀態**
   - 設定 GitHub Actions 失敗通知
   - 監控 Railway 部署狀態

2. **數據質量**
   - 定期檢查 Google Sheets 數據
   - 監控 AI 分析結果

3. **API 使用量**
   - 監控 OpenAI API 使用量
   - 檢查 Twitter API 限制

## 更新和維護

### 代碼更新

1. 推送代碼到 GitHub
2. Railway 會自動部署新版本
3. 檢查部署日誌確認成功

### 數據備份

建議定期備份：
- Google Sheets 數據
- PostgreSQL 數據庫 (可使用 Railway 的備份功能)

## 支援

如遇問題，請查看：
- Railway 文檔：https://docs.railway.app
- 項目 README.md
- GitHub Issues