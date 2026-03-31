from flask import Blueprint, jsonify
from app.service import market_service

stock_bp = Blueprint("stock", __name__, url_prefix="/api")


@stock_bp.route("/nasdaq100")
def get_nasdaq100():
    from app.task.scheduler import get_store
    s = get_store()
    return jsonify({
        "stocks": [q.to_api_dict() for q in s["stocks"]],
        "updatedAt": s["updated_at"], "updatedEt": s["updated_et"],
        "session": s["session"] or {}, "stats": s["stats"] or {},
        "fetchCount": s["fetch_count"],
    })


@stock_bp.route("/nasdaq100/top")
def get_top():
    from app.task.scheduler import get_store
    stocks = [q.to_api_dict() for q in get_store()["stocks"]]
    return jsonify({
        "gainers": stocks[:10],
        "losers": stocks[-10:][::-1] if len(stocks) >= 10 else stocks[::-1],
    })


@stock_bp.route("/nasdaq100/history")
def get_history():
    from app.task.scheduler import get_store
    return jsonify(get_store()["history"])


@stock_bp.route("/status")
def get_status():
    from app.task.scheduler import get_store
    from app.config import NASDAQ100_TICKERS
    s = get_store()
    return jsonify({
        "session": market_service.get_market_session(),
        "fetchCount": s["fetch_count"],
        "updatedAt": s["updated_at"],
        "tickerCount": len(NASDAQ100_TICKERS),
        "stockCount": len(s["stocks"]),
    })
