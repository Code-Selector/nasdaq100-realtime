#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
MySQL 数据库连接与操作模块
==========================
- 使用 pymysql 连接 MySQL
- 提供建表、写入、查询方法
"""

import pymysql
from contextlib import contextmanager

# ═══════════════════════════════════════════════════════════════════════
#  数据库配置
# ═══════════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "trader",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# ═══════════════════════════════════════════════════════════════════════
#  连接管理
# ═══════════════════════════════════════════════════════════════════════
@contextmanager
def get_conn():
    """获取数据库连接(上下文管理器，自动提交/回滚/关闭)"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════
#  建表
# ═══════════════════════════════════════════════════════════════════════
DDL_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS nasdaq100_snapshot (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id      BIGINT        NOT NULL COMMENT '拉取批次号',
    ticker        VARCHAR(10)   NOT NULL,
    name          VARCHAR(50)   DEFAULT NULL,
    price         DECIMAL(12,4) DEFAULT NULL,
    change_pct    DECIMAL(8,4)  DEFAULT NULL,
    change_amt    DECIMAL(12,4) DEFAULT NULL,
    open_price    DECIMAL(12,4) DEFAULT NULL,
    high_price    DECIMAL(12,4) DEFAULT NULL,
    low_price     DECIMAL(12,4) DEFAULT NULL,
    high_52w      DECIMAL(12,4) DEFAULT NULL,
    low_52w       DECIMAL(12,4) DEFAULT NULL,
    volume        BIGINT        DEFAULT NULL,
    market_cap    DECIMAL(20,2) DEFAULT NULL,
    pe            DECIMAL(10,2) DEFAULT NULL,
    prev_close    DECIMAL(12,4) DEFAULT NULL,
    ah_price      DECIMAL(12,4) DEFAULT NULL COMMENT '盘后价',
    ah_change_pct DECIMAL(8,4)  DEFAULT NULL COMMENT '盘后涨跌幅',
    ah_change_amt DECIMAL(12,4) DEFAULT NULL COMMENT '盘后涨跌额',
    ah_time       VARCHAR(30)   DEFAULT NULL,
    regular_close_time VARCHAR(30) DEFAULT NULL,
    src_update_time VARCHAR(30) DEFAULT NULL COMMENT '数据源更新时间',
    fetched_at    DATETIME      NOT NULL     COMMENT '拉取时间(北京)',
    INDEX idx_batch (batch_id),
    INDEX idx_ticker_batch (ticker, batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='纳斯达克100快照';
"""

DDL_FETCH_LOG = """
CREATE TABLE IF NOT EXISTS nasdaq100_fetch_log (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id      BIGINT   NOT NULL,
    fetched_at    DATETIME NOT NULL,
    fetched_et    VARCHAR(40) DEFAULT NULL,
    stock_count   INT      DEFAULT 0,
    avg_change    DECIMAL(8,4) DEFAULT NULL,
    up_count      INT      DEFAULT 0,
    down_count    INT      DEFAULT 0,
    flat_count    INT      DEFAULT 0,
    session_code  VARCHAR(20) DEFAULT NULL,
    session_label VARCHAR(50) DEFAULT NULL,
    UNIQUE KEY uk_batch (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='拉取日志';
"""


def init_tables():
    """创建表（幂等）"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL_SNAPSHOT)
            cur.execute(DDL_FETCH_LOG)
    print("  [DB] 表已就绪")


# ═══════════════════════════════════════════════════════════════════════
#  写入
# ═══════════════════════════════════════════════════════════════════════
def next_batch_id() -> int:
    """获取下一个 batch_id"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(batch_id), 0) + 1 AS nxt FROM nasdaq100_fetch_log")
            return cur.fetchone()["nxt"]


def save_snapshot(batch_id: int, stocks: list, now_cn: str, now_et: str,
                  session: dict, stats: dict):
    """将一次抓取的全部股票数据写入 MySQL"""
    if not stocks:
        return

    insert_sql = """
        INSERT INTO nasdaq100_snapshot
            (batch_id, ticker, name, price, change_pct, change_amt,
             open_price, high_price, low_price, high_52w, low_52w,
             volume, market_cap, pe, prev_close,
             ah_price, ah_change_pct, ah_change_amt, ah_time,
             regular_close_time, src_update_time, fetched_at)
        VALUES
            (%(batch_id)s, %(ticker)s, %(name)s, %(price)s, %(change_pct)s, %(change_amt)s,
             %(open_price)s, %(high_price)s, %(low_price)s, %(high_52w)s, %(low_52w)s,
             %(volume)s, %(market_cap)s, %(pe)s, %(prev_close)s,
             %(ah_price)s, %(ah_change_pct)s, %(ah_change_amt)s, %(ah_time)s,
             %(regular_close_time)s, %(src_update_time)s, %(fetched_at)s)
    """

    log_sql = """
        INSERT INTO nasdaq100_fetch_log
            (batch_id, fetched_at, fetched_et, stock_count,
             avg_change, up_count, down_count, flat_count,
             session_code, session_label)
        VALUES
            (%(batch_id)s, %(fetched_at)s, %(fetched_et)s, %(stock_count)s,
             %(avg_change)s, %(up_count)s, %(down_count)s, %(flat_count)s,
             %(session_code)s, %(session_label)s)
    """

    rows = []
    for s in stocks:
        rows.append({
            "batch_id": batch_id,
            "ticker": s.get("ticker"),
            "name": s.get("name"),
            "price": s.get("price"),
            "change_pct": s.get("changePercent"),
            "change_amt": s.get("change"),
            "open_price": s.get("open"),
            "high_price": s.get("high"),
            "low_price": s.get("low"),
            "high_52w": s.get("high52w"),
            "low_52w": s.get("low52w"),
            "volume": s.get("volume"),
            "market_cap": s.get("marketCap"),
            "pe": s.get("pe"),
            "prev_close": s.get("prevClose"),
            "ah_price": s.get("afterHoursPrice"),
            "ah_change_pct": s.get("afterHoursChangePct"),
            "ah_change_amt": s.get("afterHoursChange"),
            "ah_time": s.get("afterHoursTime"),
            "regular_close_time": s.get("regularCloseTime"),
            "src_update_time": s.get("updateTime"),
            "fetched_at": now_cn,
        })

    log_row = {
        "batch_id": batch_id,
        "fetched_at": now_cn,
        "fetched_et": now_et,
        "stock_count": stats.get("total", 0),
        "avg_change": stats.get("avgChange"),
        "up_count": stats.get("up", 0),
        "down_count": stats.get("down", 0),
        "flat_count": stats.get("flat", 0),
        "session_code": session.get("code"),
        "session_label": session.get("label"),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(insert_sql, rows)
            cur.execute(log_sql, log_row)


# ═══════════════════════════════════════════════════════════════════════
#  查询
# ═══════════════════════════════════════════════════════════════════════
def load_latest() -> dict | None:
    """加载最新一批快照数据，返回与旧 JSON 格式兼容的 dict"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 最新 batch
            cur.execute("SELECT * FROM nasdaq100_fetch_log ORDER BY batch_id DESC LIMIT 1")
            log = cur.fetchone()
            if not log:
                return None

            bid = log["batch_id"]
            cur.execute("SELECT * FROM nasdaq100_snapshot WHERE batch_id = %s ORDER BY change_pct DESC", (bid,))
            rows = cur.fetchall()

    stocks = []
    for i, r in enumerate(rows, 1):
        stocks.append({
            "rank": i,
            "ticker": r["ticker"],
            "name": r["name"],
            "price": _to_float(r["price"]),
            "changePercent": _to_float(r["change_pct"]),
            "change": _to_float(r["change_amt"]),
            "open": _to_float(r["open_price"]),
            "high": _to_float(r["high_price"]),
            "low": _to_float(r["low_price"]),
            "high52w": _to_float(r["high_52w"]),
            "low52w": _to_float(r["low_52w"]),
            "volume": r["volume"],
            "marketCap": _to_float(r["market_cap"]),
            "pe": _to_float(r["pe"]),
            "prevClose": _to_float(r["prev_close"]),
            "afterHoursPrice": _to_float(r["ah_price"]),
            "afterHoursChangePct": _to_float(r["ah_change_pct"]),
            "afterHoursChange": _to_float(r["ah_change_amt"]),
            "afterHoursTime": r["ah_time"],
            "regularCloseTime": r["regular_close_time"],
            "updateTime": r["src_update_time"],
        })

    return {
        "stocks": stocks,
        "updatedAt": str(log["fetched_at"]) if log["fetched_at"] else None,
        "updatedEt": log["fetched_et"],
        "session": {
            "code": log["session_code"],
            "label": log["session_label"],
        },
        "stats": {
            "total": log["stock_count"],
            "up": log["up_count"],
            "down": log["down_count"],
            "flat": log["flat_count"],
            "avgChange": _to_float(log["avg_change"]),
        },
    }


def load_history(limit: int = 60) -> list:
    """加载最近 N 条拉取日志摘要 (用于前端趋势图)"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fetched_at, avg_change, up_count, down_count "
                "FROM nasdaq100_fetch_log ORDER BY batch_id DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()

    # 按时间正序返回
    rows.reverse()
    return [
        {
            "time": str(r["fetched_at"]) if r["fetched_at"] else None,
            "avgChange": _to_float(r["avg_change"]),
            "up": r["up_count"],
            "down": r["down_count"],
        }
        for r in rows
    ]


def get_total_fetch_count() -> int:
    """获取历史总拉取次数"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(batch_id), 0) AS cnt FROM nasdaq100_fetch_log")
            return cur.fetchone()["cnt"]


def _to_float(v):
    """Decimal / None -> float / None"""
    if v is None:
        return None
    return float(v)
