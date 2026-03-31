import threading
import time
from app.config import FETCH_INTERVAL
from app.service import fetch_service, market_service

_store = {
    "stocks": [], "updated_at": None, "updated_et": None,
    "session": None, "stats": None, "fetch_count": 0, "history": [],
}
_lock = threading.Lock()


def get_store() -> dict:
    with _lock:
        return {**_store}


def restore_from_db():
    stocks = market_service.load_latest_stocks()
    meta = market_service.load_latest_meta()
    history = market_service.load_history(60)
    with _lock:
        _store["stocks"] = stocks
        _store["history"] = history
        _store["fetch_count"] = market_service.get_fetch_count()
        if meta:
            _store.update({k: meta[k] for k in ("updated_at", "updated_et", "session", "stats")})
    print(f"  [BOOT] restored {len(stocks)} stocks, {len(history)} history records")


def _fetch_loop():
    while True:
        try:
            stocks = fetch_service.fetch_quotes()
            if not stocks:
                time.sleep(FETCH_INTERVAL)
                continue
            session = market_service.get_market_session()
            stats = market_service.compute_stats(stocks)
            batch_id = market_service.save_batch(stocks, session, stats)
            now_cn, now_et = market_service.now_cn_str(), market_service.now_et_str()
            with _lock:
                _store.update(stocks=stocks, updated_at=now_cn, updated_et=now_et,
                              session=session, stats=stats, fetch_count=batch_id)
                _store["history"].append({
                    "time": now_cn, "avgChange": stats["avg_change"],
                    "up": stats["up"], "down": stats["down"],
                })
                if len(_store["history"]) > 60:
                    _store["history"] = _store["history"][-60:]
            print(f"  [OK] #{batch_id} | {now_cn} | ↑{stats['up']} ↓{stats['down']} avg:{stats['avg_change']:+.2f}%")
        except Exception as e:
            print(f"  [ERR] {e}")
        time.sleep(FETCH_INTERVAL)


def start():
    threading.Thread(target=_fetch_loop, daemon=True, name="fetcher").start()
    print(f"  [BOOT] fetcher started (interval {FETCH_INTERVAL}s)")
