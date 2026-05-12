from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lemmatizer.core import discover_text_files, lemmatize_pair, lemmatize_text, parse_lemma_list


def main() -> int:
    parser = argparse.ArgumentParser(description="Multilingual lemmatization CLI")
    parser.add_argument("--input", type=Path, help="Path to one *_text.txt file or any raw text file.")
    parser.add_argument("--language", help="Language code: de, fr, ar, am/hy, jp/ja, kr/ko.")
    parser.add_argument("--expected", type=Path, help="Optional comma-separated *_entities.txt lemma list.")
    parser.add_argument("--all", action="store_true", help="Process every *_text.txt file in --root.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Directory used with --all.")
    parser.add_argument("--write-dir", type=Path, help="Write <prefix>_lemmas.txt files into this directory.")
    parser.add_argument("--backend", choices=["current", "stanza", "hybrid"], default="current", help="Lemmatization backend.")
    parser.add_argument("--json", action="store_true", help="Print JSON for single-file mode.")
    parser.add_argument(
        "--reference-vocabulary",
        action="store_true",
        help="Use --expected or paired *_entities.txt files as a canonical lemma vocabulary.",
    )
    args = parser.parse_args()

    if args.all:
        return _run_all(args)
    if not args.input:
        parser.error("Either --input or --all is required.")
    language = args.language
    if args.expected:
        report = lemmatize_pair(
            args.input,
            args.expected,
            language=language,
            use_reference=args.reference_vocabulary,
            backend=args.backend,
        )
    else:
        if not language:
            language = args.input.name.removesuffix("_text.txt")
        if args.backend == "stanza":
            report = lemmatize_pair(args.input, None, language=language, backend="stanza")
        else:
            report = lemmatize_text(args.input.read_text(encoding="utf-8"), language)
    if args.write_dir:
        args.write_dir.mkdir(parents=True, exist_ok=True)
        output_path = args.write_dir / f"{args.input.stem.removesuffix('_text')}_lemmas.txt"
        output_path.write_text(", ".join(report.unique_lemmas), encoding="utf-8")
    if args.json:
        print(report.to_json())
    else:
        print(", ".join(report.unique_lemmas))
        if report.metrics:
            print(_format_metrics(report.metrics))
    return 0


def _run_all(args: argparse.Namespace) -> int:
    pairs = discover_text_files(args.root)
    if args.write_dir:
        args.write_dir.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        report = lemmatize_pair(
            pair.text_path,
            pair.entities_path,
            language=pair.language,
            use_reference=args.reference_vocabulary and pair.entities_path is not None,
            backend=args.backend,
        )
        if args.write_dir:
            output_path = args.write_dir / f"{pair.prefix}_lemmas.txt"
            output_path.write_text(", ".join(report.unique_lemmas), encoding="utf-8")
        metrics = _format_metrics(report.metrics) if report.metrics else "no expected file"
        print(f"{pair.prefix}\t{pair.language}\t{len(report.unique_lemmas)} lemmas\t{metrics}")
    return 0


def _format_metrics(metrics: dict[str, float]) -> str:
    return (
        f"precision={metrics['precision']:.3f} "
        f"recall={metrics['recall']:.3f} "
        f"f1={metrics['f1']:.3f} "
        f"matched={int(metrics['matched'])}/{int(metrics['expected'])}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
