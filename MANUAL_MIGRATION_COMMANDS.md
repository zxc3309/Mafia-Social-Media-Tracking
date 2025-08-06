# 手動數據庫遷移指南

如果自動遷移失敗，可以使用以下手動命令修復 PostgreSQL 數據庫架構。

## 問題描述
Railway PostgreSQL 數據庫中的 `analyzed_posts.post_id` 字段類型為 `INTEGER`，但 Twitter post ID 是字符串格式（如 "1953033563881742583#m"），導致插入失敗。

## 解決方案

### 方法1: 修改現有字段類型（推薦）

```sql
-- 1. 連接到 PostgreSQL 數據庫
-- 使用 Railway CLI: railway run psql

-- 2. 檢查當前表結構
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'analyzed_posts';

-- 3. 檢查 post_id 字段類型
SELECT data_type, character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'analyzed_posts' 
AND column_name = 'post_id';

-- 4. 如果是 integer 類型，需要修改（清空數據避免轉換錯誤）
DELETE FROM analyzed_posts;

-- 5. 修改字段類型
ALTER TABLE analyzed_posts ALTER COLUMN post_id TYPE VARCHAR(255);

-- 6. 驗證修改
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'analyzed_posts' 
AND column_name = 'post_id';

-- 7. 測試插入
INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
VALUES ('test_1234567890123456789#m', 'twitter', 'test_1234567890123456789#m', 'test');

-- 8. 清理測試數據
DELETE FROM analyzed_posts WHERE post_id = 'test_1234567890123456789#m';
```

### 方法2: 完全重建表（核心選項）

```sql
-- 1. 備份重要數據（如果有）
CREATE TABLE analyzed_posts_backup AS SELECT * FROM analyzed_posts;

-- 2. 刪除現有表
DROP TABLE IF EXISTS analyzed_posts CASCADE;

-- 3. 重新創建表
CREATE TABLE analyzed_posts (
    id SERIAL PRIMARY KEY,
    post_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    original_post_id VARCHAR(255) NOT NULL,
    author_username VARCHAR(255) NOT NULL,
    author_display_name VARCHAR(255),
    original_content TEXT,
    summary TEXT,
    importance_score REAL,
    repost_content TEXT,
    post_url VARCHAR(500),
    post_time TIMESTAMP,
    collected_at TIMESTAMP,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(100),
    status VARCHAR(50) DEFAULT 'new'
);

-- 4. 測試新表
INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
VALUES ('test_nuclear_1234567890#m', 'twitter', 'test_nuclear_1234567890#m', 'nuclear_test');

-- 5. 驗證並清理
SELECT * FROM analyzed_posts WHERE author_username = 'nuclear_test';
DELETE FROM analyzed_posts WHERE author_username = 'nuclear_test';
```

## Railway CLI 操作步驟

### 1. 安裝 Railway CLI
```bash
npm install -g @railway/cli
```

### 2. 登錄 Railway
```bash
railway login
```

### 3. 連接到項目
```bash
railway link [你的項目ID]
```

### 4. 連接到 PostgreSQL
```bash
railway run psql
```

### 5. 執行遷移命令
在 PostgreSQL shell 中執行上述 SQL 命令。

## 驗證遷移成功

### 檢查字段類型
```sql
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'analyzed_posts' 
AND column_name = 'post_id';
```

預期結果：
```
 column_name |     data_type      | character_maximum_length 
-------------|--------------------|--------------------------
 post_id     | character varying  |                      255
```

### 測試 Twitter ID 插入
```sql
-- 測試插入長 Twitter ID
INSERT INTO analyzed_posts (post_id, platform, original_post_id, author_username)
VALUES ('1953033563881742583#m', 'twitter', '1953033563881742583#m', 'test_twitter_id');

-- 驗證插入成功
SELECT post_id FROM analyzed_posts WHERE author_username = 'test_twitter_id';

-- 清理測試
DELETE FROM analyzed_posts WHERE author_username = 'test_twitter_id';
```

## 自動化腳本

如果你可以上傳文件到 Railway，可以使用以下腳本：

### 使用簡化遷移腳本
```bash
railway run python simple_migration.py
```

### 使用核心選項腳本
```bash
railway run python nuclear_migration.py
```

### 驗證遷移結果
```bash
railway run python deployment_health_check.py
```

## 故障排除

### 如果遇到權限錯誤
確保你有數據庫管理權限，或聯繫項目管理員。

### 如果遇到連接超時
```sql
-- 增加連接超時時間
SET statement_timeout = '30s';
```

### 如果遇到鎖定問題
```sql
-- 檢查活躍連接
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- 必要時終止阻塞連接（謹慎使用）
-- SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND pid != pg_backend_pid();
```

## 完成後

1. 重新部署應用程式
2. 運行測試確保系統正常
3. 檢查日誌確認沒有更多錯誤

遷移完成後，Twitter post ID 將能正常插入數據庫，系統將正常運行。