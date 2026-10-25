import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from database.db import get_db_connection, generate_next_patient_id
from ml.preprocessing import ALL_FEATURES, NUMERICAL_FEATURES, clean_dataset
from ml.predict import predict_single_patient, reload_model
from ml.train_model import train_and_compare_models

def allowed_file(filename):
    """Checks if uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def parse_uploaded_file(file_path):
    """
    Parses a CSV or Excel file into a pandas DataFrame.
    """
    ext = file_path.rsplit('.', 1)[1].lower()
    if ext == 'csv':
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='latin1')
    elif ext in ['xlsx', 'xls']:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: .{ext}")
    return df

def inspect_dataset_file(file_path):
    """
    Inspects an uploaded file: columns, row count, null counts, duplicate rows, sample preview.
    """
    df = parse_uploaded_file(file_path)
    row_count = len(df)
    columns = list(df.columns)
    
    # Missing values
    missing_dict = df.isnull().sum().to_dict()
    
    # Duplicate rows count
    duplicate_count = int(df.duplicated().sum())

    # Preview first 10 rows safely as JSON serializable
    df_preview = df.head(10).fillna('')
    preview_rows = df_preview.to_dict(orient='records')

    # Data types
    dtypes_dict = {col: str(df[col].dtype) for col in columns}

    # Match against standard features
    cleaned_df = clean_dataset(df.head(2))
    matched_features = [f for f in ALL_FEATURES if f in cleaned_df.columns]
    missing_features = [f for f in ALL_FEATURES if f not in cleaned_df.columns]

    has_target = 'diabetes' in cleaned_df.columns or 'Outcome' in df.columns or 'Diabetes' in df.columns

    return {
        'filename': os.path.basename(file_path),
        'row_count': row_count,
        'columns': columns,
        'missing_values': missing_dict,
        'duplicate_count': duplicate_count,
        'data_types': dtypes_dict,
        'preview_rows': preview_rows,
        'matched_features': matched_features,
        'missing_features': missing_features,
        'has_target': has_target
    }

def import_historical_records(file_path, perform_predictions=True, duplicate_action="skip"):
    """
    Imports records from a dataset into the SQLite database.
    Assigns sequential DIA-XXXXX permanent IDs, performs initial predictions,
    and logs the dataset upload.
    """
    df = parse_uploaded_file(file_path)
    df_cleaned = clean_dataset(df)
    filename = os.path.basename(file_path)

    conn = get_db_connection()
    cursor = conn.cursor()

    imported_count = 0
    skipped_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check existing patient IDs and find highest current DIA- counter
    cursor.execute("SELECT patient_id FROM patients")
    existing_ids = {row['patient_id'] for row in cursor.fetchall()}

    cursor.execute("SELECT patient_id FROM patients WHERE patient_id LIKE 'DIA-%' ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    current_num = 0
    if last_row:
        try:
            current_num = int(last_row['patient_id'].split('-')[1])
        except (IndexError, ValueError):
            current_num = len(existing_ids)

    for _, row in df_cleaned.iterrows():
        # Determine patient ID
        # Check if dataset has an existing patient id column
        pid = None
        for id_col in ['patient_id', 'Patient_ID', 'PatientID', 'id', 'ID', 'prediction value']:
            if id_col in row and pd.notnull(row[id_col]):
                val = str(row[id_col]).strip()
                if val.startswith('DIA-'):
                    pid = val
                break

        if not pid or pid in existing_ids:
            if duplicate_action == "skip" and pid in existing_ids:
                skipped_count += 1
                continue
            current_num += 1
            pid = f"DIA-{current_num:05d}"
            while pid in existing_ids:
                current_num += 1
                pid = f"DIA-{current_num:05d}"
            existing_ids.add(pid)

        # Extract features
        gender = str(row.get('gender', 'Other')).strip().capitalize()
        age = float(row.get('age', 0)) if pd.notnull(row.get('age')) else 0.0
        hypertension = int(row.get('hypertension', 0)) if pd.notnull(row.get('hypertension')) else 0
        heart_disease = int(row.get('heart_disease', 0)) if pd.notnull(row.get('heart_disease')) else 0
        smoking_history = str(row.get('smoking_history', 'No Info')).strip()
        bmi = float(row.get('bmi', 0)) if pd.notnull(row.get('bmi')) else 0.0
        hba1c = float(row.get('HbA1c_level', 0)) if pd.notnull(row.get('HbA1c_level')) else 0.0
        glucose = float(row.get('blood_glucose_level', 0)) if pd.notnull(row.get('blood_glucose_level')) else 0.0

        pred_cat = None
        pred_prob = None
        pred_date = None

        if perform_predictions and age > 0 and bmi > 0:
            try:
                p_dict = {
                    'gender': gender, 'age': age, 'hypertension': hypertension,
                    'heart_disease': heart_disease, 'smoking_history': smoking_history,
                    'bmi': bmi, 'HbA1c_level': hba1c, 'blood_glucose_level': glucose
                }
                pred_res = predict_single_patient(p_dict)
                pred_cat = pred_res['prediction_category']
                pred_prob = pred_res['risk_probability']
                pred_date = now_str
            except Exception:
                pass

        cursor.execute('''
            INSERT INTO patients (
                patient_id, name, gender, age, hypertension, heart_disease,
                smoking_history, bmi, hba1c_level, blood_glucose_level,
                latest_prediction, latest_probability, latest_prediction_date,
                source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pid, None, gender, age, hypertension, heart_disease,
            smoking_history, bmi, hba1c, glucose,
            pred_cat, pred_prob, pred_date,
            f"Import: {filename}", now_str, now_str
        ))

        if pred_cat:
            cursor.execute('''
                INSERT INTO predictions (
                    patient_id, prediction_category, risk_probability,
                    model_version, features_json, contributing_factors_json, prediction_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                pid, pred_cat, pred_prob,
                pred_res.get('model_version', '1.0'),
                json.dumps(p_dict),
                json.dumps(pred_res.get('contributing_factors', [])),
                now_str
            ))

        imported_count += 1

    # Record in dataset_uploads
    cursor.execute('''
        INSERT INTO dataset_uploads (
            filename, uploaded_at, row_count, imported_count, skipped_count, dataset_type, status
        ) VALUES (?, ?, ?, ?, ?, 'Historical Records', 'Completed')
    ''', (filename, now_str, len(df), imported_count, skipped_count))

    conn.commit()
    conn.close()

    return {
        'filename': filename,
        'total_rows': len(df),
        'imported_count': imported_count,
        'skipped_count': skipped_count
    }

def retrain_model_from_dataset(file_path, target_col='diabetes'):
    """
    Retrains the classification pipeline on an uploaded labeled dataset,
    backs up the old model, and reloads the active model.
    """
    df = parse_uploaded_file(file_path)
    df_clean = clean_dataset(df)

    if target_col not in df_clean.columns:
        raise ValueError(f"Target column '{target_col}' not found in uploaded dataset!")

    # Check binary target
    unique_vals = set(df_clean[target_col].dropna().unique())
    if not unique_vals.issubset({0, 1, 0.0, 1.0}):
        raise ValueError(f"Target column '{target_col}' must contain binary 0 and 1 values. Found: {unique_vals}")

    # Retrain pipeline
    metrics_result = train_and_compare_models(dataset_path=file_path)
    reload_model()

    # Record dataset upload
    filename = os.path.basename(file_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO dataset_uploads (
            filename, uploaded_at, row_count, imported_count, skipped_count, dataset_type, status
        ) VALUES (?, ?, ?, ?, 0, 'Training Dataset', 'Model Retrained')
    ''', (filename, now_str, len(df), len(df)))
    conn.commit()
    conn.close()

    return metrics_result

def get_upload_history():
    """Returns list of past dataset uploads."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dataset_uploads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
