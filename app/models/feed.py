from datetime import datetime
from feedgen.entry import FeedEntry
from pydantic import BaseModel

from feedgen.feed import FeedGenerator

from app.settings import settings


class Category(BaseModel):
    term: str
    scheme: str | None = None

    def to_feedgen(self) -> dict[str, str]:
        category = {"term": self.term}

        if self.scheme is not None:
            category["scheme"] = self.scheme

        return category


class Person(BaseModel):
    name: str
    email: str | None = None
    uri: str | None = None

    def to_feedgen(self) -> dict[str, str]:
        person = {"name": self.name}

        if self.email is not None:
            person["email"] = self.email

        if self.uri is not None:
            person["uri"] = self.uri

        return person


class Link(BaseModel):
    href: str
    rel: str | None = None
    type: str | None = None
    hreflang: str | None = None
    title: str | None = None
    length: int | None = None

    def to_feedgen(self) -> dict[str, str]:
        link = {"href": self.href}

        if self.rel is not None:
            link["rel"] = self.rel

        if self.type is not None:
            link["type"] = self.type

        if self.hreflang is not None:
            link["hreflang"] = self.hreflang

        if self.title is not None:
            link["title"] = self.title

        if self.length is not None:
            link["length"] = str(self.length)

        return link


class Image(BaseModel):
    url: str
    length: str | None = None
    type: str | None = None


class Article(BaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    summary: str | None = None
    content: str | None = None

    image: Image | None = None

    publish_date: datetime | None = None
    update_date: datetime | None = None
    ttl: int | None = None

    links: list[Link] = []
    categories: list[Category] = []
    comments: str | None = None

    authors: list[Person] = []
    contributors: list[Person] = []

    def to_feedgen(self, fg: FeedGenerator) -> FeedEntry:
        fe = fg.add_entry()

        if self.id is not None:
            _ = fe.id(self.id)

        if self.title is not None:
            _ = fe.title(self.title)

        if self.ttl is not None:
            _ = fe.ttl(self.ttl)

        if self.description is not None:
            _ = fe.description(self.description)

        if self.content is not None:
            _ = fe.content(self.content)

        if self.image is not None:
            _ = fe.enclosure(self.image.url, self.image.length, self.image.type)

        if self.publish_date is not None:
            _ = fe.pubDate(self.publish_date)

        if self.update_date is not None:
            _ = fe.updated(self.update_date)

        if self.ttl is not None:
            _ = fe.ttl(self.ttl)

        if self.summary is not None:
            _ = fe.summary(self.summary)

        for link in self.links:
            _ = fe.link(link.to_feedgen())

        for category in self.categories:
            _ = fe.category(category.to_feedgen())

        if self.comments is not None:
            _ = fe.comments(self.comments)

        for author in self.authors:
            _ = fe.author(author.to_feedgen())

        for contributor in self.contributors:
            _ = fe.contributor(contributor.to_feedgen())

        return fe


class Generator(BaseModel):
    generator: str = settings.generator.name
    version: str | None = settings.generator.version

    def to_feedgen(self) -> dict[str, str]:
        generator = {"generator": self.generator}

        if self.version is not None:
            generator["version"] = self.version

        return generator


class Feed(BaseModel):
    id: str = "my feed"
    title: str | None = None
    subtitle: str | None = None
    description: str = "example feed"
    language: str | None = None

    logo: str | None = None
    image: str | None = None

    generator: Generator | None = Generator()
    last_build_date: datetime | None = None
    publish_date: datetime | None = None
    ttl: int | None = None

    categories: list[Category] = []

    authors: list[Person] = []
    contributors: list[Person] = []
    managing_editor: Person | None = None

    articles: list[Article] = []

    links: list[Link] = []

    def to_feedgen(self) -> FeedGenerator:
        fg = FeedGenerator()

        _ = fg.id(self.id)

        _ = fg.description(self.description)

        if self.title is not None:
            _ = fg.title(self.title)

        if self.subtitle is not None:
            _ = fg.subtitle(self.subtitle)

        if self.language is not None:
            _ = fg.language(self.language)

        if self.logo is not None:
            _ = fg.logo(self.logo)

        if self.image is not None:
            _ = fg.image(self.image)

        if self.generator is not None:
            _ = fg.generator(**self.generator.to_feedgen())

        if self.last_build_date is not None:
            _ = fg.lastBuildDate(self.last_build_date)

        if self.publish_date is not None:
            _ = fg.pubDate(self.publish_date)

        if self.ttl is not None:
            _ = fg.ttl(self.ttl)

        for category in self.categories:
            _ = fg.category(category.to_feedgen())

        for author in self.authors:
            _ = fg.author(author.to_feedgen())

        for contributor in self.contributors:
            _ = fg.contributor(contributor.to_feedgen())

        if self.managing_editor is not None:
            _ = fg.managingEditor(**self.managing_editor.to_feedgen())

        for article in self.articles:
            _ = article.to_feedgen(fg)

        for link in self.links:
            _ = fg.link(link.to_feedgen())

        return fg
