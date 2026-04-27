import json
from datetime import date, timedelta
import db

def test_index_returns_200(client):
    resp = client.get('/')
    assert resp.status_code == 200

def test_index_shows_exercise_name(client, tmp_db):
    db.add_exercise('Push-ups')
    resp = client.get('/')
    assert b'Push-ups' in resp.data

def test_history_returns_200(client):
    resp = client.get('/history?week=-1')
    assert resp.status_code == 200

def test_history_clamps_future_week(client):
    resp = client.get('/history?week=1')
    assert resp.status_code == 200

def test_admin_exercises_get(client):
    resp = client.get('/admin/exercises')
    assert resp.status_code == 200

def test_admin_exercises_add(client, tmp_db):
    resp = client.post(
        '/admin/exercises',
        data={'action': 'add', 'name': 'Squats'},
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert b'Squats' in resp.data

def test_admin_exercises_delete(client, tmp_db):
    db.add_exercise('Lunges')
    ex_id = db.get_active_exercises()[0]['id']
    resp = client.post(
        '/admin/exercises',
        data={'action': 'delete', 'exercise_id': str(ex_id)},
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert b'Lunges' not in resp.data

def test_admin_plan_get(client):
    resp = client.get('/admin/plan')
    assert resp.status_code == 200

def test_admin_plan_save(client, tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    resp = client.post(
        '/admin/plan',
        data={f'plan_{ex_id}_0': '20', f'plan_{ex_id}_2': '25'},
        follow_redirects=True
    )
    assert resp.status_code == 200
    plan = db.get_weekly_plan()
    assert plan[(ex_id, 0)] == 20
    assert plan[(ex_id, 2)] == 25

def test_api_log(client, tmp_db):
    db.add_exercise('Pull-ups')
    ex_id = db.get_active_exercises()[0]['id']
    today_str = date.today().isoformat()
    resp = client.post(
        '/api/log',
        data=json.dumps({'exercise_id': ex_id, 'date': today_str, 'actual_reps': 8}),
        content_type='application/json'
    )
    assert resp.status_code == 200
    assert resp.get_json() == {'ok': True}
    monday = date.today() - timedelta(days=date.today().weekday())
    logs = db.get_week_logs(monday)
    assert logs[(ex_id, today_str)] == 8
