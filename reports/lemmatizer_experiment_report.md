# Lemmatizer backend experiment

Probe set: concrete failure cases from `analysis.txt`, scored as expected lemma present and named bad lemma absent. This is a targeted regression benchmark, not a balanced corpus metric; low `current`/`simplemma` scores are expected because the probes were selected from their observed mistakes.

Fresh elapsed includes first pipeline/model load inside the process. Warm elapsed is an immediate second pass with cached pipelines and is the better proxy for steady-state service speed.

Tie break: when candidates pass the same number of probes, the faster warm run is listed as best.

## Aggregate Probe Score

| Candidate | Score | Languages run | Fresh elapsed | Warm elapsed |
| --- | ---: | ---: | ---: | ---: |
| current | 1/78 (0.013) | 25 | 15.75s | 0.21s |
| simplemma | 0/68 (0.000) | 20 | 0.00s | 0.00s |
| spacy | 34/45 (0.756) | 15 | 8.76s | 0.09s |
| stanza | 60/78 (0.769) | 25 | 69.10s | 4.10s |
| udpipe | 56/78 (0.718) | 25 | 32.78s | 0.51s |

## spaCy-Covered Probe Subset

This table compares candidates only on languages where spaCy had an installed official pipeline and at least one probe.

| Candidate | Score | Languages run | Fresh elapsed | Warm elapsed |
| --- | ---: | ---: | ---: | ---: |
| current | 0/45 (0.000) | 14 | 5.96s | 0.00s |
| simplemma | 0/40 (0.000) | 12 | 0.00s | 0.00s |
| spacy | 34/45 (0.756) | 14 | 8.33s | 0.08s |
| stanza | 39/45 (0.867) | 14 | 40.88s | 2.63s |
| udpipe | 37/45 (0.822) | 14 | 16.76s | 0.34s |

## Per-Language Result

| Language | Best candidate | Score | Current | Simplemma | Stanza | UDPipe | spaCy | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| be | udpipe | 2/2 | 1/2 | unsupported | 1/2 | 2/2 | unsupported | Candidate worth production follow-up. |
| bg | stanza | 2/3 | 0/3 | 0/3 | 2/3 | 1/3 | unsupported | Candidate worth production follow-up. |
| cs | udpipe | 3/4 | 0/4 | 0/4 | 3/4 | 3/4 | unsupported | Candidate worth production follow-up. |
| da | udpipe | 3/4 | 0/4 | 0/4 | 3/4 | 3/4 | 2/4 | Candidate worth production follow-up. |
| de | spacy | 3/3 | 0/3 | 0/3 | 3/3 | 2/3 | 3/3 | Candidate worth production follow-up. |
| en | spacy | 1/2 | 0/2 | 0/2 | 1/2 | 1/2 | 1/2 | Candidate worth production follow-up. |
| es | udpipe | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 1/2 | Candidate worth production follow-up. |
| et | udpipe | 2/4 | 0/4 | 0/4 | 2/4 | 2/4 | unsupported | Candidate worth production follow-up. |
| fi | stanza | 3/3 | 0/3 | 0/3 | 3/3 | 2/3 | 2/3 | Candidate worth production follow-up. |
| fr | stanza | 4/4 | 0/4 | 0/4 | 4/4 | 3/4 | 3/4 | Candidate worth production follow-up. |
| he | udpipe | 1/3 | 0/3 | unsupported | 0/3 | 1/3 | unsupported | Candidate worth production follow-up. |
| hr | spacy | 2/2 | 0/2 | 0/2 | 2/2 | 2/2 | 2/2 | Candidate worth production follow-up. |
| hy | udpipe | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 | unsupported | Candidate worth production follow-up. |
| id | stanza | 2/2 | 0/2 | 0/2 | 2/2 | 0/2 | unsupported | Candidate worth production follow-up. |
| it | udpipe | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 | 1/3 | Candidate worth production follow-up. |
| ja | spacy | 3/3 | 0/3 | unsupported | 1/3 | 3/3 | 3/3 | Candidate worth production follow-up. |
| ko | current | no probes | no probes | unsupported | no probes | no probes | no probes | No analysis probe for this language in current corpus. |
| lv | stanza | 4/4 | 0/4 | 0/4 | 4/4 | 3/4 | unsupported | Candidate worth production follow-up. |
| nb | spacy | 4/5 | 0/5 | 0/5 | 4/5 | 4/5 | 4/5 | Candidate worth production follow-up. |
| pt | stanza | 4/4 | 0/4 | 0/4 | 4/4 | 3/4 | 3/4 | Candidate worth production follow-up. |
| sk | udpipe | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 | unsupported | Candidate worth production follow-up. |
| sv | spacy | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 | 3/3 | Candidate worth production follow-up. |
| tr | udpipe | 1/5 | 0/5 | 0/5 | 1/5 | 1/5 | unsupported | Candidate worth production follow-up. |
| uk | spacy | 5/5 | 0/5 | 0/5 | 4/5 | 4/5 | 5/5 | Candidate worth production follow-up. |
| zh | udpipe | 2/2 | 0/2 | unsupported | 2/2 | 2/2 | 1/2 | Candidate worth production follow-up. |

