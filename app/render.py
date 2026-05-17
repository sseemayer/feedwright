from enum import Enum

from app.models.feed import Feed


class OutputFormat(str, Enum):
    json = "json"
    rss = "rss"
    atom = "atom"

    def render(self, feed: Feed) -> str:
        if self == OutputFormat.json:
            return feed.model_dump_json(indent=2, exclude_none=True)

        elif self == OutputFormat.rss:
            return feed.to_feedgen().rss_str(pretty=True).decode("utf-8")

        elif self == OutputFormat.atom:
            return feed.to_feedgen().atom_str(pretty=True).decode("utf-8")

        else:
            raise ValueError(f"Unsupported output format: {self}")
