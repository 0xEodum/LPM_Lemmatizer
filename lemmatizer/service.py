from __future__ import annotations

import time
from collections.abc import Iterable

from lemmatizer.backends import ChineseBackend, JapaneseBackend, KoreanBackend, LemmaBackend, SimplemmaBackend, StanzaBackend
from lemmatizer.languages import normalize_language
from lemmatizer.models import LemmaResult


class UniversalLemmatizer:
    def __init__(self, backends: Iterable[LemmaBackend] | None = None) -> None:
        self._backends = tuple(backends or _default_backends())

    def normalize_language(self, language: str) -> str:
        return normalize_language(language)

    def supports(self, language: str) -> bool:
        normalized = normalize_language(language)
        return any(backend.supports(normalized) for backend in self._backends)

    def lemmatize(self, text: str, language: str) -> LemmaResult:
        normalized = normalize_language(language)
        backend = self._backend_for(normalized)
        started = time.perf_counter()
        tokens = backend.lemmatize(text, normalized)
        elapsed = time.perf_counter() - started
        return LemmaResult(language=normalized, tokens=tokens, elapsed_seconds=elapsed)

    def _backend_for(self, language: str) -> LemmaBackend:
        for backend in self._backends:
            if backend.supports(language):
                return backend
        raise ValueError(f"Unsupported language: {language}")


def _default_backends() -> tuple[LemmaBackend, ...]:
    return (
        JapaneseBackend(),
        KoreanBackend(),
        ChineseBackend(),
        SimplemmaBackend(),
        StanzaBackend(),
    )
