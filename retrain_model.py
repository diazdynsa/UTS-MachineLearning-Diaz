"""
Script retrain model dengan scikit-learn versi terbaru.
Jalankan dengan: python3.11 retrain_model.py
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(ROOT_DIR, "dataset", "personality_datasert.csv")
MODEL_DIR = os.path.join(ROOT_DIR, "model")

# ---------------------------------------------------------------------------
# 1. Load dataset
# ---------------------------------------------------------------------------
df = pd.read_csv(DATASET_PATH)
print(f"Dataset shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Personality value counts:\n{df['Personality'].value_counts()}")

# ---------------------------------------------------------------------------
# 2. Preprocessing
# ---------------------------------------------------------------------------
# Drop duplicates
df = df.drop_duplicates().reset_index(drop=True)
print(f"After dedup: {df.shape}")

# Target
df["label"] = (df["Personality"] == "Extrovert").astype(int)

# Features
NUM_COLS = [
    "Time_spent_Alone",
    "Social_event_attendance",
    "Going_outside",
    "Friends_circle_size",
    "Post_frequency",
]
CAT_COLS = ["Stage_fear", "Drained_after_socializing"]
ALL_FEATURES = NUM_COLS + CAT_COLS

# Impute missing values
for col in NUM_COLS:
    median_val = df[col].median()
    df[col] = df[col].fillna(median_val)
for col in CAT_COLS:
    mode_val = df[col].mode()[0]
    df[col] = df[col].fillna(mode_val)

X = df[ALL_FEATURES]
y = df["label"]

# ---------------------------------------------------------------------------
# 3. Train/test split
# ---------------------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {X_train.shape}, Test: {X_test.shape}")

# ---------------------------------------------------------------------------
# 4. Build pipeline
# ---------------------------------------------------------------------------
preprocessor = ColumnTransformer(
    transformers=[
        ("num", "passthrough", NUM_COLS),
        ("cat", OneHotEncoder(drop="if_binary", handle_unknown="ignore", sparse_output=False), CAT_COLS),
    ]
)

pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        n_jobs=-1,
    )),
])

# ---------------------------------------------------------------------------
# 5. Train
# ---------------------------------------------------------------------------
pipeline.fit(X_train, y_train)
print("Model trained!")

# ---------------------------------------------------------------------------
# 6. Evaluate
# ---------------------------------------------------------------------------
y_pred = pipeline.predict(X_test)
acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
cm = confusion_matrix(y_test, y_pred).tolist()

print(f"Accuracy : {acc:.4f}")
print(f"Precision: {prec:.4f}")
print(f"Recall   : {rec:.4f}")
print(f"F1 Score : {f1:.4f}")
print(f"Confusion Matrix: {cm}")

# ---------------------------------------------------------------------------
# 7. Feature importances
# ---------------------------------------------------------------------------
# Get feature names after transform
ohe = pipeline.named_steps["preprocessor"].named_transformers_["cat"]
ohe_features = ohe.get_feature_names_out(CAT_COLS).tolist()
all_transformed = [f"num__{c}" for c in NUM_COLS] + [f"cat__{c}" for c in ohe_features]

importances = pipeline.named_steps["classifier"].feature_importances_
feat_imp = sorted(
    [{"feature": n, "importance": round(float(v), 6)} for n, v in zip(all_transformed, importances)],
    key=lambda x: x["importance"],
    reverse=True,
)

# ---------------------------------------------------------------------------
# 8. Mean per class
# ---------------------------------------------------------------------------
df_extro = df[df["label"] == 1]
df_intro = df[df["label"] == 0]

mean_per_class = {
    "Extrovert": {col: round(float(df_extro[col].mean()), 4) for col in NUM_COLS},
    "Introvert": {col: round(float(df_intro[col].mean()), 4) for col in NUM_COLS},
}

# ---------------------------------------------------------------------------
# 9. Feature metadata
# ---------------------------------------------------------------------------
feature_metadata = {}
for col in NUM_COLS:
    feature_metadata[col] = {
        "type": "numerical",
        "min": float(df[col].min()),
        "max": float(df[col].max()),
        "median": float(df[col].median()),
    }
for col in CAT_COLS:
    feature_metadata[col] = {
        "type": "categorical",
        "categories": sorted(df[col].dropna().unique().tolist()),
    }

# ---------------------------------------------------------------------------
# 10. Save model
# ---------------------------------------------------------------------------
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "personality_rf_model.pkl")
joblib.dump(pipeline, MODEL_PATH)
print(f"Model saved: {MODEL_PATH}")

# ---------------------------------------------------------------------------
# 11. Save metadata
# ---------------------------------------------------------------------------
metadata = {
    "model": "RandomForestClassifier",
    "best_hyperparameters": {"n_estimators": 50, "max_depth": 5},
    "label_mapping": {"Introvert": 0, "Extrovert": 1},
    "features": {"numerical": NUM_COLS, "categorical": CAT_COLS},
    "feature_metadata": feature_metadata,
    "mean_per_class": mean_per_class,
    "feature_importance": feat_imp,
    "evaluation_metrics": {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
    },
    "confusion_matrix": cm,
    "train_test_split": {"test_size": 0.2, "stratify": True, "random_state": 42},
    "dataset": "personality_datasert.csv",
    "preprocessing": {
        "imputation_numerical": "median",
        "imputation_categorical": "mode",
        "duplicates_removed": True,
        "column_transformer": {
            "categorical": "OneHotEncoder(drop='if_binary', handle_unknown='ignore')",
            "numerical": "passthrough",
        },
    },
}

META_PATH = os.path.join(MODEL_DIR, "model_metadata.json")
with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)
print(f"Metadata saved: {META_PATH}")

# ---------------------------------------------------------------------------
# 12. Verify: test load & predict
# ---------------------------------------------------------------------------
loaded = joblib.load(MODEL_PATH)
test_row = pd.DataFrame([{
    "Time_spent_Alone": 7.0,
    "Social_event_attendance": 2.0,
    "Going_outside": 1.0,
    "Friends_circle_size": 3.0,
    "Post_frequency": 1.0,
    "Stage_fear": "Yes",
    "Drained_after_socializing": "Yes",
}], columns=ALL_FEATURES)
pred = loaded.predict(test_row)
proba = loaded.predict_proba(test_row)
print(f"Test predict: {pred}, proba: {proba}")
print("SUCCESS — model is compatible with sklearn", __import__("sklearn").__version__)
