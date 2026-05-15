from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from lemmatizer.languages import normalize_language


DEFAULT_SPACY_LANGUAGES = ("de", "ja", "uk", "sv", "hr", "nb")
DEFAULT_UDPIPE_LANGUAGES = (
    "be",
    "bg",
    "cs",
    "da",
    "en",
    "es",
    "et",
    "fi",
    "fr",
    "he",
    "hy",
    "id",
    "it",
    "ko",
    "lv",
    "pt",
    "ru",
    "sk",
    "tr",
    "zh",
)


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    udpipe: tuple[str, ...]
    spacy: tuple[str, ...]

    @classmethod
    def default(cls) -> ServiceConfig:
        return cls(udpipe=DEFAULT_UDPIPE_LANGUAGES, spacy=DEFAULT_SPACY_LANGUAGES)


def load_service_config(path: str | Path) -> ServiceConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed_keys = {"udpipe", "spacy"}
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"Unknown config fields: {', '.join(unknown_keys)}")
    return build_service_config(
        udpipe=payload.get("udpipe", ()),
        spacy=payload.get("spacy", ()),
    )


def build_service_config(*, udpipe: Iterable[str], spacy: Iterable[str]) -> ServiceConfig:
    udpipe_languages = _normalize_unique("udpipe", udpipe)
    spacy_languages = _normalize_unique("spacy", spacy)
    overlap = sorted(set(udpipe_languages) & set(spacy_languages))
    if overlap:
        raise ValueError(f"Languages configured for multiple backends: {', '.join(overlap)}")
    _validate_backend_languages("UDPipe", udpipe_languages, _udpipe_supported_languages())
    _validate_backend_languages("spaCy", spacy_languages, _spacy_supported_languages())
    return ServiceConfig(udpipe=udpipe_languages, spacy=spacy_languages)


def _normalize_unique(field: str, languages: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(normalize_language(language) for language in languages)
    duplicates = sorted({language for language in normalized if normalized.count(language) > 1})
    if duplicates:
        raise ValueError(f"Duplicate languages in {field}: {', '.join(duplicates)}")
    return normalized


def _validate_backend_languages(backend_name: str, languages: tuple[str, ...], supported: set[str]) -> None:
    unsupported = sorted(set(languages) - supported)
    if unsupported:
        raise ValueError(f"{backend_name} backend does not support: {', '.join(unsupported)}")


def _spacy_supported_languages() -> set[str]:
    from lemmatizer.backends.spacy_backend import SPACY_MODELS

    return set(SPACY_MODELS)


def _udpipe_supported_languages() -> set[str]:
    from lemmatizer.backends.udpipe_backend import UDPIPE_CODES

    return set(UDPIPE_CODES)
