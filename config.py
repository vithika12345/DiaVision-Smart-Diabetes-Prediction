import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'diavision-healthcare-analytics-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'diavision.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    MODEL_PATH = os.path.join(MODELS_DIR, 'diavision_best_model.joblib')
    METRICS_PATH = os.path.join(MODELS_DIR, 'model_metrics.json')
    METADATA_PATH = os.path.join(MODELS_DIR, 'feature_metadata.json')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB maximum upload
    
    # Feature configurations
    DEFAULT_FEATURES = [
        'gender', 'age', 'hypertension', 'heart_disease', 
        'smoking_history', 'bmi', 'HbA1c_level', 'blood_glucose_level'
    ]
    TARGET_COLUMN = 'diabetes'
