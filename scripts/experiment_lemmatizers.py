from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lemmatizer import UniversalLemmatizer, normalize_language
from lemmatizer.backends.simplemma_backend import SimplemmaBackend
from lemmatizer.models import LemmaToken
from lemmatizer.text import PUNCT_OR_NUMBER_RE, clean_lemma, is_usable_lemma


@dataclass(frozen=True, slots=True)
class Probe:
    language: str
    label: str
    expected_any: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateResult:
    candidate: str
    language: str
    supported: bool
    elapsed_seconds: float
    warmed_elapsed_seconds: float
    passed: int
    total: int
    error: str
    unique_lemmas: tuple[str, ...]
    failed_probes: tuple[dict[str, object], ...]


class Candidate(Protocol):
    name: str

    def supports(self, language: str) -> bool:
        ...

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        ...


CONTENT_LANGUAGES = {
    "be",
    "bg",
    "cs",
    "da",
    "de",
    "en",
    "es",
    "et",
    "fi",
    "fr",
    "he",
    "hr",
    "hy",
    "id",
    "it",
    "ja",
    "ko",
    "lv",
    "nb",
    "pt",
    "sk",
    "sv",
    "tr",
    "uk",
    "zh",
}

STANZA_CODES = {
    "be": "be",
    "bg": "bg",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "en": "en",
    "es": "es",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "he": "he",
    "hr": "hr",
    "hy": "hy",
    "id": "id",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "lv": "lv",
    "nb": "no",
    "pt": "pt",
    "ru": "ru",
    "sk": "sk",
    "sv": "sv",
    "tr": "tr",
    "uk": "uk",
    "zh": "zh",
}

STANZA_PROCESSORS = {
    "de": "tokenize,mwt,pos,lemma",
    "es": "tokenize,mwt,pos,lemma",
    "fr": "tokenize,mwt,pos,lemma",
    "pt": "tokenize,mwt,pos,lemma",
}

UDPIPE_CODES = {
    "nb": "nb",
    **{code: code for code in CONTENT_LANGUAGES | {"ru"}},
}

SPACY_MODELS = {
    "da": "da_core_news_sm",
    "de": "de_core_news_sm",
    "en": "en_core_web_sm",
    "es": "es_core_news_sm",
    "fi": "fi_core_news_sm",
    "fr": "fr_core_news_sm",
    "hr": "hr_core_news_sm",
    "it": "it_core_news_sm",
    "ja": "ja_core_news_sm",
    "ko": "ko_core_news_sm",
    "nb": "nb_core_news_sm",
    "pt": "pt_core_news_sm",
    "sv": "sv_core_news_sm",
    "uk": "uk_core_news_sm",
    "zh": "zh_core_web_sm",
}

