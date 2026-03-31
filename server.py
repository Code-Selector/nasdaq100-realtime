#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
纳斯达克100 实时行情后端 API
============================
- Flask 后端，内存存储 + MySQL 持久化
- 后台线程每 60s 拉取新浪财经数据
- 提供 REST API 给前端消费
- 静态文件伺服 front/ 目录

启动: python server.py
访问: http://localhost:5188
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, time as dt_time

# ── 绕过代理 ──
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

import pytz
import requests
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

import db  # MySQL 模块

# ═══════════════════════════════════════════════════════════════════════
#  配置
# ═══════════════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.join(BASE_DIR, "front")

ET = pytz.timezone("US/Eastern")
CN = pytz.timezone("Asia/Shanghai")

FETCH_INTERVAL = 60  # 秒

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

# ═══════════════════════════════════════════════════════════════════════
#  内存数据存储
# ═══════════════════════════════════════════════════════════════════════
_store = {
    "stocks": [],           # 最新一次抓取的全部股票数据
    "updated_at": None,     # 最后更新时间 (北京时间字符串)
    "updated_et": None,     # 最后更新时间 (美东时间字符串)
    "session": "",          # 当前交易时段
    "stats": {},            # 统计信息
    "fetch_count": 0,       # 累计拉取次数
    "history": [],          # 近 60 条快照摘要 (用于前端趋势)
}
_lock = threading.Lock()


# ═══════════════════════════════════════════════════════════════════════
#  交易时段
# ═══════════════════════════════════════════════════════════════════════
def get_market_session() -> dict:
    now_et = datetime.now(ET)
    t = now_et.time()
    wd = now_et.weekday()

    if wd >= 5:
        return {"code": "closed", "label": "周末休市", "color": "#ef4444"}
    if dt_time(4, 0) <= t < dt_time(9, 30):
        return {"code": "pre", "label": "盘前 Pre-Market", "color": "#eab308"}
    elif dt_time(9, 30) <= t < dt_time(16, 0):
        return {"code": "regular", "label": "盘中 Regular", "color": "#22c55e"}
    elif dt_time(16, 0) <= t < dt_time(20, 0):
        return {"code": "after", "label": "盘后 After-Hours", "color": "#f97316"}
    else:
        return {"code": "closed", "label": "休市 Closed", "color": "#ef4444"}


# ═══════════════════════════════════════════════════════════════════════
#  数据拉取 (新浪财经)
# ═══════════════════════════════════════════════════════════════════════
def _safe_float(s):
    try:
        return round(float(s), 4) if s else None
    except (ValueError, TypeError):
        return None


def _safe_int(s):
    try:
        return int(s) if s else None
    except (ValueError, TypeError):
        return None


