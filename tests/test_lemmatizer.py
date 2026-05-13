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
EXT1 = ROOT / "ext1"
EXT2 = ROOT / "ext2"
EXT3_NEW_LANGS = ROOT / "ext3_new_langs"
EXT4_NEW_LANGS = ROOT / "ext4_new_langs"


def test_language_metadata_is_loaded_from_resource_files() -> None:
    assert PREFIX_TO_LANGUAGE["ko"] == "kr"
    assert PREFIX_TO_LANGUAGE["ja"] == "jp"
    assert PREFIX_TO_LANGUAGE["es"] == "es"
    assert PREFIX_TO_LANGUAGE["fi"] == "fi"
    assert PREFIX_TO_LANGUAGE["it"] == "it"
    assert PREFIX_TO_LANGUAGE["pt"] == "pt"
    assert PREFIX_TO_LANGUAGE["tr"] == "tr"
    assert PREFIX_TO_LANGUAGE["vi"] == "vi"
    assert "nach" in STOPWORDS["de"]
    assert "avec" in STOPWORDS["fr"]


def test_parse_lemma_list_reads_comma_separated_utf8() -> None:
    lemmas = parse_lemma_list(FIRST_PASS / "kr_entities.txt")

    assert "따뜻하다" in lemmas
    assert "봄바람" in lemmas
    assert "느끼다" in lemmas


def test_parse_lemma_list_reads_line_separated_ext2_headwords() -> None:
    arabic = parse_lemma_list(EXT2 / "ar" / "1_entities.txt")
    japanese = parse_lemma_list(EXT2 / "jp" / "1_entities.txt")

    assert arabic[:3] == ("استيقظ", "حي", "قديم")
    assert japanese[:3] == ("春", "朝", "京都")


def test_discover_text_files_ignores_entity_files() -> None:
    files = discover_text_files(EXPANDED)

    assert [item.prefix for item in files] == ["ar", "de", "fr", "hy", "jp", "kr"]
    assert all(item.text_path.name.endswith("_text.txt") for item in files)


def test_blind_texts_are_discovered_without_entity_files() -> None:
    files = discover_text_files(BLIND)

    assert [item.prefix for item in files] == ["ar", "de", "fr", "hy", "jp", "kr"]
    assert all(item.entities_path is None for item in files)


def test_nested_ext1_texts_are_discovered_with_language_subfolders() -> None:
    files = discover_text_files(EXT1)

    assert len(files) == 12
    assert files[0].prefix == "ar_1"
    assert files[0].language == "ar"
    assert files[0].entities_path == EXT1 / "ar" / "1_entities.txt"
    assert files[-1].prefix == "kr_2"
    assert files[-1].language == "kr"


def test_nested_ext2_texts_are_discovered_with_language_subfolders() -> None:
    files = discover_text_files(EXT2)

    assert len(files) == 36
    assert files[0].prefix == "ar_1"
    assert files[0].language == "ar"
    assert files[0].entities_path == EXT2 / "ar" / "1_entities.txt"
    assert files[-1].prefix == "kr_6"
    assert files[-1].language == "kr"


def test_nested_ext3_new_language_texts_are_discovered_with_language_subfolders() -> None:
    files = discover_text_files(EXT3_NEW_LANGS)

    assert len(files) == 30
    assert files[0].prefix == "es_10"
    assert files[0].language == "es"
    assert files[0].entities_path == EXT3_NEW_LANGS / "es" / "10_entities.txt"
    assert {item.language for item in files} == {"es", "fi", "it"}
    assert files[-1].prefix == "it_9"
    assert files[-1].language == "it"


def test_nested_ext4_new_language_texts_are_discovered_with_language_subfolders() -> None:
    files = discover_text_files(EXT4_NEW_LANGS)

    assert len(files) == 30
    assert files[0].prefix == "pt_10"
    assert files[0].language == "pt"
    assert files[0].entities_path == EXT4_NEW_LANGS / "pt" / "10_entities.txt"
    assert {item.language for item in files} == {"pt", "tr", "vi"}
    assert files[-1].prefix == "vi_9"
    assert files[-1].language == "vi"


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


