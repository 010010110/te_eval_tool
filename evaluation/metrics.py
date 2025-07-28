import os
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score
)
from sklearn.preprocessing import label_binarize


def youdens_j(recall, specificity):
    return recall + specificity - 1


def compute_specificity(cm):
    """
    Computes specificity for each class from confusion matrix.
    """
    FP = cm.sum(axis=0) - np.diag(cm)
    TN = cm.sum() - (FP + cm.sum(axis=1) - np.diag(cm) + np.diag(cm))
    FN = cm.sum(axis=1) - np.diag(cm)
    with np.errstate(divide='ignore', invalid='ignore'):
        specificity = TN / (TN + FP)
    return np.nan_to_num(specificity)


def evaluate_model(predictions, labels, outputs_dir, probabilities=None, class_names=None):
    os.makedirs(outputs_dir, exist_ok=True)

    accuracy = accuracy_score(labels, predictions)
    precision = precision_score(labels, predictions, average='macro', zero_division=0)
    recall = recall_score(labels, predictions, average='macro', zero_division=0)
    f1 = f1_score(labels, predictions, average='macro', zero_division=0)
    cm = confusion_matrix(labels, predictions)

    metrics = {
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1,
    }

    # auROC and mAP (only if probabilities are provided)
    if probabilities is not None and class_names is not None:
        labels_bin = label_binarize(labels, classes=class_names)
        try:
            roc_auc = roc_auc_score(labels_bin, probabilities, average='macro', multi_class='ovr')
            metrics["auROC"] = roc_auc
        except ValueError:
            metrics["auROC"] = "unavailable"

        try:
            ap_score = average_precision_score(labels_bin, probabilities, average='macro')
            metrics["mAP"] = ap_score
        except ValueError:
            metrics["mAP"] = "unavailable"
    else:
        metrics["auROC"] = "not available (no probabilities)"
        metrics["mAP"] = "not available (no probabilities)"

    # Youden’s J
    specificities = compute_specificity(cm)
    mean_specificity = np.mean(specificities)
    j_stat = youdens_j(recall, mean_specificity)
    metrics["Youden’s J"] = j_stat

    # Save metrics
    metrics_path = os.path.join(outputs_dir, "metrics.txt")
    with open(metrics_path, "w") as f:
        for k, v in metrics.items():
            f.write(f"{k}: {v:.4f}\n" if isinstance(v, float) else f"{k}: {v}\n")

    # Save confusion matrix
    cm_df = pd.DataFrame(cm)
    cm_df.to_csv(os.path.join(outputs_dir, "confusion_matrix.csv"), index=False)

    print("✅ Evaluation complete. Metrics and confusion matrix saved.")
