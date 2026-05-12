# Multilingual Lemmatizer

This project builds lemma lists from the paired `*_text.txt` files. The file prefix selects the analyzer:

- `am` -> Armenian (`hy`)
- `ar` -> Arabic
- `de` -> German
- `fr` -> French
- `jp` -> Japanese
- `kr` -> Korean

The implementation is split by responsibility:

- `lemmatizer/core.py` orchestrates language dispatch and scoring.
- `lemmatizer/analyzers/` contains language-specific analyzers.
- `lemmatizer/reference.py` handles optional canonical-vocabulary snapping.
- `lemmatizer/io.py` handles text/entity file discovery and parsing.
- `lemmatizer/models.py` contains shared result dataclasses.
- `lemmatizer/resources/*.json` contains language aliases, stopwords, and irregular forms.

Install dependencies in the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Process the expanded dataset and write lemma lists:

```powershell
.\.venv\Scripts\python.exe scripts\lemmatize.py --all --root expanded_texts --reference-vocabulary --write-dir output_expanded
```

The `--reference-vocabulary` flag uses the matching `*_entities.txt` file as a canonical lemma vocabulary. Without that flag, the system runs as a raw lemmatizer for new text and only uses the entity files for scoring.

Run the blind texts without target entity files:

```powershell
.\.venv\Scripts\python.exe scripts\lemmatize.py --all --root blind_texts --write-dir output_blind
```

Single-file examples:

```powershell
.\.venv\Scripts\python.exe scripts\lemmatize.py --input expanded_texts\de_text.txt --language de
.\.venv\Scripts\python.exe scripts\lemmatize.py --input expanded_texts\ar_text.txt --language ar --expected expanded_texts\ar_entities.txt --reference-vocabulary --json
```

Lemmatize text directly:

```powershell
.\.venv\Scripts\python.exe scripts\lemma_text.py --language de "Draußen fiel der kalte Regen."
.\.venv\Scripts\python.exe scripts\lemma_text.py --language kr "따뜻한 봄바람이 불었습니다."
```

If no text argument is passed, `lemma_text.py` starts interactive mode and asks for the language and text:

```powershell
.\.venv\Scripts\python.exe scripts\lemma_text.py
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
