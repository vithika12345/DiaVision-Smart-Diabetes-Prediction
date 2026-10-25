import os
import io
import json
import csv
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_file, Response, session
)
from werkzeug.utils import secure_filename

from config import Config
from database.db import init_db, generate_next_patient_id, get_db_connection
from ml.predict import predict_single_patient, predict_batch_records, reload_model
from ml.train_model import train_and_compare_models
from services.patient_service import (
    create_patient, get_patient, get_patients_paginated,
    update_patient_record, delete_patient_record, record_new_prediction,
    get_patient_history, get_dashboard_metrics
)
from services.dataset_service import (
    allowed_file, parse_uploaded_file, inspect_dataset_file,
    import_historical_records, retrain_model_from_dataset, get_upload_history
)
from services.recommendation_service import get_personalized_recommendations
from services.habit_service import (
    get_patient_habit_plan, save_patient_habit_plan, DAYS_OF_WEEK
)
from services.report_service import (
    generate_patients_csv, generate_doctor_visit_summary
)

app = Flask(__name__)
app.config.from_object(Config)

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MODELS_DIR'], exist_ok=True)
os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)

# Initialize database on startup
init_db()

# In-memory storage for batch preview session
_batch_cache = {}

@app.context_processor
def inject_global_data():
    """Provides active model name and system metadata to all templates."""
    model_name = "Random Forest"
    if os.path.exists(Config.METRICS_PATH):
        try:
            with open(Config.METRICS_PATH, 'r') as f:
                data = json.load(f)
                model_name = data.get('selected_model', model_name)
        except Exception:
            pass
    return {'active_model_name': model_name}

# ==============================================================================
# Routes
# ==============================================================================

@app.route('/')
def dashboard():
    """Main healthcare analytics dashboard."""
    stats = get_dashboard_metrics()
    return render_template('dashboard.html', stats=stats, active_page='dashboard')

@app.route('/predict', methods=['GET', 'POST'])
def predict_page():
    """New patient registration & risk prediction."""
    if request.method == 'GET':
        next_pid = generate_next_patient_id()
        return render_template('predict.html', next_patient_id=next_pid, active_page='predict')

    try:
        # Extract and validate form inputs
        form_data = {
            'patient_id': request.form.get('patient_id', '').strip(),
            'name': request.form.get('name', '').strip() or None,
            'gender': request.form.get('gender', 'Other').strip().capitalize(),
            'age': float(request.form.get('age', 0)),
            'hypertension': int(request.form.get('hypertension', 0)),
            'heart_disease': int(request.form.get('heart_disease', 0)),
            'smoking_history': request.form.get('smoking_history', 'No Info').strip(),
            'bmi': float(request.form.get('bmi', 0)),
            'HbA1c_level': float(request.form.get('HbA1c_level', 0)),
            'blood_glucose_level': float(request.form.get('blood_glucose_level', 0))
        }

        # Range validation
        if form_data['age'] < 1 or form_data['age'] > 120:
            flash("Please enter a valid age between 1 and 120.", "warning")
            return redirect(url_for('predict_page'))

        if form_data['bmi'] < 10 or form_data['bmi'] > 90:
            flash("Please enter a valid BMI between 10.0 and 90.0 kg/m².", "warning")
            return redirect(url_for('predict_page'))

        if form_data['HbA1c_level'] < 3.5 or form_data['HbA1c_level'] > 16.0:
            flash("Please enter a valid HbA1c between 3.5% and 16.0%.", "warning")
            return redirect(url_for('predict_page'))

        if form_data['blood_glucose_level'] < 50 or form_data['blood_glucose_level'] > 450:
            flash("Please enter a valid blood glucose level between 50 and 450 mg/dL.", "warning")
            return redirect(url_for('predict_page'))

        # Run machine learning prediction
        prediction_result = predict_single_patient(form_data)

        # Save patient to SQLite database
        patient_id = create_patient(form_data, prediction_result=prediction_result, source="Manual Entry")
        saved_patient = get_patient(patient_id)

        # Generate structured clinical recommendations
        recs = get_personalized_recommendations(form_data, prediction_result)

        flash(f"Risk evaluation complete for patient {patient_id}. Record successfully saved to database.", "info")
        return render_template(
            'prediction_result.html',
            patient=saved_patient,
            prediction=prediction_result,
            recs=recs,
            active_page='predict'
        )

    except Exception as e:
        flash(f"Error executing prediction: {str(e)}", "danger")
        return redirect(url_for('predict_page'))

