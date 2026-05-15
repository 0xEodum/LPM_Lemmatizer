from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lemmatizer.grpc_server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the lemmatizer gRPC service.")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args(argv)

    serve(config_path=args.config, host=args.host, port=args.port, max_workers=args.max_workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
