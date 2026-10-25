import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

from config import Config
from ml.preprocessing import get_preprocessor, clean_dataset, ALL_FEATURES
from ml.model_evaluation import evaluate_classifier
from ml.preprocessing import get_preprocessor, clean_dataset, ALL_FEATURES
from ml.model_evaluation import evaluate_classifier

def train_and_compare_models(dataset_path=None, test_size=0.20, random_state=42):
    """
    Trains multiple classifiers on the diabetes dataset, evaluates them on a stratified test set,
    selects the best model prioritizing Recall and balanced F1-score, and persists the pipeline and metrics.
    """
    if dataset_path is None:
        dataset_path = os.path.join(Config.DATA_DIR, 'diabetes_prediction_dataset.csv')

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Training dataset not found at: {dataset_path}")

    print(f"Loading dataset from: {dataset_path}...")
    df_raw = pd.read_csv(dataset_path)
    df = clean_dataset(df_raw)

    target_col = Config.TARGET_COLUMN
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in dataset!")

    # Drop rows where target is missing
    df = df.dropna(subset=[target_col])
    df[target_col] = df[target_col].astype(int)

    # Features and Target
    X = df[ALL_FEATURES]
    y = df[target_col]

    print(f"Dataset Shape: {X.shape}, Positive Cases: {y.sum()} ({y.mean()*100:.2f}%)")

    # Stratified Train-Test Split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    models_to_evaluate = {
        'Logistic Regression': LogisticRegression(max_iter=1000, class_weight='balanced', random_state=random_state),
        'Decision Tree': DecisionTreeClassifier(max_depth=6, class_weight='balanced', random_state=random_state),
        'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=12, class_weight='balanced', random_state=random_state, n_jobs=-1),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=random_state)
    }

    comparison_results = []
    trained_pipelines = {}

    for name, clf in models_to_evaluate.items():
        print(f"Training {name}...")
        preprocessor = get_preprocessor()
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', clf)
        ])
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline

        eval_res = evaluate_classifier(pipeline, X_test, y_test, model_name=name)
        comparison_results.append(eval_res)
        print(f" -> {name} | Acc: {eval_res['accuracy']:.4f} | Prec: {eval_res['precision']:.4f} | Rec: {eval_res['recall']:.4f} | F1: {eval_res['f1_score']:.4f} | ROC-AUC: {eval_res['roc_auc']:.4f}")

    # Model Selection Strategy:
    # In clinical screening, Recall is prioritized to minimize False Negatives, combined with high F1-score & ROC-AUC.
    # Score formula: 0.45 * Recall + 0.35 * F1 + 0.20 * ROC_AUC
    def selection_score(item):
        return (0.45 * item['recall']) + (0.35 * item['f1_score']) + (0.20 * item['roc_auc'])

    best_eval = max(comparison_results, key=selection_score)
    best_name = best_eval['model_name']
    best_pipeline = trained_pipelines[best_name]

    print(f"\nWinning Model Selected: {best_name} (Selection Score: {selection_score(best_eval):.4f})")

    # Extract Feature Importances if available
    feature_importances = {}
    try:
        classifier_step = best_pipeline.named_steps['classifier']
        preprocessor_step = best_pipeline.named_steps['preprocessor']
        
        # Get one-hot encoded feature names
        cat_encoder = preprocessor_step.named_transformers_['cat'].named_steps['onehot']
        cat_features = list(cat_encoder.get_feature_names_out(['gender', 'smoking_history']))
        all_transformed_features = ['age', 'bmi', 'HbA1c_level', 'blood_glucose_level'] + cat_features + ['hypertension', 'heart_disease']

        if hasattr(classifier_step, 'feature_importances_'):
            raw_imp = classifier_step.feature_importances_
            feature_importances = {feat: round(float(imp), 4) for feat, imp in zip(all_transformed_features, raw_imp)}
        elif hasattr(classifier_step, 'coef_'):
            raw_coef = np.abs(classifier_step.coef_[0])
            norm_coef = raw_coef / raw_coef.sum()
            feature_importances = {feat: round(float(imp), 4) for feat, imp in zip(all_transformed_features, norm_coef)}
    except Exception as e:
        print(f"Warning: Could not extract feature importances: {e}")

    # Save Best Model Pipeline
    os.makedirs(Config.MODELS_DIR, exist_ok=True)
    os.makedirs(os.path.join(Config.MODELS_DIR, 'versions'), exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_id = f"v_{timestamp}"

    joblib.dump(best_pipeline, Config.MODEL_PATH)
    # Save a versioned backup
    version_path = os.path.join(Config.MODELS_DIR, 'versions', f"diavision_model_{version_id}.joblib")
    joblib.dump(best_pipeline, version_path)

    # Save comprehensive metrics and metadata
    metrics_data = {
        'version': version_id,
        'training_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'selected_model': best_name,
        'selection_criteria': 'Prioritizing Recall (clinical sensitivity) combined with F1-Score and ROC-AUC',
        'dataset_source': os.path.basename(dataset_path),
        'total_samples': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'positive_prevalence': round(float(y.mean()), 4),
        'best_metrics': best_eval,
        'models_comparison': comparison_results,
        'feature_importances': feature_importances
    }

    with open(Config.METRICS_PATH, 'w') as f:
        json.dump(metrics_data, f, indent=2)

    # Save Feature Metadata for frontend validation & clinical ranges
    metadata = {
        'features': ALL_FEATURES,
        'ranges': {
            'age': {'min': 1, 'max': 120, 'unit': 'years', 'label': 'Age'},
            'gender': {'options': ['Female', 'Male', 'Other'], 'label': 'Gender'},
            'hypertension': {'options': [0, 1], 'labels': {0: 'No', 1: 'Yes'}, 'label': 'Hypertension'},
            'heart_disease': {'options': [0, 1], 'labels': {0: 'No', 1: 'Yes'}, 'label': 'Heart Disease'},
            'smoking_history': {
                'options': ['never', 'No Info', 'current', 'former', 'ever', 'not current'],
                'labels': {
                    'never': 'Never Smoked',
                    'No Info': 'No Information',
                    'current': 'Current Smoker',
                    'former': 'Former Smoker',
                    'ever': 'Ever Smoked',
                    'not current': 'Not Currently Smoking'
                },
                'label': 'Smoking History'
            },
            'bmi': {'min': 10.0, 'max': 90.0, 'unit': 'kg/m²', 'normal_range': [18.5, 24.9], 'label': 'Body Mass Index (BMI)'},
            'HbA1c_level': {'min': 3.5, 'max': 16.0, 'unit': '%', 'normal_range': [4.0, 5.6], 'prediabetes': [5.7, 6.4], 'diabetes_criterion': 6.5, 'label': 'HbA1c Level'},
            'blood_glucose_level': {'min': 50, 'max': 450, 'unit': 'mg/dL', 'normal_range': [70, 99], 'prediabetes': [100, 125], 'elevated': 140, 'critical': 300, 'label': 'Blood Glucose Level'}
        }
    }

    with open(Config.METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Model saved to {Config.MODEL_PATH}")
    print(f"Metrics saved to {Config.METRICS_PATH}")
    return metrics_data

if __name__ == '__main__':
    train_and_compare_models()
