from pathlib import Path
import subprocess
import sys

from lemmatizer.core import (
    discover_text_files,
    lemmatize_pair,
    lemmatize_text,
    parse_lemma_list,
)
from lemmatizer.config import PREFIX_TO_LANGUAGE, STOPWORDS


ROOT = Path(__file__).resolve().parents[1]
FIRST_PASS = ROOT / "first_pass"
EXPANDED = ROOT / "expanded_texts"
BLIND = ROOT / "blind_texts"


def test_language_metadata_is_loaded_from_resource_files() -> None:
    assert PREFIX_TO_LANGUAGE["ko"] == "kr"
    assert PREFIX_TO_LANGUAGE["ja"] == "jp"
    assert "nach" in STOPWORDS["de"]
    assert "avec" in STOPWORDS["fr"]


def test_parse_lemma_list_reads_comma_separated_utf8() -> None:
    lemmas = parse_lemma_list(FIRST_PASS / "kr_entities.txt")

    assert "따뜻하다" in lemmas
    assert "봄바람" in lemmas
    assert "느끼다" in lemmas


def test_discover_text_files_ignores_entity_files() -> None:
    files = discover_text_files(EXPANDED)

    assert [item.prefix for item in files] == ["ar", "de", "fr", "hy", "jp", "kr"]
    assert all(item.text_path.name.endswith("_text.txt") for item in files)


def test_blind_texts_are_discovered_without_entity_files() -> None:
    files = discover_text_files(BLIND)

    assert [item.prefix for item in files] == ["ar", "de", "fr", "hy", "jp", "kr"]
    assert all(item.entities_path is None for item in files)


def test_language_specific_dictionary_forms() -> None:
    german = lemmatize_text("Draußen fiel der kalte Regen.", "de").unique_lemmas
    japanese = lemmatize_text("雪が白く積もっていました。", "jp").unique_lemmas
    korean = lemmatize_text("따뜻한 봄바람이 불었습니다.", "kr").unique_lemmas
    korean_alias = lemmatize_text("따뜻한 봄바람이 불었습니다.", "ko").unique_lemmas
    arabic = lemmatize_text("قمت بزيارة السوق القديم.", "ar").unique_lemmas

    assert "fallen" in german
    assert "kalt" in german
    assert "白い" in japanese
    assert "積もる" in japanese
    assert "따뜻하다" in korean
    assert "봄바람" in korean
    assert korean_alias == korean
    assert "زيارة" in arabic
    assert "سوق" in arabic


def test_sample_pairs_reach_useful_gold_recall_with_reference_vocabulary() -> None:
    recalls = {}
    for text_file in discover_text_files(FIRST_PASS):
        report = lemmatize_pair(text_file.text_path, text_file.entities_path, use_reference=True)
        recalls[text_file.prefix] = report.metrics["recall"]

    assert recalls["de"] >= 0.80
    assert recalls["fr"] >= 0.75
    assert recalls["jp"] >= 0.80
    assert recalls["kr"] >= 0.80
    assert recalls["ar"] >= 0.65
    assert recalls["am"] >= 0.65


def test_expanded_pairs_reach_useful_gold_recall_with_reference_vocabulary() -> None:
    recalls = {}
    for text_file in discover_text_files(EXPANDED):
        report = lemmatize_pair(text_file.text_path, text_file.entities_path, use_reference=True)
        recalls[text_file.prefix] = report.metrics["recall"]

    assert recalls["de"] >= 0.90
    assert recalls["fr"] >= 0.90
    assert recalls["jp"] >= 0.85
    assert recalls["kr"] >= 0.90
    assert recalls["ar"] >= 0.90
    assert recalls["hy"] >= 0.90


def test_text_cli_accepts_positional_text() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "lemma_text.py"),
            "--language",
            "de",
            "Draußen fiel der kalte Regen.",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    assert "fallen" in result.stdout
    assert "kalt" in result.stdout


def test_text_cli_prompts_interactively_without_text_argument() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lemma_text.py")],
        cwd=ROOT,
        input="kr\n따뜻한 봄바람이 불었습니다.\n\n",
        check=True,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )

    assert "Language" in result.stdout
    assert "따뜻하다" in result.stdout
    assert "봄바람" in result.stdout
