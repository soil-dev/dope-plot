import numpy as np
import pandas as pd
import pytest

from dope_plot.cli import (
    REQUIRED_COLUMNS,
    _safe_name_for_path,
    _sigmoid_scale,
    calculate_team_average,
    load_csv_data,
    process_personality_data,
)


def test_safe_name_for_path_sanitizes() -> None:
    assert _safe_name_for_path("Alice/Bob..") == "Alice_Bob"
    assert _safe_name_for_path("   ") == "unnamed"
    assert _safe_name_for_path("Ok-Name_1") == "Ok-Name_1"


def test_sigmoid_scale_zero_series_returns_zero() -> None:
    series = pd.Series([0, 0, 0], dtype=float)
    scaled = _sigmoid_scale(series, max_value=25)
    assert np.allclose(scaled.to_numpy(), [0, 0, 0], equal_nan=False)


def test_sigmoid_scale_nonzero() -> None:
    series = pd.Series([10.0, -10.0, 0.0])
    scaled = _sigmoid_scale(series, max_value=25)
    # tanh(1) ≈ 0.7616, tanh(-1) ≈ -0.7616, tanh(0) = 0
    assert scaled[0] > 0
    assert scaled[1] < 0
    assert scaled[2] == pytest.approx(0.0)
    assert abs(scaled[0]) <= 25
    assert abs(scaled[1]) <= 25


# --- load_csv_data ---


def test_load_csv_data_missing_file() -> None:
    with pytest.raises(SystemExit):
        load_csv_data("nonexistent_file_xyz.csv")


def test_load_csv_data_missing_columns(tmp_path) -> None:
    csv = tmp_path / "bad.csv"
    csv.write_text("Name,Dove\nAlice,10\n")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_no_data_rows(tmp_path) -> None:
    csv = tmp_path / "empty_rows.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock\n")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_blank_name(tmp_path) -> None:
    csv = tmp_path / "blank_name.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock\n,20,10,15,5\n")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_non_numeric_scores(tmp_path) -> None:
    csv = tmp_path / "bad_score.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock\nAlice,twenty,10,15,5\n")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_non_finite_scores(tmp_path) -> None:
    csv = tmp_path / "infinite_score.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock\nAlice,inf,10,15,5\n")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_negative_scores(tmp_path) -> None:
    csv = tmp_path / "neg.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock\nAlice,20,-5,14,11\n")
    with pytest.raises(SystemExit):
        load_csv_data(str(csv))


def test_load_csv_data_valid(tmp_path) -> None:
    csv = tmp_path / "data.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock,Note\nAlice,20,10,15,5,D/O\n")
    df = load_csv_data(str(csv))
    assert set(REQUIRED_COLUMNS).issubset(df.columns)
    assert len(df) == 1


# --- calculate_team_average ---


def _make_df():
    return pd.DataFrame(
        {
            "Name": ["Alice", "Bob"],
            "Dove": [20.0, 10.0],
            "Owl": [5.0, 15.0],
            "Peacock": [8.0, 12.0],
            "Eagle": [2.0, 18.0],
        }
    )


def test_calculate_team_average_values() -> None:
    df = _make_df()
    avg = calculate_team_average(df)
    assert avg["Name"] == "Team Average Profile"
    assert avg["Dove"] == pytest.approx(15.0)
    assert avg["Owl"] == pytest.approx(10.0)
    assert avg["Peacock"] == pytest.approx(10.0)
    assert avg["Eagle"] == pytest.approx(10.0)


def test_calculate_team_average_note_dominant() -> None:
    df = _make_df()
    avg = calculate_team_average(df)
    # Dove avg=15 is highest; note should start with 'D'
    assert avg["Note"].startswith("D")
    assert "/" in avg["Note"]


# --- process_personality_data ---

_MINIMAL_CONFIG = {
    "chart": {"max_value": 25, "figure_size": [8, 8], "grid_step": 5},
    "colors": {
        "top_right": "lightskyblue",
        "bottom_right": "khaki",
        "top_left": "lightgreen",
        "bottom_left": "lightcoral",
        "alpha": 0.2,
    },
    "paths": {"icons_dir": "dope_plot/assets/icons", "icon_set": "hunt", "output": "charts"},
}


def test_process_personality_data_adds_xy(tmp_path) -> None:
    csv = tmp_path / "data.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock,Note\nAlice,20,10,15,5,D/O\nBob,10,2,14,5,O/D\n")
    df = process_personality_data(str(csv), _MINIMAL_CONFIG)
    assert "X" in df.columns
    assert "Y" in df.columns


def test_process_personality_data_xy_within_bounds(tmp_path) -> None:
    csv = tmp_path / "data.csv"
    csv.write_text("Name,Dove,Eagle,Owl,Peacock,Note\nAlice,20,10,15,5,D/O\nBob,10,2,14,5,O/D\n")
    df = process_personality_data(str(csv), _MINIMAL_CONFIG)
    max_val = _MINIMAL_CONFIG["chart"]["max_value"]
    assert (df["X"].abs() <= max_val).all()
    assert (df["Y"].abs() <= max_val).all()
