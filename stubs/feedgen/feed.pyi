from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, overload

from feedgen.entry import FeedEntry

class FeedGenerator:
    # --- title ---
    @overload
    def title(self) -> str | None: ...
    @overload
    def title(self, title: str) -> FeedGenerator: ...
    def title(self, title: str | None = None) -> str | None | FeedGenerator: ...

    # --- id ---
    @overload
    def id(self) -> str | None: ...
    @overload
    def id(self, id: str) -> FeedGenerator: ...
    def id(self, id: str | None = None) -> str | None | FeedGenerator: ...

    # --- updated / lastBuildDate ---
    @overload
    def updated(self) -> datetime | None: ...
    @overload
    def updated(self, updated: str | datetime) -> FeedGenerator: ...
    def updated(self, updated: str | datetime | None = None) -> datetime | None | FeedGenerator: ...
    def lastBuildDate(self, lastBuildDate: str | datetime | None = None) -> datetime | None | FeedGenerator: ...

    # --- author ---
    @overload
    def author(self) -> list[dict[str, str]]: ...
    @overload
    def author(
        self,
        author: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedGenerator: ...
    def author(
        self,
        author: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedGenerator: ...

    # --- link ---
    @overload
    def link(self) -> list[dict[str, str]]: ...
    @overload
    def link(
        self,
        link: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedGenerator: ...
    def link(
        self,
        link: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedGenerator: ...

    # --- category ---
    @overload
    def category(self) -> list[dict[str, str]]: ...
    @overload
    def category(
        self,
        category: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedGenerator: ...
    def category(
        self,
        category: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedGenerator: ...

    # --- contributor ---
    @overload
    def contributor(self) -> list[dict[str, str]]: ...
    @overload
    def contributor(
        self,
        contributor: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedGenerator: ...
    def contributor(
        self,
        contributor: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedGenerator: ...

    # --- generator ---
    @overload
    def generator(self) -> str | None: ...
    @overload
    def generator(self, generator: str, version: str | None = ..., uri: str | None = ...) -> FeedGenerator: ...
    def generator(
        self,
        generator: str | None = None,
        version: str | None = None,
        uri: str | None = None,
    ) -> str | None | FeedGenerator: ...

    # --- icon ---
    @overload
    def icon(self) -> str | None: ...
    @overload
    def icon(self, icon: str) -> FeedGenerator: ...
    def icon(self, icon: str | None = None) -> str | None | FeedGenerator: ...

    # --- logo ---
    @overload
    def logo(self) -> str | None: ...
    @overload
    def logo(self, logo: str) -> FeedGenerator: ...
    def logo(self, logo: str | None = None) -> str | None | FeedGenerator: ...

    # --- image ---
    def image(
        self,
        url: str | None = None,
        title: str | None = None,
        link: str | None = None,
        width: str | int | None = None,
        height: str | int | None = None,
        description: str | None = None,
    ) -> dict[str, str | int] | None | FeedGenerator: ...

    # --- rights / copyright ---
    @overload
    def rights(self) -> str | None: ...
    @overload
    def rights(self, rights: str) -> FeedGenerator: ...
    def rights(self, rights: str | None = None) -> str | None | FeedGenerator: ...
    def copyright(self, copyright: str | None = None) -> str | None | FeedGenerator: ...

    # --- subtitle / description ---
    @overload
    def subtitle(self) -> str | None: ...
    @overload
    def subtitle(self, subtitle: str) -> FeedGenerator: ...
    def subtitle(self, subtitle: str | None = None) -> str | None | FeedGenerator: ...
    def description(self, description: str | None = None) -> str | None | FeedGenerator: ...

    # --- RSS-only fields ---
    def docs(self, docs: str | None = None) -> str | None | FeedGenerator: ...
    def language(self, language: str | None = None) -> str | None | FeedGenerator: ...
    def managingEditor(self, managingEditor: str | None = None) -> str | None | FeedGenerator: ...
    def pubDate(self, pubDate: str | datetime | None = None) -> datetime | None | FeedGenerator: ...
    def rating(self, rating: str | None = None) -> str | None | FeedGenerator: ...
    def skipHours(self, hours: set[int] | list[int] | None = None, replace: bool = False) -> set[int] | None | FeedGenerator: ...
    def skipDays(self, days: set[str] | list[str] | None = None, replace: bool = False) -> set[str] | None | FeedGenerator: ...
    def textInput(
        self,
        title: str | None = None,
        description: str | None = None,
        name: str | None = None,
        link: str | None = None,
    ) -> dict[str, str] | None | FeedGenerator: ...
    def ttl(self, ttl: int | None = None) -> int | None | FeedGenerator: ...
    def webMaster(self, webMaster: str | None = None) -> str | None | FeedGenerator: ...
    def cloud(
        self,
        domain: str | None = None,
        port: int | None = None,
        path: str | None = None,
        registerProcedure: str | None = None,
        protocol: str | None = None,
    ) -> dict[str, Any] | None | FeedGenerator: ...

    # --- entry management ---
    def add_entry(self, feedEntry: FeedEntry | None = None, order: Literal["prepend", "append"] = "prepend") -> FeedEntry: ...
    def add_item(self, item: FeedEntry | None = None) -> FeedEntry: ...
    @overload
    def entry(self) -> list[FeedEntry]: ...
    @overload
    def entry(self, entry: list[FeedEntry], replace: bool = ...) -> FeedGenerator: ...
    def entry(self, entry: list[FeedEntry] | None = None, replace: bool = False) -> list[FeedEntry] | FeedGenerator: ...
    def item(self, item: list[FeedEntry] | None = None, replace: bool = False) -> list[FeedEntry] | FeedGenerator: ...
    def remove_entry(self, entry: FeedEntry | int) -> None: ...
    def remove_item(self, item: FeedEntry | int) -> None: ...

    # --- output ---
    def atom_str(
        self,
        pretty: bool = False,
        extensions: bool = True,
        encoding: str = "UTF-8",
        xml_declaration: bool = True,
    ) -> bytes: ...
    def atom_file(
        self,
        filename: str,
        extensions: bool = True,
        pretty: bool = False,
        encoding: str = "UTF-8",
        xml_declaration: bool = True,
    ) -> None: ...
    def rss_str(
        self,
        pretty: bool = False,
        extensions: bool = True,
        encoding: str = "UTF-8",
        xml_declaration: bool = True,
    ) -> bytes: ...
    def rss_file(
        self,
        filename: str,
        extensions: bool = True,
        pretty: bool = False,
        encoding: str = "UTF-8",
        xml_declaration: bool = True,
    ) -> None: ...

    # --- extensions ---
    def load_extension(self, name: str, atom: bool = True, rss: bool = True) -> None: ...
    def register_extension(
        self,
        namespace: str,
        extension_class_feed: type | None = None,
        extension_class_entry: type | None = None,
        atom: bool = True,
        rss: bool = True,
    ) -> None: ...

    # Dynamic extension attributes (populated by load_extension)
    def __getattr__(self, name: str) -> Any: ...
