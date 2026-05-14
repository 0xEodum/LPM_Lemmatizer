from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lemmatizer import UniversalLemmatizer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lemmatize multilingual UTF-8 text.")
    parser.add_argument("text", nargs="?", help="Text to lemmatize. Omit when --input is used.")
    parser.add_argument("--language", "-l", help="Language name or code.")
    parser.add_argument("--input", "-i", type=Path, help="UTF-8 text file to lemmatize.")
    parser.add_argument("--all", action="store_true", help="Process every *.txt file under --root.")
    parser.add_argument("--root", type=Path, default=ROOT / "val", help="Directory used with --all.")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON.")
    args = parser.parse_args(argv)

    if args.all:
        return _run_all(args)
    if not args.language:
        raise SystemExit("--language is required unless --all is used.")
    text = _read_text(args)
    result = UniversalLemmatizer().lemmatize(text, args.language)
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    for lemma in result.unique_lemmas:
        print(lemma)
    return 0


def _run_all(args: argparse.Namespace) -> int:
    lemmatizer = UniversalLemmatizer()
    results = []
    for path in sorted(args.root.glob("*.txt")):
        result = lemmatizer.lemmatize(path.read_text(encoding="utf-8"), path.stem)
        payload = result.to_dict()
        payload["path"] = str(path)
        results.append(payload)
    total = sum(float(item["elapsed_seconds"]) for item in results)
    aggregate = {
        "file_count": len(results),
        "average_elapsed_seconds": total / len(results) if results else 0.0,
        "results": results,
    }
    if args.json:
        print(json.dumps(aggregate, ensure_ascii=False, indent=2))
        return 0
    for item in results:
        print(f"{item['language']}\t{item['elapsed_seconds']:.4f}s\t{', '.join(item['unique_lemmas'])}")
    print(f"average\t{aggregate['average_elapsed_seconds']:.4f}s")
    return 0


def _read_text(args: argparse.Namespace) -> str:
    if args.input is not None:
        return args.input.read_text(encoding="utf-8")
    if args.text is not None:
        return args.text
    raise SystemExit("Provide text or --input.")


if __name__ == "__main__":
    raise SystemExit(main())
