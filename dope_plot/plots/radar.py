import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Circle, Patch
from matplotlib.path import Path as MplPath

from ..constants import CATEGORIES
from .base import add_axis_labels, add_bird_images, add_date, add_quadrant_labels, add_quadrants, setup_plot

logger = logging.getLogger(__name__)

# Fixed seed for the Monte Carlo overlap estimate so the reported percentage is
# reproducible: the same pair of profiles always yields the same overlap value.
_OVERLAP_RNG_SEED = 0


def _to_cartesian(angles: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert polar (angle, radius) arrays into cartesian (x, y) arrays.

    Single source of truth for the polar->cartesian conversion used throughout
    the radar plotting code: x = r*cos(theta), y = r*sin(theta).
    """
    return np.cos(angles) * values, np.sin(angles) * values


def calculate_angles(categories: list[str], values: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Calculate angles and values for the radar plot.

    Args:
        categories: List of category names to be displayed on the radar plot
        values: List of numerical values corresponding to each category

    Returns:
        tuple: (angles, values) where:
            - angles: numpy array of angles (in radians) for each category
            - values: numpy array of values with first value repeated at end

    Note:
        The function adds the first value/angle at the end of each array
        to create a closed polygon effect in the radar plot.
    """

    num_categories = len(categories)

    # Generate evenly spaced angles for each category
    # Starts at -π/4 (45° counterclockwise) and goes around the circle
    # endpoint=False ensures we don't duplicate the last point
    angles = np.linspace(-np.pi / 4, 2 * np.pi - np.pi / 4, num_categories, endpoint=False)

    # Convert values to numpy array
    values_array = np.array(values)

    # Add the first angle to the end to close the circular plot
    angles = np.concatenate((angles, [angles[0]]))
    # Add the first value to the end to close the polygon
    values_array = np.concatenate((values_array, [values_array[0]]))

    return angles, values_array


def add_labels(
    ax: Axes,
    angles: np.ndarray,
    values: np.ndarray,
) -> None:
    """Add numerical value labels to each point on the radar plot.

    Args:
        ax: The matplotlib axes object to draw on
        angles: Array of angles (in radians) for each point
        values: Array of numerical values to be displayed as labels

    Note:
        - Labels are offset slightly from their points for better visibility
        - The last value is skipped since it's a duplicate of the first (closing point)
        - Labels are positioned using trigonometric calculations for proper placement
    """

    if len(values) > 0:
        # Calculate offset distance for labels (10% of maximum value)
        # This prevents labels from overlapping with the plot lines
        offset = 0.1 * max(values)

        # Iterate through all values except the last (which is a duplicate)
        for i, value in enumerate(values[:-1]):
            # Calculate the point position using polar to cartesian conversion
            x = np.cos(angles[i]) * value  # x = r * cos(θ)
            y = np.sin(angles[i]) * value  # y = r * sin(θ)

            # Calculate perpendicular offset for label positioning
            # Uses rotated vector (-sin, cos) for perpendicular direction
            perp_x = -np.sin(angles[i]) * offset
            perp_y = np.cos(angles[i]) * offset

            # Add text label at the calculated position
            # Centered both horizontally and vertically
            ax.text(x + perp_x, y + perp_y, str(round(value)), ha="center", va="center")


def add_grid(ax: Axes, config: dict) -> None:
    """Add grid lines to the radar plot for better readability.

    Args:
        ax: The matplotlib axes object to draw on
        config: Dictionary containing chart configuration parameters including:
            - 'max_value': Maximum value for the grid extent
            - 'grid_step': Spacing between concentric grid circles
    """

    # Get the maximum value from config to determine grid size
    max_value = config["chart"]["max_value"]

    # Add diagonal grid lines (X-shaped)
    # First diagonal: bottom-left to top-right
    ax.plot(
        [-max_value, max_value],
        [-max_value, max_value],
        "-",  #  solid line
        color="grey",
        linewidth=0.5,
    )
    # Second diagonal: top-left to bottom-right
    ax.plot(
        [-max_value, max_value],
        [max_value, -max_value],
        "-",  #  solid line
        color="grey",
        linewidth=0.5,
    )

    # Add horizontal and vertical axes through origin
    ax.axhline(0, color="k", linestyle="-", linewidth=0.5)  # horizontal line
    ax.axvline(0, color="k", linestyle="-", linewidth=0.5)  # vertical line

    # Add concentric circular grid lines
    # Creates circles at regular intervals defined by grid_step
    for i in range(0, max_value + 1, config["chart"]["grid_step"]):
        # Create a circle centered at origin (0,0) with radius i
        circle = Circle(
            (0, 0),
            i,
            fill=False,
            linestyle="--",  # dashed line
            alpha=0.2,
        )
        ax.add_artist(circle)  # add circle to plot


def calculate_overlap(values1: np.ndarray, values2: np.ndarray, angles: np.ndarray) -> float:
    """Calculate the percentage overlap between two radar plots.

    Args:
        values1: Values for first radar plot
        values2: Values for second radar plot
        angles: Angles for both plots

    Returns:
        float: Percentage of overlap between the two plots (0-100)
    """
    # Convert both polygons to cartesian coordinates
    x1, y1 = _to_cartesian(angles, values1)
    x2, y2 = _to_cartesian(angles, values2)

    # Create polygons
    polygon1 = MplPath(np.column_stack((x1, y1)))
    polygon2 = MplPath(np.column_stack((x2, y2)))

    # Estimate the intersection-over-union via Monte Carlo sampling of the bbox
    n_samples = 10000
    bbox = [min(x1.min(), x2.min()), max(x1.max(), x2.max()), min(y1.min(), y2.min()), max(y1.max(), y2.max())]

    # Generate random sample points within the bounding box (seeded for reproducibility)
    rng = np.random.default_rng(_OVERLAP_RNG_SEED)
    x = rng.uniform(bbox[0], bbox[1], n_samples)
    y = rng.uniform(bbox[2], bbox[3], n_samples)
    sample_points = np.column_stack((x, y))

    # Count sample points falling inside each polygon
    in_poly1 = polygon1.contains_points(sample_points)
    in_poly2 = polygon2.contains_points(sample_points)

    # Overlap = intersection / union
    intersection = np.sum(in_poly1 & in_poly2)
    union = np.sum(in_poly1 | in_poly2)

    return (intersection / union) * 100 if union > 0 else 0.0


def plot_with_overlap(
    ax: Axes,
    angles: np.ndarray,
    values1: np.ndarray,
    values2: np.ndarray | None = None,
    color1: str = "blue",
    color2: str = "red",
    alpha: float = 0.3,
) -> None:
    """Draw radar plot with optional overlap of two datasets.

    Args:
        ax: The matplotlib axes object
        angles: Array of angles for the plots
        values1: Values for first radar plot
        values2: Optional values for second radar plot
        color1: Color for first plot
        color2: Color for second plot
        alpha: Transparency level for fills
    """
    # Plot first dataset
    x1, y1 = _to_cartesian(angles, values1)
    ax.plot(x1, y1, "x", markersize=5, color=color1)
    ax.fill(x1, y1, color=color1, alpha=alpha)

    # Plot second dataset if provided
    if values2 is not None:
        x2, y2 = _to_cartesian(angles, values2)
        ax.plot(x2, y2, "x", markersize=5, color=color2)
        ax.fill(x2, y2, color=color2, alpha=alpha)


def _format_title(data: dict) -> str:
    """Format radar chart title with optional note."""
    note = data.get("Note")
    if note and not pd.isna(note):
        return f"{data['Name']}, {note}"
    return f"{data['Name']}"


def radar_chart(data1: dict, filename: Path, config: dict, data2: dict | None = None) -> None:
    """Create a radar chart for personality data.

    Args:
        data1: Dictionary containing personality scores and metadata
        filename: Path where the chart should be saved
        config: Loaded configuration dictionary
        data2: Optional second profile to overlay for a comparison chart

    Raises:
        Exception: For any errors during chart creation
    """
    fig = None
    try:
        # The order is critical for angle calculations:
        # Starting at -π/2 and going clockwise:
        # Owl (bottom right) → Dove (top right) → Peacock (top left) → Eagle (bottom left)
        ordered_categories = CATEGORIES
        values1 = [data1[cat] for cat in ordered_categories]
        angles, values1_array = calculate_angles(ordered_categories, values1)

        # Create and configure the matplotlib figure and axes
        fig, ax = setup_plot(config)

        # Add chart components in layers:
        # 1. Background elements
        add_grid(ax, config)  # Add grid lines
        add_quadrants(ax, config)  # Add quadrant labels/divisions
        add_bird_images(ax, config)  # Add bird images if configured
        add_quadrant_labels(ax, config)  # Add quadrant labels
        add_axis_labels(ax)  # Add X and Y axis labels

        # 2. Data visualization elements
        if data2:
            values2 = [data2[cat] for cat in ordered_categories]
            _, values2_array = calculate_angles(ordered_categories, values2)

            # Plot both datasets with different colors
            plot_with_overlap(ax, angles, values1_array, values2_array)

            # Calculate and display overlap percentage
            overlap = calculate_overlap(values1_array, values2_array, angles)
            ax.text(0, -config["chart"]["max_value"] - 3, f"Overlap: {overlap:.1f}%", ha="center", va="center")

            # Add legend with filled swatches that match the plotted polygons
            legend_handles = [
                Patch(facecolor="blue", alpha=0.3, label=f"{data1['Name']}"),
                Patch(facecolor="red", alpha=0.3, label=f"{data2['Name']}"),
            ]
            ax.legend(
                handles=legend_handles,
                title="Legend",
                loc="upper center",
                edgecolor="black",
                framealpha=1.0,
                fancybox=False,
                bbox_to_anchor=(1, 0.9),
            )

            title = f"Comparison: {data1['Name']} vs {data2['Name']}"
        else:
            # Single plot
            plot_with_overlap(ax, angles, values1_array)
            add_labels(ax, angles, values1_array)
            title = _format_title(data1)

        # 3. Metadata and title elements
        # Add current date to plot
        add_date(ax, config)
        # Set chart title using name and note from data
        plt.title(
            f"{title}",
            fontsize=14,
            fontweight="bold",
            y=1.03,
        )

        # Save the chart to file (format set explicitly so file-like buffers work)
        plt.savefig(filename, dpi=300, bbox_inches="tight", format="png")
        logger.info(f"Plot saved to {filename}")

    except Exception as e:
        # Log any errors and re-raise them
        logger.error(f"Error creating radar chart: {str(e)}")
        raise
    finally:
        if fig is not None:
            plt.close(fig)  # Close figure to free memory