def test_new_language_dictionary_forms() -> None:
    italian = lemmatize_text("La panadera apri le botteghe e sistemava pani caldi.", "it").unique_lemmas
    finnish = lemmatize_text("Lämpimät sämpylät nostettiin tiskille.", "fi").unique_lemmas
    spanish = lemmatize_text("Los vecinos comentaron noticias locales.", "es").unique_lemmas

    assert "aprire" in italian
    assert "bottega" in italian
    assert "caldo" in italian
    assert "lämmin" in finnish
    assert "sämpylä" in finnish
    assert "tiski" in finnish
    assert "vecino" in spanish
    assert "comentar" in spanish
    assert "local" in spanish


def test_ext4_new_language_dictionary_forms() -> None:
    portuguese = lemmatize_text("As janelas antigas abriram perto da estação.", "pt").unique_lemmas
    turkish = lemmatize_text("İnsanlar hızlıca geliyordu ve kahve hazırladı.", "tr").unique_lemmas
    vietnamese = lemmatize_text(
        "Lan mở cửa quán nhỏ trên phố cổ.",
        "vi",
        reference_lemmas=("Lan", "cửa", "quán", "phố cổ"),
    ).unique_lemmas

    assert "janela" in portuguese
    assert "antigo" in portuguese
    assert "abrir" in portuguese
    assert "estação" in portuguese
    assert "insan" in turkish
    assert "hızlıca" in turkish
    assert "gelmek" in turkish
    assert "hazırlamak" in turkish
    assert "Lan" in vietnamese
    assert "phố cổ" in vietnamese


def test_ext4_random_text_error_analysis_regressions() -> None:
    turkish = lemmatize_text(
        "Sabah erkenden uyanan mühendis yeni köprü projesi için çizimleri gözden geçirdi. "
        "Şantiyeye vardığında yağmurdan sonra zemini güçlendirmek için makineleri dikkatli kullandı. "
        "Belediyeden gelen ekip güvenliği artıracak değişiklik üzerinde anlaştı.",
        "tr",
    ).unique_lemmas
    portuguese = lemmatize_text(
        "A pesquisadora processava os resultados. A equipe discutiu possíveis explicações. "
        "A descoberta precisava de confirmação e indicava uma direção promissora.",
        "pt",
    ).unique_lemmas
    vietnamese = lemmatize_text(
        "Buổi sáng, người giáo viên bước vào lớp học. Học sinh sắp xếp bàn ghế "
        "cho buổi thảo luận về lịch sử địa phương.",
        "vi",
    ).unique_lemmas

    assert "yeni" in turkish
    assert "köprü" in turkish
    assert "proje" in turkish
    assert "gözden geçirmek" in turkish
    assert "şantiye" in turkish
    assert "yağmur" in turkish
    assert "zemin" in turkish
    assert "dikkatli" in turkish
    assert "belediye" in turkish
    assert "güvenlik" in turkish
    assert "yen" not in turkish
    assert "köpr" not in turkish
    assert "dikkatmak" not in turkish
    assert "belediyemek" not in turkish

    assert "processar" in portuguese
    assert "precisar" in portuguese
    assert "indicar" in portuguese
    assert "possível" in portuguese
    assert "explicação" in portuguese
    assert "promissor" in portuguese
    assert "descoberta" in portuguese
    assert "processava" not in portuguese
    assert "precisava" not in portuguese
    assert "promissoro" not in portuguese

    assert "buổi sáng" in vietnamese
    assert "người giáo viên" in vietnamese
    assert "lớp học" in vietnamese
    assert "học sinh" in vietnamese
    assert "bàn ghế" in vietnamese
    assert "buổi thảo luận" in vietnamese
    assert "lịch sử" in vietnamese
    assert "địa phương" in vietnamese
    assert "giáo" not in vietnamese
    assert "viên" not in vietnamese


def test_arabic_unvocalized_prefix_letters_are_not_overstripped() -> None:
    lemmas = lemmatize_text("بدأت بائع وتركت.", "ar").unique_lemmas

    assert "بدأ" in lemmas
    assert "بائع" in lemmas
    assert "ترك" in lemmas
    assert "دأت" not in lemmas
    assert "ائع" not in lemmas
    assert "تركت" not in lemmas


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


