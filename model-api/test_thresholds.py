import joblib
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score

# Load model
model = joblib.load("model.pkl")

# Regenerate test data (same as training)
np.random.seed(42)
n_samples = 200000

amounts = np.clip(np.random.lognormal(mean=3.2, sigma=1.0, size=n_samples), 10, 5000)
hours = np.random.randint(0, 24, size=n_samples)
new_country = np.random.binomial(1, 0.05, size=n_samples)
new_device = np.random.binomial(1, 0.06, size=n_samples)
velocity = np.random.poisson(1.5, size=n_samples)
amount_zscore = (amounts - np.mean(amounts)) / np.std(amounts)
is_night = ((hours >= 23) | (hours <= 5)).astype(int)

fraud_labels = np.zeros(n_samples, dtype=int)

for i in range(n_samples):
    fraud_score = 0
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
    
    if fraud_score >= 7:
        fraud_labels[i] = 1 if np.random.random() < 0.90 else 0
    elif fraud_score >= 5:
        fraud_labels[i] = 1 if np.random.random() < 0.70 else 0
    elif fraud_score >= 3:
        fraud_labels[i] = 1 if np.random.random() < 0.30 else 0
    else:
        fraud_labels[i] = 1 if np.random.random() < 0.01 else 0

X = np.column_stack([amounts, hours, new_country, new_device, velocity, amount_zscore, is_night])

from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, fraud_labels, test_size=0.25, random_state=42, stratify=fraud_labels)

# Get probabilities
y_proba = model.predict_proba(X_test)[:, 1]

# Test different thresholds
print("Finding optimal threshold for 80%+ precision:\n")
for threshold in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
    y_pred = (y_proba >= threshold).astype(int)
    
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    print(f"Threshold {threshold:.2f}:")
    print(f"  Precision: {precision:.3f} ({precision*100:.1f}%)")
    print(f"  Recall: {recall:.3f} ({recall*100:.1f}%)")
    print(f"  F1-Score: {f1:.3f}")
    
    if precision >= 0.80:
        print("  ✅ MEETS 80% PRECISION TARGET")
    print()