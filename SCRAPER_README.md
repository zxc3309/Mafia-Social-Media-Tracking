# X/Twitter 爬蟲使用指南

本系統支援使用網頁爬蟲作為 Twitter 數據收集的**第二選擇**，當免費的 Nitter 服務不可用時自動啟用。

## 📋 系統優先順序

1. **🆓 Nitter (首選)** - 免費、安全、無需帳號
2. **🕷️ 網頁爬蟲 (本指南)** - 需要帳號，但比 API 便宜
3. **📡 官方 API (最後備案)** - 最可靠但有速率限制

**注意**: 系統會自動按優先順序選擇可用的方法，通常無需手動配置爬蟲。

## 功能特點

### 反檢測機制
1. **瀏覽器指紋隨機化**
   - 隨機 User Agent
   - 隨機視窗大小和解析度
   - 隨機時區和語言設置
   - 覆蓋自動化檢測標記

2. **人類行為模擬**
   - 隨機延遲（3-10秒）
   - 模擬滑鼠移動
   - 模擬滾動行為
   - 隨機瀏覽模式

3. **代理輪換支援**
   - 支援 HTTP/HTTPS 代理
   - 自動輪換代理
   - 建議使用住宅代理

4. **帳號輪換**
   - 支援多帳號配置
   - Cookie 持久化
   - 自動登入管理

5. **速率限制**
   - 每日抓取限制
   - 請求間隔控制
   - 自動暫停機制

## 安裝設置

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 設置爬蟲環境
```bash
python setup_scraper.py
```

### 3. 配置環境變數
編輯 `.env` 文件，添加以下配置：

**注意**: 只有當 Nitter 服務不穩定或無法使用時才需要配置爬蟲。

```env
# 啟用爬蟲模式
USE_X_SCRAPER=true

# 爬蟲帳號（格式: username:password,username2:password2）
X_SCRAPER_ACCOUNTS=your_username:your_password

# 可選配置
SCRAPER_HEADLESS=true  # 無頭模式（建議 true）
SCRAPER_MIN_DELAY=3    # 最小延遲秒數
SCRAPER_MAX_DELAY=10   # 最大延遲秒數
SCRAPER_DAILY_LIMIT=500  # 每日限制

# 代理配置（可選）
SCRAPER_PROXY_ENABLED=true
SCRAPER_PROXY_LIST=http://proxy1:port,http://proxy2:port

# Nitter 實例（備用方案）
NITTER_INSTANCES=https://nitter.net,https://nitter.it
```

## 使用方法

### 1. 測試爬蟲
```bash
# 使用爬蟲收集數據
python main.py --run-once

# 只收集 Twitter 數據
python main.py --platform twitter
```

### 2. 切換模式
- **使用 API**: 設置 `USE_X_SCRAPER=false`
- **使用爬蟲**: 設置 `USE_X_SCRAPER=true`

## 最佳實踐

### 1. 帳號準備
- 使用老帳號（建議超過6個月）
- 避免使用新註冊帳號
- 準備多個備用帳號
- 定期更換帳號

### 2. 代理選擇
- **住宅代理**（推薦）: 檢測率最低
- **數據中心代理**: 便宜但易被檢測
- **免費代理**: 不建議使用

### 3. 抓取策略
- 控制每日抓取量（建議 < 500）
- 隨機化抓取順序
- 避免固定時間模式
- 定期暫停和休息

### 4. Cookie 管理
- Cookie 自動保存在 `scraper_cookies/` 目錄
- 定期清理過期 Cookie
- 不要共享 Cookie 文件

## 故障排除

### 1. 登入失敗
- 檢查帳號密碼是否正確
- 確認帳號未被封鎖
- 嘗試手動登入確認
- 清除舊 Cookie 重試

### 2. 頻繁被檢測
- 增加請求延遲
- 使用更好的代理
- 減少每日抓取量
- 增加帳號數量

### 3. 數據不完整
- 檢查網頁結構是否變化
- 查看日誌中的錯誤信息
- 嘗試降低抓取速度

## 監控和日誌

爬蟲活動會記錄在日誌中：
```bash
# 查看日誌
tail -f logs/social_media_tracker.log

# 搜索爬蟲相關日誌
grep "scraper" logs/social_media_tracker.log
```

## 注意事項

1. **法律合規**: 確保遵守當地法律和網站服務條款
2. **道德使用**: 不要過度抓取，尊重網站資源
3. **數據安全**: 妥善保管帳號密碼和 Cookie
4. **備份計劃**: 準備 API 作為備用方案

## 進階配置

### 自定義 User Agents
編輯 `user_agents.txt` 文件，每行一個 User Agent。

### 調整反檢測參數
在 `x_scraper_client.py` 中可以調整：
- 瀏覽器啟動參數
- JavaScript 注入腳本
- 請求頭配置

## 性能優化

1. **並行抓取**: 可以運行多個實例，使用不同帳號
2. **緩存優化**: 利用數據庫緩存減少重複抓取
3. **選擇性抓取**: 只抓取最近更新的帳號

## 未來改進

- [ ] 支援更多反檢測技術
- [ ] 實現分散式爬蟲
- [ ] 添加驗證碼處理
- [ ] 支援更多社交平台