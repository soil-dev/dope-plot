import logging
import tomllib
from importlib import resources
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = Path("config.toml")
BUNDLED_CONFIG_FILE = "default_config.toml"

_REQUIRED_KEYS: dict[str, list] = {
    "chart": ["max_value", "figure_size", "grid_step"],
    "colors": ["top_right", "bottom_right", "top_left", "bottom_left", "alpha"],
    "paths": ["icons_set", "output"],
}


def _validate_config(config: dict) -> None:
    """Validate that a config dict has the sections and keys renderers require."""
    for section, keys in _REQUIRED_KEYS.items():
        if section not in config:
            raise KeyError(f"Missing required config section: [{section}]")
        for key in keys:
            if key not in config[section]:
                raise KeyError(f"Missing required config key: [{section}].{key}")


def _load_config_from_path(config_path: Path) -> dict:
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error("Failed to load config from %s: %s", config_path, e)
        raise


def _load_bundled_config() -> dict:
    package_root = resources.files(__package__)
    config_file = package_root.joinpath(BUNDLED_CONFIG_FILE)
    try:
        with config_file.open("rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        logger.error("Failed to load bundled config: %s", e)
        raise

    icons_set = package_root.joinpath(config["paths"]["icons_set"])
    config["paths"]["icons_set"] = str(icons_set)
    return config


def load_config(config_path: Path | str | None = None) -> dict:
    """Load and validate configuration from TOML.

    Explicit paths are loaded as-is. Without an explicit path, a local
    ``config.toml`` in the current working directory takes precedence; if it is
    absent, the package's bundled default config and assets are used so the
    installed console script works outside the source checkout.
    """
    if config_path is not None:
        config = _load_config_from_path(Path(config_path))
    elif DEFAULT_CONFIG_FILE.exists():
        config = _load_config_from_path(DEFAULT_CONFIG_FILE)
    else:
        config = _load_bundled_config()

    _validate_config(config)

    return config
