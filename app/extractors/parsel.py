import json

from abc import ABCMeta, abstractmethod
from enum import Enum
from urllib.parse import urljoin

import cssselect
from parsel import Selector as ParselSelector, SelectorList
from typing import Literal, cast, override
from pydantic import BaseModel, Field, ConfigDict
from fastapi import HTTPException, status

from app.models.extractor import Extractor, ExtractorConfig, SourceDocument
from app.models.feed import Article, Feed, Image, Link, Person


class DocumentType(str, Enum):
    HTML = "html"
    XML = "xml"
    JSON = "json"


class SelectorBase(BaseModel, metaclass=ABCMeta):
    model_config = ConfigDict(extra="forbid")

    re: str | None = Field(
        None, description="Regular expression to apply to the selected data"
    )

    re_first: str | None = Field(
        None,
        description="Regular expression to apply to the selected data, returning the first match",
    )

    @abstractmethod
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]: ...

    def select(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        selected = self.select_raw(selector)

        if self.re is not None:
            selected = SelectorList(
                [
                    ParselSelector(json.dumps(match), type="json")
                    for match in selected.re(self.re)
                ]
            )

        if self.re_first is not None:
            selected = selected.re_first(self.re_first)

            selected = SelectorList(
                [ParselSelector(json.dumps(selected), type="json")] if selected else []
            )

        return selected


class ConstantSelector(SelectorBase):
    """A constant selector that always returns the same value"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"constant": "https://example.com/"}]},
    )

    constant: str = Field(..., description="The constant value to return")

    @override
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:

        return SelectorList(
            [ParselSelector(text=json.dumps(self.constant), type="json")]
        )


class CssSelector(SelectorBase):
    """A CSS selector to select the data from a HTML document"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"css": "h1::text"}, {"css": "a::attr(href)"}]},
    )

    css: str = Field(
        ..., description="CSS selector to select the data from the document"
    )

    @override
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:

        try:
            return selector.css(self.css)

        except cssselect.parser.SelectorSyntaxError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": f"Invalid CSS selector: {self.css}",
                    "message": str(e),
                },
            )


class XPathSelector(SelectorBase):
    """An XPath selector to select the data from a HTML or XML document"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"xpath": "//h1/text()"}, {"xpath": "//a/@href"}]
        },
    )

    xpath: str = Field(
        ..., description="XPath selector to select the data from the document"
    )

    @override
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:

        try:
            return selector.xpath(self.xpath)

        except ValueError as e:
            PREFIX = "ValueError: XPath error: "

            e_as_str = str(e)
            if e_as_str.startswith(PREFIX):
                e_as_str = e_as_str[len(PREFIX) :]

                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": f"Invalid XPath selector: {self.xpath}",
                        "message": e_as_str,
                    },
                )

            else:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": f"Error applying XPath selector: {self.xpath}",
                        "message": e_as_str,
                    },
                )


class JmesPathSelector(SelectorBase):
    """A JMESPath selector to select the data from a JSON document"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"jmespath": "data[*].title"}, {"jmespath": "to_string(id)"}]
        },
    )

    jmespath: str = Field(
        ..., description="JMESPath selector to select the data from the document"
    )

    @override
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        return selector.jmespath(self.jmespath)


class NoOpSelector(SelectorBase):
    """A no-op selector that returns the input selector as is. Use only for root context fields, never for value extraction."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"type": "noop"}]},
    )

    @override
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        return (
            selector if isinstance(selector, SelectorList) else SelectorList([selector])
        )


class OrSelector(SelectorBase):
    """A selector that tries multiple selectors in order and returns the first non-empty result"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"selectors": [{"css": "h1::text"}, {"xpath": "//h1/text()"}]}]
        },
    )

    selectors: list["Selector"] = Field(
        ..., description="List of selectors to try in order"
    )

    @override
    def select_raw(
        self, selector: ParselSelector | SelectorList[ParselSelector]
    ) -> SelectorList[ParselSelector]:
        for sel in self.selectors:
            selected = sel.select(selector)
            if selected:
                return selected

        return SelectorList([])


type Selector = (
    ConstantSelector
    | CssSelector
    | XPathSelector
    | JmesPathSelector
    | NoOpSelector
    | OrSelector
)


class LinkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the link data"
    )
    href: Selector = Field(
        ...,
        description="Selector to select the href of the link",
        examples=[{"css": "a::attr(href)"}, {"xpath": "//a/@href"}],
    )
    title: Selector = Field(
        ...,
        description="Selector to select the title of the link",
        examples=[{"css": "a::text"}, {"xpath": "//a/text()"}],
    )

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
        self,
        selector: ParselSelector | SelectorList[ParselSelector],
        base_url: str,
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
                    link_out[key] = str(value).strip()

            if "href" not in link_out:
                continue

            link_out["href"] = urljoin(base_url, link_out["href"])

            out.append(Link.model_validate(link_out))

        return out


class ImageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
        self,
        selector: ParselSelector | SelectorList[ParselSelector],
        base_url: str,
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
                image_out[key] = str(value).strip()

        if "url" not in image_out:
            return None

        image_out["url"] = urljoin(base_url, image_out["url"])

        return Image.model_validate(image_out)


class PersonConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
        self,
        selector: ParselSelector | SelectorList[ParselSelector],
        base_url: str,
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
                    person_out[key] = str(value).strip()

            if "uri" in person_out:
                person_out["uri"] = urljoin(base_url, person_out["uri"])

            out.append(Person.model_validate(person_out))

        return out


class ArticlesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: Selector = Field(
        NoOpSelector(),
        description="Selector to select the repeating article element",
        examples=[
            {"css": "article.post"},
            {"xpath": "//article"},
            {"jmespath": "data"},
        ],
    )

    id: Selector = Field(
        ...,
        description="Selector to select the ID of the article (relative to root)",
        examples=[
            {"css": "a::attr(href)"},
            {"xpath": ".//a/@href"},
            {"jmespath": "to_string(id)"},
        ],
    )
    title: Selector = Field(
        ...,
        description="Selector to select the title of the article (relative to root)",
        examples=[
            {"css": "h2::text"},
            {"xpath": ".//h2/text()"},
            {"jmespath": "title"},
        ],
    )
    summary: Selector | None = Field(
        None,
        description="Selector to select the summary of the article (relative to root)",
        examples=[{"css": "p.summary::text"}, {"jmespath": "summary"}],
    )
    description: Selector | None = Field(
        None,
        description="Selector to select the description of the article (relative to root)",
        examples=[{"css": "p::text"}, {"jmespath": "description"}],
    )
    content: Selector | None = Field(
        None, description="Selector to select the content of the article"
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
        self,
        selector: ParselSelector | SelectorList[ParselSelector],
        base_url: str,
    ) -> list[Article]:

        out: list[Article] = []
        for article_selector in self.root.select(selector):
            article_out = {}

            id = self.id.select(article_selector).get()
            title = self.title.select(article_selector).get()
            summary = (
                self.summary.select(article_selector).get() if self.summary else None
            )
            description = (
                self.description.select(article_selector).get()
                if self.description
                else None
            )
            content = (
                self.content.select(article_selector).get() if self.content else None
            )

            article_out["id"] = str(id).strip() if id else None
            article_out["title"] = str(title).strip() if title else None
            article_out["summary"] = str(summary).strip() if summary else None
            article_out["description"] = (
                str(description).strip() if description else None
            )
            article_out["content"] = str(content).strip() if content else None

            if self.image:
                article_out["image"] = self.image.extract(article_selector, base_url)

            links: list[Link] = []
            for link_config in self.links:
                links.extend(link_config.extract(article_selector, base_url))

            article_out["links"] = links

            out.append(Article.model_validate(article_out))

        return out


class ParselExtractor(Extractor):
    model_config = ConfigDict(extra="forbid")

    autoconfigure_instructions = """\
Use CSS or XPath selectors for HTML, XPath for XML, and JMESPath for JSON.
Set each articles root selector to the repeating item and make child selectors relative
to that root. Use constant selectors for stable feed metadata when appropriate. Never
use an empty selector for a value. Feed id, title, and description are required, and
the articles configuration must extract at least one item. Configure a feed link and
an article link so that the result can render as both RSS and Atom.

Rember that for JMESPath selectors, string concatenation is performed using a join method:

```
join(' ', [field1, field2])  # Concatenate field1 and field2 with a space as a separator
```
"""

    document_type: DocumentType = Field(
        DocumentType.HTML, description="Type of the document to parse"
    )

    root: Selector = Field(
        NoOpSelector(), description="Selector to select the root of the feed"
    )

    id: Selector = Field(
        ...,
        description="Selector to select the ID of the feed. Use a constant selector for a static URL.",
        examples=[
            {"constant": "https://example.com/"},
            {"css": "link[rel=canonical]::attr(href)"},
        ],
    )
    title: Selector = Field(
        ...,
        description="Selector to select the title of the feed",
        examples=[
            {"constant": "Example News"},
            {"css": "title::text"},
            {"xpath": "//title/text()"},
        ],
    )
    subtitle: Selector | None = Field(
        None,
        description="Selector to select the subtitle of the feed",
        examples=[
            {"css": "meta[name=description]::attr(content)"},
            {"xpath": "//meta[@name='description']/@content"},
        ],
    )
    description: Selector = Field(
        ...,
        description="Selector to select the description of the feed. Required: extraction will fail if this resolves to an empty value.",
        examples=[
            {"xpath": "//meta[@name='description']/@content"},
            {"css": "meta[name=description]::attr(content)"},
            {"constant": "Latest articles"},
        ],
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
    async def extract(self, document: SourceDocument, config: ExtractorConfig) -> Feed:
        selector = ParselSelector(text=document.content, type=self.document_type.value)

        root = self.root.select(selector)
        id = self.id.select(root).get()
        title = self.title.select(root).get()
        subtitle = self.subtitle.select(root).get() if self.subtitle else None
        description = self.description.select(root).get()
        language = self.language.select(root).get() if self.language else None
        logo = self.logo.select(root).get() if self.logo else None

        links: list[Link] = []
        for link_config in self.links:
            links.extend(link_config.extract(root, document.url))

        articles: list[Article] = []
        for articles_config in self.articles:
            articles.extend(articles_config.extract(root, document.url))

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
