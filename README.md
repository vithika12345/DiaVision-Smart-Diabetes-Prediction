# Diavision — Diabetes Prediction & Patient Records Management System

> **Academic Machine Learning & Clinical Decision-Support System**  
> Built with Python Flask, Scikit-Learn, Pandas, SQLite, Chart.js, and Lucide Icons.

---

## 1. Overview & Key Objectives

**Diavision** is an end-to-end healthcare web application designed to predict diabetes risk using patient health biomarkers and an optimized machine learning pipeline. It provides a real, persistent SQLite patient record management system, feature explainability, high-throughput batch prediction, live interactive analytics, personalized health recommendations (including Indian balanced meal guidance), and printable clinical consultation summaries.

### Core Features

1. **New Patient Intake & Prediction**:
   - Generates sequential, permanent Patient IDs (`DIA-00001`, `DIA-00002`, etc.).
   - Supports demographic and physiological parameters (`gender`, `age`, `hypertension`, `heart_disease`, `smoking_history`, `bmi`, `HbA1c_level`, `blood_glucose_level`).
   - Calibrated probability estimates with clear categorization into **Lower Risk** or **Higher Risk**.
   - Explainability engine highlighting contributing factors based on clinical reference thresholds.

2. **Personalized Health Guidance**:
   - **Recommended Actions** ("What Should I Do?") card.
   - **Habits to Limit or Avoid** ("What Should I Avoid?") card.
   - **Personalized Physical Activity Guidance** tailored to age, BMI, and cardiovascular condition.
   - **Balanced Food Guidance** featuring practical Indian meal examples (roti with dal & vegetables, portioned rice with roasted legumes, sprout salads).
   - **Smart Health Alerts** triggering immediate clinical review notices for critical glucose readings (>= 300 mg/dL) or marked hyperglycemia (>= 200 mg/dL).

3. **Patient Records Management**:
   - Searchable, filterable, sortable, and paginated patient table.
   - Profile view with **Health Progress Tracker** (date-wise glucose and risk trajectory charts).
   - Audit trail tracking every field update, timestamp, and modification note.
   - Prediction history log ensuring historical predictions are never silently overwritten.

4. **Batch Prediction & Dataset Management**:
   - Upload CSV or Excel (`.xlsx`, `.xls`) files.
   - **Operation A (Import Historical Records)**: Ingests spreadsheets into SQLite with duplicate detection and batch predictions.
   - **Operation B (Model Retraining)**: Benchmark and retrain classifiers on new labeled datasets with automatic versioned backups in `models/versions/`.

5. **7-Day Healthy Habit Planner**:
   - Interactive weekly wellness planner tracking daily walking, optimal hydration, balanced meals, and restorative sleep.
   - Real-time weekly progress meter saved in SQLite.

6. **Doctor Visit Consultation Summary**:
   - Printable consultation summary formatted with Diavision branding, recorded biomarkers, observation tiers, targeted physician inquiry questions, and appointment checklists.

---

## 2. Technology Stack

- **Backend**: Python 3.10+ / Flask 3.x
- **Machine Learning**: scikit-learn, pandas, NumPy, joblib
- **Database**: SQLite with parameterized queries
- **Data Ingestion**: openpyxl for Excel uploads, pandas for CSV parsing
- **Frontend**: HTML5, Vanilla CSS3 (Custom Healthcare Design System with Dark/Light Mode), JavaScript
- **Visualizations**: Chart.js
- **Icons**: Lucide Icons
- **Testing**: Python `unittest` suite (14 automated tests)

---

## 3. Project Structure

