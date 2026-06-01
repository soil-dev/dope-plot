import logging
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Rectangle

logger = logging.getLogger(__name__)


def setup_plot(config: dict) -> tuple[Figure, Axes]:
    """Initialize the plot with basic settings.

    Args:
        config: Dictionary containing chart configuration parameters including:
            - 'figure_size': tuple of (width, height)
            - 'max_value': maximum value for axis limits

    Returns:
        tuple: (figure, axes) matplotlib objects for further plotting
    """

    # Create new figure and axes with specified size from config
    fig, ax = plt.subplots(figsize=tuple(config["chart"]["figure_size"]))

    # Force the plot to maintain equal aspect ratio
    ax.set_aspect("equal", adjustable="box")

    # Set the x and y axis limits symmetrically based on max_value
    ax.set_xlim(-config["chart"]["max_value"], config["chart"]["max_value"])
    ax.set_ylim(-config["chart"]["max_value"], config["chart"]["max_value"])

    # Remove tick marks and numbers from both axes
    ax.set_xticks([])
    ax.set_yticks([])

    return fig, ax


def _add_bird_image(ax, img_path, x, y) -> None:
    """Add a bird image to the plot at specified coordinates.

    Args:
        ax: The matplotlib axes object to draw on
        img_path: Path to the bird image file
        x: X-coordinate for image placement
        y: Y-coordinate for image placement
    """

    # Check if the image file exists at the specified path
    if Path(img_path).exists():
        # Load the image file using matplotlib
        img = plt.imread(img_path)

        # Create an OffsetImage object with the loaded image
        # zoom=0.2 scales the image to 20% of its original size
        imagebox = OffsetImage(img, zoom=0.2)

        # Create an AnnotationBbox to place the image at specific coordinates
        # This allows the image to be positioned precisely on the plot
        ab = AnnotationBbox(imagebox, (x, y))

        # Add the annotation box containing the image to the plot
        ax.add_artist(ab)
    else:
        logger.warning("Image not found at %s", img_path)


def add_bird_images(ax: Axes, config: dict) -> None:
    """Add bird images to the corners of the plot.

    Args:
        ax: The matplotlib axes object to draw on
        config: Dictionary containing configuration including:
            - 'chart.max_value': Determines corner positions
            - 'paths.birds_dir': Directory containing bird images
    """

    # Get the maximum value from config to determine corner positions
    max_value = config["chart"]["max_value"]

    # Set up path to directory containing bird images
    birds_dir = Path(config["paths"]["birds_dir"])

    # Define bird placements in corners:
    # (bird_name, x_position, y_position)
    birds = [
        ("peacock", -max_value, max_value),  # top-left
        ("eagle", -max_value, -max_value),  # bottom-left
        ("dove", max_value, max_value),  # top-right
        ("owl", max_value, -max_value),  # bottom-right
    ]

    # Add each bird image to its respective corner
    for bird, x, y in birds:
        # Construct full path to bird image file
        bird_path = birds_dir / f"{bird}.png"
        # Add the bird image to the plot
        _add_bird_image(ax, bird_path, x, y)


def add_quadrants(ax: Axes, config: dict) -> None:
    """Add colored quadrants to the plot background.

    Args:
        ax: The matplotlib axes object to draw on
        config: Dictionary containing:
            - 'chart.max_value': Size of quadrants
            - 'colors': Dictionary with:
                - top_right, bottom_right, top_left, bottom_left: quadrant colors
                - alpha: transparency value
    """
    # Get the maximum value to determine quadrant sizes
    max_value = config["chart"]["max_value"]

    # Define quadrants with their positions and colors
    # Each quadrant is defined by its bottom-left corner (x,y) and color
    quadrants = [
        ((-max_value, 0), config["colors"]["top_left"]),
        ((-max_value, -max_value), config["colors"]["bottom_left"]),
        ((0, 0), config["colors"]["top_right"]),
        ((0, -max_value), config["colors"]["bottom_right"]),
    ]

    # Create and add each quadrant rectangle to the plot
    for (x, y), color in quadrants:
        rect = Rectangle(
            (x, y),  # Bottom-left corner position
            width=max_value,
            height=max_value,
            facecolor=color,
            alpha=config["colors"]["alpha"],
            edgecolor=None,
            zorder=-1,  # Place behind other elements
        )
        # Add the rectangle to the plot
        ax.add_patch(rect)


def add_quadrant_labels(ax: Axes, config: dict) -> None:
    """Add labels to the quadrants."""
    max_value = config["chart"]["max_value"]
    labels = [
        (max_value / 2, max_value * 0.96, "Supportive & Caring"),  # Top-Right (Dove)
        (-max_value / 2, -max_value * 0.96, "Controlling & Forceful"),  # Bottom-Left (Eagle)
        (-max_value / 2, max_value * 0.96, "Talkative & Dramatic"),  # Top-Left (Peacock)
        (max_value / 2, -max_value * 0.96, "Analytical & Logical"),  # Bottom-Right (Owl)
    ]

    for x, y, text in labels:
        ax.text(x, y, text, ha="center", va="center")


def add_axis_labels(ax: Axes) -> None:
    """Add descriptive labels to the axes."""
    labels = [
        (-0.015, 0.5, "Confident, Assertive, Bold", 90),  # Left Y-axis
        (0.5, 1.015, "Warm & Friendly, People-oriented", 0),  # Top X-axis
        (1.015, 0.5, "Shy, Non-assertive, Retiring", 270),  # Right Y-axis
        (0.5, -0.015, "Cold & Aloof, Task-oriented", 0),  # Bottom X-axis
    ]

    for x, y, text, rotation in labels:
        plt.text(x, y, text, transform=ax.transAxes, rotation=rotation, va="center", ha="center", fontstyle="italic")


def add_date(ax: Axes, config: dict) -> None:
    """Add generation date and project link to the plot.

    Args:
        ax: The matplotlib axes object to draw on
        config: Dictionary containing configuration including:
            - 'chart.show_project_link': whether to show project link
    """
    # Format current date as YYYY-MM-DD
    date_string = datetime.now().strftime("%Y-%m-%d")
    y_pos = -0.1
    link_fontsize = 5
    date_fontsize = 10
    if config.get("chart", {}).get("show_project_link", True):
        # Add project link centered under the plot
        ax.text(
            0.5,
            y_pos,
            "https://github.com/arapov/bird-plot",
            transform=ax.transAxes,
            ha="center",
            fontsize=link_fontsize,
            color="black",
        )
    # Add date text to the plot
    ax.text(
        1,  # X position: right edge
        y_pos,  # Y position: 10% below bottom of axes
        f"Generated: {date_string}",
        transform=ax.transAxes,  # Use axes coordinates (0-1 range)
        ha="right",
        fontsize=date_fontsize,
    )
