import sys
from pathlib import Path

# The eval harness reuses the backend's own parser and services.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
