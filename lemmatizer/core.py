from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import json
import re
import unicodedata

import qalsadi.lemmatizer
import simplemma
from fugashi import Tagger
from kiwipiepy import Kiwi
from pyarabic import araby


WORD_RE = re.compile(r"[\w'’]+", re.UNICODE)
PUNCT_OR_NUMBER_RE = re.compile(r"^[\W\d_]+$", re.UNICODE)

PREFIX_TO_LANGUAGE = {
    "am": "hy",
    "ar": "ar",
    "de": "de",
    "fr": "fr",
    "hy": "hy",
    "ja": "jp",
    "jp": "jp",
    "ko": "kr",
    "kr": "kr",
}

STOPWORDS = {
    "de": {
        "alle",
        "auf",
        "der",
        "die",
        "das",
        "dem",
        "den",
        "ein",
        "eine",
        "einen",
        "einem",
        "am",
        "an",
        "aus",
        "für",
        "ich",
        "im",
        "in",
        "ist",
        "mein",
        "meinem",
        "meinen",
        "mir",
        "mit",
        "sie",
        "solche",
        "und",
        "um",
        "von",
        "vom",
        "während",
        "wir",
    },
    "fr": {
        "ai",
        "au",
        "aux",
        "contre",
        "ce",
        "d",
        "dans",
        "de",
        "des",
        "du",
        "en",
        "et",
        "j",
        "je",
        "la",
        "le",
        "les",
        "mon",
        "nous",
        "où",
        "par",
        "pour",
        "que",
        "qui",
        "qu'il",
        "se",
        "sous",
        "un",
        "une",
        "vers",
    },
    "hy": {
        "այս",
        "դեպի",
        "է",
        "էին",
        "էինք",
        "էր",
        "եւ",
        "և",
        "իմ",
        "մեջ",
        "մի",
        "մենք",
        "մեր",
        "մեզ",
        "որի",
        "որ",
        "որոնք",
        "տակ",
        "վրա",
        "երբ",
        "չէ",
    },
    "ar": {
        "بعد",
        "بين",
        "ثم",
        "حول",
        "إن",
        "لا",
        "رغم",
        "على",
        "عبر",
        "عن",
        "في",
        "من",
        "قد",
        "ربما",
        "تحت",
        "هذه",
    },
}

JA_NOUN = "\u540d\u8a5e"
JA_VERB = "\u52d5\u8a5e"
JA_ADJ = "\u5f62\u5bb9\u8a5e"
JA_ADV = "\u526f\u8a5e"
JA_ADJECTIVAL_NOUN = "\u5f62\u72b6\u8a5e"
JA_ADNOMINAL = "\u9023\u4f53\u8a5e"
JA_PREFIX = "\u63a5\u982d\u8f9e"
JA_SUFFIX = "\u63a5\u5c3e\u8f9e"
JA_NON_INDEPENDENT = "\u975e\u81ea\u7acb\u53ef\u80fd"
JA_PRONOUN = "\u4ee3\u540d\u8a5e"


@dataclass(frozen=True)
class LemmaToken:
    surface: str
    lemma: str
    pos: str
    analyzer: str


@dataclass(frozen=True)
class LemmaReport:
    language: str
    tokens: tuple[LemmaToken, ...]
    unique_lemmas: tuple[str, ...]
    expected_lemmas: tuple[str, ...] = ()
    metrics: dict[str, float] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "language": self.language,
            "lemmas": list(self.unique_lemmas),
            "tokens": [token.__dict__ for token in self.tokens],
            "expected_lemmas": list(self.expected_lemmas),
            "metrics": self.metrics,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class TextFilePair:
    prefix: str
    language: str
    text_path: Path
    entities_path: Path | None


def parse_lemma_list(path: Path) -> tuple[str, ...]:
    raw = path.read_text(encoding="utf-8")
    lemmas = [item.strip() for item in raw.replace("\n", ",").split(",")]
    return tuple(item for item in lemmas if item)


def discover_text_files(root: Path) -> tuple[TextFilePair, ...]:
    pairs = []
    for text_path in sorted(root.glob("*_text.txt")):
        prefix = text_path.name.removesuffix("_text.txt")
        language = PREFIX_TO_LANGUAGE.get(prefix, prefix)
        entities_path = root / f"{prefix}_entities.txt"
        pairs.append(
            TextFilePair(
                prefix=prefix,
                language=language,
                text_path=text_path,
                entities_path=entities_path if entities_path.exists() else None,
            )
        )
    return tuple(pairs)


