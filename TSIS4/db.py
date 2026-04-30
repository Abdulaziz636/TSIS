from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_CONFIG


SCHEMA_FILE = Path(__file__).with_name("schema.sql")


class Database:
    def __init__(self):
        self.available = False
        self.last_error = ""
        try:
            with self.connect() as conn, conn.cursor() as cur:
                cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
            self.available = True
        except Exception as exc:
            self.last_error = str(exc)

    def connect(self):
        return psycopg2.connect(**DB_CONFIG)

    def one_value(self, sql, params=()):
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]

    def ensure_player(self, username):
        return self.one_value(
            """
            INSERT INTO players(username)
            VALUES(%s)
            ON CONFLICT(username) DO UPDATE SET username = EXCLUDED.username
            RETURNING id
            """,
            (username,),
        )

    def save_result(self, username, score, level):
        if not self.available:
            return
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO game_sessions(player_id, score, level_reached) VALUES(%s, %s, %s)",
                (self.ensure_player(username), score, level),
            )

    def personal_best(self, username):
        if not self.available or not username:
            return 0
        return self.one_value(
            """
            SELECT COALESCE(MAX(gs.score), 0)
            FROM game_sessions gs
            JOIN players p ON p.id = gs.player_id
            WHERE p.username = %s
            """,
            (username,),
        )

    def top10(self):
        if not self.available:
            return []
        with self.connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT p.username, gs.score, gs.level_reached, gs.played_at
                FROM game_sessions gs
                JOIN players p ON p.id = gs.player_id
                ORDER BY gs.score DESC, gs.played_at ASC
                LIMIT 10
                """
            )
            return cur.fetchall()