PROBES = (
    Probe("he", "customers plural with attached preposition", ("לקוח",), ("קוח",)),
    Probe("he", "vegetables with conjunction", ("ירק",), ("וירקות",)),
    Probe("he", "pitas plural", ("פיתה",), ("פיתות",)),
    Probe("hy", "Armenia definite article", ("հայաստան",), ("հայաստանը",)),
    Probe("hy", "mountains genitive plural", ("լեռ",), ("լեռների",)),
    Probe("hy", "mountain definite article", ("լեռ",), ("լեռը",)),
    Probe("be", "secrets genitive plural", ("таямніца",), ("таямніц",)),
    Probe("be", "nature genitive", ("прырода",), ("прырады",)),
    Probe("bg", "grill noun not verb", ("скара",), ("скарам",)),
    Probe("bg", "masculine cheerful adjective", ("весел",), ("весели",)),
    Probe("bg", "blooming verb", ("цъфтя",), ("цъфтят",)),
    Probe("zh", "street should be segmented", ("街道",), ("街道上会", "上会")),
    Probe("zh", "this-is should split", ("这", "是"), ("这是",)),
    Probe("hr", "islands genitive plural", ("otok",), ("otoka",)),
    Probe("hr", "no Serbian Cyrillic leakage", (), ("за", "не")),
    Probe("cs", "unforgettable keeps negative prefix", ("nezapomenutelný",), ("zapomenutelný",)),
    Probe("cs", "lighting verb infinitive", ("rozsvěcovat",), ("rozsvěcují",)),
    Probe("cs", "clock striking verb infinitive", ("odbíjet",), ("odbíjí",)),
    Probe("cs", "cup diminutive", ("šálek",), ("šálka",)),
    Probe("da", "does as infinitive", ("gøre",), ("gø",)),
    Probe("da", "create as infinitive", ("skabe",), ("skab",)),
    Probe("da", "warm adjective", ("varm",), ("varme",)),
    Probe("da", "dark adjective", ("mørk",), ("mørke",)),
    Probe("en", "leaves noun", ("leaf",), ("leave",)),
    Probe("en", "felt irregular verb", ("feel",), ()),
    Probe("fr", "tables noun", ("table",), ("tabler",)),
    Probe("fr", "terrace noun", ("terrasse",), ("terrer",)),
    Probe("fr", "reflexive active verb", ("activer", "s'activer"), ("s'active",)),
    Probe("fr", "special adjective masculine", ("spécial",), ("spéciale",)),
    Probe("it", "wood noun not verb", ("legno",), ("legnare",)),
    Probe("it", "superlative adjective", ("profumato",), ("profumatissimo",)),
    Probe("it", "fill verb infinitive", ("riempire",), ("riempie",)),
    Probe("de", "contracted preposition", ("in",), ("im",)),
    Probe("de", "dense adjective", ("dicht",), ("dichten",)),
    Probe("de", "reflexive pronoun", ("sich",), ("er|es|sie",)),
    Probe("et", "cranberries partitive", ("jõhvikas",), ("jõhv",)),
    Probe("et", "walk noun preserved", ("jalutuskäik",), ("jalutu",)),
    Probe("et", "always adverb preserved", ("alati",), ("algama",)),
    Probe("et", "cranes partitive", ("sookurg",), ("sookurgi",)),
    Probe("fi", "jump verb infinitive", ("hypätä",), ("hyppäävä",)),
    Probe("fi", "when not wish particle", ("kun",), ("kunpa",)),
    Probe("fi", "this pronoun", ("tämä",), ("tämän",)),
    Probe("id", "reduplicated fruit", ("buah",), ("buah-buah", "buah-buahan")),
    Probe("id", "prefix removal", ("kepul",), ("mengepul",)),
    Probe("ja", "pink stays katakana", ("ピンク",), ("pink",)),
    Probe("ja", "very stays hiragana", ("とても",), ("迚も",)),
    Probe("ja", "light-up compound", ("ライトアップ",), ()),
    Probe("sk", "small adjective masculine", ("malý",), ("malá",)),
    Probe("sk", "high adjective masculine", ("vysoký",), ("vysoká",)),
    Probe("sk", "good adjective masculine", ("dobrý",), ("dobré",)),
    Probe("es", "colors noun", ("color",), ("colorar",)),
    Probe("es", "greet verb infinitive", ("saludar",), ("saluda",)),
    Probe("pt", "contracted pelo not peel verb", ("por", "pelo"), ("pelar",)),
    Probe("pt", "indefinite article not invented verb", ("um", "uma"), ("umar",)),
    Probe("pt", "dessa not invented verb", ("desse", "essa", "dessa", "de"), ("dessar",)),
    Probe("pt", "cream noun", ("nata",), ("nato",)),
    Probe("sv", "copula infinitive", ("vara",), ("ära",)),
    Probe("sv", "preposition for", ("för",), ("föra",)),
    Probe("sv", "only adverb", ("bara",), ("bar",)),
    Probe("nb", "weather noun", ("vær", "været"), ("være",)),
    Probe("nb", "so adverb", ("så",), ("se",)),
    Probe("nb", "love verb infinitive", ("elske",), ("elsker",)),
    Probe("nb", "pack verb infinitive", ("pakke",), ("pakker",)),
    Probe("nb", "drink verb infinitive", ("drikke",), ("drikker",)),
    Probe("uk", "boundless adjective", ("безкрайній",), ("безкрайніми",)),
    Probe("uk", "garlic adjective", ("часниковий",), ("часниковими",)),
    Probe("uk", "ancestor noun", ("предок",), ("предків",)),
    Probe("uk", "flow verb", ("текти",), ("теча",)),
    Probe("uk", "melodic adjective", ("мелодійний",), ("мелодія",)),
    Probe("lv", "sunrise dative", ("saullēkts",), ("saullēktam",)),
    Probe("lv", "everyone pronoun", ("ikviens",), ("ikvienam",)),
    Probe("lv", "celebrate verb infinitive", ("svinēt",), ("svinētu",)),
    Probe("lv", "wreaths noun", ("vainags",), ("vainaguns",)),
    Probe("tr", "connecting verb infinitive", ("bağlamak",), ("bağla",)),
    Probe("tr", "walking verb infinitive", ("yürümek",), ("yürü",)),
    Probe("tr", "rising verb infinitive", ("yükselmek",), ("yüksel",)),
    Probe("tr", "hearing verb infinitive", ("duymak",), ("duy",)),
    Probe("tr", "unique adjective not antonym root", ("eşsiz",), ("eş",)),
)


