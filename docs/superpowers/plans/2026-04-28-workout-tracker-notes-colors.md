# Workout Tracker Phase 2: Notes + Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add free-text note fields per (exercise × day) in the Plan and This Week tabs, and apply visual polish (gray rows, yellow headers, full grid borders).

**Architecture:** Extend `weekly_plan` with a `plan_note` column and add a new `workout_notes` table for per-date overrides. `get_weekly_plan()` stays unchanged (returns reps only); new `get_plan_notes()` returns the weekly note defaults. A new `/api/note` endpoint handles per-date note saves. JS auto-saves on blur. CSS replaces the minimal row hints with a full grid style.

**Tech Stack:** Python 3 / Flask 3 / SQLite / Jinja2 / vanilla JS / pytest

---

### Task 1: Extend schema in init_db()

**Files:**
- Modify: `db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write failing test for workout_notes table**

Add to `tests/test_db.py`:

```python
def test_init_creates_workout_notes_table(tmp_db):
    conn = db.get_db()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert 'workout_notes' in tables
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /home/apala4/claude/workout-tracker
python3 -m pytest tests/test_db.py::test_init_creates_workout_notes_table -v
```
Expected: FAILED — `AssertionError: assert 'workout_notes' in ...`

- [ ] **Step 3: Write failing test for plan_note column**

Add to `tests/test_db.py`:

```python
def test_weekly_plan_has_plan_note_column(tmp_db):
    conn = db.get_db()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(weekly_plan)").fetchall()}
    conn.close()
    assert 'plan_note' in cols
```

- [ ] **Step 4: Run to verify it fails**

```bash
python3 -m pytest tests/test_db.py::test_weekly_plan_has_plan_note_column -v
```
Expected: FAILED

- [ ] **Step 5: Update init_db() in db.py**

Replace the `executescript` body inside `init_db()`:

```python
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
```

- [ ] **Step 6: Run both new tests**

```bash
python3 -m pytest tests/test_db.py::test_init_creates_workout_notes_table tests/test_db.py::test_weekly_plan_has_plan_note_column -v
```
Expected: Both PASSED

- [ ] **Step 7: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass (tmp_db fixture creates a fresh DB per test).

- [ ] **Step 8: Delete workout.db and restart app**

```bash
rm -f /home/apala4/claude/workout-tracker/workout.db
pkill -f "python3 app.py" 2>/dev/null || true
cd /home/apala4/claude/workout-tracker && python3 app.py &
sleep 1
curl -s http://localhost:5000/ | grep -c 'table' && echo "app running"
```

- [ ] **Step 9: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: extend schema with plan_note column and workout_notes table"
```

---

### Task 2: Add get_plan_notes() and update save_weekly_plan() to persist notes

**Files:**
- Modify: `db.py`
- Modify: `tests/test_db.py`

`get_plan_notes()` returns `{(exercise_id, weekday): plan_note}` for rows where plan_note is not NULL.  
`save_weekly_plan(plan, notes=None)` gains an optional `notes` dict `{(exercise_id, weekday): note_str}`; existing callers using 3-tuples still work unchanged.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_db.py`:

```python
def test_get_plan_notes_empty(tmp_db):
    assert db.get_plan_notes() == {}

