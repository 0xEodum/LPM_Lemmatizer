from __future__ import annotations

from pathlib import Path

from lemmatizer.config import PREFIX_TO_LANGUAGE
from lemmatizer.models import TextFilePair


def parse_lemma_list(path: Path) -> tuple[str, ...]:
    raw = path.read_text(encoding="utf-8")
    lemmas = [item.strip() for item in raw.replace("\n", ",").split(",")]
    return tuple(item for item in lemmas if item)


def discover_text_files(root: Path) -> tuple[TextFilePair, ...]:
    pairs = []
    for text_path in sorted(root.rglob("*_text.txt")):
        stem_prefix = text_path.name.removesuffix("_text.txt")
        parent_prefix = text_path.parent.name
        language_key = parent_prefix if parent_prefix in PREFIX_TO_LANGUAGE else stem_prefix
        language = PREFIX_TO_LANGUAGE.get(language_key, language_key)
        prefix = stem_prefix if text_path.parent == root else f"{language_key}_{stem_prefix}"
        entities_path = text_path.with_name(f"{stem_prefix}_entities.txt")
        pairs.append(
            TextFilePair(
                prefix=prefix,
                language=language,
                text_path=text_path,
                entities_path=entities_path if entities_path.exists() else None,
            )
        )
    return tuple(pairs)
