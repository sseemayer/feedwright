import jq

from pydantic import BaseModel, ConfigDict, Field

from app.models.extractor import Extractor, ExtractorConfig
from app.models.feed import Article, Feed

from app.settings import settings


class ArticlesConfig(BaseModel):
    query: str = Field(
        ..., description="glom expression to select articles from the JSON data"
    )

    title: str | None = None
    summary: str | None = None


class JqExtractor(Extractor):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str

    root: str = Field(
        ".", description="glom expression to select the root of the JSON data"
    )

    articles: ArticlesConfig = Field(
        ..., description="Configuration for selecting articles from the JSON data"
    )

    async def extract(self, config: ExtractorConfig) -> Feed:

        async with settings.http.get_async_client() as client:
            response = await client.get(self.url)
            _ = response.raise_for_status()
            data = response.json()

        if self.root != ".":
            data = jq.compile(self.root).input(data).first()

        title_query = jq.compile(self.articles.title) if self.articles.title else None
        summary_query = (
            jq.compile(self.articles.summary) if self.articles.summary else None
        )

        articles = []

        for article in jq.compile(self.articles.query).input(data).all():
            out_article = Article()

            if title_query is not None:
                out_article.title = title_query.input(article).first()

            if summary_query is not None:
                out_article.summary = summary_query.input(article).first()

            articles.append(out_article)

        feed = config.feed_defaults.model_copy(update={"articles": articles})

        return feed
