from __future__ import annotations

import simplemma

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import WORD_RE, clean_lemma, is_usable_lemma


_LANGUAGE_MAP = {
    "bg": "bg",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "en": "en",
    "es": "es",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "hr": "hbs",
    "hy": "hy",
    "id": "id",
    "it": "it",
    "lv": "lv",
    "nb": "nb",
    "pt": "pt",
    "ru": "ru",
    "sk": "sk",
    "sv": "sv",
    "tr": "tr",
    "uk": "uk",
}


class SimplemmaBackend(LemmaBackend):
    name = "simplemma"

    def supports(self, language: str) -> bool:
        return language in _LANGUAGE_MAP

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        simplemma_language = _LANGUAGE_MAP[language]
        tokens = []
        for match in WORD_RE.finditer(text):
            surface = match.group(0)
            lookup = _lookup_form(surface, language)
            lemma = clean_lemma(simplemma.lemmatize(lookup, lang=simplemma_language))
            if not is_usable_lemma(lemma):
                continue
            tokens.append(LemmaToken(surface=surface, lemma=lemma, language=language, backend=self.name))
        return tuple(tokens)


def _lookup_form(surface: str, language: str) -> str:
    if language == "tr":
        return surface.replace("İ", "i").replace("I", "ı").lower()
    if language == "de" and surface[:1].isupper():
        return surface
    return surface.casefold()
