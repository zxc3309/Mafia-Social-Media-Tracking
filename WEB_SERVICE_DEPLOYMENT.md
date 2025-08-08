# 🌐 Web Service Deployment Guide

## 概述

新的部署方式將應用轉換為**持續運行的Web服務**，內建自動排程功能。這解決了之前所有的觸發問題！

## ✨ 新架構特點

- ✅ **持續運行** - 不需要外部觸發部署
- ✅ **內建排程** - APScheduler自動在每天9:00執行
- ✅ **Web API** - 提供手動觸發和狀態查詢
- ✅ **Railway友好** - 設計用於雲端長期運行
- ✅ **低資源使用** - 空閒時僅使用~50MB記憶體

## 🚀 部署步驟

### 1. 推送更新到GitHub
所有新代碼已經準備好，只需推送：

```bash
git add -A
git commit -m "Transform to web service with built-in scheduler"
git push origin main
```

### 2. Railway會自動重新部署
- Railway檢測到代碼變更
- 自動使用新的Dockerfile
- 服務將以Web模式啟動

### 3. 設置GitHub Secret
在GitHub倉庫設置中添加：

| Secret名稱 | 值 | 說明 |
|------------|----|----|
| `RAILWAY_SERVICE_URL` | `https://your-service.railway.app` | Railway服務URL |

獲取Railway URL：
1. 打開Railway項目
2. 點擊你的服務
3. 在"Deployments"或"Settings"中找到服務URL

### 4. 測試設置
運行GitHub Action："Daily Collection - Webhook Trigger"

## 📋 可用端點

部署完成後，你的服務將提供以下API：

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 健康檢查和基本信息 |
| `/health` | GET | 系統健康狀態 |
| `/status` | GET | 詳細系統狀態和統計 |
| `/trigger` | POST | 手動觸發數據收集 |
| `/trigger-sync` | POST | 同步觸發（等待完成） |
| `/trigger/twitter` | POST | 只觸發Twitter收集 |
| `/trigger/linkedin` | POST | 只觸發LinkedIn收集 |

## ⏰ 自動排程

服務啟動後會自動：
- 在每天**9:00 AM CST**執行數據收集
- 將結果保存到PostgreSQL數據庫
- 更新Google Sheets

## 🧪 測試方法

### 1. 檢查服務是否運行
```bash
curl https://your-service.railway.app/
```

### 2. 查看系統狀態
```bash
curl https://your-service.railway.app/status
```

### 3. 手動觸發收集
```bash
curl -X POST https://your-service.railway.app/trigger
```

### 4. 查看Railway日誌
在Railway控制台查看實時日誌

## 🔧 本地開發

### 運行Web服務器模式
```bash
python main.py --web-server
```

### 運行一次性收集（開發測試）
```bash
python main.py --run-once
```

### 運行本地排程器
```bash
python main.py --start-scheduler
```

## 🛠️ 故障排除

### 服務無法啟動
- 檢查Railway日誌
- 確認所有環境變數已設置
- 驗證依賴安裝正確

### 排程不執行
- 檢查`/status`端點確認scheduler狀態
- 查看Railway日誌中的錯誤信息
- 確認時區設置正確

### GitHub Action失敗
- 確認`RAILWAY_SERVICE_URL`已設置
- 檢查URL是否正確（不要包含結尾斜線）
- 驗證服務是否可以從外部訪問

## 💡 優勢對比

### 舊方法（觸發部署）
- ❌ 依賴外部觸發
- ❌ API認證問題
- ❌ 每次都重新部署
- ❌ 複雜的工作流

### 新方法（Web服務）
- ✅ 自主運行
- ✅ 簡單HTTP請求
- ✅ 持續運行，立即響應
- ✅ 標準Web服務模式

## 🔄 遷移完成

完成部署後：
1. ✅ 服務24/7運行
2. ✅ 每天9:00自動收集
3. ✅ 可透過API手動觸發
4. ✅ GitHub Actions簡化為HTTP請求
5. ✅ 無需複雜的認證或觸發機制

這個新架構完全解決了之前所有的觸發和認證問題！