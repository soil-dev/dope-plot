import logging
import tomllib
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

_REQUIRED_KEYS: Dict[str, list] = {
    "chart": ["max_value", "figure_size", "grid_step"],
    "colors": ["top_right", "bottom_right", "top_left", "bottom_left", "alpha"],
    "paths": ["birds_dir", "output"],
}


def load_config(config_path: Path = Path("config.toml")) -> Dict:
    """Load and validate configuration from TOML file."""
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

    for section, keys in _REQUIRED_KEYS.items():
        if section not in config:
            raise KeyError(f"Missing required config section: [{section}]")
        for key in keys:
            if key not in config[section]:
                raise KeyError(f"Missing required config key: [{section}].{key}")

    return config
