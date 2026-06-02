"""Characterization + smoke tests for dope_plot.plots.scatter."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from dope_plot.plots.base import setup_plot
from dope_plot.plots.scatter import _clusters, _conflict, add_grid, add_name_boxes, scatter_chart

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
    # No text overlap -> every card rests on its point with no dot.
    assert len(ax.collections) == before


def test_add_name_boxes_small_nudge_has_no_dot(fig_ax):
    _, ax = fig_ax
    # Two cards whose text overlaps -> one is nudged a little to clear the text, but
    # a small nudge is left unmarked (no dot/line); it still reads as on its point.
    df = pd.DataFrame({"Name": ["Alpha", "Beta"], "Note": ["D/O", "D/O"], "X": [0.0, 0.5], "Y": [0.0, 0.0]})
    before = len(ax.collections)
    add_name_boxes(ax, df, MV)
    assert len(ax.collections) == before  # no dot for a small nudge
    # ...but the overlap was still resolved: the labels end up on different rows.
    ys = sorted(t.get_position()[1] for t in ax.texts if "/" in t.get_text())
    assert ys[0] != ys[1]


def test_add_name_boxes_far_push_draws_dot(fig_ax):
    _, ax = fig_ax
    # A tight pile forces some cards well off their point -> those get a dot + line.
    df = pd.DataFrame({"Name": list("ABCDEF"), "Note": ["D/O"] * 6, "X": [5.0] * 6, "Y": [5.0] * 6})
    before = len(ax.collections)
    add_name_boxes(ax, df, MV)
    assert len(ax.collections) - before >= 1


def test_add_name_boxes_handles_nan_note(fig_ax):
    _, ax = fig_ax
    df = pd.DataFrame({"Name": ["Solo"], "Note": [np.nan], "X": [0.0], "Y": [0.0]})
    add_name_boxes(ax, df, MV)
    # NaN note should not leak the string "nan" into the label.
    assert any(t.get_text().strip() == "Solo" for t in ax.texts)


# --- clustering + conflict (text-aware: cards may overlap as long as text is clear) ---


def test_clusters_groups_overlapping_separates_distant():
    anchors = np.array([[5.0, 5.0], [5.0, 5.0], [-18.0, -18.0]])
    sizes = np.array([[8.0, 1.0], [8.0, 1.0], [8.0, 1.0]])
    text = sizes  # treat the whole card as text for this pure-geometry check
    sizes_of_groups = sorted(len(g) for g in _clusters(anchors, sizes, text))
    assert sizes_of_groups == [1, 2]  # two coincident together, the far one alone


def test_clusters_allow_box_overlap_when_text_clear():
    # 8-wide cards overlap at dx=6.5, but the real 4-wide texts are clear apart, so
    # they are NOT clustered (cards may overlap as long as the text stays legible).
    anchors = np.array([[0.0, 0.0], [6.5, 0.0]])
    fat = np.array([[8.0, 1.0], [8.0, 1.0]])
    text = np.array([[4.0, 1.0], [4.0, 1.0]])
    assert sorted(len(g) for g in _clusters(anchors, fat, text)) == [1, 1]


def test_clusters_group_when_text_actually_overlaps():
    anchors = np.array([[0.0, 0.0], [3.0, 0.0]])
    fat = np.array([[8.0, 1.0], [8.0, 1.0]])
    text = np.array([[4.0, 1.0], [4.0, 1.0]])
    assert sorted(len(g) for g in _clusters(anchors, fat, text)) == [2]


def test_conflict_uses_text_extents():
    sizes = np.array([[8.0, 1.0], [8.0, 1.0]])
    text = np.array([[4.0, 1.0], [4.0, 1.0]])
    # Boxes overlap at dx=6.5 but the 4-wide texts are clear -> no conflict.
    assert not _conflict(0, (0.0, 0.0), 1, (6.5, 0.0), sizes, text)
    # Closer: the texts themselves overlap -> conflict.
    assert _conflict(0, (0.0, 0.0), 1, (3.0, 0.0), sizes, text)


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
