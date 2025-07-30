import os
from dotenv import load_dotenv

load_dotenv()

# API Keys 和憑證配置
GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_PATH", "credentials/service-account.json")
X_API_BEARER_TOKEN = os.getenv("X_API_BEARER_TOKEN")
LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_API_TYPE = os.getenv("AI_API_TYPE", "openai")  # "openai" or "anthropic"

# Google Sheets 配置
INPUT_SPREADSHEET_NAME = os.getenv("INPUT_SPREADSHEET_NAME", "Social Media Tracking - Accounts")
OUTPUT_SPREADSHEET_NAME = os.getenv("OUTPUT_SPREADSHEET_NAME", "Social Media Tracking - Results")
INPUT_WORKSHEET_NAME = os.getenv("INPUT_WORKSHEET_NAME", "Accounts")
OUTPUT_WORKSHEET_NAME = os.getenv("OUTPUT_WORKSHEET_NAME", "Analyzed Posts")

# 數據庫配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///social_media_tracking.db")

# 定時任務配置
COLLECTION_SCHEDULE_HOUR = int(os.getenv("COLLECTION_SCHEDULE_HOUR", "9"))  # 每天上午9點執行
COLLECTION_SCHEDULE_MINUTE = int(os.getenv("COLLECTION_SCHEDULE_MINUTE", "0"))

# AI Prompts 配置變數
IMPORTANCE_FILTER_PROMPT = os.getenv("IMPORTANCE_FILTER_PROMPT", """
請分析以下社交媒體貼文的重要性，從1-10評分（10為最重要）。

評分標準：
- 重大新聞事件如募資、新產品發表、重大合作、重大收購、重大事件等：8-10分
- 有洞見的行業趨勢或市場動態：6-8分
- 個人觀點或日常分享：1-4分

請只回答數字分數，不需要解釋。

貼文內容：
{post_content}

重要性評分：
""")

SUMMARIZATION_PROMPT = os.getenv("SUMMARIZATION_PROMPT", """
請將以下社交媒體貼文內容摘要為簡潔的中文，重點突出關鍵信息：

原始內容：
{post_content}

摘要（限制在100字以內）：
""")

REPOST_GENERATION_PROMPT = os.getenv("REPOST_GENERATION_PROMPT", """
基於以下內容，生成一個適合在社交媒體轉發的貼文，要求：
1. 保持原意但用自己的話表達
2. 增加適當的觀點或評論
3. 使用吸引人的語調
4. 長度控制在280字以內

原始內容：
{post_content}

轉發內容：
""")

# 平台配置
PLATFORMS = {
    "twitter": {
        "enabled": True,
        "rate_limit_per_15min": 450,
        "posts_per_request": 100
    },
    "linkedin": {
        "enabled": False,  # 暫時禁用 LinkedIn
        "rate_limit_per_day": 1000,
        "posts_per_request": 50
    }
}

# 重要性篩選閾值
IMPORTANCE_THRESHOLD = int(os.getenv("IMPORTANCE_THRESHOLD", "8"))

# 日誌配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/social_media_tracker.log")