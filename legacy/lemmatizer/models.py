from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class LemmaToken:
    surface: str
    lemma: str
    pos: str
    analyzer: str


@dataclass(frozen=True)
class LemmaReport:
    language: str
    tokens: tuple[LemmaToken, ...]
    unique_lemmas: tuple[str, ...]
    expected_lemmas: tuple[str, ...] = ()
    metrics: dict[str, float] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "lemmas": list(self.unique_lemmas),
            "tokens": [token.__dict__ for token in self.tokens],
            "expected_lemmas": list(self.expected_lemmas),
            "metrics": self.metrics,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class TextFilePair:
    prefix: str
    language: str
    text_path: Path
    entities_path: Path | None