class CurrentCandidate:
    name = "current"

    def __init__(self) -> None:
        self._lemmatizer = UniversalLemmatizer()

    def supports(self, language: str) -> bool:
        return self._lemmatizer.supports(language)

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        return self._lemmatizer.lemmatize(text, language).tokens


class SimplemmaCandidate:
    name = "simplemma"

    def __init__(self) -> None:
        self._backend = SimplemmaBackend()

    def supports(self, language: str) -> bool:
        return self._backend.supports(language)

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        return self._backend.lemmatize(text, language)


class StanzaCandidate:
    name = "stanza"

    def __init__(self, download_missing: bool) -> None:
        self._download_missing = download_missing

    def supports(self, language: str) -> bool:
        return language in STANZA_CODES

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        import stanza

        stanza_code = STANZA_CODES[language]
        processors = STANZA_PROCESSORS.get(language, "tokenize,pos,lemma")
        if self._download_missing:
            stanza.download(stanza_code, processors=processors, verbose=False)
        doc = _stanza_pipeline(stanza_code, processors)(text)
        tokens = []
        for sentence in doc.sentences:
            for word in sentence.words:
                lemma = clean_lemma(word.lemma or word.text)
                if is_usable_lemma(lemma):
                    tokens.append(LemmaToken(word.text, lemma, language, self.name, word.upos))
        return tuple(tokens)


class UDPipeCandidate:
    name = "udpipe"

    def __init__(self, download_missing: bool) -> None:
        self._download_missing = download_missing

    def supports(self, language: str) -> bool:
        return language in UDPIPE_CODES

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        from ufal.udpipe import Model, Sentence

        udpipe_code = UDPIPE_CODES[language]
        if self._download_missing:
            _download_udpipe_model(udpipe_code)
        model = _udpipe_model(udpipe_code)
        tokenizer = model.newTokenizer(Model.DEFAULT)
        if tokenizer is None:
            raise RuntimeError(f"UDPipe model for {udpipe_code} has no tokenizer")
        tokenizer.setText(text)
        tokens = []
        sentence = Sentence()
        while tokenizer.nextSentence(sentence):
            model.tag(sentence, Model.DEFAULT)
            for word in sentence.words[1:]:
                lemma = clean_lemma(word.lemma or word.form)
                if not lemma or PUNCT_OR_NUMBER_RE.match(lemma):
                    continue
                tokens.append(LemmaToken(word.form, lemma, language, self.name, word.upostag))
            sentence = Sentence()
        return tuple(tokens)


