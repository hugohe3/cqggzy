"""
全局配置
========
所有常量集中管理，避免两个脚本各自定义导致不一致。
"""

import os

# ==================== API ====================
API_URL = "https://www.cqggzy.com/inteligentsearch/rest/esinteligentsearch/getFullTextDataNew"
PAGE_URL = "https://www.cqggzy.com/jyxx/transaction_detail.html"
BASE_URL = "https://www.cqggzy.com"

# ==================== 输出 ====================
OUTPUT_DIR = "output"
LINKS_FILE = os.path.join(OUTPUT_DIR, "links.json")
DETAILS_CSV = os.path.join(OUTPUT_DIR, "details.csv")
DETAILS_JSON = os.path.join(OUTPUT_DIR, "details.json")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")
COOKIES_FILE = os.path.join(OUTPUT_DIR, "cookies.json")

# ==================== 默认参数 ====================
DEFAULT_KEYWORD = ""
DEFAULT_REGION = ""
DEFAULT_BIZ_TYPE = ""
DEFAULT_INFO_TYPE = "交易结果"
DEFAULT_TIME_PERIOD = "近三月"
PAGE_SIZE = 20
BATCH_SIZE = 10  # 每批保存一次进度

# ==================== 浏览器 ====================
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ==================== HTTP 并发 ====================
MAX_CONCURRENT = 10   # 异步并发数
REQUEST_TIMEOUT = 15  # 单次请求超时(秒)
