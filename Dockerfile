FROM python:3.9.18-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建空的 .env 文件（雲端部署使用環境變數）
RUN touch .env

# 創建日誌目錄
RUN mkdir -p logs

# 設定環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口（如果需要）
EXPOSE 8080

# 運行數據庫遷移和應用程式
# 使用 set -e 確保任何命令失敗都會停止執行
CMD ["sh", "-c", "set -e && echo '🚀 Starting Railway deployment...' && python force_migration.py && echo '✅ Migration completed, starting main application...' && python main.py --run-once"]