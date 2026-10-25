import json
from datetime import datetime
from database.db import get_db_connection, generate_next_patient_id

def create_patient(data, prediction_result=None, source="Manual Entry"):
    """
    Creates a new patient record in SQLite.
    Saves initial prediction and creates an audit log entry.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Generate or validate Patient ID
    patient_id = data.get('patient_id')
    if not patient_id or patient_id.strip() == '':
        patient_id = generate_next_patient_id()
    else:
        patient_id = patient_id.strip().upper()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = data.get('name', '').strip() or None
    gender = data.get('gender', 'Other')
    age = float(data.get('age', 0))
    hypertension = int(data.get('hypertension', 0))
    heart_disease = int(data.get('heart_disease', 0))
    smoking_history = str(data.get('smoking_history', 'No Info'))
    bmi = float(data.get('bmi', 0))
    hba1c = float(data.get('HbA1c_level', 0))
    glucose = float(data.get('blood_glucose_level', 0))

    # Check if patient already exists
    cursor.execute("SELECT id FROM patients WHERE patient_id = ?", (patient_id,))
    existing_patient = cursor.fetchone()

    latest_pred = prediction_result.get('prediction_category') if prediction_result else None
    latest_prob = prediction_result.get('risk_probability') if prediction_result else None
    latest_pred_date = now_str if prediction_result else None

    if existing_patient:
        # Update existing patient record with new measurements
        cursor.execute('''
            UPDATE patients SET
                name = COALESCE(?, name),
                gender = ?, age = ?, hypertension = ?, heart_disease = ?,
                smoking_history = ?, bmi = ?, hba1c_level = ?, blood_glucose_level = ?,
                latest_prediction = ?, latest_probability = ?, latest_prediction_date = ?,
                updated_at = ?
            WHERE patient_id = ?
        ''', (
            name, gender, age, hypertension, heart_disease,
            smoking_history, bmi, hba1c, glucose,
            latest_pred, latest_prob, latest_pred_date,
            now_str, patient_id
        ))
    else:
        # Insert new patient
        cursor.execute('''
            INSERT INTO patients (
                patient_id, name, gender, age, hypertension, heart_disease,
                smoking_history, bmi, hba1c_level, blood_glucose_level,
                latest_prediction, latest_probability, latest_prediction_date,
                source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id, name, gender, age, hypertension, heart_disease,
            smoking_history, bmi, hba1c, glucose,
            latest_pred, latest_prob, latest_pred_date,
            source, now_str, now_str
        ))

    # Save prediction history if prediction was generated
    if prediction_result:
        cursor.execute('''
            INSERT INTO predictions (
                patient_id, prediction_category, risk_probability,
                model_version, features_json, contributing_factors_json, prediction_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            patient_id,
            prediction_result['prediction_category'],
            prediction_result['risk_probability'],
            prediction_result.get('model_version', '1.0'),
            json.dumps(prediction_result.get('input_summary', {})),
            json.dumps(prediction_result.get('contributing_factors', [])),
            now_str
        ))

    # Audit log entry
    cursor.execute('''
        INSERT INTO audit_logs (patient_id, action, fields_changed, timestamp, user_note)
        VALUES (?, 'CREATE', ?, ?, ?)
    ''', (
        patient_id,
        json.dumps({'source': source, 'initial_values': data}),
        now_str,
        'Patient record registered'
    ))

    conn.commit()
    conn.close()
    return patient_id

def get_patient(patient_id):
    """Fetches a single patient record by patient_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_patients_paginated(search="", risk_filter="", page=1, per_page=15, sort_by="id", sort_dir="desc"):
    """
    Retrieves filtered, sorted, paginated patient records.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if search:
        search_term = f"%{search.strip()}%"
        conditions.append("(patient_id LIKE ? OR name LIKE ?)")
        params.extend([search_term, search_term])

    if risk_filter and risk_filter != 'all':
        conditions.append("latest_prediction = ?")
        params.append(risk_filter)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Validate sort column to avoid SQL injection
    allowed_sorts = {
        'id': 'id',
        'patient_id': 'patient_id',
        'name': 'name',
        'age': 'age',
        'bmi': 'bmi',
        'blood_glucose_level': 'blood_glucose_level',
        'hba1c_level': 'hba1c_level',
        'latest_prediction': 'latest_prediction',
        'latest_prediction_date': 'latest_prediction_date',
        'created_at': 'created_at'
    }
    col = allowed_sorts.get(sort_by, 'id')
    direction = 'ASC' if sort_dir.lower() == 'asc' else 'DESC'

    # Get total count
    count_query = f"SELECT COUNT(*) AS total FROM patients{where_clause}"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()['total']

    # Get paginated data
    offset = (page - 1) * per_page
    query = f"SELECT * FROM patients{where_clause} ORDER BY {col} {direction} LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    patients = [dict(r) for r in rows]
    conn.close()

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    return {
        'patients': patients,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    }

def update_patient_record(patient_id, update_data, note="Patient record updated"):
    """
    Updates patient details and records an audit log of modified fields.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    old_row = cursor.fetchone()
    if not old_row:
        conn.close()
        return False, "Patient not found"

    old_data = dict(old_row)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    changes = {}
    updatable_fields = [
        'name', 'gender', 'age', 'hypertension', 'heart_disease',
        'smoking_history', 'bmi', 'hba1c_level', 'blood_glucose_level'
    ]

    for field in updatable_fields:
        if field in update_data:
            new_val = update_data[field]
            old_val = old_data.get(field)
            # compare
            if str(old_val) != str(new_val):
                changes[field] = {'old': old_val, 'new': new_val}

    if changes:
        set_clauses = [f"{f} = ?" for f in changes.keys()]
        set_clauses.append("updated_at = ?")
        values = [update_data[f] for f in changes.keys()]
        values.append(now_str)
        values.append(patient_id)

        sql = f"UPDATE patients SET {', '.join(set_clauses)} WHERE patient_id = ?"
        cursor.execute(sql, values)

        cursor.execute('''
            INSERT INTO audit_logs (patient_id, action, fields_changed, timestamp, user_note)
            VALUES (?, 'UPDATE', ?, ?, ?)
        ''', (
            patient_id,
            json.dumps(changes),
            now_str,
            note
        ))

        conn.commit()

    conn.close()
    return True, changes

