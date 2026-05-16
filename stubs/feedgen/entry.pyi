from __future__ import annotations

from datetime import datetime
from typing import Any, overload

from lxml.etree import _Element

class FeedEntry:
    # --- title ---
    @overload
    def title(self) -> str | None: ...
    @overload
    def title(self, title: str) -> FeedEntry: ...
    def title(self, title: str | None = None) -> str | None | FeedEntry: ...

    # --- id / guid ---
    @overload
    def id(self) -> str | None: ...
    @overload
    def id(self, id: str) -> FeedEntry: ...
    def id(self, id: str | None = None) -> str | None | FeedEntry: ...
    def guid(self, guid: str | None = None, permalink: bool = False) -> str | None | FeedEntry: ...

    # --- updated ---
    @overload
    def updated(self) -> datetime | None: ...
    @overload
    def updated(self, updated: str | datetime) -> FeedEntry: ...
    def updated(self, updated: str | datetime | None = None) -> datetime | None | FeedEntry: ...

    # --- author ---
    @overload
    def author(self) -> list[dict[str, str]]: ...
    @overload
    def author(
        self,
        author: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedEntry: ...
    def author(
        self,
        author: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedEntry: ...

    # --- content ---
    @overload
    def content(self) -> dict[str, str | None] | None: ...
    @overload
    def content(self, content: str, src: str | None = ..., type: str | None = ...) -> FeedEntry: ...
    def content(
        self,
        content: str | None = None,
        src: str | None = None,
        type: str | None = None,
    ) -> dict[str, str | None] | None | FeedEntry: ...

    # --- link ---
    @overload
    def link(self) -> list[dict[str, str]]: ...
    @overload
    def link(
        self,
        link: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedEntry: ...
    def link(
        self,
        link: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedEntry: ...

    # --- summary / description ---
    @overload
    def summary(self) -> str | None: ...
    @overload
    def summary(self, summary: str, type: str | None = ...) -> FeedEntry: ...
    def summary(self, summary: str | None = None, type: str | None = None) -> str | None | FeedEntry: ...
    def description(self, description: str | None = None, isSummary: bool = False) -> str | None | FeedEntry: ...

    # --- category ---
    @overload
    def category(self) -> list[dict[str, str]]: ...
    @overload
    def category(
        self,
        category: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedEntry: ...
    def category(
        self,
        category: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedEntry: ...

    # --- contributor ---
    @overload
    def contributor(self) -> list[dict[str, str]]: ...
    @overload
    def contributor(
        self,
        contributor: dict[str, str] | list[dict[str, str]],
        replace: bool = ...,
        **kwargs: str,
    ) -> FeedEntry: ...
    def contributor(
        self,
        contributor: dict[str, str] | list[dict[str, str]] | None = None,
        replace: bool = False,
        **kwargs: str,
    ) -> list[dict[str, str]] | FeedEntry: ...

    # --- published / pubDate ---
    @overload
    def published(self) -> datetime | None: ...
    @overload
    def published(self, published: str | datetime) -> FeedEntry: ...
    def published(self, published: str | datetime | None = None) -> datetime | None | FeedEntry: ...
    def pubDate(self, pubDate: str | datetime | None = None) -> datetime | None | FeedEntry: ...

    # --- rights ---
    @overload
    def rights(self) -> str | None: ...
    @overload
    def rights(self, rights: str) -> FeedEntry: ...
    def rights(self, rights: str | None = None) -> str | None | FeedEntry: ...

    # --- comments ---
    @overload
    def comments(self) -> str | None: ...
    @overload
    def comments(self, comments: str) -> FeedEntry: ...
    def comments(self, comments: str | None = None) -> str | None | FeedEntry: ...

    # --- source ---
    @overload
    def source(self) -> dict[str, str] | None: ...
    @overload
    def source(self, url: str, title: str) -> FeedEntry: ...
    def source(self, url: str | None = None, title: str | None = None) -> dict[str, str] | None | FeedEntry: ...

    # --- enclosure ---
    def enclosure(
        self,
        url: str | None = None,
        length: str | int | None = None,
        type: str | None = None,
    ) -> dict[str, str] | None | FeedEntry: ...

    # --- ttl ---
    @overload
    def ttl(self) -> int | None: ...
    @overload
    def ttl(self, ttl: int) -> FeedEntry: ...
    def ttl(self, ttl: int | None = None) -> int | None | FeedEntry: ...

    # --- XML rendering (used internally) ---
    def atom_entry(self, extensions: bool = True) -> _Element: ...
    def rss_entry(self, extensions: bool = True) -> _Element: ...

    # --- extensions ---
    def load_extension(self, name: str, atom: bool = True, rss: bool = True) -> None: ...
    def register_extension(
        self,
        namespace: str,
        extension_class_entry: type | None = None,
        atom: bool = True,
        rss: bool = True,
    ) -> None: ...

    def __getattr__(self, name: str) -> Any: ...
