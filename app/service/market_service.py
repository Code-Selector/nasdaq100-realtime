from datetime import datetime, time as dt_time
import pytz
from app.config import TZ_ET, TZ_CN
from app.model.stock import StockQuote
from app.dao import stock_dao

ET = pytz.timezone(TZ_ET)
CN = pytz.timezone(TZ_CN)


def get_market_session() -> dict:
    now_et = datetime.now(ET)
    t, wd = now_et.time(), now_et.weekday()
    if wd >= 5:
        return {"code": "closed", "label": "周末休市", "color": "#ef4444"}
    if dt_time(4, 0) <= t < dt_time(9, 30):
        return {"code": "pre", "label": "盘前 Pre-Market", "color": "#eab308"}
    if dt_time(9, 30) <= t < dt_time(16, 0):
        return {"code": "regular", "label": "盘中 Regular", "color": "#22c55e"}
    if dt_time(16, 0) <= t < dt_time(20, 0):
        return {"code": "after", "label": "盘后 After-Hours", "color": "#f97316"}
    return {"code": "closed", "label": "休市 Closed", "color": "#ef4444"}


def compute_stats(stocks: list[StockQuote]) -> dict:
    pcts = [s.change_pct for s in stocks if s.change_pct is not None]
    up = sum(1 for p in pcts if p > 0)
    down = sum(1 for p in pcts if p < 0)
    return {
        "total": len(stocks), "up": up, "down": down,
        "flat": len(pcts) - up - down,
        "avg_change": round(sum(pcts) / len(pcts), 2) if pcts else 0.0,
        "maxChange": max(pcts) if pcts else 0.0,
        "minChange": min(pcts) if pcts else 0.0,
    }


def now_cn_str() -> str:
    return datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S")


def now_et_str() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S %Z")


def save_batch(stocks: list[StockQuote], session: dict, stats: dict) -> int:
    batch_id = stock_dao.next_batch_id()
    fetched_cn, fetched_et = now_cn_str(), now_et_str()
    stock_dao.insert_snapshot(batch_id, stocks, fetched_cn)
    stock_dao.insert_fetch_log(batch_id, fetched_cn, fetched_et, session, stats)
    return batch_id


def _f(v):
    return float(v) if v is not None else None


def load_latest_stocks() -> list[StockQuote]:
    log, rows = stock_dao.query_latest_batch()
    if not log:
        return []
    return [StockQuote(
        ticker=r["ticker"], name=r["name"], price=_f(r["price"]),
        change_pct=_f(r["change_pct"]), change_amt=_f(r["change_amt"]),
        open_price=_f(r["open_price"]), high_price=_f(r["high_price"]),
        low_price=_f(r["low_price"]), high_52w=_f(r["high_52w"]),
        low_52w=_f(r["low_52w"]), volume=r["volume"],
        market_cap=_f(r["market_cap"]), pe=_f(r["pe"]),
        prev_close=_f(r["prev_close"]), ah_price=_f(r["ah_price"]),
        ah_change_pct=_f(r["ah_change_pct"]), ah_change_amt=_f(r["ah_change_amt"]),
        ah_time=r["ah_time"], regular_close_time=r["regular_close_time"],
        src_update_time=r["src_update_time"], rank=i,
    ) for i, r in enumerate(rows, 1)]


def load_latest_meta() -> dict | None:
    log, _ = stock_dao.query_latest_batch()
    if not log:
        return None
    return {
        "updated_at": str(log["fetched_at"]) if log["fetched_at"] else None,
        "updated_et": log["fetched_et"],
        "session": {"code": log["session_code"] or "closed", "label": log["session_label"] or ""},
        "stats": {
            "total": log["stock_count"], "up": log["up_count"],
            "down": log["down_count"], "flat": log["flat_count"],
            "avg_change": _f(log["avg_change"]) or 0.0,
        },
    }


def load_history(limit: int = 60) -> list[dict]:
    return [{
        "time": str(r["fetched_at"]) if r["fetched_at"] else None,
        "avgChange": _f(r["avg_change"]), "up": r["up_count"], "down": r["down_count"],
    } for r in stock_dao.query_history(limit)]


def get_fetch_count() -> int:
    return stock_dao.query_max_batch_id()
