from __future__ import annotations

from functools import lru_cache

import stanza

from lemmatizer.config import PREFIX_TO_LANGUAGE, STOPWORDS
from lemmatizer.models import LemmaReport, LemmaToken
from lemmatizer.text_utils import PUNCT_OR_NUMBER_RE, unique


STANZA_LANGUAGE = {
    "ar": "ar",
    "de": "de",
    "fr": "fr",
    "hy": "hy",
    "jp": "ja",
    "kr": "ko",
    "pt": "pt",
    "tr": "tr",
    "vi": "vi",
}

PROCESSORS = {
    "ar": "tokenize,mwt,pos,lemma",
    "de": "tokenize,mwt,pos,lemma",
    "fr": "tokenize,mwt,pos,lemma",
    "hy": "tokenize,mwt,pos,lemma",
    "ja": "tokenize,pos,lemma",
    "ko": "tokenize,pos,lemma",
    "pt": "tokenize,mwt,pos,lemma",
    "tr": "tokenize,pos,lemma",
    "vi": "tokenize,pos,lemma",
}

CONTENT_UPOS = {"ADJ", "ADV", "NOUN", "PROPN", "VERB"}


def lemmatize_text_stanza(text: str, language: str) -> LemmaReport:
    language = PREFIX_TO_LANGUAGE.get(language, language)
    stanza_language = STANZA_LANGUAGE.get(language)
    if stanza_language is None:
        raise ValueError(f"Unsupported Stanza language: {language}")
    doc = _pipeline(stanza_language)(text)
    tokens = []
    for sentence in doc.sentences:
        for word in sentence.words:
            lemma = word.lemma or word.text
            if not _should_keep(word.upos, lemma, language):
                continue
            tokens.append(LemmaToken(surface=word.text, lemma=lemma, pos=word.upos, analyzer="stanza"))
    return LemmaReport(language=language, tokens=tuple(tokens), unique_lemmas=unique(token.lemma for token in tokens))


@lru_cache(maxsize=8)
def _pipeline(stanza_language: str) -> stanza.Pipeline:
    return stanza.Pipeline(
        lang=stanza_language,
        processors=PROCESSORS[stanza_language],
        download_method=None,
        verbose=False,
    )


def _should_keep(upos: str, lemma: str, language: str) -> bool:
    if upos not in CONTENT_UPOS:
        return False
    if PUNCT_OR_NUMBER_RE.match(lemma):
        return False
    if lemma.casefold() in STOPWORDS.get(language, set()):
        return False
    return True
