"""Tests for the in-process render-to-bytes service layer."""

import pytest

from dope_plot.service import comparison_png, radar_png, scatter_png

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
CSV = "Name,Dove,Eagle,Owl,Peacock,Note\nAlice,16,4,9,3,D/O\nBob,6,5,2,12,P/D\n"


def test_scatter_png_returns_png_bytes():
    out = scatter_png(CSV)
    assert out[:8] == PNG_MAGIC
    assert len(out) > 1000


def test_radar_png_returns_png_bytes():
    out = radar_png("Alice", 16, 4, 9, 3, "D/O")
    assert out[:8] == PNG_MAGIC


def test_comparison_png_returns_png_bytes():
    a = {"Name": "Alice", "Dove": 16, "Eagle": 4, "Owl": 9, "Peacock": 3, "Note": "D/O"}
    b = {"Name": "Bob", "Dove": 6, "Eagle": 5, "Owl": 2, "Peacock": 12, "Note": "P/D"}
    out = comparison_png(a, b)
    assert out[:8] == PNG_MAGIC


def test_scatter_png_raises_on_invalid_csv():
    # Missing score columns -> ValueError (not a process exit).
    with pytest.raises(ValueError):
        scatter_png("Name,Dove\nAlice,5\n")


def test_scatter_png_raises_on_negative_scores():
    with pytest.raises(ValueError):
        scatter_png("Name,Dove,Eagle,Owl,Peacock\nAlice,16,-4,9,3\n")
