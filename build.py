"""Poetry build script: bundle the default icon set into the package.

The canonical icons live at the repo top level (icons/<set>/<bird>.png) — the
package directory must not duplicate them in git. But a wheel can only ship
files that live inside the package, so at build time the set named
``BUNDLED_SET`` is copied flat into ``dope_plot/assets/icons/`` (a gitignored
build artifact), which the bundled default config points at
(``icons_set = "assets/icons"``).

Run automatically by poetry-core via ``[tool.poetry.build]``; tests call
:func:`bundle_icons` directly so a fresh checkout behaves like a built one.
"""

import shutil
from pathlib import Path

BUNDLED_SET = "hunt"

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "icons" / BUNDLED_SET
DEST = ROOT / "dope_plot" / "assets" / "icons"


def bundle_icons() -> None:
    """Copy icons/<BUNDLED_SET>/*.png flat into dope_plot/assets/icons/."""
    pngs = sorted(SRC.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"no icons found to bundle in {SRC}")
    DEST.mkdir(parents=True, exist_ok=True)
    for png in pngs:
        shutil.copy2(png, DEST / png.name)


def build(setup_kwargs: dict | None = None):
    """poetry-core build-script entry point."""
    bundle_icons()
    return setup_kwargs


if __name__ == "__main__":
    build()
