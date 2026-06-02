"""Smoke tests for the MCP server (skipped if the optional 'mcp' extra is absent)."""

import asyncio

import pytest

pytest.importorskip("mcp")

from dope_plot import mcp_server  # noqa: E402


def test_tools_registered():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {t.name for t in tools}
    assert {"scatter_chart", "radar_chart", "comparison_chart"} <= names


def test_radar_tool_returns_image():
    # The decorated tool function returns an mcp Image carrying PNG bytes.
    image = mcp_server.radar_chart("Alice", 16, 4, 9, 3, "D/O")
    assert image.data[:8] == b"\x89PNG\r\n\x1a\n"
