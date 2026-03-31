"""
全局配置
========
集中管理数据库、时区、拉取间隔、Ticker 列表等配置项。
支持环境变量覆盖。
"""

import os

# ── 数据库 ──────────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = os.getenv("DB_NAME", "trader")
DB_CHARSET = "utf8mb4"

# ── 服务 ────────────────────────────────────────────────────────────
SERVER_PORT = int(os.getenv("PORT", 5188))
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", 60))  # 秒

# ── 时区 ────────────────────────────────────────────────────────────
TZ_ET = "US/Eastern"
TZ_CN = "Asia/Shanghai"

# ── 前端静态目录 ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONT_DIR = os.path.join(BASE_DIR, "front")

NASDAQ100_TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD",
    "AMGN", "AMZN", "ANSS", "APP", "ARM", "ASML", "AVGO", "AZN",
    "BIIB", "BKNG", "BKR", "CCEP", "CDNS", "CDW", "CEG", "CHTR",
    "CMCSA", "COIN", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CTAS",
    "CTSH", "DASH", "DDOG", "DLTR", "DXCM",
    "EA", "EXC",
    "FANG", "FAST", "FTNT",
    "GEHC", "GFS", "GILD", "GOOG", "GOOGL",
    "HON",
    "IDXX", "ILMN", "INTC", "INTU", "ISRG",
    "KDP", "KHC", "KLAC",
    "LRCX", "LULU",
    "MAR", "MCHP", "MDB", "MDLZ", "MELI", "META", "MNST", "MRNA",
    "MRVL", "MSFT", "MU",
    "NFLX", "NVDA", "NXPI",
    "ODFL", "ON", "ORLY",
    "PANW", "PAYX", "PCAR", "PDD", "PEP", "PYPL",
    "QCOM",
    "REGN", "ROP", "ROST",
    "SBUX", "SMCI", "SNPS", "TEAM", "TMUS", "TSLA", "TTD",
    "TXN",
    "VRSK", "VRTX",
    "WBD", "WDAY",
    "XEL",
    "ZS",
]

SINA_HQ_URL = "https://hq.sinajs.cn/list="
SINA_BATCH_SIZE = 50
SINA_HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
SINA_TIMEOUT = 15
