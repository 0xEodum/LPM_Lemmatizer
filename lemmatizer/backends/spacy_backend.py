from __future__ import annotations

from functools import lru_cache
from threading import RLock
from typing import Iterable

import spacy

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import clean_lemma, is_usable_lemma


SPACY_MODELS = {
    "da": "da_core_news_sm",
    "de": "de_core_news_sm",
    "en": "en_core_web_sm",
    "es": "es_core_news_sm",
    "fi": "fi_core_news_sm",
    "fr": "fr_core_news_sm",
    "hr": "hr_core_news_sm",
    "it": "it_core_news_sm",
    "ja": "ja_core_news_sm",
    "ko": "ko_core_news_sm",
    "nb": "nb_core_news_sm",
    "pt": "pt_core_news_sm",
    "sv": "sv_core_news_sm",
    "uk": "uk_core_news_sm",
    "zh": "zh_core_web_sm",
}


class SpacyBackend(LemmaBackend):
    name = "spacy"

    def __init__(self, languages: Iterable[str]) -> None:
        self._languages = frozenset(languages)
        self._lock = RLock()

    def supports(self, language: str) -> bool:
        return language in self._languages

    def preload(self) -> None:
        for language in sorted(self._languages):
            self._pipeline(language)

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        nlp = self._pipeline(language)
        with self._lock:
            doc = nlp(text)
        tokens = []
        for token in doc:
            lemma = clean_lemma(token.lemma_ or token.text)
            if is_usable_lemma(lemma):
                tokens.append(LemmaToken(token.text, lemma, language, self.name, token.pos_))
        return tuple(tokens)

    def _pipeline(self, language: str) -> spacy.Language:
        if not self.supports(language):
            raise ValueError(f"spaCy is not configured for language: {language}")
        try:
            return _load_spacy_pipeline(SPACY_MODELS[language])
        except OSError as exc:
            model = SPACY_MODELS[language]
            raise RuntimeError(f"Missing spaCy model {model}; run `python -m spacy download {model}`") from exc


@lru_cache(maxsize=32)
def _load_spacy_pipeline(model_name: str) -> spacy.Language:
    return spacy.load(
        model_name,
        exclude=["parser", "ner", "textcat", "textcat_multilabel", "senter", "sentencizer"],
    )
