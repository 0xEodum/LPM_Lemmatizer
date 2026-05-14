from __future__ import annotations

from functools import lru_cache

from fugashi import Tagger

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import clean_lemma, is_usable_lemma


_CONTENT_POS = {"名詞", "動詞", "形容詞", "副詞", "形状詞", "連体詞"}


class JapaneseBackend(LemmaBackend):
    name = "fugashi"

    def supports(self, language: str) -> bool:
        return language == "ja"

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        tokens = []
        for word in _tagger()(text):
            pos = getattr(word.feature, "pos1", "")
            if pos not in _CONTENT_POS:
                continue
            lemma = clean_lemma(getattr(word.feature, "lemma", "") or word.surface)
            if lemma == "*" or not is_usable_lemma(lemma):
                lemma = word.surface
            tokens.append(LemmaToken(surface=word.surface, lemma=lemma, language=language, backend=self.name, pos=pos))
        return tuple(tokens)


@lru_cache(maxsize=1)
def _tagger() -> Tagger:
    return Tagger()
