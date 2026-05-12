from __future__ import annotations

import re

import simplemma

from lemmatizer.config import FRENCH_IRREGULARS, GERMAN_IRREGULARS, LEMMA_OVERRIDES, STOPWORDS
from lemmatizer.models import LemmaToken
from lemmatizer.reference import ReferenceSnapper
from lemmatizer.text_utils import WORD_RE, PUNCT_OR_NUMBER_RE


def lemmatize_simple(text: str, language: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    tokens = []
    for match in WORD_RE.finditer(text):
        surface = match.group(0)
        lower = surface.casefold()
        if lower in STOPWORDS.get(language, set()):
            continue
        candidates = _base_candidates(surface, lower, language, text, match.start())
        if language == "hy":
            candidates = _armenian_candidates(lower) + candidates
        elif language == "de":
            candidates.extend(_german_candidates(surface, lower))
        elif language == "fr":
            candidates.extend(_french_candidates(lower))
        lemma = snapper.snap(surface, candidates)
        lemma = LEMMA_OVERRIDES.get(language, {}).get(lemma, lemma)
        if _should_keep(lemma, language):
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos="", analyzer=f"simplemma:{language}"))
    if language == "de":
        tokens.extend(_german_reference_compounds(tokens, snapper))
    return tokens


def _base_candidates(surface: str, lower: str, language: str, text: str, start: int) -> list[str]:
    if language == "de":
        candidates = []
        if lower.startswith(("ein", "aus", "durch", "davon", "hinter")) and lower.endswith("en"):
            candidates.append(lower)
        if surface[:1].isupper() and not _is_sentence_initial(text, start):
            candidates.append(simplemma.lemmatize(surface, lang="de"))
        candidates.extend([simplemma.lemmatize(lower, lang="de"), lower])
        if lower.endswith("en") and len(lower) > 4:
            candidates.append(lower[:-2])
        return candidates
    if language == "fr":
        return _french_surface_candidates(lower)
    if language == "hy":
        normalized = lower.replace("եւ", "և")
        return [normalized, simplemma.lemmatize(normalized, lang=language), lower]
    return [simplemma.lemmatize(lower, lang=language), lower]


def _is_sentence_initial(text: str, start: int) -> bool:
    before = text[:start].rstrip()
    return not before or before[-1] in ".!?"


def _armenian_candidates(token: str) -> list[str]:
    token = token.replace("եւ", "և")
    if token in LEMMA_OVERRIDES.get("hy", {}):
        return [LEMMA_OVERRIDES["hy"][token]]
    candidates = []
    if token.endswith("եցին"):
        candidates.append(token[:-4] + "ել")
    if token.endswith("վում"):
        candidates.append(token[:-3] + "վել")
    if token.endswith("վեց"):
        candidates.append(token[:-3] + "վել")
    if token.endswith("ային"):
        candidates.append(token)
    suffixes = [
        "ները",
        "ների",
        "յան",
        "ին",
        "ներ",
        "երը",
        "երի",
        "ում",
        "ով",
        "ից",
        "ու",
        "ը",
        "ի",
    ]
    for suffix in suffixes:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            stem = token[: -len(suffix)]
            if len(stem) >= 2:
                candidates.append(stem)
    if token.endswith("անում"):
        candidates.append(token[:-4] + "անալ")
    if token.endswith("ում"):
        candidates.append(token[:-2] + "ել")
    if token.endswith("ված"):
        candidates.append(token[:-3] + "վել")
        candidates.append(token[:-3] + "ել")
    if token.endswith("ած"):
        candidates.append(token[:-2] + "ել")
    if token.endswith("եց"):
        candidates.append(token[:-2] + "ել")
    if token.endswith("ում"):
        candidates.append(token[:-2] + "վել")
    if token.endswith("ալ"):
        candidates.append(token[:-2] + "անք")
    if token.endswith("ող"):
        candidates.append(token[:-2] + "ել")
        candidates.append(token[:-2] + "ալ")
    if token == "եկող":
        candidates.append("գալ")
    candidates.extend(LEMMA_OVERRIDES.get("hy", {}).get(candidate, candidate) for candidate in list(candidates))
    return candidates


def _german_candidates(surface: str, token: str) -> list[str]:
    candidates = []
    if token in GERMAN_IRREGULARS:
        candidates.append(GERMAN_IRREGULARS[token])
    for source, target in {"ä": "a", "ö": "o", "ü": "u", "ß": "ss"}.items():
        if source in token:
            candidates.append(token.replace(source, target))
    if token.endswith("en") and any(mark in token for mark in "äöü"):
        candidates.append(token[:-2])
    if surface[:1].isupper():
        candidates.append(surface)
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


def _french_surface_candidates(token: str) -> list[str]:
    part = re.split(r"['’]", token, maxsplit=1)[-1]
    candidates = []
    has_clitic = part != token
    if has_clitic and part.endswith(("é", "ée")):
        candidates.append(part)
    if part.endswith("s") and len(part) > 3:
        candidates.append(part[:-1])
    if part.endswith("ant") and len(part) > 5:
        candidates.append(part[:-3] + "er")
    candidates.append(simplemma.lemmatize(part, lang="fr"))
    candidates.append(part)
    if part != token:
        candidates.append(token)
    return candidates


def _should_keep(lemma: str, language: str) -> bool:
    normalized = lemma.casefold()
    if normalized in STOPWORDS.get(language, set()):
        return False
    return not PUNCT_OR_NUMBER_RE.match(lemma)
