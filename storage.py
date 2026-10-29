"""SQLite progress log and JSON profile storage."""
import json
import random
import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

DATA = Path(__file__).parent / "data"
DB = DATA / "athlete.db"
PROFILES = DATA / "profiles"

SCHEMA = """CREATE TABLE IF NOT EXISTS logs(
 id INTEGER PRIMARY KEY AUTOINCREMENT, athlete TEXT, day TEXT, weight_kg REAL, sleep_h REAL,
 resting_hr INTEGER, workout_min INTEGER, rpe INTEGER, mood INTEGER, notes TEXT)"""


def _conn():
    DATA.mkdir(exist_ok=True)
    PROFILES.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def readiness(sleep_h: float, mood: int, rpe: int) -> int:
    """Simple 0-100 heuristic: sleep 40%, mood 30%, low effort yesterday 30%."""
    s = min(sleep_h / 8, 1) * 40
    m = (mood - 1) / 4 * 30
    r = (10 - rpe) / 9 * 30
    return round(max(0, min(100, s + m + r)))


def add_log(athlete, day, weight_kg, sleep_h, resting_hr, workout_min, rpe, mood, notes=""):
    with closing(_conn()) as c, c:
        c.execute(
            "INSERT INTO logs(athlete,day,weight_kg,sleep_h,resting_hr,workout_min,rpe,mood,notes)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (athlete, str(day), weight_kg, sleep_h, resting_hr, workout_min, rpe, mood, notes),
        )


def get_logs(athlete: str, days: Optional[int] = None) -> list[dict]:
    sql, args = "SELECT * FROM logs WHERE athlete=?", [athlete]
    if days:
        sql += " AND day>=?"
        args.append(str(date.today() - timedelta(days=days)))
    with closing(_conn()) as c:
        rows = [dict(r) for r in c.execute(sql + " ORDER BY day ASC, id ASC", args)]
    for r in rows:
        r["readiness"] = readiness(r["sleep_h"], r["mood"], r["rpe"])
    return rows


def clear_logs(athlete: str):
    with closing(_conn()) as c, c:
        c.execute("DELETE FROM logs WHERE athlete=?", (athlete,))


def add_demo_data(athlete: str, days: int = 14):
    rnd = random.Random(7)
    w = 70.0
    for i in range(days, 0, -1):
        w += rnd.uniform(-0.25, 0.15)
        add_log(athlete, date.today() - timedelta(days=i), round(w, 1), round(rnd.uniform(5.5, 8.5), 1),
                rnd.randint(52, 62), rnd.choice([0, 45, 60, 75, 90]), rnd.randint(3, 9), rnd.randint(2, 5))


def save_profile(name: str, data: dict):
    _conn().close()
    (PROFILES / f"{re.sub(r'[^A-Za-z0-9_-]', '_', name) or 'athlete'}.json").write_text(json.dumps(data, indent=2))


def list_profiles() -> list[str]:
    _conn().close()
    return sorted(p.stem for p in PROFILES.glob("*.json"))


def load_profile(stem: str) -> dict:
    return json.loads((PROFILES / f"{stem}.json").read_text())


def make_progress_tool(athlete: str):
    """A tool bound to one athlete so the Performance Analyst can read their log."""

    @tool
    def get_progress_log(days: int = 14) -> dict:
        """Read the athlete's logged weight, sleep, resting HR, workout minutes, effort (RPE), mood
        and readiness for the last N days. Use it before judging progress."""
        rows = get_logs(athlete, days)
        if not rows:
            return {"entries": 0, "note": "No data logged yet. Ask the athlete to log a few days."}
        keep = ("day", "weight_kg", "sleep_h", "resting_hr", "workout_min", "rpe", "mood", "readiness", "notes")
        return {"entries": len(rows), "rows": [{k: r[k] for k in keep} for r in rows]}

    return get_progress_log