@app.route('/patient/<patient_id>/repredict', methods=['POST'])
def repredict_patient(patient_id):
    """Re-runs prediction for an existing patient without overwriting history."""
    patient = get_patient(patient_id)
    if not patient:
        flash(f"Patient {patient_id} not found.", "warning")
        return redirect(url_for('patients_page'))

    try:
        p_dict = {
            'gender': patient['gender'],
            'age': patient['age'],
            'hypertension': patient['hypertension'],
            'heart_disease': patient['heart_disease'],
            'smoking_history': patient['smoking_history'],
            'bmi': patient['bmi'],
            'HbA1c_level': patient['hba1c_level'],
            'blood_glucose_level': patient['blood_glucose_level']
        }
        pred_res = predict_single_patient(p_dict)
        record_new_prediction(patient_id, pred_res)
        flash(f"New prediction successfully evaluated for {patient_id}.", "info")
    except Exception as e:
        flash(f"Error evaluating prediction: {e}", "danger")

    return redirect(url_for('patient_detail_page', patient_id=patient_id))

@app.route('/patients')
def patients_page():
    """Searchable, filterable, paginated patient records."""
    search_query = request.args.get('search', '').strip()
    risk_filter = request.args.get('risk', '').strip()
    page = int(request.args.get('page', 1))

    paginated = get_patients_paginated(
        search=search_query,
        risk_filter=risk_filter,
        page=page,
        per_page=15
    )

    return render_template(
        'patients.html',
        paginated=paginated,
        search_query=search_query,
        risk_filter=risk_filter,
        active_page='patients'
    )

@app.route('/patients/<patient_id>')
def patient_detail_page(patient_id):
    """Patient detailed profile, health progress tracker, and history."""
    patient = get_patient(patient_id)
    if not patient:
        flash(f"Patient {patient_id} not found.", "warning")
        return redirect(url_for('patients_page'))

    history = get_patient_history(patient_id)
    return render_template('patient_detail.html', patient=patient, history=history, active_page='patients')

@app.route('/patients/update', methods=['POST'])
def update_patient():
    """Updates a patient's clinical measurements and creates an audit entry."""
    patient_id = request.form.get('patient_id')
    note = request.form.get('user_note', 'Updated clinical parameters')

    update_data = {
        'name': request.form.get('name', '').strip() or None,
        'gender': request.form.get('gender', 'Other').strip().capitalize(),
        'age': float(request.form.get('age', 0)),
        'blood_glucose_level': float(request.form.get('blood_glucose_level', 0)),
        'hba1c_level': float(request.form.get('hba1c_level', 0)),
        'bmi': float(request.form.get('bmi', 0)),
        'hypertension': int(request.form.get('hypertension', 0)),
        'heart_disease': int(request.form.get('heart_disease', 0))
    }

    success, changes = update_patient_record(patient_id, update_data, note=note)
    if success:
        flash(f"Patient {patient_id} updated successfully. Modified fields logged in audit trail.", "info")
    else:
        flash(f"Failed to update patient {patient_id}.", "danger")

    return redirect(request.referrer or url_for('patients_page'))

@app.route('/patients/delete', methods=['POST'])
def delete_patient():
    """Deletes a patient record with confirmation."""
    patient_id = request.form.get('patient_id')
    if patient_id:
        delete_patient_record(patient_id)
        flash(f"Patient {patient_id} permanently deleted.", "warning")
    return redirect(url_for('patients_page'))

@app.route('/batch-prediction')
def batch_prediction_page():
    """Batch prediction page."""
    cached = _batch_cache.get('last_batch')
    summary = cached.get('summary') if cached else None
    preview = cached.get('preview') if cached else None
    return render_template('batch_prediction.html', batch_summary=summary, batch_preview=preview, active_page='batch')

@app.route('/batch-prediction/process', methods=['POST'])
def process_batch_prediction():
    """Processes uploaded dataset and runs batch risk prediction."""
    if 'batch_file' not in request.files:
        flash("No file selected.", "warning")
        return redirect(url_for('batch_prediction_page'))

    file = request.files['batch_file']
    if file.filename == '' or not allowed_file(file.filename):
        flash("Please upload a valid CSV or Excel file (.csv, .xlsx, .xls).", "warning")
        return redirect(url_for('batch_prediction_page'))

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"batch_{filename}")
    file.save(save_path)

    try:
        df_raw = parse_uploaded_file(save_path)
        df_out, summary = predict_batch_records(df_raw)

        # Cache in memory
        _batch_cache['last_batch'] = {
            'df': df_out,
            'summary': summary,
            'preview': df_out.head(25).to_dict(orient='records'),
            'filename': filename
        }

        flash(f"Batch prediction completed: {summary['eligible_rows']} eligible rows evaluated, {summary['higher_risk_count']} predicted higher risk.", "info")
        return redirect(url_for('batch_prediction_page'))

    except Exception as e:
        flash(f"Error processing batch prediction: {str(e)}", "danger")
        return redirect(url_for('batch_prediction_page'))

