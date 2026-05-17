# pyright: reportAny=false, reportExplicitAny=false

from typing import Any, override
from jq import _Program as JqProgram, compile  # pyright: ignore[reportPrivateUsage]

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.extractor import Extractor, ExtractorConfig
from app.models.feed import Article, Feed, Image, Link, Person

from app.settings import settings


class ImageConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    query: JqProgram = Field(
        ..., description="jq expression to select the image data from the JSON data"
    )

    url: JqProgram
    length: JqProgram | None = None
    type: JqProgram | None = None

    @field_validator("query", "url", "length", "type", mode="before")
    def compile_query(cls, value: str) -> JqProgram:
        return compile(value)

    def extract(self, data: Any) -> Image | None:
        image_data = self.query.input(data).first()
        if image_data is None:
            return None

        out: dict[str, Any] = {}

        for key in ["url", "length", "type"]:
            field_query: JqProgram | None = getattr(self, key)
            if field_query is None:
                continue

            value = field_query.input(image_data).first()
            if value is not None:
                out[key] = value

        return Image.model_validate(out)


class LinkConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    query: JqProgram = Field(
        ..., description="jq expression to select the link data from the JSON data"
    )

    href: JqProgram
    rel: JqProgram | None = None
    type: JqProgram | None = None
    hreflang: JqProgram | None = None
    title: JqProgram | None = None
    length: JqProgram | None = None

    @field_validator(
        "query", "href", "rel", "type", "hreflang", "title", "length", mode="before"
    )
    def compile_query(cls, value: str) -> JqProgram:
        return compile(value)

    def extract(self, data: Any) -> list[Link]:
        out: list[Link] = []
        for link_data in self.query.input(data).all():
            link_out = {}
            for key in [
                "href",
                "rel",
                "type",
                "hreflang",
                "title",
                "length",
            ]:
                link_query: JqProgram | None = getattr(self, key)
                if link_query is None:
                    continue

                value = link_query.input(link_data).first()
                if value is not None:
                    link_out[key] = value

            out.append(Link.model_validate(link_out))

        return out


class PersonConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    query: JqProgram = Field(
        ..., description="jq expression to select the person data from the JSON data"
    )

    name: JqProgram
    email: JqProgram | None = None
    uri: JqProgram | None = None

    @field_validator("query", "name", "email", "uri", mode="before")
    def compile_query(cls, value: str) -> JqProgram:
        return compile(value)

    def extract(self, data: Any) -> list[Person]:
        out: list[Person] = []
        for person_data in self.query.input(data).all():
            person_out = {}
            for key in ["name", "email", "uri"]:
                person_query: JqProgram | None = getattr(self, key)
                if person_query is None:
                    continue

                value = person_query.input(person_data).first()
                if value is not None:
                    person_out[key] = value

            out.append(Person.model_validate(person_out))

        return out


class ArticlesConfig(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    query: JqProgram = Field(
        ..., description="jq expression to select articles from the JSON data"
    )

    title: JqProgram | None = None
    summary: JqProgram | None = None
    description: JqProgram | None = None

    image: ImageConfig | None = None
    links: list[LinkConfig] = []

    authors: list[PersonConfig] = []
    contributors: list[PersonConfig] = []

    @field_validator("query", "title", "summary", "description", mode="before")
    def compile_query(cls, value: str) -> JqProgram:
        return compile(value)

    def extract(self, data: Any) -> list[Article]:
        out: list[Article] = []
        for article_data in self.query.input(data).all():
            article_out: dict[str, Any] = {}

            for key in ["title", "summary", "description"]:
                article_query: JqProgram | None = getattr(self, key)
                if article_query is None:
                    continue

                value = article_query.input(article_data).first()
                if value is not None:
                    article_out[key] = value

            if self.image is not None:
                image = self.image.extract(article_data)
                if image is not None:
                    article_out["image"] = image

            links: list[Link] = []
            for link_config in self.links:
                links.extend(link_config.extract(article_data))
            article_out["links"] = links

            authors: list[Person] = []
            for author_config in self.authors:
                authors.extend(author_config.extract(article_data))
            article_out["authors"] = authors

            contributors: list[Person] = []
            for contributor_config in self.contributors:
                contributors.extend(contributor_config.extract(article_data))
            article_out["contributors"] = contributors

            out.append(Article.model_validate(article_out))

        return out


class JqExtractor(Extractor):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(..., description="URL to fetch the JSON data from")

    root: JqProgram = Field(
        compile("."), description="jq expression to select the root of the JSON data"
    )

    id: JqProgram | None = Field(
        None, description="jq expression to select the feed ID from the JSON data"
    )

    title: JqProgram | None = Field(
        None, description="jq expression to select the feed title from the JSON data"
    )

    subtitle: JqProgram | None = Field(
        None, description="jq expression to select the feed subtitle from the JSON data"
    )

    description: JqProgram | None = Field(
        None,
        description="jq expression to select the feed description from the JSON data",
    )

    language: JqProgram | None = Field(
        None, description="jq expression to select the feed language from the JSON data"
    )

    logo: JqProgram | None = Field(
        None, description="jq expression to select the feed logo URL from the JSON data"
    )

    articles: ArticlesConfig = Field(
        ..., description="Configuration for selecting articles from the JSON data"
    )

    links: list[LinkConfig] = Field(
        [],
        description="Configuration for selecting feed-level links from the JSON data",
    )

    @field_validator(
        "root",
        "id",
        "title",
        "subtitle",
        "description",
        "language",
        "logo",
        mode="before",
    )
    def compile_root(cls, value: str) -> JqProgram:
        return compile(value)

    @override
    async def extract(self, config: ExtractorConfig) -> Feed:

        async with settings.http.get_async_client() as client:
            response = await client.get(self.url)
            _ = response.raise_for_status()
            data = response.json()

        data = self.root.input(data).first()

        out: dict[str, Any] = {
            "articles": [],
            "links": [],
        }

        for key in ["id", "title", "subtitle", "description", "language", "logo"]:
            field_query: JqProgram | None = getattr(self, key)
            if field_query is None:
                continue

            value = field_query.input(data).first()
            if value is not None:
                out[key] = value

        out["articles"] = self.articles.extract(data)

        for link_config in self.links:
            out["links"].extend(link_config.extract(data))

        feed = config.feed_defaults.model_copy(update=out)

        return feed
