from __future__ import annotations

import qalsadi.lemmatizer
from pyarabic import araby

from lemmatizer.config import STOPWORDS
from lemmatizer.models import LemmaToken
from lemmatizer.reference import ReferenceSnapper
from lemmatizer.text_utils import PUNCT_OR_NUMBER_RE


def lemmatize_arabic(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    lemmatizer = qalsadi.lemmatizer.Lemmatizer()
    tokens = []
    for surface in araby.tokenize(text):
        if PUNCT_OR_NUMBER_RE.match(surface):
            continue
        surface_candidates = _arabic_candidates(surface)
        has_stripped_form = surface_candidates and surface_candidates[0] != araby.strip_diacritics(surface)
        if has_stripped_form:
            candidates = [*surface_candidates, lemmatizer.lemmatize(surface)]
        else:
            candidates = [lemmatizer.lemmatize(surface), *surface_candidates]
        lemma = snapper.snap(surface, candidates)
        if _should_keep(lemma):
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos="", analyzer="qalsadi"))
    return tokens


def _arabic_candidates(surface: str) -> list[str]:
    normalized = araby.strip_diacritics(surface).replace("ـ", "")
    variants = []
    for prefix in ("وال", "بال", "كال", "فال", "لل", "ال", "و", "ف", "ب", "ك", "ل"):
        if normalized.startswith(prefix) and len(normalized) > len(prefix) + 2:
            variants.append(normalized[len(prefix) :])
            break
    variants.append(normalized)
    more = []
    for variant in variants:
        more.append(variant)
        if variant.endswith("ية"):
            more.append(variant[:-2] + "ي")
        if variant.endswith("ة"):
            more.append(variant[:-1])
        if variant.endswith("ات"):
            more.append(variant[:-2] + "ة")
        if variant.endswith("ون") or variant.endswith("ين"):
            more.append(variant[:-2])
        if variant.startswith("أ"):
            more.append("ا" + variant[1:])
        if variant.endswith("اء") and len(variant) > 3:
            more.append(variant[:-2])
        if variant.endswith("ار") and len(variant) > 3:
            more.append(variant[:-2] + "ر")
        if "سرار" in variant:
            more.append("سر")
    return more


def _should_keep(lemma: str) -> bool:
    return lemma.casefold() not in STOPWORDS.get("ar", set()) and not PUNCT_OR_NUMBER_RE.match(lemma)