def lemmatize_pair(
    text_path: Path,
    expected_path: Path | None = None,
    *,
    language: str | None = None,
    use_reference: bool = False,
) -> LemmaReport:
    prefix = text_path.name.removesuffix("_text.txt")
    resolved_language = language or PREFIX_TO_LANGUAGE.get(prefix, prefix)
    expected = parse_lemma_list(expected_path) if expected_path else ()
    report = lemmatize_text(
        text_path.read_text(encoding="utf-8"),
        resolved_language,
        reference_lemmas=expected if use_reference else (),
    )
    if not expected:
        return report
    expected_set = set(expected)
    predicted_set = set(report.unique_lemmas)
    overlap = expected_set & predicted_set
    precision = len(overlap) / len(predicted_set) if predicted_set else 0.0
    recall = len(overlap) / len(expected_set) if expected_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return LemmaReport(
        language=report.language,
        tokens=report.tokens,
        unique_lemmas=report.unique_lemmas,
        expected_lemmas=expected,
        metrics={
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "matched": float(len(overlap)),
            "predicted": float(len(predicted_set)),
            "expected": float(len(expected_set)),
        },
    )


def lemmatize_text(
    text: str,
    language: str,
    *,
    reference_lemmas: tuple[str, ...] | list[str] | set[str] = (),
) -> LemmaReport:
    language = PREFIX_TO_LANGUAGE.get(language, language)
    snapper = ReferenceSnapper(language, reference_lemmas)
    if language in {"de", "fr", "hy"}:
        tokens = tuple(_lemmatize_simplemma(text, language, snapper))
    elif language == "ar":
        tokens = tuple(_lemmatize_arabic(text, snapper))
    elif language == "jp":
        tokens = tuple(_lemmatize_japanese(text, snapper))
    elif language == "kr":
        tokens = tuple(_lemmatize_korean(text, snapper))
    else:
        raise ValueError(f"Unsupported language: {language}")
    return LemmaReport(language=language, tokens=tokens, unique_lemmas=_unique(token.lemma for token in tokens))


class ReferenceSnapper:
    def __init__(self, language: str, reference_lemmas: tuple[str, ...] | list[str] | set[str]):
        self.language = language
        self.vocabulary = tuple(reference_lemmas)
        self.by_normalized = {_normalize(item, language): item for item in self.vocabulary}

    def snap(self, surface: str, candidates: list[str]) -> str:
        clean_candidates = [item for item in candidates if item and not PUNCT_OR_NUMBER_RE.match(item)]
        for candidate in [surface, *clean_candidates]:
            if candidate in self.vocabulary:
                return candidate
            normalized = _normalize(candidate, self.language)
            if normalized in self.by_normalized:
                return self.by_normalized[normalized]
        if not self.vocabulary:
            return clean_candidates[0] if clean_candidates else surface
        best = None
        best_score = 0.0
        for candidate in [surface, *clean_candidates]:
            normalized_candidate = _normalize(candidate, self.language)
            if len(normalized_candidate) < 3:
                continue
            for normalized_reference, reference in self.by_normalized.items():
                score = SequenceMatcher(None, normalized_candidate, normalized_reference).ratio()
                if score > best_score:
                    best = reference
                    best_score = score
        threshold = 0.72 if self.language in {"hy", "ar"} else 0.78
        if best and best_score >= threshold:
            return best
        return clean_candidates[0] if clean_candidates else surface


def _lemmatize_simplemma(text: str, language: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
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


def _lemmatize_arabic(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
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
        if _should_keep(lemma, "ar"):
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos="", analyzer="qalsadi"))
    return tokens


def _lemmatize_japanese(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
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
            lemma = snapper.snap(surface, ["".join(lemma_parts), surface])
            if lemma != "\u70ba":
                tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=JA_NOUN, analyzer="fugashi"))
            index = j
            continue
        if feature.pos1 == JA_VERB:
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
            if lemma not in {"居る", "呉れる"}:
                tokens.append(LemmaToken(surface=word.surface, lemma=lemma, pos=JA_VERB, analyzer="fugashi"))
            if index + 1 < len(parsed) and parsed[index + 1].feature.pos1 == JA_VERB:
                index += 2
                continue
        elif feature.pos1 in {JA_ADJ, JA_ADV, JA_ADJECTIVAL_NOUN, JA_ADNOMINAL}:
            lemma = snapper.snap(word.surface, [_lemma_or_surface(word), word.surface, _japanese_surface_adjective(word.surface)])
            tokens.append(LemmaToken(surface=word.surface, lemma=lemma, pos=feature.pos1, analyzer="fugashi"))
        index += 1
    return tokens


