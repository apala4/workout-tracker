from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import date, timedelta
import db

app = Flask(__name__)

def _week_start(offset=0):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(weeks=offset)

@app.route('/')
def index():
    today = date.today()
    monday = _week_start(0)
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    exercises = db.get_active_exercises()
    plan = db.get_weekly_plan()
    plan_notes = db.get_plan_notes()
    logs = db.get_week_logs(monday)
    notes = db.get_week_notes(monday)
    return render_template('index.html',
        exercises=exercises, plan=plan, plan_notes=plan_notes,
        logs=logs, notes=notes,
        week_dates=week_dates, today=today)

@app.route('/history')
def history():
    try:
        offset = int(request.args.get('week', -1))
    except ValueError:
        offset = -1
    if offset >= 0:
        offset = -1
    monday = _week_start(offset)
    week_dates = [monday + timedelta(days=i) for i in range(7)]
    exercises = db.get_active_exercises()
    plan = db.get_weekly_plan()
    logs = db.get_week_logs(monday)
    return render_template('history.html',
        exercises=exercises, plan=plan, logs=logs,
        week_dates=week_dates, offset=offset)

@app.route('/admin/exercises', methods=['GET', 'POST'])
def admin_exercises():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name', '').strip()
            if name:
                db.add_exercise(name)
        elif action == 'delete':
            db.delete_exercise(int(request.form.get('exercise_id')))
        return redirect(url_for('admin_exercises'))
    return render_template('admin_exercises.html',
        exercises=db.get_active_exercises())

@app.route('/admin/plan', methods=['GET', 'POST'])
def admin_plan():
    if request.method == 'POST':
        exercises = db.get_active_exercises()
        plan = []
        notes = {}
        for ex in exercises:
            for weekday in range(7):
                val = request.form.get(f'plan_{ex["id"]}_{weekday}', '').strip()
                note = request.form.get(f'plan_note_{ex["id"]}_{weekday}', '').strip()
                if val.isdigit() and int(val) > 0:
                    plan.append((ex['id'], weekday, int(val)))
                    if note:
                        notes[(ex['id'], weekday)] = note
        db.save_weekly_plan(plan, notes)
        return redirect(url_for('admin_plan'))
    exercises = db.get_active_exercises()
    plan = db.get_weekly_plan()
    plan_notes = db.get_plan_notes()
    return render_template('admin_plan.html', exercises=exercises, plan=plan, plan_notes=plan_notes)

@app.route('/api/log', methods=['POST'])
def api_log():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'ok': False, 'error': 'invalid json'}), 400
    db.log_workout(int(data['exercise_id']), data['date'], int(data['actual_reps']))
    return jsonify({'ok': True})

@app.route('/api/note', methods=['POST'])
def api_note():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'ok': False, 'error': 'invalid json'}), 400
    db.save_note(int(data['exercise_id']), data['date'], data.get('note', '').strip())
    return jsonify({'ok': True})

if __name__ == '__main__':
    db.init_db()
    app.run(host='0.0.0.0', port=5000)
