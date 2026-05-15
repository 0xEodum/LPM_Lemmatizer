from lemmatizer.backends.base import LemmaBackend
from lemmatizer.backends.chinese import ChineseBackend
from lemmatizer.backends.japanese import JapaneseBackend
from lemmatizer.backends.korean import KoreanBackend
from lemmatizer.backends.simplemma_backend import SimplemmaBackend
from lemmatizer.backends.spacy_backend import SpacyBackend
from lemmatizer.backends.stanza_backend import StanzaBackend
from lemmatizer.backends.udpipe_backend import UDPipeBackend

__all__ = [
    "ChineseBackend",
    "JapaneseBackend",
    "KoreanBackend",
    "LemmaBackend",
    "SimplemmaBackend",
    "SpacyBackend",
    "StanzaBackend",
    "UDPipeBackend",
]
