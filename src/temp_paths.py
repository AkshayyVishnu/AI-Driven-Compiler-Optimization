"""
Workspace-local temp helpers for sandbox-safe runtime artifacts.
"""

from __future__ import annotations

import os
import uuid


def runtime_temp_dir() -> str:
    root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.abspath(os.path.join(root, ".runtime_tmp"))
    os.makedirs(path, exist_ok=True)
    return path


def new_runtime_workspace(prefix: str) -> str:
    path = os.path.join(runtime_temp_dir(), f"{prefix}_{uuid.uuid4().hex}")
    os.makedirs(path, exist_ok=True)
    return path
