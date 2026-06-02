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


def validate_personality_df(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and coerce a personality DataFrame, raising ValueError on bad data.

    Returns a copy with the four score columns coerced to numeric. Shared by the
    CLI (which turns failures into a clean process exit) and the in-process
    service/MCP layer (which surfaces the error to the caller).
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
    if df.empty:
        raise ValueError("no data rows")
    if (df["Name"].isna() | df["Name"].astype(str).str.strip().eq("")).any():
        raise ValueError("blank names")

    df = df.copy()
    for col in SCORE_COLUMNS:
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.isna().any() or not np.isfinite(numeric).all():
            raise ValueError(f"non-numeric, blank, or non-finite scores in column: {col}")
        df[col] = numeric

    negative = [col for col in SCORE_COLUMNS if (df[col] < 0).any()]
    if negative:
        raise ValueError(f"negative scores in columns: {', '.join(sorted(negative))}")
    return df


def load_csv_data(file_path):
    """Load, validate and coerce CSV data from a path (exits the process on error)."""
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

    try:
        return validate_personality_df(df)
    except ValueError as exc:
        logger.error("CSV file '%s': %s", file_path, exc)
        sys.exit(1)


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


def _add_coordinates(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Add scaled X/Y quadrant coordinates from the (validated) score columns."""
    df = df.copy()
    cols = SCORE_COLUMNS
    # Emphasise each row's dominant bird(s) by 1.2x before projecting to X/Y.
    max_scores = df[cols].max(axis=1)
    adjusted = df[cols].where(~df[cols].eq(max_scores, axis=0), df[cols] * 1.2).astype(int)
    df["X"] = (adjusted["Dove"] + adjusted["Owl"]) - (adjusted["Peacock"] + adjusted["Eagle"])
    df["Y"] = (adjusted["Peacock"] + adjusted["Dove"]) - (adjusted["Eagle"] + adjusted["Owl"])
    # Compress to [-max_value, max_value] with tanh, normalised per cohort.
    df["X"] = _sigmoid_scale(df["X"], config["chart"]["max_value"])
    df["Y"] = _sigmoid_scale(df["Y"], config["chart"]["max_value"])
    return df


def process_personality_data(data_file: str, config: dict) -> pd.DataFrame:
    """Load a CSV file and add scaled X/Y coordinates (CLI entry path)."""
    return _add_coordinates(load_csv_data(data_file), config)


def process_dataframe(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Validate an in-memory DataFrame and add scaled X/Y coordinates.

    Raises ValueError on invalid data; used by the in-process service layer.
    """
    return _add_coordinates(validate_personality_df(df), config)


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