class SpacyCandidate:
    name = "spacy"

    def __init__(self, download_missing: bool) -> None:
        self._download_missing = download_missing

    def supports(self, language: str) -> bool:
        return language in SPACY_MODELS

    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        model_name = SPACY_MODELS[language]
        if self._download_missing:
            _download_spacy_model(model_name)
        doc = _spacy_pipeline(model_name)(text)
        tokens = []
        for token in doc:
            lemma = clean_lemma(token.lemma_ or token.text)
            if is_usable_lemma(lemma):
                tokens.append(LemmaToken(token.text, lemma, language, self.name, token.pos_))
        return tuple(tokens)


@lru_cache(maxsize=32)
def _stanza_pipeline(language: str, processors: str):
    import stanza

    return stanza.Pipeline(
        lang=language,
        processors=processors,
        download_method=None,
        use_gpu=False,
        verbose=False,
    )


@lru_cache(maxsize=32)
def _udpipe_model(language: str):
    from ufal.udpipe import Model

    path = _udpipe_model_path(language)
    model = Model.load(str(path))
    if model is None:
        raise RuntimeError(f"Could not load UDPipe model: {path}")
    return model


def _download_udpipe_model(language: str) -> None:
    from spacy_udpipe import utils as spacy_udpipe_utils

    path = _udpipe_model_path(language)
    if _looks_like_udpipe_model(path):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    filename = spacy_udpipe_utils.LANGUAGES[language]
    url = "https://raw.githubusercontent.com/jwijffels/udpipe.models.ud.2.5/master/inst/udpipe-ud-2.5-191206/" + filename
    urllib.request.urlretrieve(url=url, filename=path)
    if not _looks_like_udpipe_model(path):
        raise RuntimeError(f"Downloaded UDPipe file is not a valid model: {path}")


def _udpipe_model_path(language: str) -> Path:
    from spacy_udpipe import utils as spacy_udpipe_utils

    return Path(spacy_udpipe_utils.MODELS_DIR) / spacy_udpipe_utils.LANGUAGES[language]


def _looks_like_udpipe_model(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1024:
        return False
    return not path.read_bytes()[:64].lstrip().lower().startswith(b"<!doctype html")


@lru_cache(maxsize=32)
def _spacy_pipeline(model_name: str):
    import spacy

    return spacy.load(
        model_name,
        exclude=["parser", "ner", "textcat", "textcat_multilabel", "senter", "sentencizer"],
    )


def _download_spacy_model(model_name: str) -> None:
    import spacy
    from spacy.cli import download

    if spacy.util.is_package(model_name):
        return
    download(model_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare lemmatization libraries on analysis.txt regression probes.")
    parser.add_argument("--root", type=Path, default=ROOT / "val", help="Directory with validation *.txt files.")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "lemmatizer_experiment_results.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports" / "lemmatizer_experiment_report.md")
    parser.add_argument("--download-missing", action="store_true", help="Download missing Stanza/UDPipe models.")
    args = parser.parse_args(argv)

    candidates: tuple[Candidate, ...] = (
        CurrentCandidate(),
        SimplemmaCandidate(),
        StanzaCandidate(args.download_missing),
        UDPipeCandidate(args.download_missing),
        SpacyCandidate(args.download_missing),
    )
    results = run_experiment(args.root, candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2), encoding="utf-8")
    args.markdown.write_text(render_markdown(results), encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"wrote {args.markdown}")
    return 0


def run_experiment(root: Path, candidates: tuple[Candidate, ...]) -> list[CandidateResult]:
    texts = {normalize_language(path.stem): path.read_text(encoding="utf-8") for path in sorted(root.glob("*.txt"))}
    probes_by_language = _group_probes(PROBES)
    results: list[CandidateResult] = []
    for language, text in texts.items():
        probes = probes_by_language.get(language, ())
        for candidate in candidates:
            results.append(_run_candidate(candidate, text, language, probes))
    return results