```
Diavision_Diabetes_Prediction/
├── app.py                     # Main Flask application entry point & routes
├── config.py                  # Environment and file path configuration
├── requirements.txt           # Python package dependencies
├── README.md                  # Complete documentation and setup guide
├── .env.example               # Environment variables template
├── .gitignore                 # Version control ignore rules
├── database/
│   ├── __init__.py
│   └── db.py                  # SQLite schema creation and connection manager
├── ml/
│   ├── __init__.py
│   ├── preprocessing.py       # Scikit-learn ColumnTransformer pipeline & data cleaning
│   ├── train_model.py         # Multi-model training, evaluation & recall-prioritizing selection
│   ├── predict.py             # Single & batch inference engine with explainability
│   └── model_evaluation.py   # Accuracy, precision, recall, F1, ROC-AUC & confusion matrix
├── models/
│   ├── diavision_best_model.joblib # Serialized winning Random Forest classifier
│   ├── model_metrics.json          # Real calculated metrics, confusion matrix & ROC points
│   ├── feature_metadata.json       # Clinical bounds and validation ranges
│   ├── versions/                   # Versioned backups from retraining
│   └── README.md
├── services/
│   ├── __init__.py
│   ├── patient_service.py     # Patient record CRUD, auto ID generator & audit logs
│   ├── dataset_service.py     # CSV/Excel parsing, historical imports & model retraining
│   ├── recommendation_service.py # Clinical guidance rules, Indian diet & alert triggers
│   ├── habit_service.py       # 7-day habit planner tracker
│   └── report_service.py      # Printable report generator & CSV export builder
├── templates/
│   ├── base.html              # Healthcare shell with sidebar, topbar & theme toggle
│   ├── dashboard.html         # Live database statistics and 6 Chart.js charts
│   ├── predict.html           # New patient registration and prediction form
│   ├── prediction_result.html # Detailed results, explainability & guidance
│   ├── patients.html          # Patient records table with search, filters & modals
│   ├── patient_detail.html    # Profile, health progress tracker & prediction history
│   ├── datasets.html          # Dataset upload, historical import & model retraining
│   ├── batch_prediction.html  # Multi-record batch inference & CSV download
│   ├── model_performance.html # Metrics cards, model comparison table & ROC curve
│   ├── habit_planner.html     # Dedicated 7-day healthy habit planner
│   ├── doctor_summary.html    # Printable physician consultation handout
│   ├── reports.html           # Cohort analytics and CSV exports
│   ├── 404.html               # 404 error page
│   └── 500.html               # 500 error page
├── static/
│   ├── css/
│   │   └── style.css          # Deep navy & teal theme, responsive, dark/light modes
│   ├── js/
│   │   ├── main.js            # Sidebar toggle, theme switcher, modals, toasts
│   │   ├── dashboard.js       # Chart.js initialization for dashboard
│   │   └── patient_charts.js  # Patient detail glucose/risk trend charts
│   └── images/
│       └── logo.svg           # Custom medical shield SVG logo
├── uploads/                   # Secure uploaded files directory
├── instance/                  # SQLite database location (diavision.db)
├── tests/
│   ├── test_routes.py         # Flask route and template tests
│   ├── test_prediction.py     # ML inference and explainability tests
│   ├── test_dataset_upload.py # Dataset parsing and schema validation tests
│   └── test_recommendations.py# Health recommendation logic tests
└── data/
    ├── diabetes_prediction_dataset.csv # 100,000-record dataset
    └── sample_batch_template.csv       # Ready-to-use CSV template
```

---

## 4. VS Code Setup & Execution (Windows PowerShell)

Follow these exact steps in **Visual Studio Code** on Windows:

### Step 1: Open the Project Folder
1. Open VS Code.
2. Click **File > Open Folder...** and select `Diavision_Diabetes_Prediction` (or the project root).
3. Open a PowerShell terminal in VS Code: Press `Ctrl + ~` or go to **Terminal > New Terminal**.

### Step 2: Create and Activate Virtual Environment
```powershell
# Create a Python virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then run `.\venv\Scripts\Activate.ps1`)*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Machine Learning Training Script (Optional)
The project comes pre-trained with the serialized Random Forest pipeline. If you wish to retrain from scratch using the 100,000-sample dataset:
```powershell
python ml/train_model.py
```
*This benchmarks Logistic Regression, Decision Tree, Random Forest, and Gradient Boosting on a stratified 20% test partition, evaluates clinical recall, and saves the winning pipeline to `models/diavision_best_model.joblib`.*

### Step 5: Run Automated Tests
Verify that all 14 unit and integration tests pass:
```powershell
python -m unittest discover tests
```

### Step 6: Start the Flask Application
```powershell
python app.py
```

### Step 7: Open the Application in Your Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 5. Machine Learning Evaluation & Results

Evaluated on a **20% held-out stratified test set (20,000 patient records)**:

| Model | Accuracy | Precision | Recall (Sensitivity) | F1-Score | ROC-AUC | Selection Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Random Forest (Balanced)** | **90.87%** | **48.03%** | **90.35%** | **0.6272** | **0.9761** | **Selected Winner** |
| Logistic Regression | 88.89% | 42.66% | 89.41% | 0.5776 | 0.9629 | Benchmark |
| Decision Tree | 85.88% | 36.89% | 93.12% | 0.5285 | 0.9693 | Benchmark |
| Gradient Boosting | 97.25% | 98.08% | 68.94% | 0.8097 | 0.9795 | Benchmark |

### Why Recall Was Given Special Weight:
In healthcare disease screening, **missing a true diabetic individual (False Negative)** can lead to undetected disease progression, organ damage, or complications. Flagging a patient for follow-up laboratory testing (False Positive) is far safer. The winning **Random Forest** achieved **90.35% Recall** (catching 1,536 out of 1,700 diabetic cases in the test partition) while maintaining a high **0.9761 ROC-AUC** and **90.87% overall accuracy**.

---

## 6. Medical Decision-Support Disclaimer

> **IMPORTANT NOTICE:**  
> Diavision is an **educational machine learning decision-support prototype** developed for academic research.  
> The predictions generated by the machine learning models are **statistical risk estimates, NOT a confirmed medical diagnosis**.  
> The health recommendations provided are **general educational information** and do not substitute for consultation with a licensed healthcare professional.  
> **Never start, stop, or alter prescribed medications based on this application.**
