import sqlite3
import os
import json
from datetime import datetime
from config import Config

def get_db_connection():
    """Returns a SQLite connection with row factory set to sqlite3.Row for dict-like access."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes database tables if they do not already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Patients Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE NOT NULL,
            name TEXT,
            gender TEXT,
            age REAL,
            hypertension INTEGER DEFAULT 0,
            heart_disease INTEGER DEFAULT 0,
            smoking_history TEXT,
            bmi REAL,
            hba1c_level REAL,
            blood_glucose_level REAL,
            latest_prediction TEXT,
            latest_probability REAL,
            latest_prediction_date TEXT,
            source TEXT DEFAULT 'Manual Entry',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_pid ON patients (patient_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_risk ON patients (latest_prediction)')

    # 2. Predictions Table (Complete historical log)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            prediction_category TEXT NOT NULL,
            risk_probability REAL,
            model_version TEXT,
            features_json TEXT,
            contributing_factors_json TEXT,
            prediction_date TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients (patient_id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_pid ON predictions (patient_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions (prediction_date)')

    # 3. Audit Logs Table (Tracks record modifications)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            action TEXT NOT NULL,
            fields_changed TEXT,
            timestamp TEXT NOT NULL,
            user_note TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_pid ON audit_logs (patient_id)')

    # 4. Dataset Uploads Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dataset_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            imported_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0,
            dataset_type TEXT DEFAULT 'Historical Records',
            status TEXT DEFAULT 'Completed'
        )
    ''')

    # 5. Habit Planner Table (7-Day Health Planner)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habit_planner (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            week_start_date TEXT NOT NULL,
            habits_json TEXT NOT NULL,
            progress_percent REAL DEFAULT 0.0,
            updated_at TEXT NOT NULL,
            UNIQUE(patient_id, week_start_date)
        )
    ''')

    conn.commit()
    conn.close()

def generate_next_patient_id():
    """Generates the next sequential permanent Patient ID (e.g. DIA-00001)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patients WHERE patient_id LIKE 'DIA-%' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return 'DIA-00001'
    
    last_id = row['patient_id']
    try:
        num_part = int(last_id.split('-')[1])
        next_num = num_part + 1
        return f"DIA-{next_num:05d}"
    except (IndexError, ValueError):
        # Fallback if custom formatted ID
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM patients")
        total = cursor.fetchone()['total']
        conn.close()
        return f"DIA-{(total + 1):05d}"
