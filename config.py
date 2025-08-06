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
INPUT_SPREADSHEET_NAME = os.getenv("INPUT_SPREADSHEET_NAME", "Social Media Tracking")
OUTPUT_SPREADSHEET_NAME = os.getenv("OUTPUT_SPREADSHEET_NAME", "Social Media Tracking")
INPUT_WORKSHEET_NAME = os.getenv("INPUT_WORKSHEET_NAME", "Accounts")
OUTPUT_WORKSHEET_NAME = os.getenv("OUTPUT_WORKSHEET_NAME", "Analyzed Posts")

# 新增的工作表配置
ALL_POSTS_WORKSHEET_NAME = os.getenv("ALL_POSTS_WORKSHEET_NAME", "All Posts & AI Scores")
PROMPT_HISTORY_WORKSHEET_NAME = os.getenv("PROMPT_HISTORY_WORKSHEET_NAME", "Prompt Optimization History")

# 數據庫配置
# Railway 會自動提供 DATABASE_URL 環境變數
# 本地開發時使用 SQLite，生產環境使用 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///social_media_tracking.db")

# 如果是 PostgreSQL URL，確保使用正確的驅動
if DATABASE_URL.startswith("postgres://"):
    # Railway 提供的是 postgres://，但 SQLAlchemy 需要 postgresql://
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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

貼文內容：
{post_content}

請只回覆一個數字（1-10），不要其他文字說明。
重要性評分：
""")

SUMMARIZATION_PROMPT = os.getenv("SUMMARIZATION_PROMPT", """
請將以下社交媒體貼文內容摘要為簡潔英文，重點突出關鍵信息：

原始內容：
{post_content}

摘要（限制在100字以內）：
""")

REPOST_GENERATION_PROMPT = os.getenv("REPOST_GENERATION_PROMPT", """
基於以下內容，生成一個適合在社交媒體轉發的貼文，要求：
1. 保持原意但用自己的話表達
2. 增加適當的觀點或評論
3. 發文者是VC，所以需要用VC的視角來寫
4. 長度控制在100字以內

原始內容：
{post_content}

轉發內容：
""")

# Twitter 客戶端優先順序配置
# 可選值: "nitter", "scraper", "api"
TWITTER_CLIENT_PRIORITY = os.getenv("TWITTER_CLIENT_PRIORITY", "nitter,scraper,api").split(",")

# 平台配置
PLATFORMS = {
    "twitter": {
        "enabled": True,
        "rate_limit_per_15min": 450,
        "posts_per_request": 10,  # 減少每次請求的推文數量
        "max_retries": 3,
        "request_delay_seconds": 1.0,  # 請求間隔
        "cache_days": 30  # 用戶信息緩存天數
    },
    "linkedin": {
        "enabled": True,
        "rate_limit_per_day": 1000,
        "posts_per_request": 50
    }
}

# Web Scraper 配置
SCRAPER_CONFIG = {
    "use_scraper": os.getenv("USE_X_SCRAPER", "false").lower() == "true",  # 是否使用爬蟲而非API
    "headless": os.getenv("SCRAPER_HEADLESS", "true").lower() == "true",  # 是否使用無頭瀏覽器
    "min_delay": float(os.getenv("SCRAPER_MIN_DELAY", "3")),  # 最小延遲（秒）
    "max_delay": float(os.getenv("SCRAPER_MAX_DELAY", "10")),  # 最大延遲（秒）
    "daily_limit": int(os.getenv("SCRAPER_DAILY_LIMIT", "500")),  # 每日抓取限制
    "proxy_enabled": os.getenv("SCRAPER_PROXY_ENABLED", "false").lower() == "true",
    "proxy_list": os.getenv("SCRAPER_PROXY_LIST", "").split(","),  # 代理列表，逗號分隔
    "user_agents_file": os.getenv("SCRAPER_USER_AGENTS_FILE", "user_agents.txt"),
    "cookies_dir": os.getenv("SCRAPER_COOKIES_DIR", "scraper_cookies"),  # Cookie存儲目錄
    "accounts": []  # 將在運行時從環境變量加載
}

# 加載爬蟲帳號配置
if os.getenv("X_SCRAPER_ACCOUNTS"):
    # 格式: username1:password1,username2:password2
    accounts_str = os.getenv("X_SCRAPER_ACCOUNTS", "")
    for account in accounts_str.split(","):
        if ":" in account:
            username, password = account.split(":", 1)
            SCRAPER_CONFIG["accounts"].append({
                "username": username.strip(),
                "password": password.strip()
            })

# Nitter 實例配置（備用方案）
default_nitter_instances = [
    "https://twitt.re",
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.pek.li",
    "https://nitter.aishiteiru.moe",
    "https://nitter.aosus.link",
    "https://nitter.dashy.a3x.dn.nyx.im"
]
NITTER_INSTANCES = os.getenv("NITTER_INSTANCES", ",".join(default_nitter_instances)).split(",") if os.getenv("NITTER_INSTANCES") else default_nitter_instances

# 重要性篩選閾值
IMPORTANCE_THRESHOLD = int(os.getenv("IMPORTANCE_THRESHOLD", "8"))

# 日誌配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/social_media_tracker.log")