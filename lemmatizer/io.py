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
