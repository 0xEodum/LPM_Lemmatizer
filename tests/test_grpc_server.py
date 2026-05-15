from __future__ import annotations

import grpc

from lemmatizer.grpc_server import LemmatizerGrpcService, create_grpc_server
from lemmatizer.models import LemmaResult, LemmaToken
from lemmatizer.proto import lemmatizer_pb2, lemmatizer_pb2_grpc


class FakeLemmatizer:
    def lemmatize(self, text: str, language: str) -> LemmaResult:
        token = LemmaToken(surface=text, lemma=text.casefold(), language=language, backend="fake", pos="NOUN")
        return LemmaResult(language=language, tokens=(token,), elapsed_seconds=0.01)

    def lemmatize_batch(self, items: tuple[tuple[str, str], ...]) -> tuple[LemmaResult, ...]:
        return tuple(self.lemmatize(text, language) for language, text in items)


def test_grpc_service_returns_single_lemma_result() -> None:
    service = LemmatizerGrpcService(FakeLemmatizer())

    response = service.Lemmatize(lemmatizer_pb2.LemmatizeRequest(language="en", text="Leaves"), None)

    assert response.language == "en"
    assert list(response.unique_lemmas) == ["leaves"]
    assert response.tokens[0].surface == "Leaves"
    assert response.tokens[0].backend == "fake"


def test_grpc_service_returns_batch_results() -> None:
    service = LemmatizerGrpcService(FakeLemmatizer())
    request = lemmatizer_pb2.LemmatizeBatchRequest(
        items=[
            lemmatizer_pb2.LemmatizeRequest(language="en", text="Leaves"),
            lemmatizer_pb2.LemmatizeRequest(language="de", text="Hauser"),
        ]
    )

    response = service.LemmatizeBatch(request, None)

    assert [item.language for item in response.results] == ["en", "de"]
    assert [item.tokens[0].lemma for item in response.results] == ["leaves", "hauser"]


def test_grpc_server_accepts_protobuf_client_request() -> None:
    server = create_grpc_server(FakeLemmatizer(), max_workers=1)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = lemmatizer_pb2_grpc.LemmatizerServiceStub(channel)
            response = stub.Lemmatize(lemmatizer_pb2.LemmatizeRequest(language="en", text="Leaves"))
    finally:
        server.stop(0)

    assert response.tokens[0].lemma == "leaves"
