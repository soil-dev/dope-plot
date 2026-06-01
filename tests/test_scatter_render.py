"""Characterization + smoke tests for bird_plot.plots.scatter."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.patches import FancyBboxPatch

from bird_plot.plots.base import setup_plot
from bird_plot.plots.scatter import _declutter, add_grid, add_name_boxes, scatter_chart

MV = 25


def _df():
    return pd.DataFrame(
        {
            "Name": ["Alice", "Bob"],
            "Note": ["D/O", "O/D"],
            "X": [10.0, -8.0],
            "Y": [5.0, -12.0],
        }
    )


@pytest.fixture
def fig_ax(base_config):
    fig, ax = setup_plot(base_config)
    yield fig, ax
    plt.close(fig)


def test_add_grid_adds_two_lines(fig_ax):
    _, ax = fig_ax
    before = len(ax.get_lines())
    add_grid(ax)
    assert len(ax.get_lines()) - before == 2


def test_add_name_boxes_one_box_and_text_per_row(fig_ax):
    _, ax = fig_ax
    df = _df()
    boxes_before = sum(isinstance(p, FancyBboxPatch) for p in ax.patches)
    texts_before = len(ax.texts)
    add_name_boxes(ax, df, MV)
    boxes_after = sum(isinstance(p, FancyBboxPatch) for p in ax.patches)
    assert boxes_after - boxes_before == len(df)
    assert len(ax.texts) - texts_before == len(df)
    assert any("Alice" in t.get_text() for t in ax.texts)


def test_add_name_boxes_draws_a_dot_per_person(fig_ax):
    _, ax = fig_ax
    df = _df()
    before = len(ax.collections)
    add_name_boxes(ax, df, MV)
    # One scatter dot (true position) per person.
    assert len(ax.collections) - before == len(df)


def test_add_name_boxes_handles_nan_note(fig_ax):
    _, ax = fig_ax
    df = pd.DataFrame({"Name": ["Solo"], "Note": [np.nan], "X": [0.0], "Y": [0.0]})
    add_name_boxes(ax, df, MV)
    # NaN note should not leak the string "nan" into the label.
    assert any(t.get_text().strip() == "Solo" for t in ax.texts)


# --- declutter ---


def test_declutter_separates_identical_points():
    # Three people on the exact same spot must end up non-overlapping.
    centers = np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    sizes = np.array([[8.0, 1.0], [8.0, 1.0], [8.0, 1.0]])
    out = _declutter(centers, sizes, MV)
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            dx = abs(out[i, 0] - out[j, 0])
            dy = abs(out[i, 1] - out[j, 1])
            # Separated on at least one axis beyond the box half-extents.
            assert dx >= (sizes[i, 0] + sizes[j, 0]) / 2 - 1e-6 or dy >= (sizes[i, 1] + sizes[j, 1]) / 2 - 1e-6


def test_declutter_is_deterministic():
    centers = np.array([[1.0, 1.0], [1.0, 1.0], [-3.0, 2.0]])
    sizes = np.array([[9.0, 1.0], [9.0, 1.0], [9.0, 1.0]])
    a = _declutter(centers, sizes, MV)
    b = _declutter(centers, sizes, MV)
    assert np.array_equal(a, b)


def test_declutter_leaves_distant_points_untouched():
    centers = np.array([[15.0, 15.0], [-15.0, -15.0]])
    sizes = np.array([[8.0, 1.0], [8.0, 1.0]])
    out = _declutter(centers, sizes, MV)
    assert np.allclose(out, centers)


def test_scatter_chart_writes_png(base_config, tmp_path):
    out = tmp_path / "scatter_all.png"
    scatter_chart(_df(), out, base_config)
    assert out.exists() and out.stat().st_size > 1000


def test_scatter_chart_reraises_on_bad_data(base_config, tmp_path):
    """Missing X/Y columns must propagate (current error contract)."""
    out = tmp_path / "bad.png"
    df = pd.DataFrame({"Name": ["NoCoords"], "Note": ["D/O"]})  # no X/Y
    with pytest.raises(KeyError):
        scatter_chart(df, out, base_config)
    assert not out.exists()
