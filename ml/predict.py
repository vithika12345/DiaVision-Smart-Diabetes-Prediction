import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import joblib
import json
import pandas as pd
import numpy as np
from config import Config
from ml.preprocessing import ALL_FEATURES, NUMERICAL_FEATURES, clean_dataset

_model_cache = None

def get_trained_model():
    """Loads and caches the trained pipeline from disk."""
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    if not os.path.exists(Config.MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at {Config.MODEL_PATH}. Please run train_model.py first.")

    _model_cache = joblib.load(Config.MODEL_PATH)
    return _model_cache

def reload_model():
    """Forces reloading the model from disk (useful after retraining)."""
    global _model_cache
    _model_cache = None
    return get_trained_model()

def explain_prediction(features_dict, risk_probability):
    """
    Computes explainability insights and contributing clinical factors
    based on established clinical ranges and model feature sensitivity.
    """
    factors = []
    
    # 1. HbA1c
    hba1c = float(features_dict.get('HbA1c_level', 0))
    if hba1c >= 6.5:
        factors.append({
            'feature': 'HbA1c Level',
            'value': f"{hba1c}%",
            'impact': 'High Risk',
            'direction': 'increases_risk',
            'note': 'Meets or exceeds clinical threshold (>=6.5%) indicative of diabetes risk.'
        })
    elif hba1c >= 5.7:
        factors.append({
            'feature': 'HbA1c Level',
            'value': f"{hba1c}%",
            'impact': 'Moderate Risk',
            'direction': 'increases_risk',
            'note': 'Falls within the prediabetes reference range (5.7% – 6.4%).'
        })
    else:
        factors.append({
            'feature': 'HbA1c Level',
            'value': f"{hba1c}%",
            'impact': 'Normal',
            'direction': 'protective',
            'note': 'Within standard normal reference range (<5.7%).'
        })

    # 2. Blood Glucose
    glucose = float(features_dict.get('blood_glucose_level', 0))
    if glucose >= 200:
        factors.append({
            'feature': 'Blood Glucose',
            'value': f"{glucose} mg/dL",
            'impact': 'High Risk',
            'direction': 'increases_risk',
            'note': 'Markedly elevated measurement (>=200 mg/dL).'
        })
    elif glucose >= 140:
        factors.append({
            'feature': 'Blood Glucose',
            'value': f"{glucose} mg/dL",
            'impact': 'Moderate Risk',
            'direction': 'increases_risk',
            'note': 'Elevated post-meal or random glucose (140 – 199 mg/dL).'
        })
    elif glucose < 70 and glucose > 0:
        factors.append({
            'feature': 'Blood Glucose',
            'value': f"{glucose} mg/dL",
            'impact': 'Low (Hypoglycemia alert)',
            'direction': 'concerning',
            'note': 'Sub-normal reading below 70 mg/dL requires clinical attention.'
        })
    else:
        factors.append({
            'feature': 'Blood Glucose',
            'value': f"{glucose} mg/dL",
            'impact': 'Normal',
            'direction': 'protective',
            'note': 'Within standard healthy fasting / baseline bounds.'
        })

    # 3. BMI
    bmi = float(features_dict.get('bmi', 0))
    if bmi >= 30:
        factors.append({
            'feature': 'BMI',
            'value': f"{bmi:.1f} kg/m²",
            'impact': 'Moderate Risk',
            'direction': 'increases_risk',
            'note': 'Falls in the obesity class, a known metabolic insulin-resistance factor.'
        })
    elif bmi >= 25:
        factors.append({
            'feature': 'BMI',
            'value': f"{bmi:.1f} kg/m²",
            'impact': 'Mild Risk',
            'direction': 'increases_risk',
            'note': 'Overweight range (25 – 29.9 kg/m²).'
        })
    elif bmi >= 18.5:
        factors.append({
            'feature': 'BMI',
            'value': f"{bmi:.1f} kg/m²",
            'impact': 'Normal',
            'direction': 'protective',
            'note': 'Optimal healthy weight range (18.5 – 24.9 kg/m²).'
        })

    # 4. Age
    age = float(features_dict.get('age', 0))
    if age >= 50:
        factors.append({
            'feature': 'Age',
            'value': f"{int(age)} years",
            'impact': 'Moderate Risk',
            'direction': 'increases_risk',
            'note': 'Age 50+ is associated with increased incidence of insulin resistance.'
        })
    elif age >= 40:
        factors.append({
            'feature': 'Age',
            'value': f"{int(age)} years",
            'impact': 'Mild Risk',
            'direction': 'increases_risk',
            'note': 'Age 40+ is a standard screening threshold recommended by clinical guidelines.'
        })

    # 5. Comorbidities
    if int(features_dict.get('hypertension', 0)) == 1:
        factors.append({
            'feature': 'Hypertension',
            'value': 'Present',
            'impact': 'Moderate Risk',
            'direction': 'increases_risk',
            'note': 'Hypertension frequently coexists with insulin resistance and vascular strain.'
        })

    if int(features_dict.get('heart_disease', 0)) == 1:
        factors.append({
            'feature': 'Heart Disease',
            'value': 'Present',
            'impact': 'Moderate Risk',
            'direction': 'increases_risk',
            'note': 'Pre-existing cardiovascular condition elevates overall metabolic vulnerability.'
        })

    # 6. Smoking
    smoking = str(features_dict.get('smoking_history', 'No Info'))
    if smoking in ['current', 'ever']:
        factors.append({
            'feature': 'Smoking History',
            'value': smoking.capitalize(),
            'impact': 'Mild Risk',
            'direction': 'increases_risk',
            'note': 'Active nicotine exposure impairs cellular glucose utilization.'
        })

    return factors

def predict_single_patient(patient_dict):
    """
    Performs diabetes risk prediction for a single patient dictionary.
    Returns:
        dict: {
            'prediction_category': 'Lower Risk' | 'Higher Risk',
            'risk_probability': float (0.0 to 100.0),
            'model_version': str,
            'contributing_factors': list of dicts,
            'input_summary': dict
        }
    """
    model = get_trained_model()

    # Build single-row DataFrame with correct column names and order
    row_data = {
        'gender': [str(patient_dict.get('gender', 'Other')).strip().capitalize()],
        'age': [float(patient_dict.get('age', 0))],
        'hypertension': [int(patient_dict.get('hypertension', 0))],
        'heart_disease': [int(patient_dict.get('heart_disease', 0))],
        'smoking_history': [str(patient_dict.get('smoking_history', 'No Info')).strip()],
        'bmi': [float(patient_dict.get('bmi', 0))],
        'HbA1c_level': [float(patient_dict.get('HbA1c_level', 0))],
        'blood_glucose_level': [float(patient_dict.get('blood_glucose_level', 0))]
    }
    df_input = pd.DataFrame(row_data)

    # Predict probability and class
    proba = model.predict_proba(df_input)[0]
    prob_risk = float(proba[1]) * 100.0  # Class 1 is diabetes
    
    # Category threshold at 45% (calibrated for sensitivity)
    category = 'Higher Risk' if prob_risk >= 45.0 else 'Lower Risk'

    factors = explain_prediction(patient_dict, prob_risk)

    version = "1.0.0"
    if os.path.exists(Config.METRICS_PATH):
        try:
            with open(Config.METRICS_PATH, 'r') as f:
                metrics = json.load(f)
                version = metrics.get('version', version)
        except Exception:
            pass

    return {
        'prediction_category': category,
        'risk_probability': round(prob_risk, 1),
        'model_version': version,
        'contributing_factors': factors,
        'input_summary': {k: row_data[k][0] for k in ALL_FEATURES}
    }

def predict_batch_records(df_raw):
    """
    Processes a batch DataFrame, validating required columns,
    and returns predictions and summary statistics.
    """
    model = get_trained_model()
    df = clean_dataset(df_raw)

    missing_cols = [col for col in ALL_FEATURES if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Batch dataset missing required features: {', '.join(missing_cols)}")

    # Identify eligible rows (no NaNs in numerical features)
    eligible_mask = df[NUMERICAL_FEATURES].notnull().all(axis=1) & (df['age'] > 0) & (df['bmi'] > 0)
    
    results = []
    probabilities = []
    categories = []

    # Predict for eligible rows
    df_eligible = df[eligible_mask][ALL_FEATURES]
    if len(df_eligible) > 0:
        probas = model.predict_proba(df_eligible)[:, 1] * 100.0
        preds = ['Higher Risk' if p >= 45.0 else 'Lower Risk' for p in probas]
    else:
        probas = []
        preds = []

    proba_idx = 0
    for idx, is_eligible in enumerate(eligible_mask):
        if is_eligible:
            p_val = round(float(probas[proba_idx]), 1)
            c_val = preds[proba_idx]
            probabilities.append(p_val)
            categories.append(c_val)
            proba_idx += 1
        else:
            probabilities.append(None)
            categories.append('Ineligible / Invalid Data')

    df_out = df_raw.copy()
    df_out['predicted_risk_category'] = categories
    df_out['risk_probability_percent'] = probabilities

    summary = {
        'total_rows': len(df_raw),
        'eligible_rows': int(eligible_mask.sum()),
        'ineligible_rows': int((~eligible_mask).sum()),
        'higher_risk_count': int((np.array(categories) == 'Higher Risk').sum()),
        'lower_risk_count': int((np.array(categories) == 'Lower Risk').sum())
    }

    return df_out, summary
