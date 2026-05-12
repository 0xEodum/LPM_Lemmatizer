from __future__ import annotations

import re
from collections.abc import Iterable


WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
PUNCT_OR_NUMBER_RE = re.compile(r"^[\W\d_]+$", re.UNICODE)


def unique(items: Iterable[str]) -> tuple[str, ...]:
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return tuple(output)
