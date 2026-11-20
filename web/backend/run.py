"""Convenience launcher for the local test server. Run from the project root::

    model/.venv/Scripts/python.exe web/backend/run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import main  # noqa: E402

if __name__ == "__main__":
    main()
