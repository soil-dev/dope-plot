"""Characterization tests for bird_plot.plots.base (headless Agg rendering).

These pin the *structure* the helpers add to an Axes (limits, counts of
patches/texts/images) so refactors that change the visual scaffolding are caught.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.offsetbox import AnnotationBbox
from matplotlib.patches import Rectangle

from bird_plot.plots.base import (
    _add_bird_image,
    add_axis_labels,
    add_bird_images,
    add_date,
    add_quadrant_labels,
    add_quadrants,
    setup_plot,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fig_ax(base_config):
    fig, ax = setup_plot(base_config)
    yield fig, ax
    plt.close(fig)


def test_setup_plot_limits_aspect_ticks(base_config):
    fig, ax = setup_plot(base_config)
    try:
        mv = base_config["chart"]["max_value"]
        assert ax.get_xlim() == (-mv, mv)
        assert ax.get_ylim() == (-mv, mv)
        assert list(ax.get_xticks()) == []
        assert list(ax.get_yticks()) == []
        assert tuple(fig.get_size_inches()) == (8.0, 8.0)
    finally:
        plt.close(fig)


def test_add_quadrants_adds_four_rectangles(fig_ax, base_config):
    _, ax = fig_ax
    add_quadrants(ax, base_config)
    rects = [p for p in ax.patches if isinstance(p, Rectangle)]
    assert len(rects) == 4


def test_add_quadrant_labels_adds_four_texts(fig_ax, base_config):
    _, ax = fig_ax
    before = len(ax.texts)
    add_quadrant_labels(ax, base_config)
    assert len(ax.texts) - before == 4
    texts = {t.get_text() for t in ax.texts}
    assert {
        "Supportive & Caring",
        "Controlling & Forceful",
        "Talkative & Dramatic",
        "Analytical & Logical",
    } <= texts


def test_add_axis_labels_adds_four_texts(fig_ax):
    _, ax = fig_ax
    before = len(ax.texts)
    add_axis_labels(ax)
    assert len(ax.texts) - before == 4


def test_add_date_without_project_link(fig_ax, base_config):
    _, ax = fig_ax
    base_config["chart"]["show_project_link"] = False
    before = len(ax.texts)
    add_date(ax, base_config)
    # Only the "Generated:" line, no project link.
    assert len(ax.texts) - before == 1
    assert any(t.get_text().startswith("Generated:") for t in ax.texts)


def test_add_date_with_project_link(fig_ax, base_config):
    _, ax = fig_ax
    base_config["chart"]["show_project_link"] = True
    before = len(ax.texts)
    add_date(ax, base_config)
    # Project link + generated date == 2 texts.
    assert len(ax.texts) - before == 2
    assert any("github.com/arapov/bird-plot" in t.get_text() for t in ax.texts)


def test_add_date_defaults_to_showing_link_when_key_missing(fig_ax, base_config):
    """Characterizes current behavior: missing key defaults to True (link shown)."""
    _, ax = fig_ax
    del base_config["chart"]["show_project_link"]
    before = len(ax.texts)
    add_date(ax, base_config)
    assert len(ax.texts) - before == 2


def test_add_date_positions_beside_bird_boxes(fig_ax, base_config):
    # With the bird boxes present and the link enabled, the date is placed by the
    # owl box and the link by the eagle box (the box-found branches).
    _, ax = fig_ax
    base_config["chart"]["show_project_link"] = True
    add_bird_images(ax, base_config)
    add_date(ax, base_config)
    texts = " ".join(t.get_text() for t in ax.texts)
    assert "Generated:" in texts
    assert "github.com/arapov/bird-plot" in texts


def _count_annotation_boxes(ax):
    return sum(isinstance(c, AnnotationBbox) for c in ax.get_children())


def test_add_bird_image_missing_logs_warning(fig_ax, caplog):
    _, ax = fig_ax
    before = _count_annotation_boxes(ax)
    with caplog.at_level(logging.WARNING):
        _add_bird_image(ax, REPO_ROOT / "birds" / "nope.png", 0, 0)
    assert _count_annotation_boxes(ax) == before
    assert any("not found" in r.message.lower() for r in caplog.records)


def test_add_bird_image_present_adds_artist(fig_ax):
    _, ax = fig_ax
    before = _count_annotation_boxes(ax)
    _add_bird_image(ax, REPO_ROOT / "birds" / "dove.png", 0, 0)
    assert _count_annotation_boxes(ax) == before + 1


def test_add_bird_images_adds_four(fig_ax, base_config):
    _, ax = fig_ax
    before = _count_annotation_boxes(ax)
    add_bird_images(ax, base_config)
    assert _count_annotation_boxes(ax) == before + 4
