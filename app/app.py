"""
Flask App — Klasifikasi Kepribadian Extrovert / Introvert
UTS Pembelajaran Mesin | Random Forest
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, session

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "uts-ml-diaz-secret-2024")

# ---------------------------------------------------------------------------
# Load model & metadata
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(ROOT_DIR, "model", "personality_rf_model.pkl")
META_PATH = os.path.join(ROOT_DIR, "model", "model_metadata.json")

# Compatibility shim for unpickling ColumnTransformer across scikit-learn versions
try:
    import sklearn.compose._column_transformer as _ct
    if not hasattr(_ct, "_RemainderColsList"):
        _ct._RemainderColsList = type("_RemainderColsList", (list,), {})
except Exception:
    pass

pipeline = joblib.load(MODEL_PATH)

with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

NUM_COLS = metadata["features"]["numerical"]
CAT_COLS = metadata["features"]["categorical"]
ALL_FEATURES = NUM_COLS + CAT_COLS
FEATURE_META = metadata["feature_metadata"]
MEAN_PER_CLASS = metadata["mean_per_class"]
FEATURE_IMPORTANCE = metadata["feature_importance"]
EVAL_METRICS = metadata["evaluation_metrics"]
LABEL_MAP = metadata["label_mapping"]
REVERSE_LABEL = {v: k for k, v in LABEL_MAP.items()}
HYPERPARAMS = metadata["best_hyperparameters"]
CONFUSION_MATRIX = metadata.get("confusion_matrix", [[0, 0], [0, 0]])

# Human-friendly Indonesian labels for features
FEATURE_LABELS = {
    "Time_spent_Alone": "Waktu Menyendiri (jam/hari)",
    "Social_event_attendance": "Kehadiran Acara Sosial (0–10)",
    "Going_outside": "Frekuensi Keluar Rumah (0–7/minggu)",
    "Friends_circle_size": "Jumlah Teman Dekat (0–15)",
    "Post_frequency": "Frekuensi Unggahan Sosmed (0–10)",
    "Stage_fear": "Cemas Tampil di Depan Umum",
    "Drained_after_socializing": "Lelah Setelah Bersosialisasi",
}

# Clean feature importance names for display
CLEAN_IMPORTANCE = []
for item in FEATURE_IMPORTANCE:
    raw = item["feature"]
    # Strip prefixes like cat__ num__
    name = raw.split("__", 1)[-1] if "__" in raw else raw
    # Map back to human label if possible
    base = name.replace("_Yes", "").replace("_No", "")
    label = FEATURE_LABELS.get(base, name)
    if "_Yes" in name:
        label += " (Ya)"
    elif "_No" in name:
        label += " (Tidak)"
    CLEAN_IMPORTANCE.append({
        "feature": name,
        "label": label,
        "importance": item["importance"],
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Render main page with metadata injected."""
    return render_template(
        "index.html",
        feature_labels=FEATURE_LABELS,
        feature_meta=FEATURE_META,
        mean_per_class=MEAN_PER_CLASS,
        feature_importance=CLEAN_IMPORTANCE,
        eval_metrics=EVAL_METRICS,
        hyperparams=HYPERPARAMS,
        confusion_matrix=CONFUSION_MATRIX,
        num_cols=NUM_COLS,
        cat_cols=CAT_COLS,
    )


@app.route("/api/predict", methods=["POST"])
def predict():
    """Accept JSON input, validate, predict, return results."""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    # --- Validate & build input row ----
    row = {}
    errors = []

    for col in NUM_COLS:
        val = data.get(col)
        if val is None or val == "":
            errors.append(f"{FEATURE_LABELS.get(col, col)} wajib diisi.")
            continue
        try:
            val = float(val)
        except (ValueError, TypeError):
            errors.append(f"{FEATURE_LABELS.get(col, col)} harus berupa angka.")
            continue
        meta = FEATURE_META[col]
        if val < meta["min"] or val > meta["max"]:
            errors.append(
                f"{FEATURE_LABELS.get(col, col)}: nilai harus antara "
                f"{meta['min']:.0f} – {meta['max']:.0f}."
            )
            continue
        row[col] = val

    for col in CAT_COLS:
        val = data.get(col)
        if val is None or val == "":
            errors.append(f"{FEATURE_LABELS.get(col, col)} wajib diisi.")
            continue
        allowed = FEATURE_META[col]["categories"]
        if val not in allowed:
            errors.append(
                f"{FEATURE_LABELS.get(col, col)}: pilih salah satu dari {allowed}."
            )
            continue
        row[col] = val

    if errors:
        return jsonify({"error": "; ".join(errors)}), 422

    # --- Predict ---
    input_df = pd.DataFrame([row], columns=ALL_FEATURES)
    pred_class = int(pipeline.predict(input_df)[0])
    pred_proba = pipeline.predict_proba(input_df)[0]

    pred_label = REVERSE_LABEL[pred_class]
    proba_dict = {
        REVERSE_LABEL[i]: round(float(p) * 100, 2)
        for i, p in enumerate(pred_proba)
    }

    # --- User vs class means ---
    comparison = {}
    for col in NUM_COLS:
        comparison[col] = {
            "user": row[col],
            "mean_introvert": MEAN_PER_CLASS["Introvert"].get(col, 0),
            "mean_extrovert": MEAN_PER_CLASS["Extrovert"].get(col, 0),
            "label": FEATURE_LABELS.get(col, col),
        }

    # --- Dominant factors ---
    imp_lookup = {it["feature"]: it["importance"] for it in CLEAN_IMPORTANCE}
    factors = []
    for col in NUM_COLS:
        diff_intro = abs(row[col] - MEAN_PER_CLASS["Introvert"].get(col, 0))
        diff_extro = abs(row[col] - MEAN_PER_CLASS["Extrovert"].get(col, 0))
        closer_to = "Introvert" if diff_intro < diff_extro else "Extrovert"
        base_imp = imp_lookup.get(col, 0)
        factors.append({
            "feature": col,
            "label": FEATURE_LABELS.get(col, col),
            "value": row[col],
            "closer_to": closer_to,
            "importance": base_imp,
        })
    for col in CAT_COLS:
        key = f"{col}_Yes" if row[col] == "Yes" else f"{col}_No"
        base_imp = imp_lookup.get(key, imp_lookup.get(col, 0))
        factors.append({
            "feature": col,
            "label": FEATURE_LABELS.get(col, col),
            "value": row[col],
            "closer_to": "Introvert" if row[col] == "Yes" else "Extrovert",
            "importance": base_imp,
        })
    factors.sort(key=lambda x: x["importance"], reverse=True)

    # --- Session history ---
    if "history" not in session:
        session["history"] = []
    entry = {
        "id": len(session["history"]) + 1,
        "input": row,
        "prediction": pred_label,
        "probability": proba_dict,
    }
    session["history"].append(entry)
    session.modified = True

    return jsonify({
        "prediction": pred_label,
        "probability": proba_dict,
        "comparison": comparison,
        "dominant_factors": factors[:5],
        "history": session["history"],
    })


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    """Clear session prediction history."""
    session.pop("history", None)
    return jsonify({"status": "cleared"})


@app.route("/health")
def health():
    """Health check endpoint for deployment."""
    return jsonify({"status": "ok", "model": "RandomForestClassifier"})


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
