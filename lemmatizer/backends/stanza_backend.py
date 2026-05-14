from __future__ import annotations

from functools import lru_cache

import stanza

from lemmatizer.backends.base import LemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import clean_lemma, is_usable_lemma


_STANZA_LANGUAGES = {"be": "be", "he": "he"}


class StanzaBackend(LemmaBackend):
    name = "stanza"

    def supports(self, language: str) -> bool:
        return language in _STANZA_LANGUAGES

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        doc = _pipeline(_STANZA_LANGUAGES[language])(text)
        tokens = []
        for sentence in doc.sentences:
            for word in sentence.words:
                lemma = clean_lemma(word.lemma or word.text)
                if not is_usable_lemma(lemma):
                    continue
                tokens.append(
                    LemmaToken(surface=word.text, lemma=lemma, language=language, backend=self.name, pos=word.upos)
                )
        return tuple(tokens)


@lru_cache(maxsize=2)
def _pipeline(language: str) -> stanza.Pipeline:
    return stanza.Pipeline(
        lang=language,
        processors="tokenize,pos,lemma",
        download_method=None,
        use_gpu=False,
        verbose=False,
    )