def _run_candidate(
    candidate: Candidate,
    text: str,
    language: str,
    probes: tuple[Probe, ...],
) -> CandidateResult:
    if not candidate.supports(language):
        return CandidateResult(candidate.name, language, False, 0.0, 0.0, 0, len(probes), "unsupported", (), ())
    started = time.perf_counter()
    try:
        tokens = candidate.lemmatize(text, language)
    except Exception as exc:
        return CandidateResult(
            candidate.name,
            language,
            True,
            time.perf_counter() - started,
            0.0,
            0,
            len(probes),
            f"{type(exc).__name__}: {exc}",
            (),
            (),
        )
    elapsed = time.perf_counter() - started
    warm_started = time.perf_counter()
    try:
        candidate.lemmatize(text, language)
    except Exception as exc:
        return CandidateResult(
            candidate.name,
            language,
            True,
            elapsed,
            time.perf_counter() - warm_started,
            0,
            len(probes),
            f"warm {type(exc).__name__}: {exc}",
            (),
            (),
        )
    warmed_elapsed = time.perf_counter() - warm_started
    unique_lemmas = _unique(token.lemma for token in tokens)
    failed = tuple(_failed_probe(probe, unique_lemmas) for probe in probes if _failed_probe(probe, unique_lemmas))
    return CandidateResult(
        candidate.name,
        language,
        True,
        elapsed,
        warmed_elapsed,
        len(probes) - len(failed),
        len(probes),
        "",
        unique_lemmas,
        failed,
    )


def _failed_probe(probe: Probe, unique_lemmas: tuple[str, ...]) -> dict[str, object]:
    keys = {_key(lemma) for lemma in unique_lemmas}
    expected_ok = not probe.expected_any or any(_key(item) in keys for item in probe.expected_any)
    forbidden_hit = tuple(item for item in probe.forbidden if _key(item) in keys)
    if expected_ok and not forbidden_hit:
        return {}
    return {
        "label": probe.label,
        "expected_any": probe.expected_any,
        "forbidden_hit": forbidden_hit,
    }


def _group_probes(probes: tuple[Probe, ...]) -> dict[str, tuple[Probe, ...]]:
    grouped: dict[str, list[Probe]] = {}
    for probe in probes:
        grouped.setdefault(probe.language, []).append(probe)
    return {language: tuple(items) for language, items in grouped.items()}


def _unique(items) -> tuple[str, ...]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        key = _key(item)
        if key in seen:
            continue
        seen.add(key)
        values.append(item)
    return tuple(values)


def _key(value: str) -> str:
    return value.strip().casefold()