def delete_patient_record(patient_id):
    """Deletes a patient record and cascade associated predictions."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
    cursor.execute("DELETE FROM predictions WHERE patient_id = ?", (patient_id,))
    cursor.execute("DELETE FROM audit_logs WHERE patient_id = ?", (patient_id,))
    cursor.execute("DELETE FROM habit_planner WHERE patient_id = ?", (patient_id,))
    conn.commit()
    conn.close()
    return True

def record_new_prediction(patient_id, prediction_result):
    """
    Records a new prediction for an existing patient without overwriting history.
    Updates the patient's latest prediction summary.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    category = prediction_result['prediction_category']
    probability = prediction_result['risk_probability']

    cursor.execute('''
        INSERT INTO predictions (
            patient_id, prediction_category, risk_probability,
            model_version, features_json, contributing_factors_json, prediction_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        patient_id,
        category,
        probability,
        prediction_result.get('model_version', '1.0'),
        json.dumps(prediction_result.get('input_summary', {})),
        json.dumps(prediction_result.get('contributing_factors', [])),
        now_str
    ))

    cursor.execute('''
        UPDATE patients
        SET latest_prediction = ?, latest_probability = ?, latest_prediction_date = ?, updated_at = ?
        WHERE patient_id = ?
    ''', (category, probability, now_str, now_str, patient_id))

    cursor.execute('''
        INSERT INTO audit_logs (patient_id, action, fields_changed, timestamp, user_note)
        VALUES (?, 'PREDICT', ?, ?, ?)
    ''', (
        patient_id,
        json.dumps({'prediction': category, 'probability': probability}),
        now_str,
        'New risk prediction performed'
    ))

    conn.commit()
    conn.close()
    return True

def get_patient_history(patient_id):
    """Returns chronological predictions and audit logs for a patient."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM predictions WHERE patient_id = ? ORDER BY prediction_date DESC", (patient_id,))
    predictions = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM audit_logs WHERE patient_id = ? ORDER BY timestamp DESC", (patient_id,))
    audit_logs = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        'predictions': predictions,
        'audit_logs': audit_logs
    }

def get_dashboard_metrics():
    """
    Calculates live dashboard statistics and chart distributions from actual database records.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total counts
    cursor.execute("SELECT COUNT(*) AS total FROM patients")
    total_patients = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS high_risk FROM patients WHERE latest_prediction = 'Higher Risk'")
    high_risk_patients = cursor.fetchone()['high_risk']

    cursor.execute("SELECT COUNT(*) AS low_risk FROM patients WHERE latest_prediction = 'Lower Risk'")
    low_risk_patients = cursor.fetchone()['low_risk']

    cursor.execute("SELECT COUNT(*) AS total_preds FROM predictions")
    total_predictions = cursor.fetchone()['total_preds']

    cursor.execute("SELECT COUNT(*) AS total_uploads FROM dataset_uploads")
    total_datasets = cursor.fetchone()['total_uploads']

    # Recent activity
    cursor.execute('''
        SELECT a.patient_id, a.action, a.timestamp, a.user_note, p.name, p.latest_prediction
        FROM audit_logs a
        LEFT JOIN patients p ON a.patient_id = p.patient_id
        ORDER BY a.id DESC LIMIT 8
    ''')
    recent_activity = [dict(r) for r in cursor.fetchall()]

    # Prediction Distribution
    cursor.execute('''
        SELECT latest_prediction, COUNT(*) AS count
        FROM patients
        WHERE latest_prediction IS NOT NULL
        GROUP BY latest_prediction
    ''')
    pred_dist = {r['latest_prediction']: r['count'] for r in cursor.fetchall()}

    # Age Distribution Buckets: <30, 30-45, 46-60, 60+
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN age < 30 THEN 1 ELSE 0 END) AS age_under_30,
            SUM(CASE WHEN age >= 30 AND age < 45 THEN 1 ELSE 0 END) AS age_30_45,
            SUM(CASE WHEN age >= 45 AND age < 60 THEN 1 ELSE 0 END) AS age_45_60,
            SUM(CASE WHEN age >= 60 THEN 1 ELSE 0 END) AS age_60_plus
        FROM patients
    ''')
    age_row = cursor.fetchone()
    age_dist = {
        'Under 30': age_row['age_under_30'] or 0,
        '30-44': age_row['age_30_45'] or 0,
        '45-59': age_row['age_45_60'] or 0,
        '60+': age_row['age_60_plus'] or 0
    }

    # Glucose Distribution Buckets: <100 (Normal), 100-139 (Normal/Elevated), 140-199 (Impaired), >=200 (High)
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN blood_glucose_level < 100 THEN 1 ELSE 0 END) AS g_normal,
            SUM(CASE WHEN blood_glucose_level >= 100 AND blood_glucose_level < 140 THEN 1 ELSE 0 END) AS g_elevated,
            SUM(CASE WHEN blood_glucose_level >= 140 AND blood_glucose_level < 200 THEN 1 ELSE 0 END) AS g_impaired,
            SUM(CASE WHEN blood_glucose_level >= 200 THEN 1 ELSE 0 END) AS g_high
        FROM patients
    ''')
    g_row = cursor.fetchone()
    glucose_dist = {
        '<100 mg/dL (Normal)': g_row['g_normal'] or 0,
        '100-139 mg/dL': g_row['g_elevated'] or 0,
        '140-199 mg/dL (Impaired)': g_row['g_impaired'] or 0,
        '200+ mg/dL (High)': g_row['g_high'] or 0
    }

    # BMI Distribution: <18.5 (Under), 18.5-24.9 (Normal), 25-29.9 (Overweight), >=30 (Obese)
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN bmi < 18.5 THEN 1 ELSE 0 END) AS bmi_under,
            SUM(CASE WHEN bmi >= 18.5 AND bmi < 25.0 THEN 1 ELSE 0 END) AS bmi_normal,
            SUM(CASE WHEN bmi >= 25.0 AND bmi < 30.0 THEN 1 ELSE 0 END) AS bmi_over,
            SUM(CASE WHEN bmi >= 30.0 THEN 1 ELSE 0 END) AS bmi_obese
        FROM patients
    ''')
    bmi_row = cursor.fetchone()
    bmi_dist = {
        'Underweight (<18.5)': bmi_row['bmi_under'] or 0,
        'Normal (18.5-24.9)': bmi_row['bmi_normal'] or 0,
        'Overweight (25-29.9)': bmi_row['bmi_over'] or 0,
        'Obese (30+)': bmi_row['bmi_obese'] or 0
    }

    # Risk distribution by Age Group
    cursor.execute('''
        SELECT 
            CASE 
                WHEN age < 30 THEN 'Under 30'
                WHEN age >= 30 AND age < 45 THEN '30-44'
                WHEN age >= 45 AND age < 60 THEN '45-59'
                ELSE '60+' 
            END AS age_group,
            latest_prediction,
            COUNT(*) as count
        FROM patients
        WHERE latest_prediction IS NOT NULL
        GROUP BY age_group, latest_prediction
    ''')
    risk_by_age = {}
    for r in cursor.fetchall():
        grp = r['age_group']
        risk_by_age.setdefault(grp, {'Higher Risk': 0, 'Lower Risk': 0})
        risk_by_age[grp][r['latest_prediction']] = r['count']

    # Prediction trends over time (last 7 recorded dates)
    cursor.execute('''
        SELECT SUBSTR(prediction_date, 1, 10) AS p_date, COUNT(*) AS count
        FROM predictions
        GROUP BY p_date
        ORDER BY p_date DESC
        LIMIT 7
    ''')
    trend_rows = cursor.fetchall()
    trends = {r['p_date']: r['count'] for r in reversed(trend_rows)}

    conn.close()

    return {
        'total_patients': total_patients,
        'high_risk_patients': high_risk_patients,
        'low_risk_patients': low_risk_patients,
        'total_predictions': total_predictions,
        'total_datasets': total_datasets,
        'recent_activity': recent_activity,
        'charts': {
            'pred_dist': pred_dist,
            'age_dist': age_dist,
            'glucose_dist': glucose_dist,
            'bmi_dist': bmi_dist,
            'risk_by_age': risk_by_age,
            'trends': trends
        }
    }
