import os
import sys

# Tambahkan direktori root dan app ke sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

APP_DIR = os.path.join(ROOT_DIR, "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.app import app

# Entrypoint WSGI untuk Vercel Serverless
app = app