@app.route('/batch-prediction/download')
def download_batch_results():
    """Downloads batch predictions as a CSV."""
    cached = _batch_cache.get('last_batch')
    if not cached or 'df' not in cached:
        flash("No batch prediction results found to download.", "warning")
        return redirect(url_for('batch_prediction_page'))

    df = cached['df']
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    filename = f"batch_results_{cached.get('filename', 'predictions.csv')}.csv"
    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/batch-prediction/save', methods=['POST'])
def save_batch_to_database():
    """Persists eligible batch prediction records into the SQLite database."""
    cached = _batch_cache.get('last_batch')
    if not cached or 'df' not in cached:
        flash("No batch data available to save.", "warning")
        return redirect(url_for('batch_prediction_page'))

    df = cached['df']
    filename = cached.get('filename', 'batch_upload.csv')
    conn = get_db_connection()
    cursor = conn.cursor()

    count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT patient_id FROM patients WHERE patient_id LIKE 'DIA-%' ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    current_num = 0
    if last_row:
        try:
            current_num = int(last_row['patient_id'].split('-')[1])
        except (IndexError, ValueError):
            cursor.execute("SELECT COUNT(*) AS total FROM patients")
            current_num = cursor.fetchone()['total']

    for _, row in df.iterrows():
        if row.get('predicted_risk_category') in ['Higher Risk', 'Lower Risk']:
            current_num += 1
            pid = f"DIA-{current_num:05d}"
            gender = str(row.get('gender', 'Other')).capitalize()
            age = float(row.get('age', 0))
            hyp = int(row.get('hypertension', 0))
            hd = int(row.get('heart_disease', 0))
            smoke = str(row.get('smoking_history', 'No Info'))
            bmi = float(row.get('bmi', 0))
            hba1c = float(row.get('HbA1c_level', 0))
            glucose = float(row.get('blood_glucose_level', 0))
            cat = str(row.get('predicted_risk_category'))
            prob = float(row.get('risk_probability_percent', 0.0))

            cursor.execute('''
                INSERT INTO patients (
                    patient_id, name, gender, age, hypertension, heart_disease,
                    smoking_history, bmi, hba1c_level, blood_glucose_level,
                    latest_prediction, latest_probability, latest_prediction_date,
                    source, created_at, updated_at
                ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pid, gender, age, hyp, hd, smoke, bmi, hba1c, glucose,
                cat, prob, now_str, f"Batch: {filename}", now_str, now_str
            ))

            cursor.execute('''
                INSERT INTO predictions (
                    patient_id, prediction_category, risk_probability,
                    model_version, features_json, prediction_date
                ) VALUES (?, ?, ?, '1.0', ?, ?)
            ''', (pid, cat, prob, json.dumps(row.to_dict()), now_str))

            count += 1

    conn.commit()
    conn.close()

    flash(f"Successfully saved {count} batch patient records into the database.", "info")
    return redirect(url_for('patients_page'))

@app.route('/datasets')
def datasets_page():
    """Dataset management page."""
    uploads = get_upload_history()
    inspection = session.pop('dataset_inspection', None)
    return render_template('datasets.html', uploads=uploads, inspection=inspection, active_page='datasets')

@app.route('/datasets/import', methods=['POST'])
def import_dataset_records():
    """Operation A: Import Historical Records into patient DB."""
    if 'dataset_file' not in request.files:
        flash("No dataset file selected.", "warning")
        return redirect(url_for('datasets_page'))

    file = request.files['dataset_file']
    if file.filename == '' or not allowed_file(file.filename):
        flash("Please upload a valid CSV or Excel file.", "warning")
        return redirect(url_for('datasets_page'))

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"import_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
    file.save(save_path)

    perform_pred = 'perform_predictions' in request.form
    dup_action = request.form.get('duplicate_action', 'skip')

    try:
        res = import_historical_records(save_path, perform_predictions=perform_pred, duplicate_action=dup_action)
        flash(f"Import complete: {res['imported_count']} records imported, {res['skipped_count']} duplicate records skipped.", "info")
    except Exception as e:
        flash(f"Error importing records: {str(e)}", "danger")

    return redirect(url_for('datasets_page'))

@app.route('/datasets/retrain', methods=['POST'])
def retrain_dataset_model():
    """Operation B: Upload Labeled Training Dataset & retrain model pipeline."""
    if 'training_file' not in request.files:
        flash("No training file selected.", "warning")
        return redirect(url_for('datasets_page'))

    file = request.files['training_file']
    if file.filename == '' or not allowed_file(file.filename):
        flash("Please upload a valid CSV or Excel file.", "warning")
        return redirect(url_for('datasets_page'))

    target_col = request.form.get('target_column', 'diabetes').strip()
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"train_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
    file.save(save_path)

    try:
        metrics = retrain_model_from_dataset(save_path, target_col=target_col)
        flash(f"Model successfully retrained! New winner: {metrics['selected_model']} (Recall: {metrics['best_metrics']['recall']*100:.1f}%, ROC-AUC: {metrics['best_metrics']['roc_auc']}).", "info")
        return redirect(url_for('model_performance_page'))
    except Exception as e:
        flash(f"Retraining failed: {str(e)}", "danger")
        return redirect(url_for('datasets_page'))

@app.route('/model-performance')
def model_performance_page():
    """Academic model performance benchmarks, ROC curves, and confusion matrix."""
    metrics_path = Config.METRICS_PATH
    if not os.path.exists(metrics_path):
        train_and_compare_models()

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    return render_template('model_performance.html', metrics=metrics, active_page='model')

@app.route('/habit-planner')
def habit_planner_page():
    """7-Day Healthy Habit Planner tracking."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id, name FROM patients ORDER BY id DESC LIMIT 100")
    patients = [dict(r) for r in cursor.fetchall()]
    conn.close()

    selected_pid = request.args.get('patient_id')
    if not selected_pid and patients:
        selected_pid = patients[0]['patient_id']

    plan = get_patient_habit_plan(selected_pid) if selected_pid else {'grid': {}, 'progress_percent': 0.0}
    return render_template(
        'habit_planner.html',
        patients_list=patients,
        selected_patient_id=selected_pid,
        plan=plan,
        active_page='habits'
    )

@app.route('/habit-planner/save', methods=['POST'])
def save_habit_plan():
    """Saves updated habit plan checkboxes for a patient."""
    patient_id = request.form.get('patient_id')
    week_start = request.form.get('week_start_date')

    grid = {'walk': {}, 'water': {}, 'meal': {}, 'sleep': {}}
    for h in ['walk', 'water', 'meal', 'sleep']:
        for d in DAYS_OF_WEEK:
            field_name = f"habit_{h}_{d}"
            grid[h][d] = field_name in request.form

    save_patient_habit_plan(patient_id, grid, week_start=week_start)
    flash(f"Habit planner progress updated for patient {patient_id}.", "info")
    return redirect(url_for('habit_planner_page', patient_id=patient_id))

@app.route('/doctor-summary/<patient_id>')
def doctor_summary_page(patient_id):
    """Printable physician consultation summary."""
    patient = get_patient(patient_id)
    if not patient:
        flash(f"Patient {patient_id} not found.", "warning")
        return redirect(url_for('patients_page'))

    history = get_patient_history(patient_id)
    latest_pred = history['predictions'][0] if history['predictions'] else None
    summary_data = generate_doctor_visit_summary(patient, latest_pred)

    return render_template('doctor_summary.html', summary=summary_data)

@app.route('/reports')
def reports_page():
    """Reports and cohort analytics."""
    stats = get_dashboard_metrics()
    metrics = {}
    if os.path.exists(Config.METRICS_PATH):
        with open(Config.METRICS_PATH, 'r') as f:
            metrics = json.load(f)

    return render_template('reports.html', stats=stats, metrics=metrics, active_page='reports')

@app.route('/reports/export/patients')
def export_patients_csv():
    """Exports all patient records as a downloadable CSV."""
    csv_data = generate_patients_csv()
    filename = f"diavision_patients_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/reports/export/audit')
def export_audit_csv():
    """Exports the audit log as a downloadable CSV."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC")
    logs = [dict(r) for r in cursor.fetchall()]
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Audit ID', 'Patient ID', 'Action', 'Timestamp', 'User Note', 'Fields Changed'])

    for l in logs:
        writer.writerow([
            l['id'], l['patient_id'], l['action'],
            l['timestamp'], l['user_note'], l['fields_changed']
        ])

    filename = f"diavision_audit_logs_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/reports/export/metrics')
def export_metrics_json():
    """Downloads the serialized model evaluation metrics."""
    if os.path.exists(Config.METRICS_PATH):
        return send_file(
            Config.METRICS_PATH,
            as_attachment=True,
            download_name=f"diavision_metrics_{datetime.now().strftime('%Y%m%d')}.json",
            mimetype="application/json"
        )
    flash("Metrics file not found.", "warning")
    return redirect(url_for('reports_page'))

@app.route('/data/sample-template')
def download_sample_template():
    """Downloads the sample batch CSV template."""
    template_path = os.path.join(Config.DATA_DIR, 'sample_batch_template.csv')
    if os.path.exists(template_path):
        return send_file(
            template_path,
            as_attachment=True,
            download_name="sample_patient_batch_template.csv",
            mimetype="text/csv"
        )
    flash("Sample template file not found.", "warning")
    return redirect(url_for('datasets_page'))

# ==============================================================================
# Error Handlers
# ==============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
