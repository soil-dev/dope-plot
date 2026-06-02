import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .constants import CATEGORIES
from .plots.radar import radar_chart
from .plots.scatter import scatter_chart

logger = logging.getLogger(__name__)

GRAPH_TYPES = ["radar", "scatter"]
DEFAULT_DATA_FILE = "data.csv"
REQUIRED_COLUMNS = {"Name", "Dove", "Owl", "Peacock", "Eagle"}
SCORE_COLUMNS = ["Dove", "Owl", "Peacock", "Eagle"]


def load_csv_data(file_path):
    """Load and validate CSV data from the given file path."""
    if not Path(file_path).exists():
        logger.error("CSV file '%s' not found!", file_path)
        sys.exit(1)

    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        logger.error("CSV file '%s' is empty.", file_path)
        sys.exit(1)
    except pd.errors.ParserError:
        logger.error("Could not parse CSV file '%s'. Check its format.", file_path)
        sys.exit(1)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        logger.error("CSV file '%s' is missing required columns: %s", file_path, ", ".join(sorted(missing)))
        sys.exit(1)

    if df.empty:
        logger.error("CSV file '%s' does not contain any data rows.", file_path)
        sys.exit(1)

    missing_names = df["Name"].isna() | df["Name"].astype(str).str.strip().eq("")
    if missing_names.any():
        logger.error("CSV file '%s' contains blank names.", file_path)
        sys.exit(1)

    for col in SCORE_COLUMNS:
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.isna().any() or not np.isfinite(numeric).all():
            logger.error(
                "CSV file '%s' contains non-numeric, blank, or non-finite scores in column: %s",
                file_path,
                col,
            )
            sys.exit(1)
        df[col] = numeric

    negative = {col: True for col in SCORE_COLUMNS if (df[col] < 0).any()}
    if negative:
        logger.error("Negative scores found in columns: %s", ", ".join(sorted(negative)))
        sys.exit(1)

    return df


def calculate_team_average(df: pd.DataFrame) -> dict:
    """Calculate the team average scores."""
    avg_scores = {cat: df[cat].mean() for cat in CATEGORIES}
    avg_scores["Name"] = "Team Average Profile"
    # Show the top two dominant birds (by average score), abbreviated to first letter
    sorted_cats = sorted(CATEGORIES, key=lambda c: avg_scores[c], reverse=True)
    avg_scores["Note"] = "/".join(c[0] for c in sorted_cats[:2])
    return avg_scores


def generate_team_average_radar(df: pd.DataFrame, config: dict) -> None:
    """Generate a single radar chart showing only the team average."""
    # Get base output directory from config
    output_base = Path(config["paths"]["output"])
    output_base.mkdir(exist_ok=True)
    team_avg = calculate_team_average(df)
    output_filename = output_base / "radar_team_average.png"
    radar_chart(team_avg, Path(output_filename), config)


def _safe_name_for_path(name: str) -> str:
    """Normalize a display name into a safe filesystem path segment."""
    # Keep alphanumerics, dot, dash, underscore; collapse others to "_".
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(name))
    safe = safe.strip("._-")
    return safe or "unnamed"


def _sigmoid_scale(series: pd.Series, max_value: float) -> pd.Series:
    """Scale series with tanh compression, guarding against divide-by-zero."""
    denom = series.abs().max()
    if denom == 0 or pd.isna(denom):
        return series * 0
    return max_value * np.tanh(series / denom)


def generate_radar_charts(df: pd.DataFrame, config: dict) -> None:
    """Generate individual and comparison radar charts for all entries."""

    # Get base output directory from config
    output_base = Path(config["paths"]["output"])
    output_base.mkdir(exist_ok=True)

    # Calculate team average
    team_avg = calculate_team_average(df)

    # Generate individual radar charts
    for _, row in df.iterrows():
        person_data = row.to_dict()
        person_name = person_data["Name"]
        person_slug = _safe_name_for_path(person_name)

        # Create person's directory if it doesn't exist
        person_dir = output_base / person_slug
        person_dir.mkdir(exist_ok=True)

        # Create comparison subdirectory
        compare_dir = person_dir / "compare"
        compare_dir.mkdir(exist_ok=True)

        # Individual radar chart
        output_filename = person_dir / f"radar_{person_slug}.png"
        radar_chart(person_data, output_filename, config)

        # Individual vs Team Average comparison
        output_filename = compare_dir / "with_TeamAverage.png"
        radar_chart(person_data, output_filename, config, data2=team_avg)

        # Generate comparisons with all other people
        for _, other_row in df.iterrows():
            if other_row["Name"] != person_name:
                other_data = other_row.to_dict()
                other_name = other_data["Name"]
                other_slug = _safe_name_for_path(other_name)
                output_filename = compare_dir / f"with_{other_slug}.png"
                radar_chart(person_data, output_filename, config, data2=other_data)


def process_personality_data(data_file: str, config: dict) -> pd.DataFrame:
    """Load and process personality data from CSV file."""
    # Load data
    df = load_csv_data(data_file)
    personality_cols = SCORE_COLUMNS

    # Adjust scores - multiply max scores by 1.2
    max_scores = df[personality_cols].max(axis=1)
    df_adjusted = (
        df[personality_cols].where(~df[personality_cols].eq(max_scores, axis=0), df[personality_cols] * 1.2).astype(int)
    )

    # Calculate X and Y coordinates
    df["X"] = (df_adjusted["Dove"] + df_adjusted["Owl"]) - (df_adjusted["Peacock"] + df_adjusted["Eagle"])
    df["Y"] = (df_adjusted["Peacock"] + df_adjusted["Dove"]) - (df_adjusted["Eagle"] + df_adjusted["Owl"])

    # Scale coordinates
    # Use tanh to smoothly compress values to [-1, 1], then scale to ±max_value
    df["X"] = _sigmoid_scale(df["X"], config["chart"]["max_value"])
    df["Y"] = _sigmoid_scale(df["Y"], config["chart"]["max_value"])

    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Generate dope-plot personality charts.")
    parser.add_argument(
        "--data",
        "-d",
        default=DEFAULT_DATA_FILE,
        help=f"Path to the CSV data file (default: {DEFAULT_DATA_FILE}).",
    )
    parser.add_argument(
        "--graph",
        "-g",
        choices=GRAPH_TYPES,
        default=["scatter"],
        nargs="+",
        help="Type of graph to generate (radar or scatter).",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=None,
        help="Path to a TOML config file. Defaults to ./config.toml, then bundled package defaults.",
    )
    args = parser.parse_args()
    config = load_config(args.config)

    # Load and process data
    df = process_personality_data(args.data, config)

    # Handle multiple graph types
    if "radar" in args.graph:
        generate_radar_charts(df, config)
        generate_team_average_radar(df, config)
    if "scatter" in args.graph:
        # Get base output directory from config
        output_base = Path(config["paths"]["output"])
        output_base.mkdir(exist_ok=True)
        output_filename = output_base / "scatter_all.png"
        scatter_chart(df, Path(output_filename), config)


if __name__ == "__main__":
    main()
