# 更安全的 X/Twitter 數據收集方案

**✅ 重要更新**: Nitter 方案現已完全整合到主系統中，作為預設的首選方案！

## 方案一：使用第三方數據服務

### 1. Apify Twitter Scraper
- **優點**: 專業維護、穩定可靠、不需要自己的帳號
- **缺點**: 需要付費（但比官方 API 便宜很多）
- **價格**: 約 $49/月 可抓取 100k 推文
- **網址**: https://apify.com/quacker/twitter-scraper

### 2. Bright Data (前 Luminati)
- **優點**: 提供現成的 Twitter 數據集、合法合規
- **缺點**: 較貴
- **特點**: 提供數據收集服務，不需要自己實現

### 3. ScraperAPI
- **優點**: 處理所有反檢測、代理輪換
- **價格**: $49/月起
- **API 調用**: 簡單的 HTTP 請求即可

## 方案二：公開數據源

### 1. Nitter 實例（免費）✅ 已整合
**現在是系統的預設首選方案！**

系統現在自動使用以下 Nitter 實例：
- https://twitt.re
- https://xcancel.com  
- https://nitter.pek.li
- https://nitter.aishiteiru.moe
- https://nitter.aosus.link
- 以及其他可用實例

**使用方法**: 無需額外配置，系統會自動檢測並使用可用實例。

### 2. RSS 訂閱
- 某些 Nitter 實例提供 RSS
- 格式: `https://nitter.net/{username}/rss`

## 方案三：混合策略 ✅ 已實現

**系統現在自動實現了混合策略！**

### 當前實施的自動優先順序：
1. **✅ Nitter 實例 (已整合)**
   - 系統自動檢測可用實例
   - 完全免費且安全
   - 無需任何配置

2. **✅ 爬蟲備用 (已整合)**
   - 當 Nitter 不可用時自動啟用
   - 需要配置 `USE_X_SCRAPER=true`

3. **✅ API 最後備案 (已整合)**
   - 當前兩種方案都失敗時使用
   - 需要有效的 Twitter API Bearer Token

### 自定義優先順序
```bash
# 完全使用免費方案
TWITTER_CLIENT_PRIORITY=nitter

# 使用混合策略（推薦）
TWITTER_CLIENT_PRIORITY=nitter,scraper,api

# 只使用付費 API
TWITTER_CLIENT_PRIORITY=api
```

## 方案四：社群合作

### 1. 數據交換
- 與其他研究者交換數據
- 建立數據共享聯盟

### 2. 分散式收集
- 多人各自收集一部分
- 匯總後共享

## 實現建議

### 1. 修改架構支援多數據源
```python
class DataCollectorFactory:
    def get_collector(self, priority_list):
        """按優先級嘗試不同的數據源"""
        for source in priority_list:
            if source == "nitter":
                return NitterCollector()
            elif source == "apify":
                return ApifyCollector()
            elif source == "scraper":
                return XScraperClient()
```

### 2. 實現 Nitter 收集器
```python
class NitterCollector:
    def __init__(self):
        self.instances = NITTER_INSTANCES
        
    def get_user_tweets(self, username):
        for instance in self.instances:
            try:
                # 使用 requests 或 httpx
                response = requests.get(f"{instance}/{username}")
                # 解析 HTML
                return self.parse_nitter_page(response.text)
            except:
                continue
        return []
```

### 3. 實現 Apify 收集器
```python
class ApifyCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def get_user_tweets(self, username):
        # 調用 Apify API
        actor_url = "https://api.apify.com/v2/acts/quacker~twitter-scraper/runs"
        # ... API 調用邏輯
```

## 風險最小化策略

如果必須使用自己的爬蟲：

### 1. 帳號準備
- 使用**老帳號**（至少 1 年以上）
- 購買**已驗證帳號**（有手機號碼）
- 準備**犧牲帳號**（預期會被封）
- **不要使用個人帳號**

### 2. 行為模擬
- 每天登入前先「正常瀏覽」10-15 分鐘
- 隨機點讚、轉推一些內容
- 模擬真實用戶的瀏覽路徑
- 週末減少活動

### 3. 技術措施
```python
# 更激進的反檢測設置
SCRAPER_CONFIG = {
    "min_delay": 10,  # 增加到 10 秒
    "max_delay": 30,  # 增加到 30 秒
    "daily_limit": 50,  # 大幅降低每日限制
    "use_residential_proxy": True,  # 必須使用住宅代理
    "random_break": True,  # 隨機休息 1-2 小時
}
```

### 4. 監控和應對
- 監控帳號狀態
- 發現異常立即停止
- 準備備用方案
- 記錄詳細日誌

## 法律和道德考慮

### 1. 遵守服務條款
- X 的 ToS 明確禁止自動化抓取
- 違反可能面臨法律風險

### 2. 尊重隱私
- 只收集公開數據
- 不收集私人信息
- 遵守 GDPR 等法規

### 3. 負責任使用
- 限制請求頻率
- 不影響服務穩定性
- 考慮數據主體權益

## 結論 ✅ 已實現

**系統現在自動實現了最安全的方案組合！**

### 當前狀態：
1. **✅ Nitter 優先** - 已整合，自動使用
2. **✅ 智能切換** - 失敗時自動嘗試其他方案  
3. **✅ 多源備份** - Nitter → Scraper → API

### 推薦使用方式：
- **大多數用戶**: 直接使用，系統會自動選擇 Nitter
- **高穩定性需求**: 配置爬蟲或 API 作為備用
- **特殊需求**: 通過 `TWITTER_CLIENT_PRIORITY` 自定義優先順序

**現在無需手動實現多源系統 - 已經內建完成！** 🎉