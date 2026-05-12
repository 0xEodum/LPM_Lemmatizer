from __future__ import annotations

from fugashi import Tagger

from lemmatizer.config import JAPANESE_COMPOUND_SUFFIXES, LEMMA_OVERRIDES
from lemmatizer.models import LemmaToken
from lemmatizer.reference import ReferenceSnapper


JA_NOUN = "\u540d\u8a5e"
JA_VERB = "\u52d5\u8a5e"
JA_ADJ = "\u5f62\u5bb9\u8a5e"
JA_ADV = "\u526f\u8a5e"
JA_ADJECTIVAL_NOUN = "\u5f62\u72b6\u8a5e"
JA_ADNOMINAL = "\u9023\u4f53\u8a5e"
JA_PREFIX = "\u63a5\u982d\u8f9e"
JA_SUFFIX = "\u63a5\u5c3e\u8f9e"
JA_PRONOUN = "\u4ee3\u540d\u8a5e"


def lemmatize_japanese(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    parsed = list(Tagger()(text))
    tokens = []
    index = 0
    while index < len(parsed):
        word = parsed[index]
        feature = word.feature
        reference_compound = _japanese_reference_compound(parsed, index, snapper)
        if reference_compound:
            surface, lemma, next_index = reference_compound
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=feature.pos1, analyzer="fugashi:reference"))
            index = next_index
            continue
        if _is_japanese_auxiliary_noun(parsed, index):
            index += 1
            continue
        if feature.pos1 in {JA_NOUN, JA_PREFIX}:
            surface_parts = [word.surface]
            lemma_parts = [_lemma_or_surface(word)]
            j = index + 1
            while j < len(parsed) and _can_continue_japanese_noun_compound(parsed, j):
                surface_parts.append(parsed[j].surface)
                lemma_parts.append(_lemma_or_surface(parsed[j]))
                j += 1
            surface = "".join(surface_parts)
            lemma = snapper.snap(surface, [_japanese_surface_noun(surface), surface, "".join(lemma_parts)])
            lemma = LEMMA_OVERRIDES.get("jp", {}).get(lemma, lemma)
            if lemma != "\u70ba":
                tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=JA_NOUN, analyzer="fugashi"))
            index = j
            continue
        if feature.pos1 == JA_VERB:
            if _is_particle_expression(parsed, index):
                index += 2
                continue
            if (
                index + 1 < len(parsed)
                and parsed[index + 1].surface == "\u305a"
                and word.surface + parsed[index + 1].surface in snapper.vocabulary
            ):
                tokens.append(
                    LemmaToken(
                        surface=word.surface + parsed[index + 1].surface,
                        lemma=word.surface + parsed[index + 1].surface,
                        pos=JA_ADV,
                        analyzer="fugashi:reference",
                    )
                )
                index += 2
                continue
            candidates = [_lemma_or_surface(word), word.surface]
            if word.surface == "\u3067\u304d":
                candidates.insert(0, "\u3067\u304d\u308b")
            if word.surface.endswith("\u3093"):
                candidates.insert(0, word.surface[:-1] + "\u3080")
            if index + 1 < len(parsed) and parsed[index + 1].feature.pos1 == JA_VERB:
                candidates.insert(0, word.surface + _lemma_or_surface(parsed[index + 1]))
            lemma = snapper.snap(word.surface, candidates)
            lemma = LEMMA_OVERRIDES.get("jp", {}).get(lemma, lemma)
            if lemma not in {"居る", "呉れる", "来る"}:
                tokens.append(LemmaToken(surface=word.surface, lemma=lemma, pos=JA_VERB, analyzer="fugashi"))
            if index + 1 < len(parsed) and parsed[index + 1].feature.pos1 == JA_VERB:
                index += 2
                continue
        elif feature.pos1 in {JA_ADJ, JA_ADV, JA_ADJECTIVAL_NOUN, JA_ADNOMINAL}:
            if word.surface == "\u3053\u306e":
                index += 1
                continue
            if index + 1 < len(parsed) and parsed[index + 1].feature.pos1 == JA_SUFFIX:
                surface = word.surface + parsed[index + 1].surface
                tokens.append(LemmaToken(surface=surface, lemma=surface, pos=feature.pos1, analyzer="fugashi"))
                index += 2
                continue
            lemma = snapper.snap(word.surface, [_japanese_surface_adjective(word.surface), word.surface, _lemma_or_surface(word)])
            lemma = LEMMA_OVERRIDES.get("jp", {}).get(lemma, lemma)
            tokens.append(LemmaToken(surface=word.surface, lemma=lemma, pos=feature.pos1, analyzer="fugashi"))
        index += 1
    return tokens


def _lemma_or_surface(word: object) -> str:
    lemma = getattr(word.feature, "lemma", "")
    return lemma if lemma and lemma != "*" else word.surface


def _can_continue_japanese_noun_compound(parsed: list[object], index: int) -> bool:
    feature = parsed[index].feature
    if feature.pos1 == JA_SUFFIX:
        return True
    if feature.pos1 != JA_NOUN:
        return False
    if feature.pos2 == JA_PRONOUN:
        return False
    previous = parsed[index - 1].surface if index > 0 else ""
    current = parsed[index].surface
    if previous in {"暗号化", "電子"} or current in JAPANESE_COMPOUND_SUFFIXES:
        return True
    return len(current) <= 2 and current.isascii()


def _japanese_reference_compound(
    parsed: list[object], index: int, snapper: ReferenceSnapper
) -> tuple[str, str, int] | None:
    if not snapper.vocabulary:
        return None
    allowed = {JA_NOUN, JA_PREFIX, JA_SUFFIX, JA_ADJECTIVAL_NOUN, JA_ADNOMINAL}
    best = None
    surface = ""
    for j in range(index, min(index + 5, len(parsed))):
        if parsed[j].feature.pos1 not in allowed:
            break
        surface += parsed[j].surface
        if surface in snapper.vocabulary:
            best = (surface, surface, j + 1)
    return best


def _is_japanese_auxiliary_noun(parsed: list[object], index: int) -> bool:
    surface = parsed[index].surface
    if surface != "\u3053\u3068":
        return False
    return index > 0 and parsed[index - 1].feature.pos1 == JA_VERB


def _is_particle_expression(parsed: list[object], index: int) -> bool:
    if parsed[index].surface not in {"とっ", "取っ"}:
        return False
    if index == 0 or parsed[index - 1].surface != "に":
        return False
    return index + 1 < len(parsed) and parsed[index + 1].surface == "て"


def _japanese_surface_adjective(surface: str) -> str:
    if surface == "\u5c0f\u3055\u306a":
        return "\u5c0f\u3055\u3044"
    if surface.endswith("\u306b"):
        return surface[:-1]
    if surface.endswith("\u304f"):
        return surface[:-1] + "\u3044"
    return surface


def _japanese_surface_noun(surface: str) -> str:
    if surface.endswith("\u304f"):
        return surface[:-1] + "\u3044"
    return surface
