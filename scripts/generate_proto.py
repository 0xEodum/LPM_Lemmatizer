from __future__ import annotations

import sys
from pathlib import Path

from grpc_tools import protoc


ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "lemmatizer" / "proto" / "lemmatizer.proto"


def main() -> int:
    return protoc.main(
        [
            "grpc_tools.protoc",
            f"--proto_path={ROOT}",
            f"--python_out={ROOT}",
            f"--grpc_python_out={ROOT}",
            str(PROTO),
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
