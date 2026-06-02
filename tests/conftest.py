"""Shared fixtures and headless matplotlib setup for the test suite.

Importing this file (pytest does so before collecting test modules) forces the
non-interactive Agg backend so rendering tests run without a display.
"""

import importlib.util
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_SET = REPO_ROOT / "icons" / "emoji"


@pytest.fixture(scope="session", autouse=True)
def bundled_icons():
    """dope_plot/assets/icons is a build artifact (see build.py): create it so a
    fresh checkout behaves like a built/installed package in the bundled-config
    tests."""
    spec = importlib.util.spec_from_file_location("_dope_build", REPO_ROOT / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.bundle_icons()


@pytest.fixture
def base_config(tmp_path):
    """A valid config dict whose paths are cwd-independent.

    - icons_set points at the real images in the repo (exercises the present-image path)
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
        "paths": {"icons_set": str(ICONS_SET), "output": str(tmp_path / "charts")},
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
