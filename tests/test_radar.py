import numpy as np
import pytest

from bird_plot.plots.radar import _format_title, calculate_angles, calculate_overlap


def test_format_title_without_note() -> None:
    data = {"Name": "Grace", "Note": ""}
    assert _format_title(data) == "Grace"


def test_format_title_with_note() -> None:
    data = {"Name": "Grace", "Note": "P/D"}
    assert _format_title(data) == "Grace, P/D"


def test_format_title_with_nan_note() -> None:
    data = {"Name": "Grace", "Note": np.nan}
    assert _format_title(data) == "Grace"


# --- calculate_angles ---


def test_calculate_angles_closes_polygon() -> None:
    categories = ["Owl", "Dove", "Peacock", "Eagle"]
    values = [10, 15, 8, 12]
    angles, vals = calculate_angles(categories, values)
    # Last element repeats first (closed polygon)
    assert angles[-1] == pytest.approx(angles[0])
    assert vals[-1] == pytest.approx(vals[0])


def test_calculate_angles_length() -> None:
    categories = ["A", "B", "C", "D"]
    values = [1, 2, 3, 4]
    angles, vals = calculate_angles(categories, values)
    assert len(angles) == len(categories) + 1
    assert len(vals) == len(values) + 1


# --- calculate_overlap ---


def test_calculate_overlap_identical_polygons() -> None:
    categories = ["Owl", "Dove", "Peacock", "Eagle"]
    values = [10.0, 15.0, 8.0, 12.0]
    angles, vals = calculate_angles(categories, values)
    overlap = calculate_overlap(vals, vals, angles)
    # Identical polygons should have ~100% overlap
    assert overlap == pytest.approx(100.0, abs=5.0)


def test_calculate_overlap_returns_float() -> None:
    categories = ["Owl", "Dove", "Peacock", "Eagle"]
    v1 = [10.0, 5.0, 8.0, 3.0]
    v2 = [3.0, 8.0, 5.0, 10.0]
    angles, vals1 = calculate_angles(categories, v1)
    _, vals2 = calculate_angles(categories, v2)
    overlap = calculate_overlap(vals1, vals2, angles)
    assert isinstance(overlap, float)
    assert 0.0 <= overlap <= 100.0


def test_calculate_overlap_zero_polygon() -> None:
    categories = ["Owl", "Dove", "Peacock", "Eagle"]
    v1 = [0.0, 0.0, 0.0, 0.0]
    v2 = [10.0, 10.0, 10.0, 10.0]
    angles, vals1 = calculate_angles(categories, v1)
    _, vals2 = calculate_angles(categories, v2)
    overlap = calculate_overlap(vals1, vals2, angles)
    # A zero-area polygon has no intersection
    assert overlap == pytest.approx(0.0, abs=1.0)


def test_calculate_overlap_is_deterministic() -> None:
    # Seeded Monte Carlo: same inputs must yield the same overlap every call.
    categories = ["Owl", "Dove", "Peacock", "Eagle"]
    angles, v1 = calculate_angles(categories, [10.0, 5.0, 8.0, 3.0])
    _, v2 = calculate_angles(categories, [3.0, 8.0, 5.0, 10.0])
    first = calculate_overlap(v1, v2, angles)
    repeats = [calculate_overlap(v1, v2, angles) for _ in range(4)]
    assert all(r == first for r in repeats)
