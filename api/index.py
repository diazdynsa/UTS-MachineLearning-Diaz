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

class VercelMiddleware:
    """WSGI middleware to ensure correct PATH_INFO when Vercel rewrites routes."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = environ.get("HTTP_X_MATCHED_PATH")
        if matched_path:
            environ["PATH_INFO"] = matched_path
        elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py"):
            environ["PATH_INFO"] = "/"
        return self.wsgi_app(environ, start_response)

# Pasang middleware ke wsgi_app Flask
app.wsgi_app = VercelMiddleware(app.wsgi_app)

# Entrypoint WSGI untuk Vercel Serverless
app = app
