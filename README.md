# Universal Lemmatizer

Library-backed multilingual lemmatizer for the languages in `langs.txt`.

## Backends

| Languages | Backend |
| --- | --- |
| Armenian, Bulgarian, Croatian, Czech, Danish, English, Estonian, Finnish, French, German, Indonesian, Italian, Latvian, Norwegian, Portuguese, Russian, Slovak, Spanish, Swedish, Turkish, Ukrainian | `simplemma` |
| Japanese | `fugashi` + `unidic-lite` |
| Korean | `kiwipiepy` |
| Chinese | `jieba` segmentation, surface form as lemma |
| Belarusian, Hebrew | Stanza `tokenize,pos,lemma` |

The public entrypoint is `lemmatizer.UniversalLemmatizer`.

## Setup

Use the existing project environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest pytest-cov
```

Download the Stanza models used for the two gap languages:

```powershell
.\.venv\Scripts\python.exe -c "import stanza; [stanza.download(lang, processors='tokenize,pos,lemma') for lang in ('be', 'he')]"
```

## Usage

Single file:

```powershell
.\.venv\Scripts\python.exe scripts\lemmatize.py --language en --input val\en.txt --json
```

All validation files:

```powershell
.\.venv\Scripts\python.exe scripts\lemmatize.py --all --root val --json
```

Direct API:

```python
from lemmatizer import UniversalLemmatizer

result = UniversalLemmatizer().lemmatize("The autumn leaves swirled.", "English")
print(result.unique_lemmas)
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_universal_lemmatizer.py --cov=lemmatizer --cov=scripts --cov-report=term-missing -q
```

Current CPU validation on `val/*.txt`:

- files processed: 25
- fresh single-process average: about `0.74s` per text
- warmed average: about `0.011s` per text
- warmed max: about `0.18s`

`langs.txt` includes Russian, and the implementation supports it, but the current `val/` directory does not include `ru.txt`.

## gRPC service

The service uses protobuf/gRPC and exposes two RPCs:

- `Lemmatize(LemmatizeRequest) returns (LemmaResult)`
- `LemmatizeBatch(LemmatizeBatchRequest) returns (LemmatizeBatchResponse)`

Backend routing is configured in `config.json`. The default config routes `de`, `ja`, `uk`, `sv`, `hr`, and `nb` to spaCy and the remaining supported service languages to UDPipe. Models are loaded once during service startup and reused for requests.

Install service dependencies and make sure model packages are present:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m spacy validate
```

Run the service:

```powershell
.\.venv\Scripts\python.exe scripts\run_lemmatizer_service.py --config config.json --host 127.0.0.1 --port 50051
```

Regenerate protobuf bindings after editing `lemmatizer/proto/lemmatizer.proto`:

```powershell
.\.venv\Scripts\python.exe scripts\generate_proto.py
```

Minimal Python client:

```python
import grpc

from lemmatizer.proto import lemmatizer_pb2, lemmatizer_pb2_grpc

with grpc.insecure_channel("127.0.0.1:50051") as channel:
    stub = lemmatizer_pb2_grpc.LemmatizerServiceStub(channel)
    response = stub.Lemmatize(lemmatizer_pb2.LemmatizeRequest(language="de", text="Die alten Haeuser standen."))
    print(response.unique_lemmas)
```
