from app.connectors.base import SourceConnector
from app.connectors.demo_company_sites import DemoCompanySitesConnector
from app.connectors.demo_hh import DemoHhConnector
from app.connectors.rss import RssConnector


def build_connectors() -> list[SourceConnector]:
    return [DemoHhConnector(), DemoCompanySitesConnector(), RssConnector()]


def connector_map() -> dict[str, SourceConnector]:
    connectors = build_connectors()
    return {item.source_name: item for item in connectors}
