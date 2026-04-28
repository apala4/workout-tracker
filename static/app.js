let currentCell = null;

function openLogPopup(cell) {
    currentCell = cell;
    document.getElementById('popup-planned').textContent = 'Planned: ' + cell.dataset.planned;
    const input = document.getElementById('popup-input');
    input.value = cell.dataset.planned;
    document.getElementById('log-overlay').classList.remove('hidden');
    input.focus();
    input.select();
}

function closePopup() {
    document.getElementById('log-overlay').classList.add('hidden');
    currentCell = null;
}

function submitLog() {
    const cell = currentCell;
    const actual_reps = parseInt(document.getElementById('popup-input').value, 10);
    if (isNaN(actual_reps) || actual_reps < 0) return;

    fetch('/api/log', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            exercise_id: parseInt(cell.dataset.exerciseId, 10),
            date: cell.dataset.date,
            actual_reps: actual_reps
        })
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) return;
        const hint = cell.querySelector('.hint');
        if (hint) hint.remove();
        const existing = cell.querySelector('.logged');
        if (existing) {
            existing.textContent = '✓' + actual_reps;
        } else {
            const span = document.createElement('span');
            span.className = 'logged';
            span.textContent = '✓' + actual_reps;
            cell.appendChild(span);
        }
        closePopup();
    });
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePopup();
    if (e.key === 'Enter' && currentCell) submitLog();
});
