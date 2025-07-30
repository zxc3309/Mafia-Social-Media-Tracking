
# Google Sheets 模板設置

## 輸入表格 (追蹤帳號列表)

請創建一個包含以下欄位的Google Sheets表格：

| platform | username | display_name | category | priority | active |
|----------|----------|--------------|----------|----------|--------|
| twitter  | elonmusk | Elon Musk    | tech     | high     | true   |
| twitter  | naval    | Naval        | business | medium   | true   |
| linkedin | satyanadella | Satya Nadella | tech | high | true |

欄位說明：
- platform: 平台名稱 (twitter/linkedin)
- username: 用戶名 (不含@符號)
- display_name: 顯示名稱
- category: 分類標籤
- priority: 優先級 (high/medium/low)
- active: 是否啟用追蹤 (true/false)

## 輸出表格 (分析結果)

系統會自動創建輸出表格，包含以下欄位：
- 時間: 貼文發布時間
- 平台: 來源平台
- 發文者: 用戶名
- 發文者顯示名稱: 顯示名稱
- 原始內容: 貼文原始內容
- 摘要內容: AI生成的摘要
- 重要性評分: 1-10的重要性評分
- 轉發內容: AI生成的轉發內容
- 原始貼文URL: 貼文鏈接
- 收集時間: 數據收集時間
- 分類: 帳號分類
- 狀態: 處理狀態

## 設置步驟

1. 創建Google Sheets文檔
2. 設置輸入表格（按上述格式）
3. 與服務帳號郵箱共享編輯權限
4. 在config.py中配置表格名稱
