"""Shared fixtures and headless matplotlib setup for the test suite.

Importing this file (pytest does so before collecting test modules) forces the
non-interactive Agg backend so rendering tests run without a display.
"""

import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BIRDS_DIR = REPO_ROOT / "birds"


@pytest.fixture
def base_config(tmp_path):
    """A valid config dict whose paths are cwd-independent.

    - birds_dir points at the real images in the repo (exercises the present-image path)
    - output points at a per-test tmp dir so rendering tests never touch the repo
    """
    return {
        "chart": {
            "max_value": 25,
            "figure_size": [8, 8],
            "grid_step": 5,
            "show_project_link": False,
        },
        "colors": {
            "top_right": "lightskyblue",
            "bottom_right": "khaki",
            "top_left": "lightgreen",
            "bottom_left": "lightcoral",
            "alpha": 0.2,
        },
        "paths": {"birds_dir": str(BIRDS_DIR), "output": str(tmp_path / "charts")},
    }


@pytest.fixture
def sample_csv(tmp_path):
    """A minimal two-person CSV; returns the path as a string."""
    csv = tmp_path / "people.csv"
    csv.write_text(
        "Name,Dove,Eagle,Owl,Peacock,Note\n"
        "Alice,20,10,15,5,D/O\n"
        "Bob,10,2,14,5,O/D\n"
    )
    return str(csv)
