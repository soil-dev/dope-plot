"""Characterization + smoke tests for bird_plot.plots.scatter."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.patches import FancyBboxPatch

from bird_plot.plots.base import setup_plot
from bird_plot.plots.scatter import add_grid, add_name_boxes, scatter_chart


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
    add_name_boxes(ax, df)
    boxes_after = sum(isinstance(p, FancyBboxPatch) for p in ax.patches)
    assert boxes_after - boxes_before == len(df)
    assert len(ax.texts) - texts_before == len(df)
    assert any("Alice" in t.get_text() for t in ax.texts)


def test_add_name_boxes_handles_nan_note(fig_ax):
    _, ax = fig_ax
    df = pd.DataFrame({"Name": ["Solo"], "Note": [np.nan], "X": [0.0], "Y": [0.0]})
    add_name_boxes(ax, df)
    # NaN note should not leak the string "nan" into the label.
    assert any(t.get_text().strip() == "Solo" for t in ax.texts)


def test_scatter_chart_writes_png(base_config, tmp_path):
    out = tmp_path / "scatter_all.png"
    scatter_chart(_df(), out, base_config)
    assert out.exists() and out.stat().st_size > 1000


def test_scatter_chart_reraises_on_bad_data(base_config, tmp_path):
    """Missing X/Y columns must propagate (current error contract)."""
    out = tmp_path / "bad.png"
    df = pd.DataFrame({"Name": ["NoCoords"], "Note": ["D/O"]})  # no X/Y
    with pytest.raises(Exception):
        scatter_chart(df, out, base_config)
    assert not out.exists()