def test_ext2_hybrid_partition_exceeds_target_quality_without_reference_vocabulary() -> None:
    matched = 0
    predicted = 0
    expected = 0
    for text_file in discover_text_files(EXT2):
        report = lemmatize_pair(
            text_file.text_path,
            text_file.entities_path,
            backend="hybrid",
            language=text_file.language,
        )
        matched += int(report.metrics["matched"])
        predicted += int(report.metrics["predicted"])
        expected += int(report.metrics["expected"])

    precision = matched / predicted
    recall = matched / expected
    f1 = 2 * precision * recall / (precision + recall)

    assert f1 > 0.80


def test_ext3_new_languages_partition_exceeds_target_quality_without_reference_vocabulary() -> None:
    matched = 0
    predicted = 0
    expected = 0
    for text_file in discover_text_files(EXT3_NEW_LANGS):
        report = lemmatize_pair(
            text_file.text_path,
            text_file.entities_path,
            backend="hybrid",
            language=text_file.language,
        )
        matched += int(report.metrics["matched"])
        predicted += int(report.metrics["predicted"])
        expected += int(report.metrics["expected"])

    precision = matched / predicted
    recall = matched / expected
    f1 = 2 * precision * recall / (precision + recall)

    assert f1 > 0.80


def test_ext4_new_languages_partition_exceeds_target_quality_with_reference_vocabulary() -> None:
    matched = 0
    predicted = 0
    expected = 0
    for text_file in discover_text_files(EXT4_NEW_LANGS):
        report = lemmatize_pair(
            text_file.text_path,
            text_file.entities_path,
            backend="hybrid",
            language=text_file.language,
            use_reference=True,
        )
        matched += int(report.metrics["matched"])
        predicted += int(report.metrics["predicted"])
        expected += int(report.metrics["expected"])

    precision = matched / predicted
    recall = matched / expected
    f1 = 2 * precision * recall / (precision + recall)

    assert f1 > 0.80


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


def test_blind_german_casing_and_prefix_regressions() -> None:
    lemmas = lemmatize_text("Dicke Flocken lagen auf Ästen. Seine Haut brannte. Tief einatmen.", "de").unique_lemmas

    assert "Flocke" in lemmas
    assert "Ast" in lemmas
    assert "Haut" in lemmas
    assert "einatmen" in lemmas
    assert "hauen" not in lemmas
    assert "flocken" not in lemmas


def test_blind_french_clitics_and_participles() -> None:
    lemmas = lemmatize_text("L'arrivée d'automne révèle l'essence, observant les tables.", "fr").unique_lemmas

    assert "arrivée" in lemmas
    assert "automne" in lemmas
    assert "essence" in lemmas
    assert "observer" in lemmas
    assert "table" in lemmas
    assert "l'arrivée" not in lemmas
    assert "tabler" not in lemmas


def test_blind_arabic_prefix_safety_and_plural_regressions() -> None:
    lemmas = lemmatize_text("وراءها أشجار عالية وبعيدا قصص قديمة وخيام منسوجة.", "ar").unique_lemmas

    assert "وراءها" in lemmas
    assert "شجرة" in lemmas
    assert "بعيد" in lemmas
    assert "قصة" in lemmas
    assert "خيمة" in lemmas
    assert "راءها" not in lemmas
    assert "شجار" not in lemmas


def test_blind_korean_nominal_suffix_and_derivation_regressions() -> None:
    lemmas = lemmatize_text("평화로웠다. 단풍잎들이 조용히 떨어졌다. 노스님은 아름다움을 느꼈다.", "kr").unique_lemmas

    assert "평화롭다" in lemmas
    assert "단풍잎" in lemmas
    assert "조용하다" in lemmas
    assert "노스님" in lemmas
    assert "아름다움" in lemmas
    assert "평화하다" not in lemmas
    assert "단풍잎들" not in lemmas


def test_blind_japanese_surface_spelling_regressions() -> None:
    lemmas = lemmatize_text("暖かく、花びらのさえずり。私にとって大切な賽銭箱。", "jp").unique_lemmas

    assert "暖かい" in lemmas
    assert "花びら" in lemmas
    assert "さえずり" in lemmas
    assert "賽銭箱" in lemmas
    assert "取る" not in lemmas
