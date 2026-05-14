from __future__ import annotations

import logging
import warnings
from functools import lru_cache

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*")
    import jieba

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import clean_lemma, is_usable_lemma


class ChineseBackend(LemmaBackend):
    name = "jieba"

    def __init__(self) -> None:
        jieba.setLogLevel(logging.ERROR)

    def supports(self, language: str) -> bool:
        return language == "zh"

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        tokens = []
        for surface in _cut(text):
            lemma = clean_lemma(surface)
            if is_usable_lemma(lemma):
                tokens.append(LemmaToken(surface=surface, lemma=lemma, language=language, backend=self.name))
        return tuple(tokens)


@lru_cache(maxsize=256)
def _cut(text: str) -> tuple[str, ...]:
    return tuple(jieba.lcut(text, cut_all=False))
