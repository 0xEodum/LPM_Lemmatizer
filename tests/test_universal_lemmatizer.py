from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lemmatizer import UniversalLemmatizer, load_language_specs
from scripts.lemmatize import main as lemmatize_main


ROOT = Path(__file__).resolve().parents[1]


def test_all_langs_txt_languages_are_supported() -> None:
    specs = load_language_specs(ROOT / "langs.txt")
    lemmatizer = UniversalLemmatizer()

    unsupported = [spec.name for spec in specs if not lemmatizer.supports(spec.code)]

    assert unsupported == []


def test_language_aliases_are_normalized() -> None:
    lemmatizer = UniversalLemmatizer()

    assert lemmatizer.normalize_language("Japanese") == "ja"
    assert lemmatizer.normalize_language("jp") == "ja"
    assert lemmatizer.normalize_language("Korean") == "ko"
    assert lemmatizer.normalize_language("kr") == "ko"
    assert lemmatizer.normalize_language("Norwegian") == "nb"


def test_common_library_backends_return_dictionary_forms() -> None:
    lemmatizer = UniversalLemmatizer()

    english = lemmatizer.lemmatize("The autumn leaves swirled outside.", "English")
    german = lemmatizer.lemmatize("Die alten Häuser standen am Fluss.", "de")
    turkish = lemmatizer.lemmatize("İnsanlar sokaklarda yürüyordu.", "tr")

    assert "leave" in english.unique_lemmas
    assert "swirl" in english.unique_lemmas
    assert "Haus" in german.unique_lemmas or "haus" in german.unique_lemmas
    assert "insan" in turkish.unique_lemmas


def test_specialized_cjk_and_korean_backends_tokenize_text() -> None:
    lemmatizer = UniversalLemmatizer()

    chinese = lemmatizer.lemmatize("春节是中国最重要的传统节日。", "zh")
    japanese = lemmatizer.lemmatize("春になると桜が咲きます。", "jp")
    korean = lemmatizer.lemmatize("서울은 바쁜 도시입니다.", "kr")

    assert "春节" in chinese.unique_lemmas
    assert "中国" in chinese.unique_lemmas
    assert any(lemma.startswith("桜") for lemma in japanese.unique_lemmas)
    assert "서울" in korean.unique_lemmas
    assert "도시" in korean.unique_lemmas


def test_stanza_gap_backends_cover_hebrew_and_belarusian() -> None:
    lemmatizer = UniversalLemmatizer()

    hebrew = lemmatizer.lemmatize("חתולים רצים בשוק.", "he")
    belarusian = lemmatizer.lemmatize("Старыя дрэвы стаялі каля дарогі.", "be")

    assert hebrew.tokens
    assert belarusian.tokens
    assert any(token.backend == "stanza" for token in hebrew.tokens)
    assert any(token.backend == "stanza" for token in belarusian.tokens)


def test_cli_outputs_json_for_single_file() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "lemmatize.py"),
            "--language",
            "en",
            "--input",
            str(ROOT / "val" / "en.txt"),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    payload = json.loads(result.stdout)

    assert payload["language"] == "en"
    assert payload["unique_lemmas"]
    assert payload["elapsed_seconds"] >= 0


def test_cli_processes_directory_from_file_stems(tmp_path: Path) -> None:
    sample = tmp_path / "en.txt"
    sample.write_text("Small tests passed quickly.", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "lemmatize.py"),
            "--all",
            "--root",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    payload = json.loads(result.stdout)

    assert payload["file_count"] == 1
    assert payload["results"][0]["language"] == "en"
    assert "pass" in payload["results"][0]["unique_lemmas"]


def test_cli_main_prints_plain_unique_lemmas(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = lemmatize_main(["--language", "en", "Small tests passed quickly."])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "pass" in output


def test_cli_main_requires_text_or_input() -> None:
    with pytest.raises(SystemExit, match="Provide text or --input"):
        lemmatize_main(["--language", "en"])


@pytest.mark.integration
def test_validation_texts_stay_under_average_processing_budget() -> None:
    lemmatizer = UniversalLemmatizer()
    paths = sorted((ROOT / "val").glob("*.txt"))

    # Warm lazy analyzers so this measures processing time, not model startup.
    for path in paths:
        lemmatizer.lemmatize(path.read_text(encoding="utf-8"), path.stem)

    durations = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        started = time.perf_counter()
        lemmatizer.lemmatize(text, path.stem)
        durations.append(time.perf_counter() - started)

    assert sum(durations) / len(durations) < 1.5
