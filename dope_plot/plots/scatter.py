import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
from matplotlib.patches import FancyBboxPatch
from matplotlib.patheffects import withSimplePatchShadow

from .base import add_axis_labels, add_bird_images, add_date, add_quadrant_labels, add_quadrants, setup_plot

logger = logging.getLogger(__name__)

_BOX_HEIGHT = 1.0
_BOX_PAD = 0.3  # FancyBboxPatch round padding, in data units (expands the box each side)
_BOX_GAP = 0.08  # minimum visual gap kept between boxes (a few px) so they never touch
_CLUSTER_PAD = 2 * _BOX_PAD + _BOX_GAP  # reserve each box's padding on both sides + the gap
_LEADER_MIN = 2.5  # only mark a moved card (dot + leader line) when pushed this far; smaller nudges read as on-point
_GRADIENT_BAND = 0.12  # half-width of the soft transition between the two fill colours

_BIRD_NAME = {"D": "Dove", "E": "Eagle", "O": "Owl", "P": "Peacock"}
# Light bird hues for the label fill (matching the quadrant colours).
_BIRD_LIGHT = {"D": "lightskyblue", "E": "lightcoral", "O": "khaki", "P": "lightgreen"}
_PASTEL = 0.5  # how far the fill colours are blended toward white (0 = none, 1 = white)

# Direction each bird leans toward, matching its quadrant corner:
# Dove top-right, Owl bottom-right, Peacock top-left, Eagle bottom-left.
_BIRD_DIR = {"D": (1.0, 1.0), "O": (1.0, -1.0), "P": (-1.0, 1.0), "E": (-1.0, -1.0)}


def _box_text(row) -> str:
    """Build the '<Name> <Note>' label, tolerating empty/NaN notes."""
    note = row.get("Note", "")
    note_str = "" if (not note or pd.isna(note)) else str(note)
    return f"{row['Name']} {note_str}".strip()


def _bird_vector(row) -> np.ndarray:
    """Direction a person leans, from their primary (and secondary) bird.

    Uses the Note's two letters (primary weighted more); falls back to the two
    highest scores. Returns an unnormalized 2-vector pointing toward that blend.
    """
    note = row.get("Note", "")
    letters = [c for c in str(note).upper() if c in _BIRD_DIR][:2] if (note and not pd.isna(note)) else []
    if not letters:
        scores = {b: (row.get(b) or 0) for b in ("Dove", "Eagle", "Owl", "Peacock")}
        letters = [b[0] for b in sorted(scores, key=scores.get, reverse=True)[:2]]
    vec = np.zeros(2)
    for letter, weight in zip(letters, (1.0, 0.5), strict=False):
        vec += np.array(_BIRD_DIR[letter]) * weight
    return vec


def _gradient_stops(row):
    """Return (primary_colour, secondary_colour, ratio) for the label fill.

    Colours are the light bird hues; ratio is the primary bird's share of the
    two scores, so the gradient leans toward whichever bird dominates.
    """
    note = row.get("Note", "")
    letters = [c for c in str(note).upper() if c in _BIRD_LIGHT][:2] if (note and not pd.isna(note)) else []
    scores = {b: (row.get(b) or 0) for b in ("Dove", "Eagle", "Owl", "Peacock")}
    if len(letters) < 2:
        for letter in (b[0] for b in sorted(scores, key=scores.get, reverse=True)):
            if letter not in letters:
                letters.append(letter)
            if len(letters) == 2:
                break
    s1, s2 = scores[_BIRD_NAME[letters[0]]], scores[_BIRD_NAME[letters[1]]]
    ratio = s1 / (s1 + s2) if (s1 + s2) else 0.5
    return _BIRD_LIGHT[letters[0]], _BIRD_LIGHT[letters[1]], ratio


def _pastel(color) -> np.ndarray:
    """Return an RGBA blended toward white for a softer, pastel fill."""
    rgba = np.array(to_rgba(color))
    rgba[:3] = rgba[:3] + (1.0 - rgba[:3]) * _PASTEL
    return rgba


