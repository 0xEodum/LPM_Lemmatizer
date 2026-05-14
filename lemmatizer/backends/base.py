from __future__ import annotations

from abc import ABC, abstractmethod

from lemmatizer.models import LemmaToken


class LemmaBackend(ABC):
    name: str

    @abstractmethod
    def supports(self, language: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def lemmatize(self, text: str, language: str) -> tuple[LemmaToken, ...]:
        raise NotImplementedError
