from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LemmaToken:
    surface: str
    lemma: str
    language: str
    backend: str
    pos: str = ""


@dataclass(frozen=True, slots=True)
class LemmaResult:
    language: str
    tokens: tuple[LemmaToken, ...]
    elapsed_seconds: float = 0.0

    @property
    def unique_lemmas(self) -> tuple[str, ...]:
        seen: set[str] = set()
        lemmas: list[str] = []
        for token in self.tokens:
            key = token.lemma.casefold()
            if key in seen:
                continue
            seen.add(key)
            lemmas.append(token.lemma)
        return tuple(lemmas)

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "elapsed_seconds": self.elapsed_seconds,
            "unique_lemmas": list(self.unique_lemmas),
            "tokens": [
                {
                    "surface": token.surface,
                    "lemma": token.lemma,
                    "language": token.language,
                    "backend": token.backend,
                    "pos": token.pos,
                }
                for token in self.tokens
            ],
        }
