import subprocess
import sys
from pathlib import Path


def test_import_main_does_not_load_optional_fingerprint_modules():
    repo_root = Path(__file__).resolve().parents[1]
    script = """
import sys

assert "app.fingerprints.dinov2" not in sys.modules
assert "app.fingerprints.onnx_embedder" not in sys.modules
import app.main

assert "app.fingerprints.dinov2" not in sys.modules
assert "app.fingerprints.onnx_embedder" not in sys.modules
assert app.main.app.title == "Valid Assessment Video API"
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
