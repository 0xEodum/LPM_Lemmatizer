from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    name: str
    code: str


_NAME_TO_CODE = {
    "armenian": "hy",
    "belarusian": "be",
    "bulgarian": "bg",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "english": "en",
    "estonian": "et",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "hebrew": "he",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "latvian": "lv",
    "norwegian": "nb",
    "portuguese": "pt",
    "russian": "ru",
    "slovak": "sk",
    "spanish": "es",
    "swedish": "sv",
    "turkish": "tr",
    "ukrainian": "uk",
}

_ALIASES = {
    **_NAME_TO_CODE,
    **{code: code for code in _NAME_TO_CODE.values()},
    "jp": "ja",
    "ja": "ja",
    "jpn": "ja",
    "kr": "ko",
    "ko": "ko",
    "kor": "ko",
    "no": "nb",
    "nb": "nb",
    "nor": "nb",
    "zh": "zh",
    "zh-cn": "zh",
    "zh-hans": "zh",
}


def normalize_language(language: str) -> str:
    key = language.strip().casefold()
    try:
        return _ALIASES[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported language: {language}") from exc


def load_language_specs(path: str | Path) -> tuple[LanguageSpec, ...]:
    raw = Path(path).read_text(encoding="utf-8")
    names = [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]
    return tuple(LanguageSpec(name=name, code=normalize_language(name)) for name in names)
