import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LEADERBOARD_FILE = BASE_DIR / "leaderboard.json"
SETTINGS_FILE = BASE_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "sound": True,
    "car_color": [40, 120, 220],
    "difficulty": "normal",
}


def load_json(path, default):
    if not path.exists():
        save_json(path, default)
        return default.copy() if isinstance(default, dict) else list(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default.copy() if isinstance(default, dict) else list(default)


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    settings.update(load_json(SETTINGS_FILE, DEFAULT_SETTINGS))
    return settings


def save_settings(settings):
    save_json(SETTINGS_FILE, settings)


def load_leaderboard():
    return load_json(LEADERBOARD_FILE, [])


def add_score(name, score, distance, coins):
    rows = load_leaderboard()
    rows.append({"name": name or "Player", "score": int(score), "distance": int(distance), "coins": int(coins)})
    rows.sort(key=lambda row: row["score"], reverse=True)
    save_json(LEADERBOARD_FILE, rows[:10])
