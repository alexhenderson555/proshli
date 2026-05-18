from app.connectors.base import SourceConnector
from app.connectors.corp_sites import CorpSitesConnector
from app.connectors.habr_career import HabrCareerConnector
from app.connectors.hh import HhConnector
from app.connectors.rss import RssConnector
from app.connectors.telegram_channels import TelegramChannelsConnector


def build_connectors() -> list[SourceConnector]:
    """Order matters only for observability — every connector is independent.

    HH first because it's the highest-yield single source (47 queries × Russia
    sweep). Habr second because the RSS feed is tiny and finishes quickly.
    Corp sites third (parallel-safe HTTP). Telegram last because it does the
    most network work (>70 channels) and we don't want a slow TG run to delay
    HH dedup metrics.
    """
    return [
        HhConnector(),
        HabrCareerConnector(),
        CorpSitesConnector(),
        TelegramChannelsConnector(),
        RssConnector(),
    ]


def connector_map() -> dict[str, SourceConnector]:
    connectors = build_connectors()
    return {item.source_name: item for item in connectors}
