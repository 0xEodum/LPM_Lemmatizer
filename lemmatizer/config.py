from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import TypeAlias


StringMap: TypeAlias = dict[str, str]
StringSetMap: TypeAlias = dict[str, set[str]]
IrregularMap: TypeAlias = dict[str, str]
CandidateMap: TypeAlias = dict[str, list[str]]


def _load_json(name: str) -> object:
    with resources.files("lemmatizer.resources").joinpath(name).open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_prefix_to_language() -> StringMap:
    return dict(_load_json("languages.json"))


@lru_cache(maxsize=1)
def load_stopwords() -> StringSetMap:
    raw = _load_json("stopwords.json")
    return {language: set(words) for language, words in raw.items()}


@lru_cache(maxsize=1)
def load_german_irregulars() -> IrregularMap:
    return dict(_load_json("german_irregulars.json"))


@lru_cache(maxsize=1)
def load_french_irregulars() -> CandidateMap:
    raw = _load_json("french_irregulars.json")
    return {key: list(value) for key, value in raw.items()}


PREFIX_TO_LANGUAGE = load_prefix_to_language()
STOPWORDS = load_stopwords()
GERMAN_IRREGULARS = load_german_irregulars()
FRENCH_IRREGULARS = load_french_irregulars()
