from __future__ import annotations

from functools import lru_cache

from kiwipiepy import Kiwi

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import clean_lemma, is_usable_lemma


_CONTENT_PREFIXES = ("N", "V")
_CONTENT_TAGS = {"MAG", "XR"}


class KoreanBackend(LemmaBackend):
    name = "kiwipiepy"

    def supports(self, language: str) -> bool:
        return language == "ko"

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        tokens = []
        for token in _kiwi().tokenize(text):
            if not token.tag.startswith(_CONTENT_PREFIXES) and token.tag not in _CONTENT_TAGS:
                continue
            lemma = clean_lemma(token.lemma or token.form)
            if not is_usable_lemma(lemma):
                continue
            tokens.append(
                LemmaToken(surface=token.form, lemma=lemma, language=language, backend=self.name, pos=token.tag)
            )
        return tuple(tokens)


@lru_cache(maxsize=1)
def _kiwi() -> Kiwi:
    return Kiwi()
