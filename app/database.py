import pymysql
from contextlib import contextmanager
from dbutils.pooled_db import PooledDB
from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET

_pool: PooledDB | None = None


def init_pool():
    global _pool
    _pool = PooledDB(
        creator=pymysql, maxconnections=10, mincached=2, blocking=True,
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset=DB_CHARSET, cursorclass=pymysql.cursors.DictCursor,
    )


@contextmanager
def get_conn():
    if _pool is None:
        init_pool()
    conn = _pool.connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
