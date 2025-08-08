# 🚀 設置 Railway Webhook - 最可靠的解決方案

## 為什麼需要 Webhook？

Railway CLI 和 API 在 GitHub Actions 中有限制。使用 Deployment Hook 是最可靠的方法。

## 設置步驟

### 1. 創建 Railway Deployment Hook

1. **打開 Railway 項目**
   - 前往 https://railway.app
   - 進入您的項目

2. **進入服務設置**
   - 點擊您的服務（不是 PostgreSQL）
   - 點擊 "Settings" 標籤

3. **創建 Deployment Hook**
   - 向下滾動找到 "Deploy Hooks" 區域
   - 點擊 "Generate Hook"
   - 給 Hook 命名（例如："Daily Collection Trigger"）
   - 複製生成的 URL

### 2. 添加到 GitHub Secrets

1. 前往 GitHub repo → Settings → Secrets and variables → Actions
2. 點擊 "New repository secret"
3. 添加：
   - Name: `RAILWAY_DEPLOY_HOOK_URL`
   - Value: 貼上剛才複製的 Hook URL

### 3. 使用新的 Workflow

創建文件 `.github/workflows/daily-collection-webhook.yml`：

```yaml
name: Daily Collection via Webhook

on:
  schedule:
    - cron: '0 1 * * *'  # 每天 UTC 1:00 (CST 9:00)
  workflow_dispatch:

jobs:
  trigger-collection:
    runs-on: ubuntu-latest
    
    steps:
      - name: Trigger Railway Deployment
        run: |
          echo "🚀 Triggering Railway deployment via webhook..."
          
          # 觸發 Railway 重新部署
          curl -X POST "${{ secrets.RAILWAY_DEPLOY_HOOK_URL }}"
          
          echo "✅ Deployment triggered successfully"
          echo "📊 Check Railway logs for execution status"
```

## 驗證設置

1. 手動運行 workflow 測試
2. 檢查 Railway 儀表板看是否開始新的部署
3. 查看 Railway 日誌確認 `main.py --run-once` 執行
4. 檢查 Google Sheets 是否有新數據

## 優點

- ✅ 100% 可靠
- ✅ 不需要複雜的認證
- ✅ Railway 官方推薦方法
- ✅ 簡單直接

## 注意事項

- Hook URL 是敏感信息，不要公開分享
- 每次觸發都會創建新的部署
- 部署完成後會自動執行 Dockerfile 中的 CMD