def fetch_data() -> list:
    """从新浪财经批量拉取美股实时行情，返回 list[dict]"""
    all_rows = []
    batch_size = 50

    for i in range(0, len(NASDAQ100_TICKERS), batch_size):
        batch = NASDAQ100_TICKERS[i:i + batch_size]
        symbol_str = ",".join(f"gb_{t.lower()}" for t in batch)
        url = f"https://hq.sinajs.cn/list={symbol_str}"

        try:
            r = requests.get(url, timeout=15, headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
            })
            r.encoding = "gbk"
        except Exception as e:
            print(f"  [WARN] 批次 {i // batch_size + 1} 请求失败: {e}")
            continue

        for line in r.text.strip().split("\n"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            var_part, val_part = line.split("=", 1)
            ticker = var_part.split("_")[-1].upper().rstrip(";")
            data_str = val_part.strip('"').rstrip('";')
            if not data_str:
                continue

            fields = data_str.split(",")
            if len(fields) < 27:
                continue
            try:
                # ── Sina 美股字段映射 ──
                # [0]  中文名
                # [1]  正常盘最新价  [2] 涨跌幅%  [3] 更新时间  [4] 涨跌额
                # [5]  今开  [6] 最高  [7] 最低
                # [8]  52周最高  [9] 52周最低
                # [10] 成交量  [12] 总市值  [13] PE
                # [21] 盘后/盘前价格  [22] 盘后涨跌幅%  [23] 盘后涨跌额
                # [24] 盘后时间戳  [25] 正常盘关闭时间
                # [26] 前一日收盘价
                all_rows.append({
                    "ticker": ticker,
                    "name": fields[0],
                    "price": _safe_float(fields[1]),
                    "changePercent": _safe_float(fields[2]),
                    "updateTime": fields[3],
                    "change": _safe_float(fields[4]),
                    "open": _safe_float(fields[5]),
                    "high": _safe_float(fields[6]),
                    "low": _safe_float(fields[7]),
                    "high52w": _safe_float(fields[8]),
                    "low52w": _safe_float(fields[9]),
                    "volume": _safe_int(fields[10]),
                    "marketCap": _safe_float(fields[12]),
                    "pe": _safe_float(fields[13]) if len(fields) > 13 else None,
                    # 盘后 / 盘前
                    "afterHoursPrice": _safe_float(fields[21]),
                    "afterHoursChangePct": _safe_float(fields[22]),
                    "afterHoursChange": _safe_float(fields[23]),
                    "afterHoursTime": fields[24].strip() if len(fields) > 24 else None,
                    "regularCloseTime": fields[25].strip() if len(fields) > 25 else None,
                    "prevClose": _safe_float(fields[26]),
                })
            except (ValueError, IndexError):
                continue

    # 按涨跌幅降序
    all_rows.sort(key=lambda x: (x.get("changePercent") or -9999), reverse=True)
    # 加排名
    for i, row in enumerate(all_rows, 1):
        row["rank"] = i
    return all_rows


def compute_stats(stocks: list) -> dict:
    pcts = [s["changePercent"] for s in stocks if s.get("changePercent") is not None]
    up = sum(1 for p in pcts if p > 0)
    down = sum(1 for p in pcts if p < 0)
    flat = sum(1 for p in pcts if p == 0)
    avg = round(sum(pcts) / len(pcts), 2) if pcts else 0
    max_pct = max(pcts) if pcts else 0
    min_pct = min(pcts) if pcts else 0
    return {
        "total": len(stocks),
        "up": up,
        "down": down,
        "flat": flat,
        "avgChange": avg,
        "maxChange": max_pct,
        "minChange": min_pct,
    }


# ═══════════════════════════════════════════════════════════════════════
#  持久化 (MySQL)
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
#  后台拉取线程
# ═══════════════════════════════════════════════════════════════════════
def _background_fetcher():
    """后台线程: 每 FETCH_INTERVAL 秒拉取一次数据"""
    while True:
        try:
            stocks = fetch_data()
            if not stocks:
                print(f"  [WARN] 本轮无数据")
                time.sleep(FETCH_INTERVAL)
                continue

            now_cn = datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S")
            now_et = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S %Z")
            session = get_market_session()
            stats = compute_stats(stocks)

            # 写入 MySQL
            batch_id = db.next_batch_id()
            db.save_snapshot(batch_id, stocks, now_cn, now_et, session, stats)

            with _lock:
                _store["stocks"] = stocks
                _store["updated_at"] = now_cn
                _store["updated_et"] = now_et
                _store["session"] = session
                _store["stats"] = stats
                _store["fetch_count"] = batch_id

                # 保留近 60 条历史摘要
                _store["history"].append({
                    "time": now_cn,
                    "avgChange": stats["avgChange"],
                    "up": stats["up"],
                    "down": stats["down"],
                })
                if len(_store["history"]) > 60:
                    _store["history"] = _store["history"][-60:]

            print(f"  [OK] #{batch_id} | {now_cn} | "
                  f"↑{stats['up']} ↓{stats['down']} avg:{stats['avgChange']:+.2f}%")

        except Exception as e:
            print(f"  [ERR] 拉取异常: {e}")

        time.sleep(FETCH_INTERVAL)


# ═══════════════════════════════════════════════════════════════════════
#  Flask 应用
# ═══════════════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder=FRONT_DIR, static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(FRONT_DIR, "index.html")


@app.route("/api/nasdaq100")
def api_nasdaq100():
    """返回最新全部数据"""
    with _lock:
        return jsonify({
            "stocks": _store["stocks"],
            "updatedAt": _store["updated_at"],
            "updatedEt": _store["updated_et"],
            "session": _store["session"],
            "stats": _store["stats"],
            "fetchCount": _store["fetch_count"],
        })


@app.route("/api/nasdaq100/top")
def api_top():
    """返回涨幅/跌幅 Top N"""
    with _lock:
        stocks = _store["stocks"]
    n = 10
    return jsonify({
        "gainers": stocks[:n],
        "losers": stocks[-n:][::-1] if len(stocks) >= n else stocks[::-1],
        "updatedAt": _store.get("updated_at"),
    })


@app.route("/api/nasdaq100/history")
def api_history():
    """返回最近60条快照摘要 (用于前端趋势图)"""
    with _lock:
        return jsonify(_store["history"])


@app.route("/api/status")
def api_status():
    """系统状态"""
    return jsonify({
        "session": get_market_session(),
        "fetchCount": _store["fetch_count"],
        "updatedAt": _store.get("updated_at"),
        "tickerCount": len(NASDAQ100_TICKERS),
        "stockCount": len(_store["stocks"]),
    })


# ═══════════════════════════════════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════════════════════════════════
def main():
    port = int(os.environ.get("PORT", 5188))

    # 初始化 MySQL 表
    db.init_tables()

    # 启动时从 MySQL 恢复上次数据
    cached = db.load_latest()
    if cached:
        with _lock:
            _store["stocks"] = cached.get("stocks", [])
            _store["updated_at"] = cached.get("updatedAt")
            _store["updated_et"] = cached.get("updatedEt")
            _store["session"] = cached.get("session", {})
            _store["stats"] = cached.get("stats", {})
            _store["fetch_count"] = db.get_total_fetch_count()
            _store["history"] = db.load_history(60)
        print(f"  [BOOT] 已从 MySQL 恢复 {len(_store['stocks'])} 条数据, "
              f"历史 {len(_store['history'])} 条")

    # 启动后台拉取线程
    t = threading.Thread(target=_background_fetcher, daemon=True)
    t.start()
    print(f"  [BOOT] 后台拉取线程已启动 (间隔 {FETCH_INTERVAL}s)")

    print(f"\n{'=' * 50}")
    print(f"  🚀 纳斯达克100 实时行情服务")
    print(f"  📡 http://localhost:{port}")
    print(f"  📊 API: http://localhost:{port}/api/nasdaq100")
    print(f"  ⏱  刷新间隔: {FETCH_INTERVAL}s")
    print(f"{'=' * 50}\n")

    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
