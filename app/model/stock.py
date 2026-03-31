from dataclasses import dataclass
from typing import Optional


@dataclass
class StockQuote:
    ticker: str
    name: Optional[str] = None
    price: Optional[float] = None
    change_pct: Optional[float] = None
    change_amt: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    pe: Optional[float] = None
    prev_close: Optional[float] = None
    ah_price: Optional[float] = None
    ah_change_pct: Optional[float] = None
    ah_change_amt: Optional[float] = None
    ah_time: Optional[str] = None
    regular_close_time: Optional[str] = None
    src_update_time: Optional[str] = None
    rank: int = 0

    def to_api_dict(self) -> dict:
        return {
            "rank": self.rank, "ticker": self.ticker, "name": self.name,
            "price": self.price, "changePercent": self.change_pct,
            "change": self.change_amt, "open": self.open_price,
            "high": self.high_price, "low": self.low_price,
            "high52w": self.high_52w, "low52w": self.low_52w,
            "volume": self.volume, "marketCap": self.market_cap,
            "pe": self.pe, "prevClose": self.prev_close,
            "afterHoursPrice": self.ah_price,
            "afterHoursChangePct": self.ah_change_pct,
            "afterHoursChange": self.ah_change_amt,
            "afterHoursTime": self.ah_time,
            "regularCloseTime": self.regular_close_time,
            "updateTime": self.src_update_time,
        }


DDL_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS nasdaq100_snapshot (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id      BIGINT        NOT NULL,
    ticker        VARCHAR(10)   NOT NULL,
    name          VARCHAR(50),
    price         DECIMAL(12,4),
    change_pct    DECIMAL(8,4),
    change_amt    DECIMAL(12,4),
    open_price    DECIMAL(12,4),
    high_price    DECIMAL(12,4),
    low_price     DECIMAL(12,4),
    high_52w      DECIMAL(12,4),
    low_52w       DECIMAL(12,4),
    volume        BIGINT,
    market_cap    DECIMAL(20,2),
    pe            DECIMAL(10,2),
    prev_close    DECIMAL(12,4),
    ah_price      DECIMAL(12,4),
    ah_change_pct DECIMAL(8,4),
    ah_change_amt DECIMAL(12,4),
    ah_time       VARCHAR(30),
    regular_close_time VARCHAR(30),
    src_update_time VARCHAR(30),
    fetched_at    DATETIME NOT NULL,
    INDEX idx_batch (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

DDL_FETCH_LOG = """
CREATE TABLE IF NOT EXISTS nasdaq100_fetch_log (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id      BIGINT   NOT NULL,
    fetched_at    DATETIME NOT NULL,
    fetched_et    VARCHAR(40),
    stock_count   INT DEFAULT 0,
    avg_change    DECIMAL(8,4),
    up_count      INT DEFAULT 0,
    down_count    INT DEFAULT 0,
    flat_count    INT DEFAULT 0,
    session_code  VARCHAR(20),
    session_label VARCHAR(50),
    UNIQUE KEY uk_batch (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
