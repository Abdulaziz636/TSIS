from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_CONFIG


BASE_DIR = Path(__file__).resolve().parent


def get_connection(dict_rows=False):
    cursor_factory = RealDictCursor if dict_rows else None
    return psycopg2.connect(**DB_CONFIG, cursor_factory=cursor_factory)


def run_sql_file(filename):
    sql_path = BASE_DIR / filename
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text(encoding="utf-8"))
