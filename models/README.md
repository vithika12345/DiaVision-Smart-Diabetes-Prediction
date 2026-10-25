# Diavision Machine Learning Models

This directory stores serialized scikit-learn classification pipelines, evaluation benchmark metrics, and model versions.

## Current Winning Pipeline

- **File**: `diavision_best_model.joblib`
- **Algorithm**: Random Forest Classifier (`n_estimators=100`, `max_depth=12`, `class_weight='balanced'`)
- **Key Metrics on Held-out 20% Test Partition**:
  - **Recall (Sensitivity)**: **90.35%** (prioritized in clinical screening to minimize false negatives)
  - **ROC-AUC**: **0.9761**
  - **Overall Accuracy**: **90.87%**
  - **F1-Score**: **0.6272**
- **Metrics File**: `model_metrics.json`
- **Clinical Feature Metadata**: `feature_metadata.json`
- **Versioned Backups**: Stored in `versions/` whenever retraining is performed.
