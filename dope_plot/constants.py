"""Shared constants for dope-plot.

CATEGORIES is the canonical bird ordering. The order is significant: it both
assigns the radar-plot angles (Owl -> Dove -> Peacock -> Eagle, clockwise) and
acts as the stable tie-break when picking the team-average's dominant birds.
Keep these in one place so the visual order and the note order never drift apart.
"""


CATEGORIES: list[str] = ["Owl", "Dove", "Peacock", "Eagle"]
