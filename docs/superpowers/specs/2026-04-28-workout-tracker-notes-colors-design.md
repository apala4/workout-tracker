# Workout Tracker Phase 2: Notes + Visual Polish

**Date:** 2026-04-28

## Overview

Three enhancements to the existing workout tracker:

1. **Plan notes** — a free-text field per (exercise × weekday) in the Plan admin tab (e.g. "10kg×4", "use resistance band")
2. **This Week notes** — the plan note pre-fills each cell on the This Week tab; user can edit it inline per day with auto-save on blur
3. **Visual polish** — alternating light-gray row backgrounds, yellow exercise names and header row, full grid borders, green today column

## Schema Changes

Two additions to the database; existing data unaffected if upgrading (ALTER TABLE / CREATE TABLE IF NOT EXISTS):

```sql
ALTER TABLE weekly_plan ADD COLUMN plan_note TEXT DEFAULT NULL;

CREATE TABLE IF NOT EXISTS workout_notes (
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    date        DATE    NOT NULL,
    note        TEXT    NOT NULL,
    PRIMARY KEY (exercise_id, date)
);
```

`weekly_plan.plan_note` — the recurring default note shown in the Plan tab and pre-filled in This Week cells.  
`workout_notes` — per-date overrides; one row per (exercise, date) the user has typed a note on This Week tab.

## Data Layer (`db.py`)

### Modified functions

**`get_weekly_plan()`** — return value changes from `{(ex_id, weekday): planned_reps}` to `{(ex_id, weekday): (planned_reps, plan_note)}`. All callers updated accordingly.

**`save_weekly_plan(plan)`** — `plan` items change from `(exercise_id, weekday, planned_reps)` to `(exercise_id, weekday, planned_reps, plan_note)`.

### New functions

**`get_week_notes(week_start)`** — returns `{(exercise_id, date_str): note}` for all rows in `workout_notes` within the week.

**`save_note(exercise_id, date_str, note)`** — `INSERT OR REPLACE INTO workout_notes`. If `note` is empty string, delete the row instead.

## Routes (`app.py`)

### Modified

**`GET /admin/plan`** — passes `plan` dict with new tuple values; template unpacks them.

**`POST /admin/plan`** — reads `plan_note_{ex_id}_{weekday}` form fields alongside existing `plan_{ex_id}_{weekday}` fields.

**`GET /`** — additionally calls `db.get_week_notes(monday)` and passes `notes` to the template.

### New

**`POST /api/note`** — JSON body `{exercise_id, date, note}`. Calls `db.save_note()`. Returns `{"ok": true}`. Returns 400 on invalid JSON or missing fields.

## Templates

### `admin_plan.html`

Each plan cell gets a second input below the reps input:

```html
<input type="text"
       name="plan_note_{{ ex.id }}_{{ weekday }}"
       value="{{ plan.get((ex.id, weekday), (None,''))[1] or '' }}"
       placeholder="note…"
       class="plan-note-input">
```

### `index.html` (This Week tab)

Every scheduled cell (today, past, future) gets a note input. The input is pre-filled from `notes.get((ex.id, d.isoformat()))` falling back to the plan note. Auto-saves on blur via JS.

```html
<input class="note-input"
       data-exercise-id="{{ ex.id }}"
       data-date="{{ d.isoformat() }}"
       value="{{ notes.get((ex.id, d.isoformat()), plan_note or '') }}"
       placeholder="note…">
```

Unscheduled cells (—) show no note input.

## JavaScript (`static/app.js`)

Add `saveNote(input)` function:

```js
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

Wire up via `onblur="saveNote(this)"` on each `.note-input`.

The existing popup (log reps) is unchanged. Note inputs sit below the rep count in each cell and do not trigger the popup.

## Styling (`static/style.css`)

Replace current subtle row styling with:

- **Table border:** `border: 2px solid #555` on `<table>`
- **Cell borders:** `border: 1px solid #555` on all `<th>` and `<td>` (switch `border-collapse: collapse`)
- **Alternating rows:** odd rows `#3a3a3a`, even rows `#454545`
- **Exercise name column & header row:** color `#e8c840` (yellow), `font-weight: 700`
- **Today column header:** `background: #2a3a1a`, text `#e8c840`
- **Today cells:** `background: #1e3818` (dark green tint)
- **Plan note input:** `width: 100%; font-size: 0.75rem; background: transparent; border: none; border-bottom: 1px solid #555; color: #aaa; padding: 2px 0`
- **Note input on This Week tab:** same style as plan note input

## Test Coverage

New tests in `tests/test_db.py`:
- `get_weekly_plan()` includes plan_note in return value
- `save_weekly_plan()` persists plan_note
- `get_week_notes()` returns correct dict
- `save_note()` insert, update, and empty-string-deletes

New tests in `tests/test_routes.py`:
- `POST /api/note` happy path returns `{"ok": true}`
- `POST /api/note` with invalid JSON returns 400
- `GET /` passes `notes` to template context (check response contains note input markup)
- `POST /admin/plan` persists plan_note

## Migration

Since the user confirmed old data is not needed, the simplest path is to drop and recreate `workout.db`. `init_db()` will use `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (SQLite 3.37+) or a try/except around the ALTER. Check SQLite version first — if < 3.37 use try/except pattern.

## Out of Scope

- History tab notes (read-only view of past notes would be a Phase 3 item)
- Note character limits (trust the user)
- Undo / revert note changes
