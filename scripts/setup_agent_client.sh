#!/bin/bash

# 設置顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Setting up Twitter Agent Client"
echo "=================================="

# 獲取腳本所在目錄的父目錄（專案根目錄）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NODE_SERVICE_DIR="$PROJECT_ROOT/node_service"
AGENT_CLIENT_DIR="$NODE_SERVICE_DIR/agent-twitter-client"

echo "📍 Project root: $PROJECT_ROOT"
echo ""

# 檢查 Node.js 是否安裝
echo "🔍 Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "Please install Node.js v18 or later from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js ${NODE_VERSION} found${NC}"

# 檢查 npm 是否安裝
echo "🔍 Checking npm installation..."
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm is not installed${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "${GREEN}✓ npm ${NPM_VERSION} found${NC}"
echo ""

# 檢查 node_service 目錄
if [ ! -d "$NODE_SERVICE_DIR" ]; then
    echo -e "${RED}❌ node_service directory not found${NC}"
    echo "Please ensure the integration has been set up correctly"
    exit 1
fi

# 檢查 agent-twitter-client 目錄
if [ ! -d "$AGENT_CLIENT_DIR" ]; then
    echo -e "${RED}❌ agent-twitter-client not found in node_service${NC}"
    echo "Please copy the agent-twitter-client code to $AGENT_CLIENT_DIR"
    exit 1
fi

# 安裝 node_service 依賴
echo "📦 Installing service dependencies..."
cd "$NODE_SERVICE_DIR"
if npm install; then
    echo -e "${GREEN}✓ Service dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install service dependencies${NC}"
    exit 1
fi
echo ""

# 安裝 agent-twitter-client 依賴
echo "📦 Installing agent-twitter-client dependencies..."
cd "$AGENT_CLIENT_DIR"
if npm install; then
    echo -e "${GREEN}✓ agent-twitter-client dependencies installed${NC}"
else
    echo -e "${RED}❌ Failed to install agent-twitter-client dependencies${NC}"
    exit 1
fi
echo ""

# 編譯 TypeScript
echo "🔨 Building agent-twitter-client..."
if npm run build; then
    echo -e "${GREEN}✓ agent-twitter-client built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build agent-twitter-client${NC}"
    exit 1
fi
echo ""

# 檢查 .env 文件
echo "🔍 Checking environment configuration..."
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✓ .env file found${NC}"
    
    # 檢查必要的環境變數
    if grep -q "^TWITTER_USERNAME=" "$ENV_FILE"; then
        echo -e "${GREEN}  ✓ TWITTER_USERNAME is set${NC}"
    else
        echo -e "${YELLOW}  ⚠ TWITTER_USERNAME is not set${NC}"
    fi
    
    if grep -q "^TWITTER_PASSWORD=" "$ENV_FILE"; then
        echo -e "${GREEN}  ✓ TWITTER_PASSWORD is set${NC}"
    else
        echo -e "${YELLOW}  ⚠ TWITTER_PASSWORD is not set${NC}"
    fi
    
    if grep -q "^TWITTER_EMAIL=" "$ENV_FILE"; then
        echo -e "${GREEN}  ✓ TWITTER_EMAIL is set${NC}"
    else
        echo -e "${YELLOW}  ⚠ TWITTER_EMAIL is not set (optional)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Please create a .env file with your Twitter credentials"
fi
echo ""

# 測試服務
echo "🧪 Testing service startup..."
cd "$PROJECT_ROOT"
python3 scripts/manage_agent_service.py test 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Service test passed${NC}"
else
    echo -e "${YELLOW}⚠ Service not running. Starting service...${NC}"
    python3 scripts/manage_agent_service.py start
    
    # 等待服務啟動
    sleep 3
    
    # 再次測試
    python3 scripts/manage_agent_service.py test
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Service started and test passed${NC}"
    else
        echo -e "${RED}❌ Service failed to start${NC}"
        echo "Please check the logs with: python3 scripts/manage_agent_service.py logs"
        exit 1
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Available commands:"
echo "  python3 scripts/manage_agent_service.py start   - Start the service"
echo "  python3 scripts/manage_agent_service.py stop    - Stop the service"
echo "  python3 scripts/manage_agent_service.py status  - Check service status"
echo "  python3 scripts/manage_agent_service.py logs    - View service logs"
echo "  python3 scripts/manage_agent_service.py test    - Test the service"
echo ""
echo "🎯 To use the agent client, ensure 'agent' is in TWITTER_CLIENT_PRIORITY"
echo "   in your config.py or .env file"