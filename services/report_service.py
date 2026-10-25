import io
import csv
import json
from database.db import get_db_connection

def generate_patients_csv(patients_list=None):
    """
    Generates a CSV string containing patient records.
    """
    if patients_list is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY id ASC")
        patients_list = [dict(r) for r in cursor.fetchall()]
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        'Patient ID', 'Name', 'Gender', 'Age', 'Hypertension', 'Heart Disease',
        'Smoking History', 'BMI', 'HbA1c Level (%)', 'Blood Glucose (mg/dL)',
        'Latest Risk Prediction', 'Risk Probability (%)', 'Prediction Date', 'Source', 'Registered Date'
    ]
    writer.writerow(headers)

    for p in patients_list:
        writer.writerow([
            p.get('patient_id'),
            p.get('name') or 'N/A',
            p.get('gender'),
            p.get('age'),
            'Yes' if p.get('hypertension') == 1 else 'No',
            'Yes' if p.get('heart_disease') == 1 else 'No',
            p.get('smoking_history'),
            p.get('bmi'),
            p.get('hba1c_level'),
            p.get('blood_glucose_level'),
            p.get('latest_prediction') or 'Not Predicted',
            p.get('latest_probability') if p.get('latest_probability') is not None else 'N/A',
            p.get('latest_prediction_date') or 'N/A',
            p.get('source'),
            p.get('created_at')
        ])

    return output.getvalue()

def generate_doctor_visit_summary(patient, latest_prediction=None):
    """
    Prepares a structured summary tailored for a patient to bring to a medical consultation.
    Includes clinical readings, trend observation, and targeted questions for the physician.
    """
    glucose = float(patient.get('blood_glucose_level', 0))
    hba1c = float(patient.get('hba1c_level', 0))
    bmi = float(patient.get('bmi', 0))
    hypertension = int(patient.get('hypertension', 0))
    heart_disease = int(patient.get('heart_disease', 0))

    questions = [
        "What specific target range do you recommend for my fasting and post-prandial blood glucose?",
        "Do you recommend a formal confirmatory laboratory test (such as fasting plasma glucose or repeat HbA1c)?"
    ]

    if bmi >= 25:
        questions.append(f"Given my BMI of {bmi:.1f} kg/m², what sustainable nutrition and physical activity benchmarks should I focus on?")

    if hypertension == 1:
        questions.append("How does my blood pressure interact with my metabolic risk, and should I adjust my salt/DASH intake?")

    if latest_prediction and latest_prediction.get('prediction_category') == 'Higher Risk':
        questions.append("Based on the algorithmic risk flags, are there any cardiovascular or renal screenings I should consider?")

    questions.append("What follow-up timeline do you recommend for my next clinical review?")

    return {
        'patient': patient,
        'latest_prediction': latest_prediction,
        'questions_to_ask': questions,
        'consultation_checklist': [
            'Current list of all vitamins, herbal supplements, or prescribed medications',
            'Recent home glucose or blood pressure readings log (if available)',
            'Family history details regarding diabetes or cardiovascular health'
        ]
    }
