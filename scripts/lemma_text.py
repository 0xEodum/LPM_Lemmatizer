from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lemmatizer.config import PREFIX_TO_LANGUAGE
from lemmatizer.core import lemmatize_text


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="Return lemmas for a text snippet.")
    parser.add_argument("text", nargs="*", help="Text to lemmatize. If omitted, interactive mode starts.")
    parser.add_argument("--language", "-l", help="Language code: de, es, fi, fr, ar, hy/am, it, jp/ja, kr/ko.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args()

    if args.text:
        if not args.language:
            parser.error("--language is required when text is passed as an argument.")
        _print_lemmas(" ".join(args.text), args.language, args.json)
        return 0

    return _interactive(args.language, args.json)


def _interactive(language: str | None, as_json: bool) -> int:
    current_language = language
    if not current_language:
        current_language = input("Language (de/es/fi/fr/ar/hy/it/jp/kr): ").strip()
    if not current_language:
        print("No language provided.")
        return 1
    if current_language not in PREFIX_TO_LANGUAGE and current_language not in set(PREFIX_TO_LANGUAGE.values()):
        print(f"Unsupported language: {current_language}")
        return 1

    while True:
        try:
            text = input("Text: ").strip()
        except EOFError:
            print()
            return 0
        if not text:
            return 0
        _print_lemmas(text, current_language, as_json)


def _print_lemmas(text: str, language: str, as_json: bool) -> None:
    report = lemmatize_text(text, language)
    if as_json:
        print(report.to_json())
        return
    print(", ".join(report.unique_lemmas))


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
