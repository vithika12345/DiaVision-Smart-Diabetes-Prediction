import json
from datetime import datetime, date, timedelta
from database.db import get_db_connection

DEFAULT_HABITS = [
    {'id': 'walk', 'title': 'Daily Movement (20-30 min walk)', 'icon': 'activity'},
    {'id': 'water', 'title': 'Optimal Hydration (8 glasses of water)', 'icon': 'droplet'},
    {'id': 'meal', 'title': 'Balanced Plate (Fiber + Protein + Whole Grain)', 'icon': 'utensils'},
    {'id': 'sleep', 'title': 'Restful Sleep (7-8 hours)', 'icon': 'moon'}
]

DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

def get_current_week_start():
    """Returns Monday's date string for the current week."""
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return start.strftime("%Y-%m-%d")

def get_patient_habit_plan(patient_id, week_start=None):
    """
    Retrieves the 7-day habit plan for a patient for a specific week.
    Initializes default checklist grid if not already present.
    """
    if not week_start:
        week_start = get_current_week_start()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM habit_planner WHERE patient_id = ? AND week_start_date = ?",
        (patient_id, week_start)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        habits_data = json.loads(row['habits_json'])
        return {
            'patient_id': patient_id,
            'week_start_date': week_start,
            'grid': habits_data.get('grid', {}),
            'progress_percent': row['progress_percent'],
            'updated_at': row['updated_at']
        }

    # Initialize empty grid: {habit_id: {day: False for day in DAYS_OF_WEEK}}
    empty_grid = {h['id']: {d: False for d in DAYS_OF_WEEK} for h in DEFAULT_HABITS}
    return {
        'patient_id': patient_id,
        'week_start_date': week_start,
        'grid': empty_grid,
        'progress_percent': 0.0,
        'updated_at': None
    }

def save_patient_habit_plan(patient_id, grid, week_start=None):
    """
    Saves updated checkboxes in the 7-day habit planner and calculates completion %.
    """
    if not week_start:
        week_start = get_current_week_start()

    total_checks = 0
    completed_checks = 0

    for habit_id, days in grid.items():
        for day, checked in days.items():
            total_checks += 1
            if checked:
                completed_checks += 1

    progress = round((completed_checks / max(1, total_checks)) * 100.0, 1)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO habit_planner (patient_id, week_start_date, habits_json, progress_percent, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(patient_id, week_start_date) DO UPDATE SET
            habits_json = excluded.habits_json,
            progress_percent = excluded.progress_percent,
            updated_at = excluded.updated_at
    ''', (patient_id, week_start, json.dumps({'grid': grid}), progress, now_str))

    conn.commit()
    conn.close()

    return {'progress_percent': progress, 'updated_at': now_str}
