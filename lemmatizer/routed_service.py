from __future__ import annotations

import time
from collections.abc import Iterable

from lemmatizer.backends import LemmaBackend, SpacyBackend, UDPipeBackend
from lemmatizer.config import ServiceConfig
from lemmatizer.languages import normalize_language
from lemmatizer.models import LemmaResult


class RoutedLemmatizer:
    def __init__(self, config: ServiceConfig) -> None:
        udpipe_backend = UDPipeBackend(config.udpipe)
        spacy_backend = SpacyBackend(config.spacy)
        self._backends: tuple[LemmaBackend, ...] = (udpipe_backend, spacy_backend)
        self._routes = {
            **{language: udpipe_backend for language in config.udpipe},
            **{language: spacy_backend for language in config.spacy},
        }
        self.preload()

    def preload(self) -> None:
        for backend in self._backends:
            preload = getattr(backend, "preload", None)
            if preload is not None:
                preload()

    def supports(self, language: str) -> bool:
        return normalize_language(language) in self._routes

    def lemmatize(self, text: str, language: str) -> LemmaResult:
        normalized = normalize_language(language)
        try:
            backend = self._routes[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported or unconfigured language: {language}") from exc
        started = time.perf_counter()
        tokens = backend.lemmatize(text, normalized)
        elapsed = time.perf_counter() - started
        return LemmaResult(language=normalized, tokens=tokens, elapsed_seconds=elapsed)

    def lemmatize_batch(self, items: Iterable[tuple[str, str]]) -> tuple[LemmaResult, ...]:
        return tuple(self.lemmatize(text=text, language=language) for language, text in items)
