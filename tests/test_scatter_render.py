"""Characterization + smoke tests for dope_plot.plots.scatter."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from dope_plot.plots.base import setup_plot
from dope_plot.plots.scatter import _BOX_GAP, _BOX_PAD, _clusters, _declutter, add_grid, add_name_boxes, scatter_chart

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


def test_add_name_boxes_one_label_per_row(fig_ax):
    _, ax = fig_ax
    df = _df()
    texts_before = len(ax.texts)
    images_before = len(ax.images)
    add_name_boxes(ax, df, MV)
    # One text label and one gradient-fill image per person.
    assert len(ax.texts) - texts_before == len(df)
    assert len(ax.images) - images_before == len(df)
    assert any("Alice" in t.get_text() for t in ax.texts)


def test_add_name_boxes_no_dot_without_collision(fig_ax):
    _, ax = fig_ax
    df = _df()  # two distinct, far-apart points
    before = len(ax.collections)
    add_name_boxes(ax, df, MV)
    # On-demand: boxes that don't overlap rest on their point with no dot.
    assert len(ax.collections) == before


def test_add_name_boxes_dot_per_collided_person(fig_ax):
    _, ax = fig_ax
    # Three coincident people -> a distinct dot each (callout).
    df = pd.DataFrame(
        {"Name": ["A", "B", "C"], "Note": ["D/O", "D/O", "D/O"], "X": [5.0, 5.0, 5.0], "Y": [5.0, 5.0, 5.0]}
    )
    before = len(ax.collections)
    add_name_boxes(ax, df, MV)
    assert len(ax.collections) - before == 3


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


# --- clustering ---


def test_clusters_groups_overlapping_separates_distant():
    anchors = np.array([[5.0, 5.0], [5.0, 5.0], [-18.0, -18.0]])
    sizes = np.array([[8.0, 1.0], [8.0, 1.0], [8.0, 1.0]])
    sizes_of_groups = sorted(len(g) for g in _clusters(anchors, sizes))
    assert sizes_of_groups == [1, 2]  # two coincident together, the far one alone


def test_declutter_separates_horizontally():
    # Boxes overlapping more vertically than horizontally separate along x.
    centers = np.array([[0.0, 0.0], [8.5, 0.0]])
    sizes = np.array([[9.0, 1.0], [9.0, 1.0]])
    out = _declutter(centers, sizes, MV)
    assert abs(out[0, 0] - out[1, 0]) >= 9.0  # cleared on the x-axis


def test_declutter_leaves_no_visual_overlap():
    # A pile of overlapping boxes must end up with no two boxes visually
    # overlapping (accounting for each box's rounded padding on every side).
    centers = np.array([[0.0, 0.0]] * 6)
    sizes = np.array([[9.0, 1.0]] * 6)
    out = _declutter(centers, sizes, MV)
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            dx, dy = abs(out[i, 0] - out[j, 0]), abs(out[i, 1] - out[j, 1])
            need_x = (sizes[i, 0] + sizes[j, 0]) / 2 + 2 * _BOX_PAD + _BOX_GAP
            need_y = (sizes[i, 1] + sizes[j, 1]) / 2 + 2 * _BOX_PAD + _BOX_GAP
            # Cleared (visual extents disjoint) on at least one axis.
            assert dx >= need_x - 1e-9 or dy >= need_y - 1e-9


def test_add_name_boxes_empty_df_is_noop(fig_ax):
    _, ax = fig_ax
    before = (len(ax.texts), len(ax.images), len(ax.patches))
    add_name_boxes(ax, pd.DataFrame({"Name": [], "Note": [], "X": [], "Y": []}), MV)
    assert (len(ax.texts), len(ax.images), len(ax.patches)) == before


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
