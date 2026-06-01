"""Integration + golden-value tests for bird_plot.cli.

The golden X/Y test pins the ENTIRE transform pipeline (max-bird 1.2x boost,
integer truncation, tanh scaling, per-column-max denominator). If any of those
mechanics change, this test fails on purpose — that is the safety net.
"""

from pathlib import Path

import numpy as np
import pytest

import bird_plot.cli as cli
from bird_plot.cli import (
    generate_radar_charts,
    generate_team_average_radar,
    load_csv_data,
    main,
    process_personality_data,
)

MINIMAL_CONFIG = {
    "chart": {"max_value": 25, "figure_size": [8, 8], "grid_step": 5, "show_project_link": False},
    "colors": {
        "top_right": "lightskyblue",
        "bottom_right": "khaki",
        "top_left": "lightgreen",
        "bottom_left": "lightcoral",
        "alpha": 0.2,
    },
    "paths": {"birds_dir": str(Path(__file__).resolve().parent.parent / "birds"), "output": "charts"},
}


# --- load_csv_data error branches not previously covered ---


def test_load_csv_data_empty_file_exits(tmp_path):
    csv = tmp_path / "empty.csv"
    csv.write_text("")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_unparseable_exits(tmp_path, monkeypatch):
    csv = tmp_path / "bad.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock\n")

    import pandas as pd

    def boom(*a, **k):
        raise pd.errors.ParserError("synthetic parse failure")

    monkeypatch.setattr(pd, "read_csv", boom)
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


# --- golden values: lock the full coordinate pipeline ---


def test_process_personality_data_golden_xy(sample_csv):
    df = process_personality_data(sample_csv, MINIMAL_CONFIG)
    # Derivation (see module docstring): Alice max=Dove, Bob max=Owl.
    # Alice raw X=24, Y=4 ; Bob raw X=19, Y=-3.
    # X denom = max(24,19)=24 ; Y denom = max(4,3)=4 ; max_value=25.
    expected_x = 25 * np.tanh([24 / 24, 19 / 24])
    expected_y = 25 * np.tanh([4 / 4, -3 / 4])
    assert df["X"].to_numpy() == pytest.approx(expected_x, abs=1e-6)
    assert df["Y"].to_numpy() == pytest.approx(expected_y, abs=1e-6)


# --- generators: directory layout + outputs ---


def test_generate_radar_charts_dir_tree(sample_csv):
    df = process_personality_data(sample_csv, MINIMAL_CONFIG)
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        cfg = {**MINIMAL_CONFIG, "paths": {**MINIMAL_CONFIG["paths"], "output": d}}
        generate_radar_charts(df, cfg)
        base = Path(d)
        # Per-person individual chart + compare dir with team-average + each other person.
        assert (base / "Alice" / "radar_Alice.png").exists()
        assert (base / "Bob" / "radar_Bob.png").exists()
        assert (base / "Alice" / "compare" / "with_TeamAverage.png").exists()
        assert (base / "Alice" / "compare" / "with_Bob.png").exists()
        assert (base / "Bob" / "compare" / "with_Alice.png").exists()
        # No self-comparison.
        assert not (base / "Alice" / "compare" / "with_Alice.png").exists()


def test_generate_team_average_radar(sample_csv):
    df = process_personality_data(sample_csv, MINIMAL_CONFIG)
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        cfg = {**MINIMAL_CONFIG, "paths": {**MINIMAL_CONFIG["paths"], "output": d}}
        generate_team_average_radar(df, cfg)
        assert (Path(d) / "radar_team_average.png").exists()


# --- main(): end-to-end dispatch ---


def _run_main(monkeypatch, sample_csv, out_dir, graph_args):
    cfg = {**MINIMAL_CONFIG, "paths": {**MINIMAL_CONFIG["paths"], "output": str(out_dir)}}
    monkeypatch.setattr(cli, "load_config", lambda *a, **k: cfg)
    argv = ["bird-plot", "--data", sample_csv] + graph_args
    monkeypatch.setattr("sys.argv", argv)
    main()


def test_main_scatter_only(monkeypatch, sample_csv, tmp_path):
    out = tmp_path / "out"
    _run_main(monkeypatch, sample_csv, out, ["--graph", "scatter"])
    assert (out / "scatter_all.png").exists()
    assert not (out / "Alice").exists()  # no radar charts


def test_main_radar_only(monkeypatch, sample_csv, tmp_path):
    out = tmp_path / "out"
    _run_main(monkeypatch, sample_csv, out, ["--graph", "radar"])
    assert (out / "Alice" / "radar_Alice.png").exists()
    assert (out / "radar_team_average.png").exists()
    assert not (out / "scatter_all.png").exists()


def test_main_both(monkeypatch, sample_csv, tmp_path):
    out = tmp_path / "out"
    _run_main(monkeypatch, sample_csv, out, ["--graph", "radar", "scatter"])
    assert (out / "scatter_all.png").exists()
    assert (out / "Alice" / "radar_Alice.png").exists()


def test_main_default_graph_is_scatter(monkeypatch, sample_csv, tmp_path):
    """No --graph: characterizes current default (scatter only, no radar)."""
    out = tmp_path / "out"
    _run_main(monkeypatch, sample_csv, out, [])
    assert (out / "scatter_all.png").exists()
    assert not (out / "Alice").exists()
