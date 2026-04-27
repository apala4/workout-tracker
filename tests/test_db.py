from datetime import date, timedelta
import db

def test_init_creates_tables(tmp_db):
    conn = db.get_db()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert {'exercises', 'weekly_plan', 'workout_logs'}.issubset(tables)

def test_add_and_get_exercise(tmp_db):
    db.add_exercise('Push-ups')
    exercises = db.get_active_exercises()
    assert len(exercises) == 1
    assert exercises[0]['name'] == 'Push-ups'

def test_delete_exercise_soft_deletes(tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    db.delete_exercise(ex_id)
    assert db.get_active_exercises() == []
    conn = db.get_db()
    row = conn.execute(
        "SELECT deleted_at FROM exercises WHERE id = ?", (ex_id,)
    ).fetchone()
    conn.close()
    assert row['deleted_at'] is not None

def test_delete_exercise_removes_plan_rows(tmp_db):
    db.add_exercise('Squats')
    ex_id = db.get_active_exercises()[0]['id']
    db.save_weekly_plan([(ex_id, 0, 20)])
    db.delete_exercise(ex_id)
    assert db.get_weekly_plan() == {}

def test_save_and_get_weekly_plan(tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    db.save_weekly_plan([(ex_id, 0, 20), (ex_id, 2, 25)])
    plan = db.get_weekly_plan()
    assert plan[(ex_id, 0)] == 20
    assert plan[(ex_id, 2)] == 25
    assert (ex_id, 1) not in plan

def test_save_weekly_plan_replaces_existing(tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    db.save_weekly_plan([(ex_id, 0, 20)])
    db.save_weekly_plan([(ex_id, 1, 15)])
    plan = db.get_weekly_plan()
    assert (ex_id, 0) not in plan
    assert plan[(ex_id, 1)] == 15

def test_log_workout_and_retrieve(tmp_db):
    db.add_exercise('Pull-ups')
    ex_id = db.get_active_exercises()[0]['id']
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db.log_workout(ex_id, today.isoformat(), 15)
    logs = db.get_week_logs(monday)
    assert logs[(ex_id, today.isoformat())] == 15

def test_log_workout_replaces_existing(tmp_db):
    db.add_exercise('Pull-ups')
    ex_id = db.get_active_exercises()[0]['id']
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db.log_workout(ex_id, today.isoformat(), 10)
    db.log_workout(ex_id, today.isoformat(), 12)
    logs = db.get_week_logs(monday)
    assert logs[(ex_id, today.isoformat())] == 12