def _gradient_image(rgba1, rgba2, ratio):
    """A 1xN horizontal gradient that splits primary->secondary at ``ratio``.

    Proportional split: the primary colour fills ``ratio`` of the width, the
    secondary the rest, with a soft transition band so the share stays legible.
    """
    xs = np.linspace(0.0, 1.0, 64)
    blend = np.clip((xs - ratio) / (2 * _GRADIENT_BAND) + 0.5, 0.0, 1.0)
    return ((1 - blend)[:, None] * rgba1 + blend[:, None] * rgba2).reshape(1, 64, 4)


def _fill_gradient_box(ax, bx, by, w, h, c1, c2, ratio):
    """Draw a rounded, borderless label box filled with a primary->secondary
    pastel gradient, plus a soft drop shadow for a bit of volume."""
    ratio = min(max(ratio, 0.05), 0.95)
    fill = _gradient_image(_pastel(c1), _pastel(c2), ratio)
    rounded = f"round,pad={_BOX_PAD}"

    # Drop shadow: a hidden white source patch (fully covered by the opaque fill
    # on top) whose offset shadow peeks out below-right.
    shadow = FancyBboxPatch(
        (bx - w / 2, by - h / 2), w, h, boxstyle=rounded, facecolor="white", edgecolor="none", zorder=2.6,
    )
    shadow.set_path_effects([withSimplePatchShadow(offset=(2.5, -2.5), alpha=0.15, shadow_rgbFace="black")])
    ax.add_patch(shadow)

    # Gradient fill, clipped to the rounded box.
    clip = FancyBboxPatch(
        (bx - w / 2, by - h / 2), w, h, boxstyle=rounded, facecolor="none", edgecolor="none", zorder=3,
    )
    ax.add_patch(clip)
    img = ax.imshow(
        fill,
        extent=(bx - w / 2 - _BOX_PAD, bx + w / 2 + _BOX_PAD, by - h / 2 - _BOX_PAD, by + h / 2 + _BOX_PAD),
        aspect="auto", origin="lower", zorder=3, interpolation="bilinear",
    )
    img.set_clip_path(clip)


def _pair_thresholds(i: int, j: int, sizes: np.ndarray, text_sizes) -> tuple:
    """Minimum centre separation on each axis before labels i, j 'conflict'.

    Default (``text_sizes`` is None): the full boxes mustn't overlap, keeping
    _CLUSTER_PAD of breathing room so cards never even touch. When ``text_sizes``
    is given, only forbid an opaque box from reaching the *other box's text* — so
    cards may overlap freely as long as every label stays fully legible.
    """
    if text_sizes is None:
        tx = (sizes[i, 0] + sizes[j, 0]) / 2 + _CLUSTER_PAD
        ty = (sizes[i, 1] + sizes[j, 1]) / 2 + _CLUSTER_PAD
    else:
        tx = max(sizes[i, 0] + text_sizes[j, 0], sizes[j, 0] + text_sizes[i, 0]) / 2 + _BOX_GAP
        ty = max(sizes[i, 1] + text_sizes[j, 1], sizes[j, 1] + text_sizes[i, 1]) / 2 + _BOX_GAP
    return tx, ty


def _text_data_extent(ax: Axes, s: str, fontsize: int, fallback: tuple) -> tuple:
    """Measure the rendered (width, height) of ``s`` in data units at ``fontsize``.

    Falls back to a rough estimate if no renderer is available yet.
    """
    try:
        renderer = ax.figure.canvas.get_renderer()
        t = ax.text(0, 0, s, fontsize=fontsize, ha="center", va="center")
        ext = t.get_window_extent(renderer)
        t.remove()
        inv = ax.transData.inverted()
        x0, y0 = inv.transform((ext.x0, ext.y0))
        x1, y1 = inv.transform((ext.x1, ext.y1))
        return abs(x1 - x0), abs(y1 - y0)
    except Exception:
        return fallback


