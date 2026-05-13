from __future__ import annotations

import qalsadi.lemmatizer
from pyarabic import araby

from lemmatizer.config import LEMMA_OVERRIDES, STOPWORDS
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
        qalsadi_lemma = lemmatizer.lemmatize(surface)
        if _should_prefer_qalsadi(surface, surface_candidates):
            candidates = [qalsadi_lemma, *surface_candidates]
        else:
            candidates = [*surface_candidates, qalsadi_lemma]
        lemma = snapper.snap(surface, candidates)
        lemma = LEMMA_OVERRIDES.get("ar", {}).get(lemma, LEMMA_OVERRIDES.get("ar", {}).get(surface, lemma))
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
        if variant.endswith("ته") and len(variant) > 3:
            more.append(variant[:-2] + "ة")
        if variant.endswith("ه") and len(variant) > 3:
            more.append(variant[:-1])
        if variant.endswith("وا") and len(variant) > 3:
            more.append(variant[:-2])
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


def _should_prefer_qalsadi(surface: str, surface_candidates: list[str]) -> bool:
    if not surface_candidates:
        return True
    normalized = araby.strip_diacritics(surface).replace("ـ", "")
    first_candidate = surface_candidates[0]
    if first_candidate == normalized:
        return True
    if normalized.startswith("ب") and first_candidate[:1] in {"ا", "أ", "إ", "آ", "د", "ع", "ي"}:
        return True
    if normalized.startswith("و") and (first_candidate.endswith("ت") or first_candidate.endswith("وا")):
        return True
    return False


def _should_keep(lemma: str) -> bool:
    return lemma.casefold() not in STOPWORDS.get("ar", set()) and not PUNCT_OR_NUMBER_RE.match(lemma)
