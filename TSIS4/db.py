import psycopg2
from psycopg2.extras import RealDictCursor

from config import DB_CONFIG


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    score INTEGER NOT NULL,
    level_reached INTEGER NOT NULL,
    played_at TIMESTAMP DEFAULT NOW()
);
"""


class Database:
    def __init__(self):
        # Если база недоступна, игра все равно запустится, но leaderboard отключится.
        self.available = False
        self.last_error = ""
        try:
            with self.connect() as conn, conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            self.available = True
        except Exception as exc:
            self.last_error = str(exc)

    def connect(self):
        return psycopg2.connect(**DB_CONFIG)

    def ensure_player(self, username):
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO players(username) VALUES(%s) ON CONFLICT(username) DO UPDATE SET username = EXCLUDED.username RETURNING id",
                (username,),
            )
            return cur.fetchone()[0]

    def save_result(self, username, score, level):
        if not self.available:
            return
        player_id = self.ensure_player(username)
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO game_sessions(player_id, score, level_reached) VALUES(%s, %s, %s)",
                (player_id, score, level),
            )

    def personal_best(self, username):
        if not self.available or not username:
            return 0
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(MAX(gs.score), 0)
                FROM game_sessions gs
                JOIN players p ON p.id = gs.player_id
                WHERE p.username = %s
                """,
                (username,),
            )
            return cur.fetchone()[0]

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
