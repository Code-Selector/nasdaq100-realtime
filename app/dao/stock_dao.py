from app.database import get_conn
from app.model.stock import DDL_SNAPSHOT, DDL_FETCH_LOG


def init_tables():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL_SNAPSHOT)
            cur.execute(DDL_FETCH_LOG)


def next_batch_id() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(batch_id), 0) + 1 AS nxt FROM nasdaq100_fetch_log")
            return cur.fetchone()["nxt"]


def insert_snapshot(batch_id: int, stocks: list, fetched_at: str):
    sql = """
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
    rows = [{
        "batch_id": batch_id, "ticker": s.ticker, "name": s.name,
        "price": s.price, "change_pct": s.change_pct, "change_amt": s.change_amt,
        "open_price": s.open_price, "high_price": s.high_price, "low_price": s.low_price,
        "high_52w": s.high_52w, "low_52w": s.low_52w,
        "volume": s.volume, "market_cap": s.market_cap, "pe": s.pe,
        "prev_close": s.prev_close,
        "ah_price": s.ah_price, "ah_change_pct": s.ah_change_pct,
        "ah_change_amt": s.ah_change_amt, "ah_time": s.ah_time,
        "regular_close_time": s.regular_close_time,
        "src_update_time": s.src_update_time, "fetched_at": fetched_at,
    } for s in stocks]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)


def insert_fetch_log(batch_id: int, fetched_at: str, fetched_et: str,
                     session: dict, stats: dict):
    sql = """
        INSERT INTO nasdaq100_fetch_log
            (batch_id, fetched_at, fetched_et, stock_count,
             avg_change, up_count, down_count, flat_count,
             session_code, session_label)
        VALUES
            (%(batch_id)s, %(fetched_at)s, %(fetched_et)s, %(stock_count)s,
             %(avg_change)s, %(up_count)s, %(down_count)s, %(flat_count)s,
             %(session_code)s, %(session_label)s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "batch_id": batch_id, "fetched_at": fetched_at,
                "fetched_et": fetched_et, "stock_count": stats["total"],
                "avg_change": stats["avg_change"],
                "up_count": stats["up"], "down_count": stats["down"],
                "flat_count": stats["flat"],
                "session_code": session["code"], "session_label": session["label"],
            })


def query_latest_batch() -> tuple[dict | None, list[dict]]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM nasdaq100_fetch_log ORDER BY batch_id DESC LIMIT 1")
            log = cur.fetchone()
            if not log:
                return None, []
            cur.execute(
                "SELECT * FROM nasdaq100_snapshot WHERE batch_id = %s ORDER BY change_pct DESC",
                (log["batch_id"],),
            )
            return log, cur.fetchall()


def query_history(limit: int = 60) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT fetched_at, avg_change, up_count, down_count "
                "FROM nasdaq100_fetch_log ORDER BY batch_id DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    rows.reverse()
    return rows


def query_max_batch_id() -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(batch_id), 0) FROM nasdaq100_fetch_log")
            return list(cur.fetchone().values())[0]
