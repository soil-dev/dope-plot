"""Characterization tests for dope_plot.config.load_config."""

from pathlib import Path

import pytest

from dope_plot.config import load_config

REPO_ROOT = Path(__file__).resolve().parent.parent

VALID_TOML = """
[chart]
max_value = 25
figure_size = [8, 8]
grid_step = 5

[colors]
top_right = "lightskyblue"
bottom_right = "khaki"
top_left = "lightgreen"
bottom_left = "lightcoral"
alpha = 0.2

[paths]
icons_set = "icons/hunt"
output = "charts"
"""


def _write(tmp_path, text):
    p = tmp_path / "config.toml"
    p.write_text(text)
    return p


def test_load_config_valid(tmp_path):
    cfg = load_config(_write(tmp_path, VALID_TOML))
    assert cfg["chart"]["max_value"] == 25
    assert cfg["chart"]["figure_size"] == [8, 8]
    assert cfg["paths"]["output"] == "charts"
    assert cfg["colors"]["alpha"] == pytest.approx(0.2)


def test_load_config_uses_bundled_defaults_without_local_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg["paths"]["output"] == "charts"
    assert Path(cfg["paths"]["icons_set"]).exists()
    assert (Path(cfg["paths"]["icons_set"]) / "dove.png").exists()


def test_load_config_missing_file_raises(tmp_path):
    # A non-existent path should surface the OSError (re-raised after logging).
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does_not_exist.toml")


def test_load_config_missing_section_raises(tmp_path):
    text = VALID_TOML.replace('[paths]\nicons_set = "icons/hunt"\noutput = "charts"\n', "")
    with pytest.raises(KeyError) as exc:
        load_config(_write(tmp_path, text))
    assert "paths" in str(exc.value)


def test_load_config_missing_key_raises(tmp_path):
    text = VALID_TOML.replace("grid_step = 5\n", "")
    with pytest.raises(KeyError) as exc:
        load_config(_write(tmp_path, text))
    assert "grid_step" in str(exc.value)


def test_shipped_config_is_valid():
    """The config.toml shipped in the repo must keep loading & validating."""
    cfg = load_config(REPO_ROOT / "config.toml")
    assert set(cfg) >= {"chart", "colors", "paths"}


def test_bundled_icons_match_the_bundled_set():
    """dope_plot/assets/icons is filled by build.py (and the test bootstrap)
    from the canonical top-level set; the artifact must mirror it exactly."""
    src = REPO_ROOT / "icons" / "emoji"  # keep in sync with build.BUNDLED_SET
    artifact = REPO_ROOT / "dope_plot" / "assets" / "icons"
    src_files = sorted(p.name for p in src.glob("*.png"))
    artifact_files = sorted(p.name for p in artifact.glob("*.png"))
    assert src_files == ["dove.png", "eagle.png", "owl.png", "peacock.png"]
    assert artifact_files == src_files
    for name in src_files:
        assert (src / name).read_bytes() == (artifact / name).read_bytes(), name
