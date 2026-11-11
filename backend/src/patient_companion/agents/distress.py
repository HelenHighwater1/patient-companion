"""Lightweight emotional-distress detection.

Keyword-based first pass — intentionally sensitive (a false positive only
means a warmer response). Feeds the answer agent's distress preamble.
"""

from __future__ import annotations

import re

_DISTRESS_RE = re.compile(
    r"\b("
    r"scared|afraid|terrified|fear(ful)?|anxious|anxiety|panic(king)?|"
    r"hopeless|despair|overwhelm(ed|ing)?|devastat(ed|ing)?|"
    r"can'?t (cope|do this|handle)|don'?t want to (live|go on)|"
    r"giving up|give up|no point|distraught|heartbroken|crying|"
    r"so sad|depress(ed|ing)|alone|nobody cares"
    r")\b",
    re.I,
)


def is_distressed(text: str) -> bool:
    return bool(_DISTRESS_RE.search(text or ""))