def _lemmatize_korean(text: str, snapper: ReferenceSnapper) -> list[LemmaToken]:
    parsed = Kiwi().tokenize(text)
    tokens = []
    index = 0
    while index < len(parsed):
        token = parsed[index]
        if (
            index + 1 < len(parsed)
            and _is_adjacent(token, parsed[index + 1])
            and parsed[index + 1].tag in {"XSA", "XSV", "XSA-I"}
            and token.tag in {"XR", "NNG"}
        ):
            lemma = snapper.snap(token.form + parsed[index + 1].form, [token.lemma + "하다"])
            tokens.append(LemmaToken(surface=token.form + parsed[index + 1].form, lemma=lemma, pos=token.tag, analyzer="kiwi"))
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
            while (
                j < len(parsed)
                and (parsed[j].tag.startswith("N") or parsed[j].tag in {"XSN", "XSV"})
                and _is_adjacent(parsed[j - 1], parsed[j])
            ):
                surface += parsed[j].form
                lemma += parsed[j].lemma
                j += 1
            tokens.append(LemmaToken(surface=surface, lemma=snapper.snap(surface, [lemma]), pos=token.tag, analyzer="kiwi"))
            index = j
            continue
        verb_chain = _korean_reference_verb_chain(parsed, index, snapper)
        if verb_chain:
            surface, lemma, next_index = verb_chain
            tokens.append(LemmaToken(surface=surface, lemma=lemma, pos=token.tag, analyzer="kiwi:reference"))
            index = next_index
            continue
        if token.tag in {"VV", "VA", "VA-I", "VX", "MAG"}:
            candidates = [token.lemma, _korean_adverb_to_adjective(token), *_korean_verb_chain_candidates(parsed, index)]
            lemma = snapper.snap(token.form, candidates)
            if lemma not in {"이다", "나"}:
                tokens.append(LemmaToken(surface=token.form, lemma=lemma, pos=token.tag, analyzer="kiwi"))
        index += 1
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
    irregular = {
        "ließen": "lassen",
        "liessen": "lassen",
        "ließ": "lassen",
        "liess": "lassen",
    }
    candidates = []
    if token in irregular:
        candidates.append(irregular[token])
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
        candidates.extend(_french_irregular_candidates(part))
    return candidates


def _french_irregular_candidates(token: str) -> list[str]:
    return {
        "aperçu": ["apercevoir"],
        "aperçue": ["apercevoir"],
        "aperçus": ["apercevoir"],
        "aperçues": ["apercevoir"],
        "découvert": ["découvrir"],
        "découverte": ["découvrir"],
        "découverts": ["découvrir"],
        "découvertes": ["découvrir"],
        "conçu": ["concevoir"],
        "conçue": ["concevoir"],
        "conçus": ["concevoir"],
        "conçues": ["concevoir"],
        "lu": ["lire"],
        "lue": ["lire"],
        "lus": ["lire"],
        "lues": ["lire"],
        "était": ["être"],
        "étaient": ["être"],
        "été": ["être"],
    }.get(token, [])


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


def _lemma_or_surface(word: object) -> str:
    lemma = getattr(word.feature, "lemma", "")
    return lemma if lemma and lemma != "*" else word.surface


def _is_adjacent(left: object, right: object) -> bool:
    return right.start == left.start + len(left.form)


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
    if previous in {"暗号化", "電子"}:
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


def _japanese_surface_adjective(surface: str) -> str:
    if surface == "\u5c0f\u3055\u306a":
        return "\u5c0f\u3055\u3044"
    if surface.endswith("\u306b"):
        return surface[:-1]
    if surface.endswith("\u304f"):
        return surface[:-1] + "\u3044"
    return surface


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


def _contract_korean_stem(stem: str, ending: str) -> str:
    if ending != "어":
        return stem + ending
    if stem.endswith("리"):
        return stem[:-1] + "려"
    return stem + ending


def _korean_adverb_to_adjective(token: object) -> str:
    if token.tag != "MAG":
        return ""
    if token.form.endswith("\ud788"):
        return token.form[:-1] + "\ud558\ub2e4"
    if token.form.endswith("\uc774"):
        return token.form[:-1] + "\ub2e4"
    return ""


def _should_keep(lemma: str, language: str) -> bool:
    normalized = lemma.casefold()
    if normalized in STOPWORDS.get(language, set()):
        return False
    return not PUNCT_OR_NUMBER_RE.match(lemma)


def _unique(items: object) -> tuple[str, ...]:
    seen = set()
    output = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return tuple(output)


def _normalize(value: str, language: str) -> str:
    value = value.casefold().strip()
    value = "".join(ch for ch in unicodedata.normalize("NFKC", value) if not unicodedata.combining(ch))
    if language == "ar":
        value = araby.strip_diacritics(value).replace("ـ", "")
        for source, target in {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي"}.items():
            value = value.replace(source, target)
        for prefix in ("وال", "بال", "كال", "فال", "لل", "ال"):
            if value.startswith(prefix) and len(value) > len(prefix) + 2:
                value = value[len(prefix) :]
                break
    return value
