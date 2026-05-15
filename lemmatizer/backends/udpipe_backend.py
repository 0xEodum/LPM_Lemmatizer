from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Iterable

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import PUNCT_OR_NUMBER_RE, clean_lemma


UDPIPE_CODES = {
    "be": "be",
    "bg": "bg",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "en": "en",
    "es": "es",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "he": "he",
    "hr": "hr",
    "hy": "hy",
    "id": "id",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "lv": "lv",
    "nb": "nb",
    "pt": "pt",
    "ru": "ru",
    "sk": "sk",
    "sv": "sv",
    "tr": "tr",
    "uk": "uk",
    "zh": "zh",
}


class UDPipeBackend(LemmaBackend):
    name = "udpipe"

    def __init__(self, languages: Iterable[str]) -> None:
        self._languages = frozenset(languages)
        self._lock = RLock()

    def supports(self, language: str) -> bool:
        return language in self._languages

    def preload(self) -> None:
        for language in sorted(self._languages):
            self._model(language)

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        model = self._model(language)
        tokenizer = model.newTokenizer(model.DEFAULT)
        if tokenizer is None:
            raise RuntimeError(f"UDPipe model for {language} has no tokenizer")
        with self._lock:
            tokenizer.setText(text)
            tokens = []
            sentence = _sentence()
            while tokenizer.nextSentence(sentence):
                model.tag(sentence, model.DEFAULT)
                for word in sentence.words[1:]:
                    lemma = clean_lemma(word.lemma or word.form)
                    if not lemma or PUNCT_OR_NUMBER_RE.match(lemma):
                        continue
                    tokens.append(LemmaToken(word.form, lemma, language, self.name, word.upostag))
                sentence = _sentence()
        return tuple(tokens)

    def _model(self, language: str):
        if not self.supports(language):
            raise ValueError(f"UDPipe is not configured for language: {language}")
        return _load_udpipe_model(UDPIPE_CODES[language])


@lru_cache(maxsize=32)
def _load_udpipe_model(language: str):
    from ufal.udpipe import Model

    path = _udpipe_model_path(language)
    model = Model.load(str(path))
    if model is None:
        raise RuntimeError(f"Could not load UDPipe model: {path}")
    return model


def _udpipe_model_path(language: str) -> Path:
    from spacy_udpipe import utils as spacy_udpipe_utils

    try:
        filename = spacy_udpipe_utils.LANGUAGES[language]
    except KeyError as exc:
        raise ValueError(f"UDPipe has no model mapping for language: {language}") from exc
    return Path(spacy_udpipe_utils.MODELS_DIR) / filename


def _sentence():
    from ufal.udpipe import Sentence

    return Sentence()
