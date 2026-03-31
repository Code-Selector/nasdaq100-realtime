#!/usr/bin/env python3
import os, time
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)

from app.config import NASDAQ100_TICKERS, FETCH_INTERVAL
from app.database import init_pool
from app.dao.stock_dao import init_tables
from app.service import fetch_service, market_service
from app.model.stock import StockQuote


def display(stocks: list[StockQuote]):
    session = market_service.get_market_session()
    stats = market_service.compute_stats(stocks)
    print(f"\n{'=' * 80}")
    print(f"  Nasdaq100 | {market_service.now_cn_str()} | {session['label']} | {len(stocks)} stocks")
    print(f"{'=' * 80}")
    if not stocks:
        return
    fmt = "  {r:>3}. {t:<7s} {n:<14s} {p:>10s} {pct:>8s} {v:>12s}"
    for title, items in [("Top 10 Gainers", stocks[:10]), ("Top 10 Losers", stocks[-10:][::-1])]:
        print(f"\n  {title}:")
        for s in items:
            print(fmt.format(
                r=s.rank, t=s.ticker, n=(s.name or "")[:12],
                p=f"${s.price:.2f}" if s.price else "N/A",
                pct=f"{s.change_pct:+.2f}%" if s.change_pct is not None else "N/A",
                v=f"{s.volume:,}" if s.volume else "N/A",
            ))
    print(f"\n  ↑{stats['up']} ↓{stats['down']} avg:{stats['avg_change']:+.2f}%")


def main():
    print(f"Nasdaq100 CLI monitor (interval {FETCH_INTERVAL}s, {len(NASDAQ100_TICKERS)} tickers)")
    init_pool()
    init_tables()
    cycle = 0
    while True:
        try:
            cycle += 1
            stocks = fetch_service.fetch_quotes()
            display(stocks)
            if stocks:
                session = market_service.get_market_session()
                stats = market_service.compute_stats(stocks)
                bid = market_service.save_batch(stocks, session, stats)
                print(f"  saved batch #{bid}")
            time.sleep(FETCH_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"  [ERR] {e}")
            time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
