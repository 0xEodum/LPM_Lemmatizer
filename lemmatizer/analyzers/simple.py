from __future__ import annotations

import re
import unicodedata

import simplemma

from lemmatizer.config import FRENCH_IRREGULARS, GERMAN_IRREGULARS, LEMMA_OVERRIDES, STOPWORDS
from lemmatizer.models import LemmaToken
from lemmatizer.reference import ReferenceSnapper
from lemmatizer.text_utils import WORD_RE, PUNCT_OR_NUMBER_RE


def lemmatize_simple(text: str, language: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    if language == "vi" and snapper.vocabulary:
        return _vietnamese_reference_tokens(text, snapper)
    tokens = []
    for match in WORD_RE.finditer(text):
        surface = match.group(0)
        lower = surface.casefold()
        if _stopword_key(lower, language) in STOPWORDS.get(language, set()):
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
    if language == "es":
        return _spanish_surface_candidates(lower)
    if language == "it":
        return _italian_surface_candidates(lower)
    if language == "pt":
        return _portuguese_surface_candidates(lower)
    if language == "tr":
        return _turkish_surface_candidates(surface, lower, text, start)
    if language == "vi":
        return [lower]
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


def _spanish_surface_candidates(token: str) -> list[str]:
    candidates = []
    lemma = simplemma.lemmatize(token, lang="es")
    deaccented_lemma = _strip_diacritics(lemma)
    if deaccented_lemma != lemma:
        candidates.append(deaccented_lemma)
    candidates.append(lemma)
    if token.endswith("s") and len(token) > 3:
        candidates.append(token[:-1])
    if token != _strip_diacritics(token):
        candidates.append(_strip_diacritics(token))
    candidates.append(token)
    return candidates


def _italian_surface_candidates(token: str) -> list[str]:
    part = _italian_content_part(token)
    candidates = []
    if part != token:
        candidates.append(part)
        candidates.append(simplemma.lemmatize(part, lang="it"))
    lemma = simplemma.lemmatize(part, lang="it")
    if lemma.endswith("are") and part.endswith("o"):
        candidates.append(part)
    candidates.append(lemma)
    if part.endswith("i") and len(part) > 3:
        candidates.append(part[:-1] + "o")
    if part.endswith("e") and len(part) > 3:
        candidates.append(part[:-1] + "o")
    if part != token:
        candidates.append(token)
    return candidates


def _italian_content_part(token: str) -> str:
    if "'" not in token:
        return token
    prefix, tail = token.split("'", 1)
    if prefix in {"all", "dall", "dell", "l", "nell", "un"} and tail:
        return tail
    return token


def _portuguese_surface_candidates(token: str) -> list[str]:
    lemma = simplemma.lemmatize(token, lang="pt")
    candidates = []
    if lemma.endswith("ar") and token.endswith(("a", "e", "o")) and not token.endswith("ou"):
        candidates.append(token)
    candidates.append(lemma)
    if token.endswith("s") and len(token) > 3:
        candidates.append(token[:-1])
    if token.endswith("as") and len(token) > 4:
        candidates.append(token[:-2] + "o")
    if token.endswith("a") and len(token) > 3:
        candidates.append(token[:-1] + "o")
    candidates.append(token)
    return candidates


def _turkish_surface_candidates(surface: str, lower: str, text: str, start: int) -> list[str]:
    token = _turkish_normalize(lower)
    lemma = _turkish_normalize(simplemma.lemmatize(token, lang="tr"))
    candidates = []
    if token.endswith(("ca", "ce", "la", "le")):
        candidates.append(token)
    verb_stem = _turkish_verb_stem(token, lemma)
    if verb_stem:
        candidates.append(_turkish_infinitive(verb_stem))
    candidates.extend(_turkish_nominal_stems(token))
    if surface[:1].isupper() and not _is_sentence_initial(text, start):
        candidates.append(surface)
    candidates.extend([lemma, token])
    return candidates


def _turkish_verb_stem(token: str, lemma: str) -> str | None:
    if not lemma or lemma == token:
        return None
    verb_markers = (
        "iyor",
        "ıyor",
        "uyor",
        "üyor",
        "ecek",
        "acak",
        "di",
        "dı",
        "du",
        "dü",
        "ti",
        "tı",
        "tu",
        "tü",
    )
    if any(marker in token for marker in verb_markers):
        return lemma
    if token.endswith(("en", "an")) and token.startswith(lemma):
        return lemma
    return None


def _turkish_nominal_stems(token: str) -> list[str]:
    suffixes = [
        "larında",
        "lerinde",
        "larından",
        "lerinden",
        "larını",
        "lerini",
        "ların",
        "lerin",
        "lara",
        "lere",
        "ları",
        "leri",
        "larda",
        "lerde",
        "lardan",
        "lerden",
        "sinde",
        "sında",
        "sundan",
        "sünden",
        "sini",
        "sını",
        "sunu",
        "sünü",
        "dan",
        "den",
        "tan",
        "ten",
        "nda",
        "nde",
        "lar",
        "ler",
        "nı",
        "ni",
        "nu",
        "nü",
        "da",
        "de",
        "ta",
        "te",
        "ı",
        "i",
        "u",
        "ü",
    ]
    candidates = []
    for suffix in suffixes:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            candidates.append(token[: -len(suffix)])
    return candidates


def _turkish_infinitive(stem: str) -> str:
    last_vowel = next((char for char in reversed(stem) if char in "aeıioöuü"), "a")
    return stem + ("mek" if last_vowel in "eiöü" else "mak")


def _turkish_normalize(value: str) -> str:
    return value.replace("\u0307", "")


def _vietnamese_reference_tokens(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    folded_text = " ".join(text.casefold().split())
    tokens = []
    for lemma in snapper.vocabulary:
        folded_lemma = " ".join(lemma.casefold().split())
        if _contains_vietnamese_phrase(folded_text, folded_lemma):
            tokens.append(LemmaToken(surface=lemma, lemma=lemma, pos="", analyzer="reference:vi"))
    return tokens


def _contains_vietnamese_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase)
    return re.search(rf"(?<!\w){escaped}(?!\w)", text, flags=re.UNICODE) is not None


def _stopword_key(lower: str, language: str) -> str:
    if language == "tr":
        return _turkish_normalize(lower)
    return lower


def _strip_diacritics(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", value) if not unicodedata.combining(ch))


def _should_keep(lemma: str, language: str) -> bool:
    normalized = lemma.casefold()
    if normalized in STOPWORDS.get(language, set()):
        return False
    return not PUNCT_OR_NUMBER_RE.match(lemma)
