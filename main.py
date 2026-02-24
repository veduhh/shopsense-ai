"""Compatibility module for platforms that run `main:app`."""

import os

from app import app


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)