## Failed Probe Details

### be
- `current`: secrets genitive plural
- `simplemma`: unsupported
- `spacy`: unsupported
- `stanza`: secrets genitive plural
- `udpipe`: no probe failures

### bg
- `current`: grill noun not verb; masculine cheerful adjective; blooming verb
- `simplemma`: grill noun not verb; masculine cheerful adjective; blooming verb
- `spacy`: unsupported
- `stanza`: grill noun not verb
- `udpipe`: grill noun not verb; masculine cheerful adjective

### cs
- `current`: unforgettable keeps negative prefix; lighting verb infinitive; clock striking verb infinitive; cup diminutive
- `simplemma`: unforgettable keeps negative prefix; lighting verb infinitive; clock striking verb infinitive; cup diminutive
- `spacy`: unsupported
- `stanza`: unforgettable keeps negative prefix
- `udpipe`: unforgettable keeps negative prefix

### da
- `current`: does as infinitive; create as infinitive; warm adjective; dark adjective
- `simplemma`: does as infinitive; create as infinitive; warm adjective; dark adjective
- `spacy`: warm adjective; dark adjective
- `stanza`: warm adjective
- `udpipe`: warm adjective

### de
- `current`: contracted preposition; dense adjective; reflexive pronoun
- `simplemma`: contracted preposition; dense adjective; reflexive pronoun
- `spacy`: no probe failures
- `stanza`: no probe failures
- `udpipe`: reflexive pronoun

### en
- `current`: leaves noun; felt irregular verb
- `simplemma`: leaves noun; felt irregular verb
- `spacy`: leaves noun
- `stanza`: leaves noun
- `udpipe`: leaves noun

### es
- `current`: colors noun; greet verb infinitive
- `simplemma`: colors noun; greet verb infinitive
- `spacy`: greet verb infinitive
- `stanza`: no probe failures
- `udpipe`: no probe failures

### et
- `current`: cranberries partitive; walk noun preserved; always adverb preserved; cranes partitive
- `simplemma`: cranberries partitive; walk noun preserved; always adverb preserved; cranes partitive
- `spacy`: unsupported
- `stanza`: walk noun preserved; cranes partitive
- `udpipe`: walk noun preserved; cranes partitive

### fi
- `current`: jump verb infinitive; when not wish particle; this pronoun
- `simplemma`: jump verb infinitive; when not wish particle; this pronoun
- `spacy`: jump verb infinitive
- `stanza`: no probe failures
- `udpipe`: jump verb infinitive

### fr
- `current`: tables noun; terrace noun; reflexive active verb; special adjective masculine
- `simplemma`: tables noun; terrace noun; reflexive active verb; special adjective masculine
- `spacy`: reflexive active verb
- `stanza`: no probe failures
- `udpipe`: reflexive active verb

### he
- `current`: customers plural with attached preposition; vegetables with conjunction; pitas plural
- `simplemma`: unsupported
- `spacy`: unsupported
- `stanza`: customers plural with attached preposition; vegetables with conjunction; pitas plural
- `udpipe`: vegetables with conjunction; pitas plural

