import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app as flask_app

app = flask_app
application = app
handler = app

if __name__ == "__main__":
    app.run()