def test_save_and_get_plan_notes(tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    db.save_weekly_plan(
        [(ex_id, 0, 20), (ex_id, 2, 25)],
        notes={(ex_id, 0): '10kg', (ex_id, 2): 'bodyweight'}
    )
    notes = db.get_plan_notes()
    assert notes[(ex_id, 0)] == '10kg'
    assert notes[(ex_id, 2)] == 'bodyweight'
    assert (ex_id, 1) not in notes

def test_save_plan_notes_replaces_with_plan(tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    db.save_weekly_plan([(ex_id, 0, 20)], notes={(ex_id, 0): 'heavy'})
    db.save_weekly_plan([(ex_id, 0, 20)], notes={(ex_id, 0): 'light'})
    assert db.get_plan_notes()[(ex_id, 0)] == 'light'

def test_save_weekly_plan_without_notes_clears_notes(tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    db.save_weekly_plan([(ex_id, 0, 20)], notes={(ex_id, 0): 'heavy'})
    db.save_weekly_plan([(ex_id, 0, 20)])
    assert db.get_plan_notes() == {}
```

- [ ] **Step 2: Run to verify all four fail**

```bash
python3 -m pytest tests/test_db.py::test_get_plan_notes_empty tests/test_db.py::test_save_and_get_plan_notes tests/test_db.py::test_save_plan_notes_replaces_with_plan tests/test_db.py::test_save_weekly_plan_without_notes_clears_notes -v
```
Expected: All FAILED (AttributeError: module 'db' has no attribute 'get_plan_notes')

- [ ] **Step 3: Add get_plan_notes() and update save_weekly_plan() in db.py**

Add `get_plan_notes` after `get_weekly_plan`:

```python
def get_plan_notes():
    conn = get_db()
    rows = conn.execute(
        "SELECT exercise_id, weekday, plan_note FROM weekly_plan WHERE plan_note IS NOT NULL"
    ).fetchall()
    conn.close()
    return {(r['exercise_id'], r['weekday']): r['plan_note'] for r in rows}
```

Replace `save_weekly_plan` with:

```python
def save_weekly_plan(plan, notes=None):
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
        note = (notes or {}).get((exercise_id, weekday)) or None
        conn.execute(
            "INSERT INTO weekly_plan (exercise_id, weekday, planned_reps, plan_note) "
            "VALUES (?, ?, ?, ?)",
            (exercise_id, weekday, planned_reps, note)
        )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run the four new tests**

```bash
python3 -m pytest tests/test_db.py::test_get_plan_notes_empty tests/test_db.py::test_save_and_get_plan_notes tests/test_db.py::test_save_plan_notes_replaces_with_plan tests/test_db.py::test_save_weekly_plan_without_notes_clears_notes -v
```
Expected: All PASSED

- [ ] **Step 5: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass (existing tests call `save_weekly_plan` with 3-tuples, which is still valid).

- [ ] **Step 6: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add get_plan_notes() and extend save_weekly_plan() to persist plan notes"
```

---

### Task 3: Add get_week_notes() and save_note() to db.py

**Files:**
- Modify: `db.py`
- Modify: `tests/test_db.py`

`get_week_notes(week_start)` returns `{(exercise_id, date_str): note}` for all workout_notes rows in that week.  
`save_note(exercise_id, date_str, note)` upserts; if note is empty string, deletes the row.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_db.py`:

```python
def test_get_week_notes_empty(tmp_db):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    assert db.get_week_notes(monday) == {}

def test_save_and_get_week_notes(tmp_db):
    db.add_exercise('Squats')
    ex_id = db.get_active_exercises()[0]['id']
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db.save_note(ex_id, today.isoformat(), 'felt strong')
    notes = db.get_week_notes(monday)
    assert notes[(ex_id, today.isoformat())] == 'felt strong'

def test_save_note_updates_existing(tmp_db):
    db.add_exercise('Squats')
    ex_id = db.get_active_exercises()[0]['id']
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db.save_note(ex_id, today.isoformat(), 'first')
    db.save_note(ex_id, today.isoformat(), 'second')
    notes = db.get_week_notes(monday)
    assert notes[(ex_id, today.isoformat())] == 'second'

def test_save_note_empty_string_deletes(tmp_db):
    db.add_exercise('Squats')
    ex_id = db.get_active_exercises()[0]['id']
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    db.save_note(ex_id, today.isoformat(), 'to delete')
    db.save_note(ex_id, today.isoformat(), '')
    assert db.get_week_notes(monday) == {}
```

- [ ] **Step 2: Run to verify all four fail**

```bash
python3 -m pytest tests/test_db.py::test_get_week_notes_empty tests/test_db.py::test_save_and_get_week_notes tests/test_db.py::test_save_note_updates_existing tests/test_db.py::test_save_note_empty_string_deletes -v
```
Expected: All FAILED

- [ ] **Step 3: Add get_week_notes() and save_note() in db.py**

Add after `get_week_logs`:

```python
def get_week_notes(week_start):
    week_end = week_start + timedelta(days=6)
    conn = get_db()
    rows = conn.execute(
        "SELECT exercise_id, date, note FROM workout_notes "
        "WHERE date BETWEEN ? AND ?",
        (week_start.isoformat(), week_end.isoformat())
    ).fetchall()
    conn.close()
    return {(r['exercise_id'], r['date']): r['note'] for r in rows}

def save_note(exercise_id, date_str, note):
    conn = get_db()
    if note:
        conn.execute(
            "INSERT OR REPLACE INTO workout_notes (exercise_id, date, note) VALUES (?, ?, ?)",
            (exercise_id, date_str, note)
        )
    else:
        conn.execute(
            "DELETE FROM workout_notes WHERE exercise_id = ? AND date = ?",
            (exercise_id, date_str)
        )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run new tests**

```bash
python3 -m pytest tests/test_db.py::test_get_week_notes_empty tests/test_db.py::test_save_and_get_week_notes tests/test_db.py::test_save_note_updates_existing tests/test_db.py::test_save_note_empty_string_deletes -v
```
Expected: All PASSED

- [ ] **Step 5: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add get_week_notes() and save_note() for per-date workout notes"
```

---

### Task 4: Add POST /api/note route

**Files:**
- Modify: `app.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_routes.py`:

```python
def test_api_note_saves_note(client, tmp_db):
    db.add_exercise('Squats')
    ex_id = db.get_active_exercises()[0]['id']
    today_str = date.today().isoformat()
    resp = client.post(
        '/api/note',
        data=json.dumps({'exercise_id': ex_id, 'date': today_str, 'note': 'felt great'}),
        content_type='application/json'
    )
    assert resp.status_code == 200
    assert resp.get_json() == {'ok': True}
    monday = date.today() - timedelta(days=date.today().weekday())
    notes = db.get_week_notes(monday)
    assert notes[(ex_id, today_str)] == 'felt great'

def test_api_note_invalid_json_returns_400(client):
    resp = client.post('/api/note', data='not-json', content_type='application/json')
    assert resp.status_code == 400
```

- [ ] **Step 2: Run to verify both fail**

```bash
python3 -m pytest tests/test_routes.py::test_api_note_saves_note tests/test_routes.py::test_api_note_invalid_json_returns_400 -v
```
Expected: Both FAILED (404)

- [ ] **Step 3: Add /api/note route to app.py**

Add after `api_log`:

```python
@app.route('/api/note', methods=['POST'])
def api_note():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'ok': False, 'error': 'invalid json'}), 400
    db.save_note(int(data['exercise_id']), data['date'], data.get('note', '').strip())
    return jsonify({'ok': True})
```

- [ ] **Step 4: Run new tests**

```bash
python3 -m pytest tests/test_routes.py::test_api_note_saves_note tests/test_routes.py::test_api_note_invalid_json_returns_400 -v
```
Expected: Both PASSED

- [ ] **Step 5: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_routes.py
git commit -m "feat: add POST /api/note endpoint for saving per-date workout notes"
```

---

### Task 5: Update admin/plan route and template with plan note inputs

**Files:**
- Modify: `app.py`
- Modify: `templates/admin_plan.html`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_routes.py`:

```python
def test_admin_plan_saves_plan_note(client, tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    resp = client.post(
        '/admin/plan',
        data={
            f'plan_{ex_id}_0': '20',
            f'plan_note_{ex_id}_0': '10kg',
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    notes = db.get_plan_notes()
    assert notes.get((ex_id, 0)) == '10kg'
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/test_routes.py::test_admin_plan_saves_plan_note -v
```
Expected: FAILED

- [ ] **Step 3: Update admin_plan route in app.py**

Replace the full `admin_plan` function:

```python
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
```

- [ ] **Step 4: Run new test**

```bash
python3 -m pytest tests/test_routes.py::test_admin_plan_saves_plan_note -v
```
Expected: PASSED

- [ ] **Step 5: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass.

- [ ] **Step 6: Update templates/admin_plan.html**

Replace the entire file:

```html
{% extends "base.html" %}
{% block content %}
<h1>Weekly Plan</h1>
{% if exercises %}
<form method="POST">
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Exercise</th>
          {% for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] %}
          <th>{{ day }}</th>
          {% endfor %}
        </tr>
      </thead>
      <tbody>
        {% for ex in exercises %}
        <tr>
          <td class="ex-name">{{ ex.name }}</td>
          {% for weekday in range(7) %}
          <td>
            <input type="number"
                   name="plan_{{ ex.id }}_{{ weekday }}"
                   value="{{ plan.get((ex.id, weekday), '') }}"
                   min="1"
                   placeholder="&mdash;"
                   class="plan-input">
            <input type="text"
                   name="plan_note_{{ ex.id }}_{{ weekday }}"
                   value="{{ plan_notes.get((ex.id, weekday), '') }}"
                   placeholder="note…"
                   class="plan-note-input">
          </td>
          {% endfor %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <button type="submit">Save</button>
</form>
{% else %}
<p>No exercises yet. <a href="{{ url_for('admin_exercises') }}">Add some first.</a></p>
{% endif %}
{% endblock %}
```

- [ ] **Step 7: Verify plan page renders note inputs**

```bash
curl -s http://localhost:5000/admin/plan | grep -c 'plan-note-input'
```
Expected: a number equal to the count of exercise×day cells (7 × number of exercises)

- [ ] **Step 8: Commit**

```bash
git add app.py templates/admin_plan.html tests/test_routes.py
git commit -m "feat: add plan note text field per exercise/day in Plan admin tab"
```

---

### Task 6: Update / route and index.html with per-day note inputs

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_routes.py`:

```python
def test_index_renders_note_inputs(client, tmp_db):
    db.add_exercise('Push-ups')
    ex_id = db.get_active_exercises()[0]['id']
    weekday = date.today().weekday()
    db.save_weekly_plan([(ex_id, weekday, 20)], notes={(ex_id, weekday): '10kg'})
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'note-input' in resp.data
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/test_routes.py::test_index_renders_note_inputs -v
```
Expected: FAILED

- [ ] **Step 3: Update index route in app.py**

Replace the full `index` function:

```python
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
```

- [ ] **Step 4: Run test — expect still FAILED (template not updated yet)**

```bash
python3 -m pytest tests/test_routes.py::test_index_renders_note_inputs -v
```
Expected: FAILED (b'note-input' not yet in template HTML)

- [ ] **Step 5: Replace templates/index.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>This Week</h1>
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Exercise</th>
        {% for d in week_dates %}
        <th class="{% if d == today %}today{% elif d < today %}past{% else %}future{% endif %}">
          {{ d.strftime('%a') }}<br><small>{{ d.strftime('%d') }}</small>
        </th>
        {% endfor %}
      </tr>
    </thead>
    <tbody>
      {% for ex in exercises %}
      <tr>
        <td class="ex-name">{{ ex.name }}</td>
        {% for d in week_dates %}
          {% set planned = plan.get((ex.id, d.weekday())) %}
          {% set logged = logs.get((ex.id, d.isoformat())) %}
          {% set plan_note = plan_notes.get((ex.id, d.weekday()), '') %}
          {% set note_val = notes.get((ex.id, d.isoformat()), plan_note) %}
          {% if d == today %}
            {% if planned %}
            <td class="cell today"
                data-exercise-id="{{ ex.id }}"
                data-date="{{ d.isoformat() }}"
                data-planned="{{ planned }}"
                onclick="openLogPopup(this)">
              <span class="planned">{{ planned }}</span>
              {% if logged %}
              <span class="logged">&#x2713;{{ logged }}</span>
              {% else %}
              <span class="hint">tap</span>
              {% endif %}
              <input class="note-input"
                     data-exercise-id="{{ ex.id }}"
                     data-date="{{ d.isoformat() }}"
                     value="{{ note_val }}"
                     placeholder="note…"
                     onclick="event.stopPropagation()"
                     onblur="saveNote(this)">
            </td>
            {% else %}
            <td class="cell today empty">&#x2014;</td>
            {% endif %}
          {% elif d < today %}
            {% if planned %}
            <td class="cell past">
              <span class="planned">{{ planned }}</span>
              {% if logged %}<span class="logged">&#x2713;{{ logged }}</span>
              {% else %}<span class="missed">&#x2014;</span>{% endif %}
              <input class="note-input"
                     data-exercise-id="{{ ex.id }}"
                     data-date="{{ d.isoformat() }}"
                     value="{{ note_val }}"
                     placeholder="note…"
                     onblur="saveNote(this)">
            </td>
            {% else %}
            <td class="cell past empty">&#x2014;</td>
            {% endif %}
          {% else %}
            {% if planned %}
            <td class="cell future">
              <span class="planned">{{ planned }}</span>
              <input class="note-input"
                     data-exercise-id="{{ ex.id }}"
                     data-date="{{ d.isoformat() }}"
                     value="{{ note_val }}"
                     placeholder="note…"
                     onblur="saveNote(this)">
            </td>
            {% else %}
            <td class="cell future empty">&#x2014;</td>
            {% endif %}
          {% endif %}
        {% endfor %}
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div id="log-overlay" class="overlay hidden">
  <div class="popup">
    <h2>Log reps</h2>
    <p id="popup-planned"></p>
    <input type="number" id="popup-input" min="0">
    <div class="popup-actions">
      <button onclick="submitLog()">Save</button>
      <button onclick="closePopup()">Cancel</button>
    </div>
  </div>
</div>
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='app.js') }}"></script>
{% endblock %}
```

- [ ] **Step 6: Run new test**

```bash
python3 -m pytest tests/test_routes.py::test_index_renders_note_inputs -v
```
Expected: PASSED

- [ ] **Step 7: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add app.py templates/index.html tests/test_routes.py
git commit -m "feat: show editable note inputs per exercise/day on This Week tab"
```

---

### Task 7: Add saveNote() JS function

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Append saveNote() to static/app.js**

Add at the end of `static/app.js`:

```javascript
function saveNote(input) {
    fetch('/api/note', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            exercise_id: parseInt(input.dataset.exerciseId, 10),
            date: input.dataset.date,
            note: input.value.trim()
        })
    });
}
```

- [ ] **Step 2: Verify in browser**

Open http://192.168.1.110:5000. Find a scheduled cell (today or a past day). Type a note and click away (blur). Refresh the page — the note must still be there.

- [ ] **Step 3: Commit**

```bash
git add static/app.js
git commit -m "feat: auto-save note on blur via POST /api/note"
```

---

### Task 8: Visual polish — replace style.css

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Run tests as baseline before CSS change**

```bash
python3 -m pytest -v
```
Expected: All pass.

- [ ] **Step 2: Replace entire static/style.css**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #1a1a1a; color: #e0e0e0; }
a { color: #7fc77f; text-decoration: none; }
h1 { margin: 1rem 0; font-size: 1.4rem; }
h2 { margin: 1.2rem 0 0.6rem; font-size: 1.1rem; }
p { color: #888; margin: 0.5rem 0; }

nav { background: #111; padding: 0.75rem 1rem; display: flex; gap: 1.5rem; border-bottom: 1px solid #333; }
nav a { color: #aaa; font-size: 0.9rem; }
nav a:hover { color: #e0e0e0; }

main { padding: 1rem; max-width: 960px; }

.table-wrap { overflow-x: auto; margin-top: 0.5rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.875rem; border: 2px solid #555; }
th { padding: 8px 10px; border: 1px solid #555; color: #e8c840; font-weight: 700; text-align: center; white-space: nowrap; }
th:first-child { text-align: left; }
td { padding: 6px 10px; border: 1px solid #555; text-align: center; vertical-align: middle; }
td:first-child { text-align: left; }
td.ex-name { font-weight: 700; color: #e8c840; white-space: nowrap; }

tbody tr:nth-child(odd)  { background: #3a3a3a; }
tbody tr:nth-child(even) { background: #454545; }

th.today { background: #2a3a1a; color: #e8c840; }
td.today { background: #1e3818; cursor: pointer; }
td.today:not(.empty) { cursor: pointer; }
td.today.empty { cursor: default; }
td.today:hover:not(.empty) { background: #243f20; }
td.future { opacity: 0.4; }
td.empty { color: #555; }

.planned { display: block; font-size: 0.78rem; color: #888; }
.logged { display: block; font-size: 0.95rem; color: #7fc77f; font-weight: 600; }
.hint { display: block; font-size: 0.7rem; color: #555; }
.missed { color: #555; }

table button { background: #3a1a1a; border: 1px solid #5a2a2a; color: #e07070; padding: 3px 8px; border-radius: 3px; cursor: pointer; font-size: 0.8rem; }
table button:hover { background: #4a2020; }

input[type="text"], input[type="number"] { background: #2a2a2a; border: 1px solid #444; color: #e0e0e0; padding: 6px 8px; border-radius: 4px; font-size: 0.875rem; }
input[type="number"].plan-input { width: 52px; text-align: center; }

.plan-note-input {
  display: block;
  width: 80px;
  margin-top: 4px;
  font-size: 0.72rem;
  background: transparent;
  border: none;
  border-bottom: 1px solid #555;
  color: #aaa;
  padding: 2px;
  border-radius: 0;
  text-align: center;
}
.plan-note-input:focus { outline: none; border-bottom-color: #e8c840; color: #eee; }

.note-input {
  display: block;
  width: 90%;
  margin: 4px auto 0;
  font-size: 0.72rem;
  background: transparent;
  border: none;
  border-bottom: 1px solid #555;
  color: #aaa;
  padding: 2px;
  border-radius: 0;
  text-align: center;
}
.note-input:focus { outline: none; border-bottom-color: #e8c840; color: #eee; }

button[type="submit"] { background: #1a3a1a; border: 1px solid #3a6a3a; color: #7fc77f; padding: 8px 20px; border-radius: 4px; cursor: pointer; font-size: 0.875rem; margin-top: 1rem; }
button[type="submit"]:hover { background: #1e4a1e; }

.history-nav { display: flex; gap: 1.5rem; margin-bottom: 1rem; font-size: 0.9rem; }

.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 100; }
.overlay.hidden { display: none; }
.popup { background: #252525; border: 1px solid #444; border-radius: 8px; padding: 1.5rem; min-width: 220px; text-align: center; }
.popup h2 { margin-bottom: 0.5rem; font-size: 1.1rem; }
.popup p { color: #888; font-size: 0.85rem; margin-bottom: 1rem; }
.popup input { font-size: 1.5rem; width: 90px; text-align: center; margin-bottom: 1rem; }
.popup-actions { display: flex; gap: 0.75rem; justify-content: center; }
.popup-actions button { padding: 8px 20px; border-radius: 4px; cursor: pointer; border: 1px solid #444; background: #333; color: #e0e0e0; font-size: 0.875rem; }
.popup-actions button:first-child { background: #1a3a1a; border-color: #3a6a3a; color: #7fc77f; }
```

- [ ] **Step 3: Run full suite**

```bash
python3 -m pytest -v
```
Expected: All pass.

- [ ] **Step 4: Verify in browser**

Open http://192.168.1.110:5000 and check:
- Table has visible borders separating every cell
- Exercise names are yellow
- All column header text is yellow
- Rows alternate between two shades of gray
- Today column has dark green background with yellow header text

- [ ] **Step 5: Commit**

```bash
git add static/style.css
git commit -m "style: grid borders, alternating gray rows, yellow headers, green today column"
```

---

### Task 9: Push to GitHub

**Files:** none

- [ ] **Step 1: Push all commits**

```bash
git push origin master
```
Expected: Output ends with `master -> master`, all 8 commits pushed.
