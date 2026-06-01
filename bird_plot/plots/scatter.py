import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch

from .base import add_axis_labels, add_bird_images, add_date, add_quadrant_labels, add_quadrants, setup_plot

logger = logging.getLogger(__name__)


def add_name_boxes(ax: Axes, df: pd.DataFrame) -> None:
    """Add names in rounded boxes to the plot."""
    for _, row in df.iterrows():
        note = row.get("Note", "")
        note_str = "" if (not note or pd.isna(note)) else str(note)
        text = f"{row['Name']} {note_str}".strip()
        text_length = len(text)
        box_width = max(8, text_length * 0.4)
        box_height = 1

        box = FancyBboxPatch(
            (float(row["X"]) - box_width / 2, float(row["Y"]) - box_height / 2),
            width=box_width,
            height=box_height,
            boxstyle="round,pad=0.3",
            edgecolor="lightblue",
            facecolor="lightblue",
            alpha=0.8,
        )
        ax.add_patch(box)
        ax.text(
            float(row["X"]),
            float(row["Y"]),
            text,
            fontsize=10,
            ha="center",
            va="center",
            color="black",
        )


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
        add_name_boxes(ax, df)  # Add name boxes

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
