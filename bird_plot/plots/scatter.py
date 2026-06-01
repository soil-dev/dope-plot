import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch

from .base import add_axis_labels, add_bird_images, add_date, add_quadrant_labels, add_quadrants, setup_plot

logger = logging.getLogger(__name__)

_BOX_HEIGHT = 1.0
_DOT_OFFSET = _BOX_HEIGHT / 2 + 0.2  # label rests just above its dot
_CLUSTER_PAD = 0.5  # breathing room kept between boxes

# Box border colour keyed to a person's dominant bird, so the label reads on any
# quadrant background (white fill) while the border still carries meaning.
_BIRD_BORDER = {"D": "royalblue", "E": "crimson", "O": "goldenrod", "P": "seagreen"}
_NEUTRAL_BORDER = "0.4"


def _box_text(row) -> str:
    """Build the '<Name> <Note>' label, tolerating empty/NaN notes."""
    note = row.get("Note", "")
    note_str = "" if (not note or pd.isna(note)) else str(note)
    return f"{row['Name']} {note_str}".strip()


def _border_color(row) -> str:
    """Pick a border colour from the dominant bird.

    Prefers the primary letter of the Note (what the label shows); falls back to
    the highest raw score, then to a neutral grey when nothing is available.
    """
    note = row.get("Note", "")
    if note and not pd.isna(note):
        color = _BIRD_BORDER.get(str(note)[:1].upper())
        if color:
            return color
    scores = {b: row.get(b) for b in ("Dove", "Eagle", "Owl", "Peacock")}
    scores = {b: v for b, v in scores.items() if v is not None and not pd.isna(v)}
    if scores:
        return _BIRD_BORDER[max(scores, key=scores.get)[0]]
    return _NEUTRAL_BORDER


def _declutter(centers: np.ndarray, sizes: np.ndarray, max_value: float, iters: int = 400) -> np.ndarray:
    """Push overlapping label boxes apart, deterministically.

    Each pair that overlaps (axis-aligned, with _CLUSTER_PAD breathing room) is
    separated along its axis of least penetration. Boxes are wide and short, so
    this naturally stacks coincident people vertically. Identical positions use
    an index-based tie-break so the result is reproducible (no randomness).
    """
    pos = centers.astype(float).copy()
    n = len(pos)
    for _ in range(iters):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = pos[i, 0] - pos[j, 0], pos[i, 1] - pos[j, 1]
                overlap_x = (sizes[i, 0] + sizes[j, 0]) / 2 + _CLUSTER_PAD - abs(dx)
                overlap_y = (sizes[i, 1] + sizes[j, 1]) / 2 + _CLUSTER_PAD - abs(dy)
                if overlap_x > 0 and overlap_y > 0:
                    if overlap_y <= overlap_x:
                        shift = overlap_y / 2
                        sgn = 1.0 if dy > 0 else (-1.0 if dy < 0 else (1.0 if i < j else -1.0))
                        pos[i, 1] += sgn * shift
                        pos[j, 1] -= sgn * shift
                    else:
                        shift = overlap_x / 2
                        sgn = 1.0 if dx > 0 else (-1.0 if dx < 0 else (1.0 if i < j else -1.0))
                        pos[i, 0] += sgn * shift
                        pos[j, 0] -= sgn * shift
                    moved = True
        if not moved:
            break
    # Keep boxes fully inside the canvas.
    pos[:, 0] = np.clip(pos[:, 0], -max_value + sizes[:, 0] / 2, max_value - sizes[:, 0] / 2)
    pos[:, 1] = np.clip(pos[:, 1], -max_value + sizes[:, 1] / 2, max_value - sizes[:, 1] / 2)
    return pos


def add_name_boxes(ax: Axes, df: pd.DataFrame, max_value: float) -> None:
    """Draw a dot at each true position plus a decluttered name box.

    A small dot marks every person's true (X, Y). Name boxes start just above
    their dot and are then pushed apart so they never overlap; a leader line
    connects any box that had to be displaced back to its dot. This keeps people
    with identical or very similar profiles individually readable.
    """
    texts = [_box_text(row) for _, row in df.iterrows()]
    if not texts:
        return
    border_colors = [_border_color(row) for _, row in df.iterrows()]

    sizes = np.array([[max(8, len(t) * 0.4), _BOX_HEIGHT] for t in texts], dtype=float)
    anchors = df[["X", "Y"]].to_numpy(dtype=float)

    # Labels rest just above their dot, then get pushed apart.
    start = anchors.copy()
    start[:, 1] += _DOT_OFFSET
    pos = _declutter(start, sizes, max_value)

    for i, text in enumerate(texts):
        bx, by = pos[i]
        ax_, ay = anchors[i]

        # Dot at the true position (always visible, drawn above the boxes).
        ax.scatter([ax_], [ay], s=7, color="black", zorder=4)

        # Leader line only when the box was pushed past its resting offset.
        if np.hypot(bx - ax_, by - ay) > _DOT_OFFSET + 0.05:
            ax.plot([bx, ax_], [by, ay], color="gray", linewidth=0.6, zorder=2)

        box = FancyBboxPatch(
            (bx - sizes[i, 0] / 2, by - sizes[i, 1] / 2),
            width=sizes[i, 0],
            height=sizes[i, 1],
            boxstyle="round,pad=0.3",
            edgecolor=border_colors[i],
            facecolor="white",
            linewidth=1.6,
            alpha=0.95,
            zorder=3,
        )
        ax.add_patch(box)
        ax.text(bx, by, text, fontsize=10, ha="center", va="center", color="black", zorder=5)


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

        # Save the chart to file
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        logger.info(f"Plot saved to {filename}")

    except Exception as e:
        logger.error(f"Error creating scatter chart: {str(e)}")
        raise
    finally:
        if fig is not None:
            plt.close(fig)  # Close figure to free memory
