from abc import ABC, abstractmethod

from app.services.ingestion import VacancyPayload


class SourceConnector(ABC):
    source_name: str

    @abstractmethod
    def fetch(self) -> list[VacancyPayload]:
        raise NotImplementedError
