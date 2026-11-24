"""
Flask App - Klasifikasi Kepribadian Extrovert / Introvert
UTS Pembelajaran Mesin | Random Forest
"""

import os
import json
import traceback
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
# Load model & metadata (lazy, with error tracking)
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(ROOT_DIR, "model", "personality_rf_model.pkl")
META_PATH = os.path.join(ROOT_DIR, "model", "model_metadata.json")

pipeline = None
metadata = None
_load_error = None

def _load_model():
    """Load model and metadata, capturing any error."""
    global pipeline, metadata, _load_error
    if pipeline is not None:
        return True
    try:
        pipeline = joblib.load(MODEL_PATH)
        with open(META_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        _load_error = None
        return True
    except Exception as e:
        _load_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        pipeline = None
        metadata = None
        return False

# Try loading at startup (non-fatal)
_load_model()

# ---------------------------------------------------------------------------
# Derived constants (safe even if model failed to load)
# ---------------------------------------------------------------------------
def _get_meta():
    """Return metadata dict, attempting reload if needed."""
    if metadata is None:
        _load_model()
    return metadata or {}

NUM_COLS = [
    "Time_spent_Alone",
    "Social_event_attendance",
    "Going_outside",
    "Friends_circle_size",
    "Post_frequency",
]
CAT_COLS = ["Stage_fear", "Drained_after_socializing"]
ALL_FEATURES = NUM_COLS + CAT_COLS

FEATURE_LABELS = {
    "Time_spent_Alone": "Waktu Menyendiri (jam/hari)",
    "Social_event_attendance": "Kehadiran Acara Sosial (0-10)",
    "Going_outside": "Frekuensi Keluar Rumah (0-7/minggu)",
    "Friends_circle_size": "Jumlah Teman Dekat (0-15)",
    "Post_frequency": "Frekuensi Unggahan Sosmed (0-10)",
    "Stage_fear": "Cemas Tampil di Depan Umum",
    "Drained_after_socializing": "Lelah Setelah Bersosialisasi",
}

def _build_clean_importance(meta):
    fi = meta.get("feature_importance", [])
    result = []
    for item in fi:
        raw = item["feature"]
        name = raw.split("__", 1)[-1] if "__" in raw else raw
        base = name.replace("_Yes", "").replace("_No", "")
        label = FEATURE_LABELS.get(base, name)
        if "_Yes" in name:
            label += " (Ya)"
        elif "_No" in name:
            label += " (Tidak)"
        result.append({"feature": name, "label": label, "importance": item["importance"]})
    return result


# ---------------------------------------------------------------------------
# Global error handlers - always return JSON for API routes
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint tidak ditemukan", "path": request.path}), 404
    return render_template("index.html", **_template_context()), 404


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500
    return render_template("index.html", **_template_context()), 500


@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    if request.path.startswith("/api/"):
        return jsonify({"error": str(e), "type": type(e).__name__, "traceback": tb}), 500
    # For non-API routes, try to render page
    try:
        return render_template("index.html", **_template_context()), 500
    except Exception:
        return f"<pre>Server Error: {e}\n\n{tb}</pre>", 500


# ---------------------------------------------------------------------------
# Template context helper
# ---------------------------------------------------------------------------
def _template_context():
    meta = _get_meta()
    clean_importance = _build_clean_importance(meta)
    return {
        "feature_labels": FEATURE_LABELS,
        "feature_meta": meta.get("feature_metadata", {}),
        "mean_per_class": meta.get("mean_per_class", {}),
        "feature_importance": clean_importance,
        "eval_metrics": meta.get("evaluation_metrics", {}),
        "hyperparams": meta.get("best_hyperparameters", {}),
        "confusion_matrix": meta.get("confusion_matrix", [[0, 0], [0, 0]]),
        "num_cols": NUM_COLS,
        "cat_cols": CAT_COLS,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
@app.route("/api/index")
def index():
    """Render main page with metadata injected."""
    return render_template("index.html", **_template_context())


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/api/predict", methods=["POST"])
def predict():
    """Accept JSON input, validate, predict, return results."""
    # --- Check model loaded ---
    if pipeline is None:
        ok = _load_model()
        if not ok:
            return jsonify({
                "error": "Model gagal dimuat",
                "detail": _load_error or "Unknown error"
            }), 503

    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({"error": "Body request bukan JSON yang valid"}), 400

        meta = _get_meta()
        feature_meta = meta.get("feature_metadata", {})
        mean_per_class = meta.get("mean_per_class", {})
        label_mapping = meta.get("label_mapping", {"Introvert": 0, "Extrovert": 1})
        reverse_label = {v: k for k, v in label_mapping.items()}

        # --- Validate & build input row ---
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
            col_meta = feature_meta.get(col, {})
            col_min = col_meta.get("min", 0)
            col_max = col_meta.get("max", 999)
            if val < col_min or val > col_max:
                errors.append(
                    f"{FEATURE_LABELS.get(col, col)}: nilai harus antara "
                    f"{col_min:.0f} - {col_max:.0f}."
                )
                continue
            row[col] = val

        for col in CAT_COLS:
            val = data.get(col)
            if val is None or val == "":
                errors.append(f"{FEATURE_LABELS.get(col, col)} wajib diisi.")
                continue
            allowed = feature_meta.get(col, {}).get("categories", ["No", "Yes"])
            if val not in allowed:
                errors.append(f"{FEATURE_LABELS.get(col, col)}: pilih salah satu dari {allowed}.")
                continue
            row[col] = val

        if errors:
            return jsonify({"error": "; ".join(errors)}), 422

        # --- Predict ---
        input_df = pd.DataFrame([row], columns=ALL_FEATURES)
        pred_class = int(pipeline.predict(input_df)[0])
        pred_proba = pipeline.predict_proba(input_df)[0]

        pred_label = reverse_label.get(pred_class, str(pred_class))
        proba_dict = {
            reverse_label.get(i, str(i)): round(float(p) * 100, 2)
            for i, p in enumerate(pred_proba)
        }

        # --- User vs class means ---
        comparison = {}
        for col in NUM_COLS:
            comparison[col] = {
                "user": row[col],
                "mean_introvert": mean_per_class.get("Introvert", {}).get(col, 0),
                "mean_extrovert": mean_per_class.get("Extrovert", {}).get(col, 0),
                "label": FEATURE_LABELS.get(col, col),
            }

        # --- Dominant factors ---
        clean_importance = _build_clean_importance(meta)
        imp_lookup = {it["feature"]: it["importance"] for it in clean_importance}

        factors = []
        for col in NUM_COLS:
            diff_intro = abs(row[col] - mean_per_class.get("Introvert", {}).get(col, 0))
            diff_extro = abs(row[col] - mean_per_class.get("Extrovert", {}).get(col, 0))
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
        try:
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
            history = session["history"]
        except Exception:
            history = []

        return jsonify({
            "prediction": pred_label,
            "probability": proba_dict,
            "comparison": comparison,
            "dominant_factors": factors[:5],
            "history": history,
        })

    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({
            "error": f"Prediksi gagal: {str(e)}",
            "type": type(e).__name__,
            "traceback": tb,
        }), 500


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    """Clear session prediction history."""
    try:
        session.pop("history", None)
    except Exception:
        pass
    return jsonify({"status": "cleared"})


@app.route("/health")
def health():
    """Health check endpoint for deployment."""
    model_ok = pipeline is not None
    return jsonify({
        "status": "ok" if model_ok else "degraded",
        "model": "RandomForestClassifier",
        "model_loaded": model_ok,
        "load_error": _load_error if not model_ok else None,
    })


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
