"""
ML - Churn Prediction Model Training
Trains a RandomForest classifier on RFM + deal features,
evaluates it, and saves the model as churn_model.pkl.
"""

import pandas as pd
import numpy as np
import os
import pickle
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, accuracy_score
)
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [TRAIN] %(message)s")
logger = logging.getLogger(__name__)

ML_DIR      = os.path.dirname(__file__)
ANALYTICS_DIR = os.path.join(ML_DIR, "..", "data", "analytics")
MODEL_PATH  = os.path.join(ML_DIR, "churn_model.pkl")
SCALER_PATH = os.path.join(ML_DIR, "scaler.pkl")

FEATURES = ["recency", "frequency", "monetary", "deal_count"]
TARGET   = "churn_label"


def load_training_data() -> pd.DataFrame:
    """Load labelled churn dataset. Falls back to synthetic data if not found."""
    path = os.path.join(ANALYTICS_DIR, "churn_training_data.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df)} training samples from CSV")
        return df
    else:
        logger.warning("Training CSV not found — generating synthetic data for demo")
        return _generate_synthetic_data()


def _generate_synthetic_data(n: int = 500) -> pd.DataFrame:
    """Generate synthetic RFM-style training data for demo/testing."""
    np.random.seed(42)
    df = pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(n)],
        "recency":     np.random.randint(1, 365, n),
        "frequency":   np.random.randint(1, 30,  n),
        "monetary":    np.random.uniform(10, 2000, n).round(2),
        "deal_count":  np.random.randint(0, 10,  n),
    })
    # Higher recency → more likely to churn; lower frequency too
    churn_prob = (
        0.5 * (df["recency"] / 365) +
        0.3 * (1 - df["frequency"] / 30) +
        0.2 * (1 - df["monetary"] / 2000)
    ).clip(0, 1)
    df[TARGET] = (np.random.rand(n) < churn_prob).astype(int)
    os.makedirs(ANALYTICS_DIR, exist_ok=True)
    df.to_csv(os.path.join(ANALYTICS_DIR, "churn_training_data.csv"), index=False)
    logger.info(f"Synthetic dataset saved ({df[TARGET].sum()} churned / {n} total)")
    return df


def train():
    """Full training pipeline."""
    df = load_training_data()

    # ── Feature matrix ────────────────────────────────────────────────────────
    X = df[FEATURES].fillna(0)
    y = df[TARGET]

    logger.info(f"Class distribution: {y.value_counts().to_dict()}")

    # ── Train/test split ──────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── Scale features ────────────────────────────────────────────────────────
    scaler  = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    # ── Train RandomForest ────────────────────────────────────────────────────
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_s, y_train)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred  = model.predict(X_test_s)
    y_proba = model.predict_proba(X_test_s)[:, 1]

    accuracy = round(accuracy_score(y_test, y_pred) * 100, 2)
    auc      = round(roc_auc_score(y_test, y_proba), 4)

    logger.info(f"Accuracy: {accuracy}%")
    logger.info(f"ROC-AUC:  {auc}")
    logger.info(f"\n{classification_report(y_test, y_pred)}")

    # ── Cross-validation ──────────────────────────────────────────────────────
    cv_scores = cross_val_score(model, X_train_s, y_train, cv=5, scoring="roc_auc")
    logger.info(f"CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # ── Feature importance ────────────────────────────────────────────────────
    importance = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    logger.info(f"Feature importances:\n{importance.to_string()}")

    # ── Save model & scaler ───────────────────────────────────────────────────
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    logger.info(f"Model saved → {MODEL_PATH}")
    logger.info(f"Scaler saved → {SCALER_PATH}")

    return {
        "accuracy": accuracy,
        "roc_auc":  auc,
        "cv_mean":  round(cv_scores.mean(), 4),
    }


if __name__ == "__main__":
    metrics = train()
    print("\nTraining Results:", metrics)
