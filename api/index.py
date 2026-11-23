import os
import sys

# Tambahkan direktori root dan app ke sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Compatibility shim untuk unpickling scikit-learn ColumnTransformer
try:
    import sklearn.compose._column_transformer as _ct
    if not hasattr(_ct, "_RemainderColsList"):
        _ct._RemainderColsList = type("_RemainderColsList", (list,), {})
except Exception:
    pass

try:
    from app.app import app
except (ImportError, ModuleNotFoundError):
    sys.path.insert(0, os.path.join(ROOT_DIR, "app"))
    import app as _app_module
    app = getattr(_app_module, "app", _app_module)

# Entrypoint WSGI untuk Vercel Serverless
app = app
