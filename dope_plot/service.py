"""In-process rendering API returning PNG bytes.

A thin, framework-agnostic layer over the chart renderers so other programs
(the MCP server, an HTTP API, notebooks, ...) can generate charts from data in
memory and get the image back as bytes — no files, no ``sys.exit``.

Invalid input raises ``ValueError`` (callers decide how to surface it).
"""

import io

import pandas as pd

from .cli import process_dataframe, validate_personality_df
from .config import load_config
from .plots.radar import radar_chart
from .plots.scatter import scatter_chart

SCORE_FIELDS = ("Dove", "Eagle", "Owl", "Peacock")


def _person(name: str, dove: float, eagle: float, owl: float, peacock: float, note: str = "") -> dict:
    return {"Name": name, "Dove": dove, "Eagle": eagle, "Owl": owl, "Peacock": peacock, "Note": note}


def _validated_profile(profile: dict) -> dict:
    """Validate one direct radar/comparison profile and return coerced values."""
    validated = validate_personality_df(pd.DataFrame([profile]))
    return validated.iloc[0].to_dict()


def scatter_png(csv_text: str, config: dict | None = None) -> bytes:
    """Render the group quadrant scatter from CSV text and return PNG bytes.

    CSV must have columns Name, Dove, Eagle, Owl, Peacock (Note optional).
    """
    config = config or load_config()
    try:
        df = pd.read_csv(io.StringIO(csv_text))
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError(f"could not parse CSV text: {exc}") from exc
    df = process_dataframe(df, config)  # validates + adds X/Y (raises ValueError if invalid)
    buf = io.BytesIO()
    scatter_chart(df, buf, config)
    return buf.getvalue()


def radar_png(
    name: str, dove: float, eagle: float, owl: float, peacock: float, note: str = "", config: dict | None = None
) -> bytes:
    """Render a single person's radar chart and return PNG bytes."""
    config = config or load_config()
    data = _validated_profile(_person(name, dove, eagle, owl, peacock, note))
    buf = io.BytesIO()
    radar_chart(data, buf, config)
    return buf.getvalue()


def comparison_png(person_a: dict, person_b: dict, config: dict | None = None) -> bytes:
    """Render an overlap radar comparing two people and return PNG bytes.

    Each person dict needs Name and the four score fields (Note optional).
    """
    config = config or load_config()
    person_a = _validated_profile(person_a)
    person_b = _validated_profile(person_b)
    buf = io.BytesIO()
    radar_chart(person_a, buf, config, data2=person_b)
    return buf.getvalue()
