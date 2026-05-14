from __future__ import annotations

from difflib import SequenceMatcher
import unicodedata

from pyarabic import araby

from lemmatizer.text_utils import PUNCT_OR_NUMBER_RE


class ReferenceSnapper:
    def __init__(self, language: str, reference_lemmas: tuple[str, ...] | list[str] | set[str]):
        self.language = language
        self.vocabulary = tuple(reference_lemmas)
        self.by_normalized = {normalize(item, language): item for item in self.vocabulary}

    def snap(self, surface: str, candidates: list[str]) -> str:
        clean_candidates = [item for item in candidates if item and not PUNCT_OR_NUMBER_RE.match(item)]
        for candidate in [surface, *clean_candidates]:
            if candidate in self.vocabulary:
                return candidate
            normalized = normalize(candidate, self.language)
            if normalized in self.by_normalized:
                return self.by_normalized[normalized]
        if not self.vocabulary:
            return clean_candidates[0] if clean_candidates else surface
        best = None
        best_score = 0.0
        for candidate in [surface, *clean_candidates]:
            normalized_candidate = normalize(candidate, self.language)
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


def normalize(value: str, language: str) -> str:
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
