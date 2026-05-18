from enum import Enum
from fastapi import Response

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

    def render_response(self, feed: Feed) -> Response:
        content = self.render(feed)

        if self == OutputFormat.json:
            media_type = "application/json"

        elif self == OutputFormat.rss:
            media_type = "application/rss+xml"

        elif self == OutputFormat.atom:
            media_type = "application/atom+xml"

        else:
            raise ValueError(f"Unsupported output format: {self}")

        return Response(content=content, media_type=media_type)