def _clusters(anchors: np.ndarray, sizes: np.ndarray, text_sizes: np.ndarray | None = None) -> list:
    """Group people whose labels conflict at their true points (connected components).

    Conflict uses :func:`_pair_thresholds`; a list of length 1 is an isolated person.
    """
    n = len(anchors)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            dx = abs(anchors[i, 0] - anchors[j, 0])
            dy = abs(anchors[i, 1] - anchors[j, 1])
            tx, ty = _pair_thresholds(i, j, sizes, text_sizes)
            if dx < tx and dy < ty:
                parent[find(i)] = find(j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _conflict(i: int, pi, j: int, pj, sizes: np.ndarray, text_sizes: np.ndarray) -> bool:
    """True when card i at ``pi`` and card j at ``pj`` overlap enough to cover text."""
    tx, ty = _pair_thresholds(i, j, sizes, text_sizes)
    return abs(pi[0] - pj[0]) < tx and abs(pi[1] - pj[1]) < ty


def _free_vertical_slot(m, pos, sizes, text_sizes, anchors, bird_vecs, max_value):
    """The smallest vertical nudge from ``anchors[m]`` (keeping its X) that clears
    every other card's text — i.e. the nearest free slot above/below.

    Returns ``(x, y)`` or None if nothing fits. Prefers the card's own vertical
    bird-lean so the nudge reads naturally.
    """
    cx, cy = anchors[m]
    half_h = sizes[m, 1] / 2
    pref = 1.0 if bird_vecs[m][1] >= 0 else -1.0
    d = 0.25
    while d <= 2 * max_value:
        for s in (pref, -pref):
            y = cy + s * d
            if not (-max_value + half_h <= y <= max_value - half_h):
                continue
            cand = (cx, y)
            if all(k == m or not _conflict(m, cand, k, pos[k], sizes, text_sizes) for k in range(len(pos))):
                return cand
        d += 0.25
    return None


def _resolve_group(group, pos, sizes, text_sizes, anchors, bird_vecs, max_value) -> list:
    """Resolve text overlaps inside one cluster by moving as few cards as possible.

    While two members' text still overlaps, the cheaper card to relocate is nudged
    to a free vertical slot and the other keeps its true point. Returns the indices
    that ended up moved (each gets a dot + leader line).
    """
    moved = []
    for _ in range(4 * len(group) + 6):
        pair = next(
            (
                (i, j)
                for a, i in enumerate(group)
                for j in group[a + 1 :]
                if _conflict(i, pos[i], j, pos[j], sizes, text_sizes)
            ),
            None,
        )
        if pair is None:
            break
        i, j = pair
        ci = _free_vertical_slot(i, pos, sizes, text_sizes, anchors, bird_vecs, max_value)
        cj = _free_vertical_slot(j, pos, sizes, text_sizes, anchors, bird_vecs, max_value)
        di = abs(ci[1] - anchors[i, 1]) if ci is not None else float("inf")
        dj = abs(cj[1] - anchors[j, 1]) if cj is not None else float("inf")
        if ci is None and cj is None:
            break  # nowhere to put either; leave them rather than loop forever
        if dj < di:
            pos[j] = cj
            moved.append(j)
        else:
            pos[i] = ci
            moved.append(i)
    return moved


def add_name_boxes(ax: Axes, df: pd.DataFrame, max_value: float) -> None:
    """Draw name boxes, nudging a label aside only when its text would be covered.

    Each box starts on its person's true (X, Y) and stays there unless another
    opaque card would cover its text. To resolve such an overlap only one card is
    moved — the other keeps its point — nudged the minimum distance to a free
    vertical slot nearby. A small nudge is left unmarked (it still reads as on its
    point); only a card pushed well off its point gets a dot there plus a dashed
    leader line. Cards may overlap freely as long as every label stays legible.
    """
    texts = [_box_text(row) for _, row in df.iterrows()]
    if not texts:
        return
    stops = [_gradient_stops(row) for _, row in df.iterrows()]  # (primary, secondary, ratio) per person
    bird_vecs = [_bird_vector(row) for _, row in df.iterrows()]

    sizes = np.array([[max(8, len(t) * 0.4), _BOX_HEIGHT] for t in texts], dtype=float)
    # Real rendered text extents (data units): a label is only "in the way" when
    # another opaque card would cover this text — not when the padded boxes graze.
    text_sizes = np.array(
        [_text_data_extent(ax, t, 10, (len(t) * 0.4, _BOX_HEIGHT * 0.7)) for t in texts], dtype=float
    )
    anchors = df[["X", "Y"]].to_numpy(dtype=float)

    # Everyone starts on their true point; within each cluster of cards whose text
    # would collide, move as few cards as possible to a free vertical slot nearby.
    pos = anchors.copy()
    moved = set()
    for group in _clusters(anchors, sizes, text_sizes=text_sizes):
        if len(group) >= 2:
            moved.update(_resolve_group(group, pos, sizes, text_sizes, anchors, bird_vecs, max_value))

    # A card pushed well off its point gets a dot there + a dashed vertical leader
    # line back to it. A card only nudged a little is left unmarked — it still reads
    # as on its point, and a tiny dot-and-stub by the box edge looks worse than none.
    for i in moved:
        if abs(pos[i][1] - anchors[i][1]) < _LEADER_MIN:
            continue
        dot_x, dot_y = anchors[i]
        ax.plot([pos[i][0], dot_x], [pos[i][1], dot_y], color="black", linewidth=0.5, linestyle="--", zorder=2)
        ax.scatter([dot_x], [dot_y], s=2, color="black", zorder=4)

    # Gradient-filled label boxes (imshow can disturb the axes aspect/limits, so
    # snapshot and restore them afterwards).
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    for i, text in enumerate(texts):
        bx, by = pos[i]
        c1, c2, ratio = stops[i]
        _fill_gradient_box(ax, bx, by, sizes[i, 0], sizes[i, 1], c1, c2, ratio)
        ax.text(bx, by, text, fontsize=10, ha="center", va="center", color="black", zorder=5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)


def add_grid(ax: Axes) -> None:
    # Add grid lines
    ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")


def scatter_chart(df: pd.DataFrame, filename: Path, config: dict) -> None:
    """Create a scatter plot of personality distributions.

    Args:
        df: DataFrame containing personality data points (with X/Y columns)
        filename: Path where the chart should be saved
        config: Loaded configuration dictionary

    Raises:
        Exception: For any errors during chart creation
    """
    fig = None
    try:
        # Create and configure the matplotlib figure and axes
        fig, ax = setup_plot(config)

        # Add chart components in layers:
        # 1. Background elements
        add_grid(ax)  # Add grid lines
        add_quadrants(ax, config)  # Add quadrant labels/divisions
        add_bird_images(ax, config)  # Add bird images if configured
        add_quadrant_labels(ax, config)  # Add quadrant labels
        add_axis_labels(ax)  # Add X and Y axis labels

        # 2. Data visualization elements
        add_name_boxes(ax, df, config["chart"]["max_value"])  # Add name boxes (decluttered)

        # 3. Metadata and title elements
        # Add current date to plot
        add_date(ax, config)

        # Set chart title
        plt.title(
            "Personality Distribution",
            fontsize=14,
            fontweight="bold",
            y=1.03,
        )

        # Save the chart to file (format set explicitly so file-like buffers work)
        plt.savefig(filename, dpi=300, bbox_inches="tight", format="png")
        logger.info(f"Plot saved to {filename}")

    except Exception as e:
        logger.error(f"Error creating scatter chart: {str(e)}")
        raise
    finally:
        if fig is not None:
            plt.close(fig)  # Close figure to free memory
