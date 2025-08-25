FROM python:3.9.18-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴和 Node.js
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 驗證 Node.js 安裝
RUN node --version && npm --version

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 安裝 Node.js 服務依賴並建置
RUN if [ -d "node_service" ]; then \
    echo "Installing Node.js service dependencies..." && \
    cd node_service && \
    npm install && \
    cd agent-twitter-client && \
    npm install && \
    npm run build && \
    cd ../..; \
    fi

# 創建空的 .env 文件（雲端部署使用環境變數）
RUN touch .env

# 創建日誌目錄
RUN mkdir -p logs

# 設定環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口（如果需要）
EXPOSE 8080

# 運行Web服務器
CMD ["python", "app.py"]