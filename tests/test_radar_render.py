"""Characterization + smoke tests for bird_plot.plots.radar rendering paths."""


import matplotlib.pyplot as plt
import pytest
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from bird_plot.plots.base import setup_plot
from bird_plot.plots.radar import (
    add_grid,
    add_labels,
    calculate_angles,
    plot_with_overlap,
    radar_chart,
)

CATS = ["Owl", "Dove", "Peacock", "Eagle"]


@pytest.fixture
def fig_ax(base_config):
    fig, ax = setup_plot(base_config)
    yield fig, ax
    plt.close(fig)


def test_add_grid_adds_circles_and_lines(fig_ax, base_config):
    _, ax = fig_ax
    add_grid(ax, base_config)
    circles = [c for c in ax.get_children() if isinstance(c, Circle)]
    # grid_step=5, max_value=25 -> radii 0,5,10,15,20,25 == 6 circles
    assert len(circles) == 6
    # Two diagonals plotted as Line2D via ax.plot
    lines = [ln for ln in ax.get_lines() if isinstance(ln, Line2D)]
    assert len(lines) >= 2


def test_plot_with_overlap_single_dataset_markers_and_fill(fig_ax):
    # The individual-chart path calls plot_with_overlap with one dataset.
    _, ax = fig_ax
    angles, vals = calculate_angles(CATS, [10, 15, 8, 12])
    n_lines_before = len(ax.get_lines())
    n_patches_before = len(ax.patches)
    plot_with_overlap(ax, angles, vals)
    assert len(ax.get_lines()) > n_lines_before  # marker line
    assert len(ax.patches) > n_patches_before  # filled polygon


def test_plot_with_overlap_two_datasets(fig_ax):
    _, ax = fig_ax
    angles, v1 = calculate_angles(CATS, [10, 15, 8, 12])
    _, v2 = calculate_angles(CATS, [5, 5, 5, 5])
    patches_before = len(ax.patches)
    plot_with_overlap(ax, angles, v1, v2)
    # Two filled polygons added.
    assert len(ax.patches) - patches_before == 2


def test_add_labels_adds_text_per_category(fig_ax):
    _, ax = fig_ax
    angles, vals = calculate_angles(CATS, [10, 15, 8, 12])
    before = len(ax.texts)
    add_labels(ax, angles, vals)
    # One label per category (closing duplicate skipped).
    assert len(ax.texts) - before == len(CATS)


def test_radar_chart_single_writes_png(base_config, tmp_path):
    out = tmp_path / "radar_alice.png"
    data = {"Name": "Alice", "Note": "D/O", "Dove": 20, "Owl": 15, "Peacock": 5, "Eagle": 10}
    radar_chart(data, out, base_config)
    assert out.exists() and out.stat().st_size > 1000


def test_radar_chart_comparison_writes_png(base_config, tmp_path):
    out = tmp_path / "compare.png"
    a = {"Name": "Alice", "Note": "D/O", "Dove": 20, "Owl": 15, "Peacock": 5, "Eagle": 10}
    b = {"Name": "Bob", "Note": "O/D", "Dove": 10, "Owl": 14, "Peacock": 5, "Eagle": 2}
    radar_chart(a, out, base_config, data2=b)
    assert out.exists() and out.stat().st_size > 1000


def test_radar_chart_reraises_on_bad_data(base_config, tmp_path):
    """Missing a required category key must propagate (current error contract)."""
    out = tmp_path / "bad.png"
    bad = {"Name": "X", "Dove": 1, "Owl": 2, "Peacock": 3}  # no "Eagle"
    with pytest.raises(Exception):
        radar_chart(bad, out, base_config)
    assert not out.exists()
