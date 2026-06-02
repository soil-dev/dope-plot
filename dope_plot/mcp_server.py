"""Model Context Protocol server for dope-plot.

Exposes the personality charts as MCP tools that return the rendered PNG inline,
so any MCP-capable client (Claude Desktop/Code, n8n's MCP node, OpenAI agents,
...) can generate charts from data passed in the call.

Run it (after ``pip install 'dope-plot[mcp]'``):

    dope-plot-mcp

and point your client's MCP config at that command (stdio transport).
"""

from mcp.server.fastmcp import FastMCP, Image

from .service import comparison_png, radar_png, scatter_png

mcp = FastMCP("dope-plot")


@mcp.tool()
def scatter_chart(csv: str) -> Image:
    """Plot a whole group on the four-quadrant TICK personality chart.

    `csv` is CSV text with a header row and columns: Name, Dove, Eagle, Owl,
    Peacock (an optional Note column may hold the primary/secondary letters,
    e.g. "D/O"). Returns the scatter chart as a PNG.
    """
    return Image(data=scatter_png(csv), format="png")


@mcp.tool()
def radar_chart(name: str, dove: float, eagle: float, owl: float, peacock: float, note: str = "") -> Image:
    """Plot one person's radar chart from their four TICK bird scores.

    Scores are Dove, Eagle, Owl and Peacock. Returns the radar chart as a PNG.
    """
    return Image(data=radar_png(name, dove, eagle, owl, peacock, note), format="png")


@mcp.tool()
def comparison_chart(
    name_a: str,
    dove_a: float,
    eagle_a: float,
    owl_a: float,
    peacock_a: float,
    name_b: str,
    dove_b: float,
    eagle_b: float,
    owl_b: float,
    peacock_b: float,
) -> Image:
    """Overlay two people's radar charts and show their overlap percentage.

    Each person is given by a name plus their four TICK bird scores (Dove,
    Eagle, Owl, Peacock). Returns the comparison chart as a PNG.
    """
    person_a = {"Name": name_a, "Dove": dove_a, "Eagle": eagle_a, "Owl": owl_a, "Peacock": peacock_a}
    person_b = {"Name": name_b, "Dove": dove_b, "Eagle": eagle_b, "Owl": owl_b, "Peacock": peacock_b}
    return Image(data=comparison_png(person_a, person_b), format="png")


def main() -> None:
    """Console-script entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
