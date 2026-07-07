from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env_loader import load_repo_env


def test_load_repo_env_does_not_override_existing_env_var(monkeypatch):
    monkeypatch.setenv("KUBECONFIG", "/tmp/custom-kubeconfig")
    load_repo_env()
    assert os.environ["KUBECONFIG"] == "/tmp/custom-kubeconfig"