def render_markdown(results: list[CandidateResult]) -> str:
    by_language: dict[str, list[CandidateResult]] = {}
    for result in results:
        by_language.setdefault(result.language, []).append(result)

    aggregate = _aggregate_scores(results)
    spacy_subset = _spacy_subset_scores(results)
    lines = [
        "# Lemmatizer backend experiment",
        "",
        "Probe set: concrete failure cases from `analysis.txt`, scored as expected lemma present and named bad lemma absent. This is a targeted regression benchmark, not a balanced corpus metric; low `current`/`simplemma` scores are expected because the probes were selected from their observed mistakes.",
        "",
        "Fresh elapsed includes first pipeline/model load inside the process. Warm elapsed is an immediate second pass with cached pipelines and is the better proxy for steady-state service speed.",
        "",
        "Tie break: when candidates pass the same number of probes, the faster warm run is listed as best.",
        "",
        "## Aggregate Probe Score",
        "",
        "| Candidate | Score | Languages run | Fresh elapsed | Warm elapsed |",
        "| --- | ---: | ---: | ---: | ---: |",
        *[
            f"| {candidate} | {passed}/{total} ({passed / total:.3f}) | {languages} | {elapsed:.2f}s | {warmed_elapsed:.2f}s |"
            for candidate, passed, total, languages, elapsed, warmed_elapsed in aggregate
            if total
        ],
        "",
        "## spaCy-Covered Probe Subset",
        "",
        "This table compares candidates only on languages where spaCy had an installed official pipeline and at least one probe.",
        "",
        "| Candidate | Score | Languages run | Fresh elapsed | Warm elapsed |",
        "| --- | ---: | ---: | ---: | ---: |",
        *[
            f"| {candidate} | {passed}/{total} ({passed / total:.3f}) | {languages} | {elapsed:.2f}s | {warmed_elapsed:.2f}s |"
            for candidate, passed, total, languages, elapsed, warmed_elapsed in spacy_subset
            if total
        ],
        "",
        "## Per-Language Result",
        "",
        "| Language | Best candidate | Score | Current | Simplemma | Stanza | UDPipe | spaCy | Notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for language in sorted(by_language):
        row = by_language[language]
        best = _best_result(row)
        cells = {result.candidate: _score_cell(result) for result in row}
        notes = _notes(best, row)
        lines.append(
            "| {language} | {best_candidate} | {best_score} | {current} | {simplemma} | {stanza} | {udpipe} | {spacy} | {notes} |".format(
                language=language,
                best_candidate=best.candidate if best else "n/a",
                best_score=_score_cell(best) if best else "n/a",
                current=cells.get("current", "n/a"),
                simplemma=cells.get("simplemma", "n/a"),
                stanza=cells.get("stanza", "n/a"),
                udpipe=cells.get("udpipe", "n/a"),
                spacy=cells.get("spacy", "n/a"),
                notes=notes,
            )
        )

    lines.extend(
        [
            "",
            "## Failed Probe Details",
            "",
        ]
    )
    for language in sorted(by_language):
        lines.append(f"### {language}")
        for result in sorted(by_language[language], key=lambda item: item.candidate):
            if result.error:
                lines.append(f"- `{result.candidate}`: {result.error}")
                continue
            if not result.failed_probes:
                lines.append(f"- `{result.candidate}`: no probe failures")
                continue
            labels = "; ".join(str(item["label"]) for item in result.failed_probes)
            lines.append(f"- `{result.candidate}`: {labels}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _best_result(results: list[CandidateResult]) -> CandidateResult | None:
    valid = [result for result in results if result.supported and not result.error]
    if not valid:
        return None
    return max(valid, key=lambda item: (item.passed / item.total if item.total else 0.0, -_tie_elapsed(item)))


def _aggregate_scores(results: list[CandidateResult]) -> list[tuple[str, int, int, int, float, float]]:
    return _score_rows(results)


def _spacy_subset_scores(results: list[CandidateResult]) -> list[tuple[str, int, int, int, float, float]]:
    spacy_languages = {
        result.language
        for result in results
        if result.candidate == "spacy" and result.supported and not result.error and result.total > 0
    }
    return _score_rows([result for result in results if result.language in spacy_languages])


def _score_rows(results: list[CandidateResult]) -> list[tuple[str, int, int, int, float, float]]:
    aggregate: dict[str, list[float]] = {}
    for result in results:
        if result.error or not result.supported:
            continue
        passed, total, languages, elapsed, warmed_elapsed = aggregate.setdefault(result.candidate, [0.0, 0.0, 0.0, 0.0, 0.0])
        aggregate[result.candidate] = [
            passed + result.passed,
            total + result.total,
            languages + 1,
            elapsed + result.elapsed_seconds,
            warmed_elapsed + result.warmed_elapsed_seconds,
        ]
    return [
        (candidate, int(values[0]), int(values[1]), int(values[2]), values[3], values[4])
        for candidate, values in sorted(aggregate.items(), key=lambda item: item[0])
    ]


def _score_cell(result: CandidateResult | None) -> str:
    if result is None:
        return "n/a"
    if not result.supported:
        return "unsupported"
    if result.error:
        return "error"
    if result.total == 0:
        return "no probes"
    return f"{result.passed}/{result.total}"


def _tie_elapsed(result: CandidateResult) -> float:
    return result.warmed_elapsed_seconds or result.elapsed_seconds


def _notes(best: CandidateResult | None, row: list[CandidateResult]) -> str:
    errors = [f"{result.candidate}: {result.error}" for result in row if result.error and result.error != "unsupported"]
    if errors:
        return "<br>".join(errors[:2])
    if best is None:
        return "No runnable candidate."
    if best.total == 0:
        return "No analysis probe for this language in current corpus."
    if best.candidate == "current":
        return "Keep current unless broader gold data says otherwise."
    return "Candidate worth production follow-up."


if __name__ == "__main__":
    raise SystemExit(main())
