from __future__ import annotations

from kiwipiepy import Kiwi

from lemmatizer.config import LEMMA_OVERRIDES
from lemmatizer.models import LemmaToken
from lemmatizer.reference import ReferenceSnapper


def lemmatize_korean(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    parsed = Kiwi().tokenize(text)
    tokens = []
    index = 0
    while index < len(parsed):
        token = parsed[index]
        if (
            index + 1 < len(parsed)
            and _is_adjacent(token, parsed[index + 1])
            and parsed[index + 1].tag in {"XSA", "XSV", "XSA-I"}
            and token.tag in {"XR", "NNG", "NNB"}
        ):
            derived = token.lemma + ("롭다" if parsed[index + 1].tag == "XSA-I" else "하다")
            lemma = snapper.snap(token.form + parsed[index + 1].form, [derived])
            lemma = LEMMA_OVERRIDES.get("kr", {}).get(lemma, lemma)
            tokens.append(LemmaToken(surface=token.form + parsed[index + 1].form, lemma=lemma, pos=token.tag, analyzer="kiwi"))
            index += 2
            continue
        if token.tag == "XPN" and index + 1 < len(parsed) and parsed[index + 1].tag.startswith("N"):
            surface = token.form + parsed[index + 1].form
            tokens.append(LemmaToken(surface=surface, lemma=surface, pos=token.tag, analyzer="kiwi"))
            index += 2
            continue
        if _can_merge_korean_reference_compound(parsed, index, snapper):
            surface, lemma, next_index = _merge_korean_reference_compound(parsed, index, snapper)
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=token.tag, analyzer="kiwi"))
            index = next_index
            continue
        if token.tag.startswith("N") and token.tag != "NP":
            surface = token.form
            lemma = token.lemma
            j = index + 1
            while j < len(parsed) and _is_adjacent(parsed[j - 1], parsed[j]):
                if parsed[j].tag == "XSN" and parsed[j].form == "들":
                    j += 1
                    continue
                if not (parsed[j].tag.startswith("N") or parsed[j].tag in {"XSN", "XSV"}):
                    break
                surface += parsed[j].form
                lemma += parsed[j].lemma
                j += 1
            resolved = snapper.snap(surface, [lemma])
            resolved = LEMMA_OVERRIDES.get("kr", {}).get(resolved, resolved)
            tokens.append(LemmaToken(surface=surface, lemma=resolved, pos=token.tag, analyzer="kiwi"))
            index = j
            continue
        known_verb_chain = _korean_known_verb_chain(parsed, index)
        if known_verb_chain:
            surface, lemma, next_index = known_verb_chain
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=token.tag, analyzer="kiwi:known-chain"))
            index = next_index
            continue
        if token.tag == "MAG" and index + 1 < len(parsed) and parsed[index + 1].tag == "XSV" and _is_adjacent(token, parsed[index + 1]):
            suffix = parsed[index + 1].lemma
            lemma = token.lemma + (suffix if suffix.endswith("다") else suffix + "다")
            tokens.append(LemmaToken(surface=token.form + parsed[index + 1].form, lemma=lemma, pos=token.tag, analyzer="kiwi:compound"))
            index += 2
            continue
        if _is_nominalized_adjective(parsed, index):
            surface = _nominalized_adjective_surface(token, parsed[index + 1])
            tokens.append(LemmaToken(surface=surface, lemma=surface, pos=token.tag, analyzer="kiwi"))
            index += 2
            continue
        verb_chain = _korean_reference_verb_chain(parsed, index, snapper)
        if verb_chain:
            surface, lemma, next_index = verb_chain
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=token.tag, analyzer="kiwi:reference"))
            index = next_index
            continue
        if token.tag.startswith("VV") or token.tag in {"VA", "VA-I", "VX", "MAG"}:
            candidates = [token.lemma, _korean_adverb_to_adjective(token), *_korean_verb_chain_candidates(parsed, index)]
            if token.tag == "MAG":
                candidates = [_korean_adverb_to_adjective(token), token.lemma, *_korean_verb_chain_candidates(parsed, index)]
            lemma = snapper.snap(token.form, candidates)
            lemma = LEMMA_OVERRIDES.get("kr", {}).get(lemma, lemma)
            if lemma not in {"이다", "나"}:
                tokens.append(LemmaToken(surface=token.form, lemma=lemma, pos=token.tag, analyzer="kiwi"))
        index += 1
    return tokens


def _is_adjacent(left: object, right: object) -> bool:
    return right.start == left.start + len(left.form)


