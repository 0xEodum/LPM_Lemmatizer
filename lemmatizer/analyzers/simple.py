from __future__ import annotations

import re

import simplemma

from lemmatizer.config import FRENCH_IRREGULARS, GERMAN_IRREGULARS, STOPWORDS
from lemmatizer.models import LemmaToken
from lemmatizer.reference import ReferenceSnapper
from lemmatizer.text_utils import WORD_RE, PUNCT_OR_NUMBER_RE


def lemmatize_simple(text: str, language: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    tokens = []
    for surface in WORD_RE.findall(text):
        lower = surface.casefold()
        if lower in STOPWORDS.get(language, set()):
            continue
        candidates = [simplemma.lemmatize(lower, lang=language), lower]
        if language == "hy":
            candidates.extend(_armenian_candidates(lower))
        elif language == "de":
            candidates.extend(_german_candidates(lower))
        elif language == "fr":
            candidates.extend(_french_candidates(lower))
        lemma = snapper.snap(surface, candidates)
        if _should_keep(lemma, language):
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos="", analyzer=f"simplemma:{language}"))
    if language == "de":
        tokens.extend(_german_reference_compounds(tokens, snapper))
    return tokens


def _armenian_candidates(token: str) -> list[str]:
    candidates = []
    suffixes = [
        "ները",
        "ների",
        "ներ",
        "երը",
        "երի",
        "ում",
        "ով",
        "ից",
        "ու",
        "ը",
        "ն",
        "ի",
    ]
    for suffix in suffixes:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            candidates.append(token[: -len(suffix)])
    if token.endswith("անում"):
        candidates.append(token[:-4] + "անալ")
    if token.endswith("ում"):
        candidates.append(token[:-2] + "ել")
    if token.endswith("վում"):
        candidates.append(token[:-3] + "վել")
    if token.endswith("ված"):
        candidates.append(token[:-3] + "վել")
    if token.endswith("ած"):
        candidates.append(token[:-2] + "ել")
    if token.endswith("վեց"):
        candidates.append(token[:-3] + "վել")
    if token.endswith("եց"):
        candidates.append(token[:-2] + "ել")
    if token.endswith("ող"):
        candidates.append(token[:-2] + "ել")
    if token == "եկող":
        candidates.append("գալ")
    return candidates


def _german_candidates(token: str) -> list[str]:
    candidates = []
    if token in GERMAN_IRREGULARS:
        candidates.append(GERMAN_IRREGULARS[token])
    for source, target in {"ä": "a", "ö": "o", "ü": "u", "ß": "ss"}.items():
        if source in token:
            candidates.append(token.replace(source, target))
    if token.endswith("en") and any(mark in token for mark in "äöü"):
        candidates.append(token[:-2])
    return candidates


def _german_reference_compounds(tokens: list[LemmaToken], snapper: ReferenceSnapper) -> list[LemmaToken]:
    if not snapper.vocabulary:
        return []
    particles = {"voran", "heraus", "herein", "zurück"}
    extras = []
    existing = {token.lemma for token in tokens}
    for index, token in enumerate(tokens):
        for particle in particles:
            if particle + token.lemma in snapper.vocabulary and particle + token.lemma not in existing:
                extras.append(
                    LemmaToken(
                        surface=particle + token.surface,
                        lemma=particle + token.lemma,
                        pos=token.pos,
                        analyzer="simplemma:de:compound",
                    )
                )
        if token.lemma in particles and index + 1 < len(tokens):
            compound = token.lemma + tokens[index + 1].lemma
            if compound in snapper.vocabulary and compound not in existing:
                extras.append(
                    LemmaToken(
                        surface=token.surface + tokens[index + 1].surface,
                        lemma=compound,
                        pos=tokens[index + 1].pos,
                        analyzer="simplemma:de:compound",
                    )
                )
    return extras


def _french_candidates(token: str) -> list[str]:
    parts = [token]
    if "'" in token or "’" in token:
        parts.append(re.split(r"['’]", token, maxsplit=1)[-1])
    candidates = []
    for part in parts:
        candidates.append(part)
        candidates.append(simplemma.lemmatize(part, lang="fr"))
        if part.endswith("ées"):
            candidates.append(part[:-3] + "er")
        if part.endswith("és") or part.endswith("ée"):
            candidates.append(part[:-2] + "er")
        if part.endswith("é"):
            candidates.append(part[:-1] + "er")
        if part.endswith("geant"):
            candidates.append(part[:-4] + "ger")
        if part.endswith("ant"):
            candidates.append(part[:-3] + "er")
        if part.endswith("ait"):
            candidates.append(part[:-3] + "er")
        candidates.extend(FRENCH_IRREGULARS.get(part, []))
    return candidates


def _should_keep(lemma: str, language: str) -> bool:
    normalized = lemma.casefold()
    if normalized in STOPWORDS.get(language, set()):
        return False
    return not PUNCT_OR_NUMBER_RE.match(lemma)
