import requests
from app.config import NASDAQ100_TICKERS, SINA_HQ_URL, SINA_BATCH_SIZE, SINA_HEADERS, SINA_TIMEOUT
from app.model.stock import StockQuote


def _float(s):
    try:
        return round(float(s), 4) if s else None
    except (ValueError, TypeError):
        return None


def _int(s):
    try:
        return int(s) if s else None
    except (ValueError, TypeError):
        return None


def fetch_quotes(tickers: list[str] | None = None) -> list[StockQuote]:
    tickers = tickers or NASDAQ100_TICKERS
    quotes: list[StockQuote] = []

    for i in range(0, len(tickers), SINA_BATCH_SIZE):
        batch = tickers[i:i + SINA_BATCH_SIZE]
        symbol_str = ",".join(f"gb_{t.lower()}" for t in batch)
        try:
            r = requests.get(f"{SINA_HQ_URL}{symbol_str}", timeout=SINA_TIMEOUT, headers=SINA_HEADERS)
            r.encoding = "gbk"
        except Exception as e:
            print(f"  [WARN] batch {i // SINA_BATCH_SIZE + 1} failed: {e}")
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
            f = data_str.split(",")
            if len(f) < 27:
                continue
            try:
                quotes.append(StockQuote(
                    ticker=ticker, name=f[0], price=_float(f[1]),
                    change_pct=_float(f[2]), change_amt=_float(f[4]),
                    open_price=_float(f[5]), high_price=_float(f[6]),
                    low_price=_float(f[7]), high_52w=_float(f[8]),
                    low_52w=_float(f[9]), volume=_int(f[10]),
                    market_cap=_float(f[12]),
                    pe=_float(f[13]) if len(f) > 13 else None,
                    prev_close=_float(f[26]),
                    ah_price=_float(f[21]), ah_change_pct=_float(f[22]),
                    ah_change_amt=_float(f[23]),
                    ah_time=f[24].strip() if len(f) > 24 else None,
                    regular_close_time=f[25].strip() if len(f) > 25 else None,
                    src_update_time=f[3],
                ))
            except (ValueError, IndexError):
                continue

    quotes.sort(key=lambda q: (q.change_pct if q.change_pct is not None else -9999), reverse=True)
    for i, q in enumerate(quotes, 1):
        q.rank = i
    return quotes
