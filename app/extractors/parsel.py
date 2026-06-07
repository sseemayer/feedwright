import json
from abc import ABCMeta, abstractmethod
from enum import Enum

from parsel import Selector as ParselSelector, SelectorList
from typing import cast, override
from pydantic import BaseModel, Field

from app.models.extractor import Extractor, ExtractorConfig
from app.models.feed import Article, Feed, Image, Link, Person

from app.settings import settings


class DocumentType(str, Enum):
    HTML = "html"
    XML = "xml"
    JSON = "json"


class SelectorBase(BaseModel, metaclass=ABCMeta):
    @abstractmethod
    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]: ...


class ConstantSelector(SelectorBase):
    """A constant selector that always returns the same value"""

    constant: str = Field(..., description="The constant value to return")

    @override
    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:

        return SelectorList(
            [ParselSelector(text=json.dumps(self.constant), type="json")]
        )


class CssSelector(SelectorBase):
    """A CSS selector to select the data from a HTML document"""

    css: str = Field(
        ..., description="CSS selector to select the data from the document"
    )

    @override
    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        return selector.css(self.css)


class XPathSelector(SelectorBase):
    """An XPath selector to select the data from a HTML or XML document"""

    xpath: str = Field(
        ..., description="XPath selector to select the data from the document"
    )

    @override
    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        return selector.xpath(self.xpath)


class JmesPathSelector(SelectorBase):
    """A JMESPath selector to select the data from a JSON document"""

    jmespath: str = Field(
        ..., description="JMESPath selector to select the data from the document"
    )

    @override
    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        return selector.jmespath(self.jmespath)


class NoOpSelector(SelectorBase):
    """A no-op selector that returns the input selector as is"""

    @override
    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        return (
            selector if isinstance(selector, SelectorList) else SelectorList([selector])
        )


type Selector = (
    ConstantSelector | CssSelector | XPathSelector | JmesPathSelector | NoOpSelector
)