### hr
- `current`: islands genitive plural; no Serbian Cyrillic leakage
- `simplemma`: islands genitive plural; no Serbian Cyrillic leakage
- `spacy`: no probe failures
- `stanza`: no probe failures
- `udpipe`: no probe failures

### hy
- `current`: Armenia definite article; mountains genitive plural; mountain definite article
- `simplemma`: Armenia definite article; mountains genitive plural; mountain definite article
- `spacy`: unsupported
- `stanza`: no probe failures
- `udpipe`: no probe failures

### id
- `current`: reduplicated fruit; prefix removal
- `simplemma`: reduplicated fruit; prefix removal
- `spacy`: unsupported
- `stanza`: no probe failures
- `udpipe`: reduplicated fruit; prefix removal

### it
- `current`: wood noun not verb; superlative adjective; fill verb infinitive
- `simplemma`: wood noun not verb; superlative adjective; fill verb infinitive
- `spacy`: superlative adjective; fill verb infinitive
- `stanza`: no probe failures
- `udpipe`: no probe failures

### ja
- `current`: pink stays katakana; very stays hiragana; light-up compound
- `simplemma`: unsupported
- `spacy`: no probe failures
- `stanza`: very stays hiragana; light-up compound
- `udpipe`: no probe failures

### ko
- `current`: no probe failures
- `simplemma`: unsupported
- `spacy`: no probe failures
- `stanza`: no probe failures
- `udpipe`: no probe failures

### lv
- `current`: sunrise dative; everyone pronoun; celebrate verb infinitive; wreaths noun
- `simplemma`: sunrise dative; everyone pronoun; celebrate verb infinitive; wreaths noun
- `spacy`: unsupported
- `stanza`: no probe failures
- `udpipe`: sunrise dative

### nb
- `current`: weather noun; so adverb; love verb infinitive; pack verb infinitive; drink verb infinitive
- `simplemma`: weather noun; so adverb; love verb infinitive; pack verb infinitive; drink verb infinitive
- `spacy`: weather noun
- `stanza`: weather noun
- `udpipe`: weather noun

### pt
- `current`: contracted pelo not peel verb; indefinite article not invented verb; dessa not invented verb; cream noun
- `simplemma`: contracted pelo not peel verb; indefinite article not invented verb; dessa not invented verb; cream noun
- `spacy`: contracted pelo not peel verb
- `stanza`: no probe failures
- `udpipe`: indefinite article not invented verb

### sk
- `current`: small adjective masculine; high adjective masculine; good adjective masculine
- `simplemma`: small adjective masculine; high adjective masculine; good adjective masculine
- `spacy`: unsupported
- `stanza`: no probe failures
- `udpipe`: no probe failures

### sv
- `current`: copula infinitive; preposition for; only adverb
- `simplemma`: copula infinitive; preposition for; only adverb
- `spacy`: no probe failures
- `stanza`: no probe failures
- `udpipe`: no probe failures

### tr
- `current`: connecting verb infinitive; walking verb infinitive; rising verb infinitive; hearing verb infinitive; unique adjective not antonym root
- `simplemma`: connecting verb infinitive; walking verb infinitive; rising verb infinitive; hearing verb infinitive; unique adjective not antonym root
- `spacy`: unsupported
- `stanza`: connecting verb infinitive; walking verb infinitive; rising verb infinitive; hearing verb infinitive
- `udpipe`: connecting verb infinitive; walking verb infinitive; rising verb infinitive; hearing verb infinitive

### uk
- `current`: boundless adjective; garlic adjective; ancestor noun; flow verb; melodic adjective
- `simplemma`: boundless adjective; garlic adjective; ancestor noun; flow verb; melodic adjective
- `spacy`: no probe failures
- `stanza`: boundless adjective
- `udpipe`: flow verb

### zh
- `current`: street should be segmented; this-is should split
- `simplemma`: unsupported
- `spacy`: this-is should split
- `stanza`: no probe failures
- `udpipe`: no probe failures
