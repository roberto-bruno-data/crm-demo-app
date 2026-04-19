from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    average_precision_score,
    matthews_corrcoef,
    roc_curve,
    precision_recall_curve,
    ConfusionMatrixDisplay
)
import matplotlib.pyplot as plt

def evaluate_model(best_rf, X_val, y_val, X_test, y_test):
    # Evaluation
    #_________________________________________________________________________

    y_val_prob = best_rf.predict_proba(X_val)[:, 1]
    y_val_pred = best_rf.predict(X_val)

    y_test_prob = best_rf.predict_proba(X_test)[:, 1]
    y_test_pred = best_rf.predict(X_test)

    # Confusion Matrix
    ConfusionMatrixDisplay.from_estimator(best_rf, X_test, y_test, cmap="Blues")
    plt.title("Confusion Matrix (Test)")
    plt.show()

    # Validation Performance
    y_val_pred = best_rf.predict(X_val)
    print("Validation Report:")
    print(classification_report(y_val, y_val_pred))

    # Test Performance
    y_test_pred = best_rf.predict(X_test)
    print("Test Report:")
    print(classification_report(y_test, y_test_pred))

    # Wahrscheinlichkeiten für ROC/PR
    y_val_prob = best_rf.predict_proba(X_val)[:, 1]
    y_test_prob = best_rf.predict_proba(X_test)[:, 1]

    # Metriken: Validation
    print("Validation ROC-AUC:", roc_auc_score(y_val, y_val_prob))
    print("Validation PR-AUC :", average_precision_score(y_val, y_val_prob))
    print("Validation MCC    :", matthews_corrcoef(y_val, y_val_pred))

    # Metriken: Test
    print("Test ROC-AUC:", roc_auc_score(y_test, y_test_prob))
    print("Test PR-AUC :", average_precision_score(y_test, y_test_prob))
    print("Test MCC    :", matthews_corrcoef(y_test, y_test_pred))

    # ROC- und PR-Kurven für Test-Set
    fpr, tpr, _ = roc_curve(y_test, y_test_prob)
    prec, rec, _ = precision_recall_curve(y_test, y_test_prob)

    plt.figure(figsize=(14, 4))

    # ROC-Kurve
    plt.subplot(1, 2, 1)
    plt.plot(fpr, tpr, label=f"ROC AUC = {roc_auc_score(y_test, y_test_prob):.2f}")
    plt.plot([0, 1], [0, 1], 'k--', label="Random")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate (Recall)")
    plt.title("ROC Curve (Test)")
    plt.legend()

    # Precision-Recall-Kurve
    plt.subplot(1, 2, 2)
    plt.plot(rec, prec, label=f"PR AUC = {average_precision_score(y_test, y_test_prob):.2f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve (Test)")
    plt.legend()

    plt.tight_layout()
    plt.show()