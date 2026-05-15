from __future__ import annotations

from scripts.experiment_lemmatizers import CandidateResult, SpacyCandidate, render_markdown


def test_spacy_candidate_declares_supported_pipeline_languages() -> None:
    candidate = SpacyCandidate(download_missing=False)

    assert candidate.supports("en")
    assert candidate.supports("de")
    assert not candidate.supports("be")


def test_report_renders_spacy_column() -> None:
    results = [
        CandidateResult("current", "en", True, 0.1, 0.01, 0, 1, "", (), ({"label": "x"},)),
        CandidateResult("spacy", "en", True, 0.2, 0.02, 1, 1, "", ("leaf",), ()),
        CandidateResult("udpipe", "en", True, 0.3, 0.03, 1, 1, "", ("leaf",), ()),
    ]

    markdown = render_markdown(results)

    assert "| Candidate | Score | Languages run | Fresh elapsed | Warm elapsed |" in markdown
    assert "| spacy | 1/1 (1.000) | 1 | 0.20s | 0.02s |" in markdown
    assert "## spaCy-Covered Probe Subset" in markdown
    assert "| Language | Best candidate | Score | Current | Simplemma | Stanza | UDPipe | spaCy | Notes |" in markdown
    assert "| en | spacy | 1/1 | 0/1 | n/a | n/a | 1/1 | 1/1 |" in markdown
