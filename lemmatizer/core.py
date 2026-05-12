from __future__ import annotations

from pathlib import Path

from lemmatizer.analyzers import lemmatize_arabic, lemmatize_japanese, lemmatize_korean, lemmatize_simple
from lemmatizer.analyzers.stanza_backend import lemmatize_text_stanza
from lemmatizer.config import PREFIX_TO_LANGUAGE
from lemmatizer.io import discover_text_files, parse_lemma_list
from lemmatizer.models import LemmaReport
from lemmatizer.reference import normalize
from lemmatizer.reference import ReferenceSnapper
from lemmatizer.text_utils import unique


def lemmatize_pair(
    text_path: Path,
    expected_path: Path | None = None,
    *,
    language: str | None = None,
    use_reference: bool = False,
    backend: str = "current",
) -> LemmaReport:
    prefix = text_path.name.removesuffix("_text.txt")
    resolved_language = language or PREFIX_TO_LANGUAGE.get(prefix, prefix)
    expected = parse_lemma_list(expected_path) if expected_path else ()
    text = text_path.read_text(encoding="utf-8")
    if backend == "stanza":
        report = lemmatize_text_stanza(text, resolved_language)
    elif backend == "hybrid":
        report = lemmatize_text_hybrid(text, resolved_language, reference_lemmas=expected if use_reference else ())
    else:
        report = lemmatize_text(text, resolved_language, reference_lemmas=expected if use_reference else ())
    if not expected:
        return report
    expected_set = {_metric_key(item, report.language) for item in expected}
    predicted_set = {_metric_key(item, report.language) for item in report.unique_lemmas}
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
        tokens = tuple(lemmatize_simple(text, language, snapper))
    elif language == "ar":
        tokens = tuple(lemmatize_arabic(text, snapper))
    elif language == "jp":
        tokens = tuple(lemmatize_japanese(text, snapper))
    elif language == "kr":
        tokens = tuple(lemmatize_korean(text, snapper))
    else:
        raise ValueError(f"Unsupported language: {language}")
    return LemmaReport(language=language, tokens=tokens, unique_lemmas=unique(token.lemma for token in tokens))


def _metric_key(value: str, language: str) -> str:
    if language == "ar":
        return normalize(value, language)
    return value


def lemmatize_text_hybrid(
    text: str,
    language: str,
    *,
    reference_lemmas: tuple[str, ...] | list[str] | set[str] = (),
) -> LemmaReport:
    language = PREFIX_TO_LANGUAGE.get(language, language)
    if language in {"de", "fr", "hy"}:
        return lemmatize_text_stanza(text, language)
    return lemmatize_text(text, language, reference_lemmas=reference_lemmas)


__all__ = [
    "LemmaReport",
    "ReferenceSnapper",
    "discover_text_files",
    "lemmatize_pair",
    "lemmatize_text",
    "lemmatize_text_hybrid",
    "parse_lemma_list",
]