def _can_merge_korean_reference_compound(parsed: list[object], index: int, snapper: ReferenceSnapper) -> bool:
    if not snapper.vocabulary:
        return False
    if index + 1 >= len(parsed):
        return False
    token = parsed[index]
    following = parsed[index + 1]
    if token.tag.startswith("N") and following.tag.startswith("N") and _is_adjacent(token, following):
        return token.lemma + following.lemma in snapper.vocabulary
    if token.tag in {"MAG", "NNG"} and following.tag.startswith("N") and _is_adjacent(token, following):
        return token.lemma + following.lemma in snapper.vocabulary
    if token.tag == "MAG" and following.tag == "XSV" and _is_adjacent(token, following):
        return token.lemma + following.lemma in snapper.vocabulary
    if token.tag in {"VV", "VA", "VA-I"} and following.tag in {"VV", "VA", "VA-I"}:
        return token.lemma.removesuffix("다") + following.lemma in snapper.vocabulary
    return False


def _merge_korean_reference_compound(parsed: list[object], index: int, snapper: ReferenceSnapper) -> tuple[str, str, int]:
    token = parsed[index]
    following = parsed[index + 1]
    surface = token.form + following.form
    if token.tag.startswith("N") and following.tag.startswith("N"):
        lemma = token.lemma + following.lemma
    elif token.tag in {"MAG", "NNG"} and following.tag.startswith("N"):
        lemma = token.lemma + following.lemma
    elif token.tag == "MAG" and following.tag == "XSV":
        lemma = token.lemma + following.lemma
    else:
        lemma = token.lemma.removesuffix("다") + following.lemma
    return surface, snapper.snap(surface, [lemma]), index + 2


def _korean_verb_chain_candidates(parsed: list[object], index: int) -> list[str]:
    token = parsed[index]
    candidates = []
    if index + 2 < len(parsed) and parsed[index + 1].tag == "EC" and parsed[index + 2].tag == "VX":
        stem = token.lemma.removesuffix("다")
        candidates.append(stem + parsed[index + 2].lemma)
        candidates.append(_contract_korean_stem(stem, parsed[index + 1].form) + parsed[index + 2].lemma)
    if index + 2 < len(parsed) and parsed[index + 1].tag == "EC" and parsed[index + 2].tag == "VV":
        stem = token.lemma.removesuffix("다")
        candidates.append(stem + parsed[index + 1].form + parsed[index + 2].lemma)
        candidates.append(_contract_korean_stem(stem, parsed[index + 1].form) + parsed[index + 2].lemma)
    return candidates


def _korean_reference_verb_chain(
    parsed: list[object], index: int, snapper: ReferenceSnapper
) -> tuple[str, str, int] | None:
    if not snapper.vocabulary or index + 2 >= len(parsed):
        return None
    if parsed[index].tag not in {"VV", "VA", "VA-I"} or parsed[index + 1].tag != "EC":
        return None
    if parsed[index + 2].tag not in {"VV", "VX"}:
        return None
    surface = parsed[index].form + parsed[index + 1].form + parsed[index + 2].form
    for candidate in _korean_verb_chain_candidates(parsed, index):
        lemma = snapper.snap(surface, [candidate])
        if lemma in snapper.vocabulary:
            return surface, lemma, index + 3
    return None


def _korean_known_verb_chain(parsed: list[object], index: int) -> tuple[str, str, int] | None:
    if index + 2 >= len(parsed):
        return None
    for candidate in _korean_verb_chain_candidates(parsed, index):
        lemma = LEMMA_OVERRIDES.get("kr", {}).get(candidate)
        if lemma:
            surface = parsed[index].form + parsed[index + 1].form + parsed[index + 2].form
            return surface, lemma, index + 3
    return None


def _contract_korean_stem(stem: str, ending: str) -> str:
    if ending != "어":
        return stem + ending
    if stem.endswith("리"):
        return stem[:-1] + "려"
    return stem + ending


def _korean_adverb_to_adjective(token: object) -> str:
    if token.tag != "MAG":
        return ""
    if token.form.endswith("히"):
        return token.form[:-1] + "하다"
    if token.form.endswith("이"):
        return token.form[:-1] + "다"
    return ""


def _is_nominalized_adjective(parsed: list[object], index: int) -> bool:
    return (
        index + 1 < len(parsed)
        and parsed[index].tag in {"VA", "VA-I"}
        and parsed[index + 1].tag == "ETN"
        and _is_adjacent(parsed[index], parsed[index + 1])
    )


def _nominalized_adjective_surface(token: object, ending: object) -> str:
    if token.form.endswith("답") and ending.form == "음":
        return token.form[:-1] + "다움"
    return token.form + ending.form
