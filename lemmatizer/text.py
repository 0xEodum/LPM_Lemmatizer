from __future__ import annotations

import regex


WORD_RE = regex.compile(r"[\p{L}\p{M}]+(?:[-'’][\p{L}\p{M}]+)*", flags=regex.VERSION1)
PUNCT_OR_NUMBER_RE = regex.compile(r"^[\p{P}\p{S}\p{N}\s]+$", flags=regex.VERSION1)


def clean_lemma(value: str | None) -> str:
    return (value or "").strip()


def is_usable_lemma(value: str) -> bool:
    return bool(value) and not PUNCT_OR_NUMBER_RE.match(value)
