import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report, precision_recall_curve, average_precision_score
from sklearn.calibration import CalibratedClassifierCV
import joblib
import json
from pathlib import Path

def create_synthetic_data():
    np.random.seed(42)
    n_samples = 200000
    
    # Generate base features
    amounts = np.clip(np.random.lognormal(mean=3.2, sigma=1.0, size=n_samples), 10, 5000)
    hours = np.random.randint(0, 24, size=n_samples)
    new_country = np.random.binomial(1, 0.05, size=n_samples)
    new_device = np.random.binomial(1, 0.06, size=n_samples)
    velocity = np.random.poisson(1.5, size=n_samples)
    
    # Engineered features
    amount_zscore = (amounts - np.mean(amounts)) / np.std(amounts)
    is_night = ((hours >= 23) | (hours <= 5)).astype(int)
    
    fraud_labels = np.zeros(n_samples, dtype=int)
    
    for i in range(n_samples):
        fraud_score = 0
        
        # Simple scoring system
        if amounts[i] > 1000:
            fraud_score += 3
        elif amounts[i] > 500:
            fraud_score += 1
            
        if is_night[i]:
            fraud_score += 2
            
        if new_country[i]:
            fraud_score += 4
            
        if new_device[i]:
            fraud_score += 2
            
        if velocity[i] >= 5:
            fraud_score += 3
        elif velocity[i] >= 3:
            fraud_score += 1
        
        # Make fraud based on score
        if fraud_score >= 7:
            fraud_labels[i] = 1 if np.random.random() < 0.90 else 0
        elif fraud_score >= 5:
            fraud_labels[i] = 1 if np.random.random() < 0.70 else 0
        elif fraud_score >= 3:
            fraud_labels[i] = 1 if np.random.random() < 0.30 else 0
        else:
            fraud_labels[i] = 1 if np.random.random() < 0.01 else 0
    
    features = np.column_stack([
        amounts, 
        hours, 
        new_country, 
        new_device, 
        velocity,
        amount_zscore,
        is_night
    ])
    
    fraud_rate = np.mean(fraud_labels)
    print(f"Fraud rate: {fraud_rate:.3f} ({int(fraud_rate * n_samples)} fraud cases)")
    
    return features, fraud_labels

def train_fraud_model():
    print("Creating synthetic fraud dataset...")
    X, y = create_synthetic_data()
    
    fraud_pct = np.mean(y) * 100
    print(f"Generated {len(X):,} transactions ({fraud_pct:.1f}% fraud)")
    
    if fraud_pct < 1.0:
        print("⚠️ WARNING: Fraud rate too low, model may not learn")
    # Train/Val/Test split: 60/20/20
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    print("\nTraining Random Forest classifier...")
    base = RandomForestClassifier(
        n_estimators=300,
        max_depth=14,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight={0: 1, 1: 4},  # less aggressive -> favors precision
        random_state=42,
        n_jobs=-1,
    )
    base.fit(X_train, y_train)

    # Probability calibration on validation set (isotonic)
    print("Calibrating probabilities (isotonic)...")
    clf = CalibratedClassifierCV(base, method="isotonic", cv="prefit")
    clf.fit(X_val, y_val)

    # Evaluate with PR metrics and choose threshold for >=90% precision on validation
    y_scores_val = clf.predict_proba(X_val)[:, 1]
    y_scores_test = clf.predict_proba(X_test)[:, 1]
    ap = average_precision_score(y_test, y_scores_test)
    print(f"\nAverage Precision (PR AUC) on test: {ap:.3f}")

    target_precision = 0.90
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_scores_val)
    chosen = 0.99  # fallback high threshold
    best_recall = -1.0
    # thresholds array is len-1 of precisions/recalls; pad to iterate safely
    padded_thresholds = list(thresholds) + ([thresholds[-1]] if len(thresholds) else [0.99])
    for p, r, t in zip(precisions, recalls, padded_thresholds):
        if p >= target_precision and r > best_recall:
            chosen = float(t)
            best_recall = r
    print(f"Chosen threshold (val) for precision>={target_precision:.2f}: {chosen:.4f} (val recall {best_recall:.3f})")

    # Report metrics on test at chosen threshold
    y_pred_test = (y_scores_test >= chosen).astype(int)
    precision = precision_score(y_test, y_pred_test, zero_division=0)
    recall = recall_score(y_test, y_pred_test, zero_division=0)
    f1 = f1_score(y_test, y_pred_test, zero_division=0)
    
    print(f"\nAt threshold {chosen:.4f} on test -> Precision: {precision:.3f}  Recall: {recall:.3f}  F1: {f1:.3f}")
    print("\nClassification Report (test):")
    print(classification_report(y_test, y_pred_test, target_names=['Legit', 'Fraud'], zero_division=0))

    # Feature importances from base model (pre-calibration)
    feature_names = ['amount', 'hour', 'new_country', 'new_device', 'velocity', 'amount_zscore', 'is_night']
    importances = base.feature_importances_
    print("\nFeature Importances:")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {imp:.3f}")

    # Save calibrated model and chosen threshold
    joblib.dump(clf, "model.pkl")
    Path("threshold.json").write_text(json.dumps({"threshold": chosen}))
    print("\n✅ Saved model.pkl and threshold.json")

if __name__ == "__main__":
    train_fraud_model()