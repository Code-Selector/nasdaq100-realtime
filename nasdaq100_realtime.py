#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
纳斯达克100成分股实时涨幅监控
==========================================
- 每 1 分钟自动刷新
- 覆盖夜盘(盘后)、盘前、盘中所有时段
- 使用新浪财经美股实时行情接口(无延迟)
- 自动保存 CSV 到 output/ 目录
==========================================
启动: python nasdaq100_realtime.py
停止: Ctrl+C
"""

import sys
import os
import time
from datetime import datetime, time as dt_time

# ── 绕过代理: 国内财经接口不需要走代理 ──
for _k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_k, None)

import pytz
import pandas as pd
import requests

import db  # MySQL 模块

# ======================== 纳斯达克100 成分股 (2025) ========================
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

# 时区
ET = pytz.timezone("US/Eastern")
CN = pytz.timezone("Asia/Shanghai")

# 输出目录 (保留兼容)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  交易时段判断
# ═══════════════════════════════════════════════════════════════════════
def get_market_session() -> str:
    """
    根据美东时间判断当前交易时段:
      - Pre-Market  (盘前):  04:00 – 09:30 ET
      - Regular     (盘中):  09:30 – 16:00 ET
      - After-Hours (盘后/夜盘): 16:00 – 20:00 ET
      - Closed      (休市):  其余时间
    """
    now_et = datetime.now(ET)
    t = now_et.time()
    weekday = now_et.weekday()

    if weekday >= 5:
        return "🔴 周末休市"
    if dt_time(4, 0) <= t < dt_time(9, 30):
        return "🟡 盘前 Pre-Market"
    elif dt_time(9, 30) <= t < dt_time(16, 0):
        return "🟢 盘中 Regular"
    elif dt_time(16, 0) <= t < dt_time(20, 0):
        return "🟠 盘后 After-Hours (夜盘)"
    else:
        return "🔴 休市 Closed"


# ═══════════════════════════════════════════════════════════════════════
#  新浪财经实时行情 (核心数据源)
# ═══════════════════════════════════════════════════════════════════════
def fetch_sina_us_realtime(tickers: list) -> pd.DataFrame:
    """
    通过新浪财经实时行情接口批量获取美股报价。
    接口: https://hq.sinajs.cn/list=gb_aapl,gb_msft,...
    返回字段(逗号分隔):
      0: 中文名, 1: 最新价, 2: 涨跌幅(%), 3: 更新时间,
      4: 涨跌额, 5: 昨开/昨收, 6: 最高, 7: 最低,
      8: 52周高, 9: 52周低, 10: 成交量, 11: 成交量(10手),
      12: 总市值, 13: 市盈率, ...
    """
    all_rows = []
    batch_size = 50  # 每批50只，避免 URL 过长

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        symbol_str = ",".join(f"gb_{t.lower()}" for t in batch)
        url = f"https://hq.sinajs.cn/list={symbol_str}"

        try:
            r = requests.get(url, timeout=15, headers={
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120"
            })
            r.encoding = "gbk"
        except Exception as e:
            print(f"  ❌ 请求失败(批次 {i // batch_size + 1}): {e}")
            continue

        for line in r.text.strip().split("\n"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            # var hq_str_gb_aapl="苹果,264.18,..."
            var_part, val_part = line.split("=", 1)
            ticker_raw = var_part.split("_")[-1]
            ticker = ticker_raw.upper().rstrip(";")
            data_str = val_part.strip('"').rstrip('";')

            if not data_str:
                continue

            fields = data_str.split(",")
            if len(fields) < 13:
                continue

            try:
                row = {
                    "ticker": ticker,
                    "名称": fields[0],
                    "最新价": _safe_float(fields[1]),
                    "涨跌幅": _safe_float(fields[2]),
                    "更新时间": fields[3],
                    "涨跌额": _safe_float(fields[4]),
                    "昨收价": _safe_float(fields[5]),
                    "最高价": _safe_float(fields[6]),
                    "最低价": _safe_float(fields[7]),
                    "52周高": _safe_float(fields[8]),
                    "52周低": _safe_float(fields[9]),
                    "成交量": _safe_int(fields[10]),
                    "总市值": _safe_float(fields[12]),
                    "市盈率": _safe_float(fields[13]) if len(fields) > 13 else None,
                }
                all_rows.append(row)
            except (ValueError, IndexError):
                continue

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df = df.sort_values("涨跌幅", ascending=False, na_position="last").reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "排名"
    return df


def _safe_float(s: str):
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _safe_int(s: str):
    try:
        return int(s) if s else None
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════════
#  数据获取 & 展示
# ═══════════════════════════════════════════════════════════════════════
def fetch_nasdaq100_realtime() -> pd.DataFrame:
    """拉取纳斯达克100成分股实时行情"""
    print(f"[{datetime.now(CN).strftime('%Y-%m-%d %H:%M:%S')}] 正在拉取纳斯达克100实时行情...")
    df = fetch_sina_us_realtime(NASDAQ100_TICKERS)
    if df.empty:
        print("  ⚠️  返回数据为空")
    else:
        print(f"  ✅ 成功获取 {len(df)} 只成分股数据")
    return df


def display_results(df: pd.DataFrame) -> None:
    """美化打印结果"""
    session = get_market_session()
    now_str = datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S")
    et_str = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S %Z")

    header = (
        "\n"
        "=" * 92 + "\n"
        f"  📊 纳斯达克100 成分股实时涨幅排行\n"
        f"  🕐 北京时间: {now_str}  |  美东时间: {et_str}\n"
        f"  📡 交易时段: {session}\n"
        f"  📈 成分股数量: {len(df)}  (共监控 {len(NASDAQ100_TICKERS)} 只)\n"
        "=" * 92
    )
    print(header)

    if df.empty:
        print("  暂无数据\n")
        return

    # ── 涨幅 Top 10 ──
    _print_table("🔺 涨幅 Top 10", df.head(10))

    # ── 跌幅 Top 10 ──
    _print_table("🔻 跌幅 Top 10", df.tail(10).iloc[::-1])

    # ── 统计 ──
    valid = df["涨跌幅"].dropna()
    up = (valid > 0).sum()
    down = (valid < 0).sum()
    flat = (valid == 0).sum()
    avg = valid.mean() if len(valid) > 0 else 0

    print(f"\n  📊 统计: 上涨 {up} 只 | 下跌 {down} 只 | 平盘 {flat} 只 | 平均涨幅 {avg:+.2f}%")
    print("=" * 92 + "\n")


def _print_table(title: str, sub_df: pd.DataFrame) -> None:
    """打印排行表格"""
    print(f"\n  {title}:")
    print("  " + "-" * 86)
    fmt = "  {arrow} {rank:>3}. {ticker:<7s} {name:<14s}  {price:>10s}  {pct:>8s}  {chg:>8s}  {vol:>12s}"
    print(f"  {'':>6} {'Ticker':<7s} {'名称':<14s}  {'最新价':>10s}  {'涨跌幅':>8s}  {'涨跌额':>8s}  {'成交量':>12s}")
    print("  " + "-" * 86)

    for idx, row in sub_df.iterrows():
        pct = row.get("涨跌幅")
        price = row.get("最新价")
        chg = row.get("涨跌额")
        vol = row.get("成交量")
        name = str(row.get("名称", ""))[:12]
        ticker = row.get("ticker", "")
        arrow = "🟢" if pct and pct > 0 else ("🔴" if pct and pct < 0 else "⚪")

        print(fmt.format(
            arrow=arrow,
            rank=idx,
            ticker=ticker,
            name=name,
            price=f"${price:.2f}" if pd.notna(price) else "N/A",
            pct=f"{pct:+.2f}%" if pd.notna(pct) else "N/A",
            chg=f"{chg:+.2f}" if pd.notna(chg) else "N/A",
            vol=f"{vol:,}" if pd.notna(vol) else "N/A",
        ))


def save_to_mysql(df: pd.DataFrame) -> None:
    """将数据保存到 MySQL"""
    if df.empty:
        return
    now_cn = datetime.now(CN).strftime("%Y-%m-%d %H:%M:%S")
    now_et = datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S %Z")
    session_str = get_market_session()
    # 解析 session_code
    code_map = {"盘前": "pre", "盘中": "regular", "盘后": "after", "休市": "closed", "周末": "closed"}
    session_code = "closed"
    for k, v in code_map.items():
        if k in session_str:
            session_code = v
            break
    session = {"code": session_code, "label": session_str}

    # 构造 stocks list (与 server.py 格式一致)
    stocks = []
    for _, row in df.iterrows():
        stocks.append({
            "ticker": row.get("ticker"),
            "name": row.get("名称"),
            "price": row.get("最新价"),
            "changePercent": row.get("涨跌幅"),
            "change": row.get("涨跌额"),
            "open": row.get("昨收价"),
            "high": row.get("最高价"),
            "low": row.get("最低价"),
            "high52w": row.get("52周高"),
            "low52w": row.get("52周低"),
            "volume": row.get("成交量"),
            "marketCap": row.get("总市值"),
            "pe": row.get("市盈率"),
            "prevClose": None,
            "afterHoursPrice": None,
            "afterHoursChangePct": None,
            "afterHoursChange": None,
            "updateTime": row.get("更新时间"),
        })

    pcts = [s["changePercent"] for s in stocks if s.get("changePercent") is not None]
    up = sum(1 for p in pcts if p > 0)
    down = sum(1 for p in pcts if p < 0)
    flat = sum(1 for p in pcts if p == 0)
    avg = round(sum(pcts) / len(pcts), 2) if pcts else 0
    stats = {"total": len(stocks), "up": up, "down": down, "flat": flat, "avgChange": avg}

    batch_id = db.next_batch_id()
    db.save_snapshot(batch_id, stocks, now_cn, now_et, session, stats)
    print(f"  💾 数据已保存到 MySQL (batch #{batch_id}, {len(stocks)} 条)")


# ═══════════════════════════════════════════════════════════════════════
#  主循环
# ═══════════════════════════════════════════════════════════════════════
def main():
    """主循环: 每1分钟拉取一次"""
    interval = 60  # 秒

    print("🚀 纳斯达克100成分股实时涨幅监控启动")
    print(f"   刷新间隔: {interval}s")
    print(f"   监控股票数: {len(NASDAQ100_TICKERS)}")
    print(f"   数据来源: 新浪财经美股实时行情 (hq.sinajs.cn)")
    print(f"   交易时段: {get_market_session()}")
    print(f"   数据存储: MySQL (trader)")
    print(f"   按 Ctrl+C 停止\n")

    # 初始化 MySQL 表
    db.init_tables()

    cycle = 0
    while True:
        try:
            cycle += 1
            print(f"\n{'─' * 42} 第 {cycle} 轮 {'─' * 42}")

            df = fetch_nasdaq100_realtime()
            display_results(df)
            save_to_mysql(df)

            print(f"  ⏳ {interval}s 后刷新...")
            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
            break
        except Exception as e:
            print(f"\n  ❌ 异常: {e}")
            import traceback
            traceback.print_exc()
            print(f"  ⏳ {interval}s 后重试...")
            time.sleep(interval)


if __name__ == "__main__":
    main()
