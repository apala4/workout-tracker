import sqlite3
from datetime import timedelta

DATABASE = 'workout.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercises (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            deleted_at TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS weekly_plan (
            exercise_id  INTEGER NOT NULL REFERENCES exercises(id),
            weekday      INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
            planned_reps INTEGER NOT NULL,
            plan_note    TEXT DEFAULT NULL,
            PRIMARY KEY (exercise_id, weekday)
        );
        CREATE TABLE IF NOT EXISTS workout_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL REFERENCES exercises(id),
            date        DATE NOT NULL,
            actual_reps INTEGER NOT NULL,
            UNIQUE (exercise_id, date)
        );
        CREATE TABLE IF NOT EXISTS workout_notes (
            exercise_id INTEGER NOT NULL REFERENCES exercises(id),
            date        DATE NOT NULL,
            note        TEXT NOT NULL,
            PRIMARY KEY (exercise_id, date)
        );
    """)
    conn.commit()
    conn.close()

def get_active_exercises():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name FROM exercises WHERE deleted_at IS NULL ORDER BY name"
    ).fetchall()
    conn.close()
    return rows

def get_weekly_plan():
    conn = get_db()
    rows = conn.execute(
        "SELECT exercise_id, weekday, planned_reps FROM weekly_plan"
    ).fetchall()
    conn.close()
    return {(r['exercise_id'], r['weekday']): r['planned_reps'] for r in rows}

def get_week_logs(week_start):
    week_end = week_start + timedelta(days=6)
    conn = get_db()
    rows = conn.execute(
        "SELECT exercise_id, date, actual_reps FROM workout_logs "
        "WHERE date BETWEEN ? AND ?",
        (week_start.isoformat(), week_end.isoformat())
    ).fetchall()
    conn.close()
    return {(r['exercise_id'], r['date']): r['actual_reps'] for r in rows}

def add_exercise(name):
    conn = get_db()
    conn.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def delete_exercise(exercise_id):
    conn = get_db()
    conn.execute(
        "UPDATE exercises SET deleted_at = datetime('now') WHERE id = ?",
        (exercise_id,)
    )
    conn.execute("DELETE FROM weekly_plan WHERE exercise_id = ?", (exercise_id,))
    conn.commit()
    conn.close()

def save_weekly_plan(plan):
    conn = get_db()
    active_ids = [
        r['id'] for r in conn.execute(
            "SELECT id FROM exercises WHERE deleted_at IS NULL"
        ).fetchall()
    ]
    if active_ids:
        placeholders = ','.join('?' * len(active_ids))
        conn.execute(
            f"DELETE FROM weekly_plan WHERE exercise_id IN ({placeholders})",
            active_ids
        )
    for exercise_id, weekday, planned_reps in plan:
        conn.execute(
            "INSERT INTO weekly_plan (exercise_id, weekday, planned_reps) VALUES (?, ?, ?)",
            (exercise_id, weekday, planned_reps)
        )
    conn.commit()
    conn.close()

def log_workout(exercise_id, date_str, actual_reps):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO workout_logs (exercise_id, date, actual_reps) VALUES (?, ?, ?)",
        (exercise_id, date_str, actual_reps)
    )
    conn.commit()
    conn.close()
