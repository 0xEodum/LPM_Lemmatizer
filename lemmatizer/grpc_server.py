from __future__ import annotations

from concurrent import futures
from pathlib import Path
from typing import Protocol

import grpc

from lemmatizer.config import ServiceConfig, load_service_config
from lemmatizer.models import LemmaResult, LemmaToken
from lemmatizer.proto import lemmatizer_pb2, lemmatizer_pb2_grpc
from lemmatizer.routed_service import RoutedLemmatizer


class LemmatizerEngine(Protocol):
    def lemmatize(self, text: str, language: str) -> LemmaResult:
        ...

    def lemmatize_batch(self, items: tuple[tuple[str, str], ...]) -> tuple[LemmaResult, ...]:
        ...


class LemmatizerGrpcService(lemmatizer_pb2_grpc.LemmatizerServiceServicer):
    def __init__(self, lemmatizer: LemmatizerEngine) -> None:
        self._lemmatizer = lemmatizer

    def Lemmatize(self, request, context):
        if not request.language.strip():
            return _abort(context, grpc.StatusCode.INVALID_ARGUMENT, "language is required")
        try:
            result = self._lemmatizer.lemmatize(text=request.text, language=request.language)
        except ValueError as exc:
            return _abort(context, grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception as exc:
            return _abort(context, grpc.StatusCode.INTERNAL, str(exc))
        return lemma_result_to_proto(result)

    def LemmatizeBatch(self, request, context):
        items = tuple((item.language, item.text) for item in request.items)
        missing_language_index = next((index for index, item in enumerate(request.items) if not item.language.strip()), None)
        if missing_language_index is not None:
            return _abort(context, grpc.StatusCode.INVALID_ARGUMENT, f"items[{missing_language_index}].language is required")
        try:
            results = self._lemmatizer.lemmatize_batch(items)
        except ValueError as exc:
            return _abort(context, grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception as exc:
            return _abort(context, grpc.StatusCode.INTERNAL, str(exc))
        return lemmatizer_pb2.LemmatizeBatchResponse(
            results=[lemma_result_to_proto(result) for result in results]
        )


def lemma_result_to_proto(result: LemmaResult):
    return lemmatizer_pb2.LemmaResult(
        language=result.language,
        elapsed_seconds=result.elapsed_seconds,
        unique_lemmas=list(result.unique_lemmas),
        tokens=[lemma_token_to_proto(token) for token in result.tokens],
    )


def lemma_token_to_proto(token: LemmaToken):
    return lemmatizer_pb2.LemmaToken(
        surface=token.surface,
        lemma=token.lemma,
        language=token.language,
        backend=token.backend,
        pos=token.pos,
    )


def create_grpc_server(lemmatizer: LemmatizerEngine, max_workers: int = 4) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    lemmatizer_pb2_grpc.add_LemmatizerServiceServicer_to_server(LemmatizerGrpcService(lemmatizer), server)
    return server


def build_lemmatizer_from_config(config_path: str | Path | None = None) -> RoutedLemmatizer:
    config = ServiceConfig.default() if config_path is None else load_service_config(config_path)
    return RoutedLemmatizer(config)


def serve(config_path: str | Path, host: str, port: int, max_workers: int = 4) -> None:
    lemmatizer = build_lemmatizer_from_config(config_path)
    server = create_grpc_server(lemmatizer, max_workers=max_workers)
    address = f"{host}:{port}"
    server.add_insecure_port(address)
    server.start()
    print(f"Lemmatizer gRPC service listening on {address}")
    server.wait_for_termination()


def _abort(context, code: grpc.StatusCode, details: str):
    if context is None:
        raise ValueError(details)
    context.abort(code, details)
