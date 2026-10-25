import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, roc_curve
)

def evaluate_classifier(model, X_test, y_test, model_name="Model"):
    """
    Evaluates a scikit-learn classifier pipeline on a test set.
    Returns metrics, confusion matrix, and downsampled ROC curve data.
    """
    y_pred = model.predict(X_test)
    y_proba = None
    roc_auc = None
    fpr_list, tpr_list = [], []

    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)[:, 1]
        try:
            roc_auc = float(roc_auc_score(y_test, y_proba))
            fpr, tpr, _ = roc_curve(y_test, y_proba)
            # Downsample ROC curve to 30 points for smooth JSON serialization & Chart.js rendering
            indices = np.linspace(0, len(fpr) - 1, 30, dtype=int)
            fpr_list = [round(float(fpr[i]), 4) for i in indices]
            tpr_list = [round(float(tpr[i]), 4) for i in indices]
        except Exception:
            roc_auc = 0.0

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))

    cm = confusion_matrix(y_test, y_pred)
    # cm shape: [[TN, FP], [FN, TP]]
    tn = int(cm[0][0])
    fp = int(cm[0][1])
    fn = int(cm[1][0])
    tp = int(cm[1][1])

    return {
        'model_name': model_name,
        'accuracy': round(acc, 4),
        'precision': round(prec, 4),
        'recall': round(rec, 4),
        'f1_score': round(f1, 4),
        'roc_auc': round(roc_auc, 4) if roc_auc is not None else 0.0,
        'confusion_matrix': {
            'tn': tn,
            'fp': fp,
            'fn': fn,
            'tp': tp,
            'matrix': [[tn, fp], [fn, tp]]
        },
        'roc_curve': {
            'fpr': fpr_list,
            'tpr': tpr_list
        }
    }