class LinkConfig(BaseModel):
    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the link data"
    )
    href: Selector = Field(..., description="Selector to select the href of the link")
    title: Selector = Field(..., description="Selector to select the title of the link")

    rel: Selector | None = Field(
        None, description="Selector to select the rel of the link"
    )
    type: Selector | None = Field(
        None, description="Selector to select the type of the link"
    )
    hreflang: Selector | None = Field(
        None, description="Selector to select the hreflang of the link"
    )
    length: Selector | None = Field(
        None, description="Selector to select the length of the link"
    )

    def extract(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> list[Link]:
        out: list[Link] = []
        for link_selector in self.root.select(selector):
            link_out = {}
            for key in [
                "href",
                "rel",
                "type",
                "hreflang",
                "title",
                "length",
            ]:
                field_selector = cast(Selector | None, getattr(self, key))
                if field_selector is None:
                    continue

                value = field_selector.select(link_selector).get()
                if value is not None:
                    link_out[key] = value

            out.append(Link.model_validate(link_out))

        return out


class ImageConfig(BaseModel):
    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the image data"
    )
    url: Selector = Field(..., description="Selector to select the URL of the image")
    length: Selector | None = Field(
        None, description="Selector to select the length of the image"
    )
    type: Selector | None = Field(
        None, description="Selector to select the type of the image"
    )

    def extract(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> Image | None:
        image_selector = self.root.select(selector)
        if image_selector is None:
            return None

        image_out = {}
        for key in ["url", "length", "type"]:
            field_selector = cast(Selector | None, getattr(self, key))
            if field_selector is None:
                continue

            value = field_selector.select(image_selector).get()
            if value is not None:
                image_out[key] = value

        return Image.model_validate(image_out)


class PersonConfig(BaseModel):
    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the person data"
    )
    name: Selector = Field(..., description="Selector to select the name of the person")
    email: Selector | None = Field(
        None, description="Selector to select the email of the person"
    )
    uri: Selector | None = Field(
        None, description="Selector to select the URI of the person"
    )

    def extract(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> list[Person]:
        out: list[Person] = []
        for person_selector in self.root.select(selector):
            person_out = {}
            for key in ["name", "email", "uri"]:
                field_selector = cast(Selector | None, getattr(self, key))
                if field_selector is None:
                    continue

                value = field_selector.select(person_selector).get()
                if value is not None:
                    person_out[key] = value

            out.append(Person.model_validate(person_out))

        return out


class ArticlesConfig(BaseModel):
    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the articles data"
    )

    id: Selector = Field(..., description="Selector to select the ID of the article")
    title: Selector = Field(
        ..., description="Selector to select the title of the article"
    )
    subtitle: Selector | None = Field(
        None, description="Selector to select the subtitle of the article"
    )
    summary: Selector | None = Field(
        None, description="Selector to select the summary of the article"
    )
    description: Selector | None = Field(
        None, description="Selector to select the description of the article"
    )

    image: ImageConfig | None = Field(
        None, description="Configuration for selecting the image data of the article"
    )
    links: list[LinkConfig] = Field(
        [],
        description="Configuration for selecting article-level links from the document",
    )

    authors: list[PersonConfig] = Field(
        [], description="Configuration for selecting the author data of the article"
    )

    contributors: list[PersonConfig] = Field(
        [],
        description="Configuration for selecting the contributor data of the article",
    )

    def extract(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> list[Article]:

        out: list[Article] = []
        for article_selector in self.root.select(selector):
            article_out = {}

            id = self.id.select(article_selector).get()
            title = self.title.select(article_selector).get()
            subtitle = (
                self.subtitle.select(article_selector).get() if self.subtitle else None
            )
            summary = (
                self.summary.select(article_selector).get() if self.summary else None
            )
            description = (
                self.description.select(article_selector).get()
                if self.description
                else None
            )

            article_out["id"] = id
            article_out["title"] = title
            article_out["subtitle"] = subtitle
            article_out["summary"] = summary
            article_out["description"] = description

            if self.image:
                article_out["image"] = self.image.extract(article_selector)

            links: list[Link] = []
            for link_config in self.links:
                links.extend(link_config.extract(article_selector))

            article_out["links"] = links

            out.append(Article.model_validate(article_out))

        return out


class ParselExtractor(Extractor):
    url: str = Field(..., description="URL to fetch the data from")
    document_type: DocumentType = Field(
        DocumentType.HTML, description="Type of the document to parse"
    )

    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the feed"
    )

    id: Selector = Field(..., description="Selector to select the ID of the feed")
    title: Selector = Field(..., description="Selector to select the title of the feed")
    subtitle: Selector | None = Field(
        None, description="Selector to select the subtitle of the feed"
    )
    description: Selector | None = Field(
        None, description="Selector to select the description of the feed"
    )

    language: Selector | None = Field(
        None, description="Selector to select the language of the feed"
    )
    logo: Selector | None = Field(
        None, description="Selector to select the logo URL of the feed"
    )

    links: list[LinkConfig] = Field(
        [], description="Configuration for selecting feed-level links from the document"
    )

    articles: list[ArticlesConfig] = Field(
        [], description="Configuration for selecting articles from the document"
    )

    @override
    async def extract(self, config: ExtractorConfig) -> Feed:

        async with settings.http.get_async_client() as client:
            response = await client.get(self.url)
            _ = response.raise_for_status()

        selector = ParselSelector(text=response.text, type=self.document_type.value)

        root = self.root.select(selector)
        id = self.id.select(root).get()
        title = self.title.select(root).get()
        subtitle = self.subtitle.select(root).get() if self.subtitle else None
        description = self.description.select(root).get() if self.description else None
        language = self.language.select(root).get() if self.language else None
        logo = self.logo.select(root).get() if self.logo else None

        links: list[Link] = []
        for link_config in self.links:
            links.extend(link_config.extract(root))

        articles: list[Article] = []
        for articles_config in self.articles:
            articles.extend(articles_config.extract(root))

        if id is None:
            raise ValueError("Feed ID is required but could not be extracted")

        if description is None:
            raise ValueError("Feed description is required but could not be extracted")

        return Feed(
            id=id,
            title=title,
            subtitle=subtitle,
            description=description,
            language=language,
            logo=logo,
            links=links,
            articles=articles,
        )
