"""Refactor guardrail: render a representative set of charts and hash their PIXELS.

The only runtime nondeterminism is the generation date (base.add_date uses
datetime.now()), which is frozen here to a fixed value. The Monte Carlo overlap
estimate is seeded in the production code itself, so it is already reproducible.
That means the ONLY thing that can change a hash is a code change to rendering.

Compares pixel arrays (not file bytes), so PNG metadata is ignored.
Run before and after a change; identical hashes == graphs unchanged.
"""

import hashlib
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import mock

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import numpy as np
import pandas as pd

import bird_plot.plots.base as base_mod
from bird_plot.cli import generate_radar_charts, generate_team_average_radar, process_personality_data
from bird_plot.plots.scatter import scatter_chart

REPO = Path(__file__).resolve().parent
CONFIG = {
    "chart": {"max_value": 25, "figure_size": [8, 8], "grid_step": 5, "show_project_link": True},
    "colors": {
        "top_right": "lightskyblue",
        "bottom_right": "khaki",
        "top_left": "lightgreen",
        "bottom_left": "lightcoral",
        "alpha": 0.2,
    },
    "paths": {"birds_dir": str(REPO / "birds"), "output": "charts"},
}


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 2, 3, 4, 5)


def _hash_png(path: Path) -> str:
    arr = mpimg.imread(path)
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def main() -> None:
    # Small fixed dataset: exercises every render path (individual radar,
    # comparison w/ overlap+legend, team average, scatter) in ~13 charts.
    # Independent of data.csv so edits there can't shift the baseline.
    df_src = pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Cara"],
            "Dove": [20, 10, 3],
            "Eagle": [10, 2, 18],
            "Owl": [15, 14, 7],
            "Peacock": [5, 5, 16],
            "Note": ["D/O", "O/D", "E/P"],
        }
    )
    with mock.patch.object(base_mod, "datetime", _FrozenDateTime):
        with tempfile.TemporaryDirectory() as d:
            cfg = {**CONFIG, "paths": {**CONFIG["paths"], "output": d}}
            csv = Path(d) / "_src.csv"
            df_src.to_csv(csv, index=False)
            df = process_personality_data(str(csv), cfg)
            generate_radar_charts(df, cfg)
            generate_team_average_radar(df, cfg)
            scatter_chart(df, Path(d) / "scatter_all.png", cfg)

            pngs = sorted(Path(d).rglob("*.png"))
            digests = {p.relative_to(d).as_posix(): _hash_png(p) for p in pngs}

    combined = hashlib.sha256(
        "\n".join(f"{k}={v}" for k, v in sorted(digests.items())).encode()
    ).hexdigest()
    print(f"charts rendered: {len(digests)}")
    for k, v in sorted(digests.items()):
        print(f"  {v[:16]}  {k}")
    print(f"COMBINED: {combined}")

    # Optional: compare against a saved baseline passed as argv[1].
    if len(sys.argv) > 1:
        baseline = Path(sys.argv[1])
        if baseline.exists():
            prev = baseline.read_text().strip()
            if prev == combined:
                print("RESULT: IDENTICAL to baseline ✓")
            else:
                print(f"RESULT: CHANGED ✗  (baseline {prev})")
                sys.exit(1)
        else:
            baseline.write_text(combined)
            print(f"RESULT: baseline written to {baseline}")


if __name__ == "__main__":
    main()
