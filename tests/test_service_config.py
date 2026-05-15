from __future__ import annotations

import json

import pytest

from lemmatizer.config import DEFAULT_SPACY_LANGUAGES, ServiceConfig, load_service_config


def test_default_service_config_routes_selected_languages_to_spacy() -> None:
    config = ServiceConfig.default()

    assert config.spacy == DEFAULT_SPACY_LANGUAGES
    assert "de" in config.spacy
    assert "ja" in config.spacy
    assert "uk" in config.spacy
    assert "de" not in config.udpipe


def test_load_service_config_normalizes_language_aliases(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"spacy": ["German", "jp", "no"], "udpipe": ["English"]}), encoding="utf-8")

    config = load_service_config(path)

    assert config.spacy == ("de", "ja", "nb")
    assert config.udpipe == ("en",)


def test_service_config_rejects_backend_overlap(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"spacy": ["de"], "udpipe": ["German"]}), encoding="utf-8")

    with pytest.raises(ValueError, match="configured for multiple backends"):
        load_service_config(path)


def test_service_config_rejects_unsupported_backend_language(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"spacy": ["be"], "udpipe": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="spaCy backend does not support"):
        load_service_config(path)
