from __future__ import annotations

from feedgen.ext.base import BaseEntryExtension, BaseExtension
from lxml.etree import _Element

class MediaExtension(BaseExtension):
    def extend_ns(self) -> dict[str, str]: ...
    def extend_rss(self, feed: _Element) -> _Element: ...
    def extend_atom(self, feed: _Element) -> _Element: ...

class MediaEntryExtension(BaseEntryExtension):
    def extend_ns(self) -> dict[str, str]: ...
    def extend_rss(self, entry: _Element) -> _Element: ...
    def extend_atom(self, entry: _Element) -> _Element: ...

    def content(
        self,
        content: dict[str, str | int] | list[dict[str, str | int]] | None = None,
        replace: bool = False,
        group: str = "default",
        **kwargs: str | int,
    ) -> list[dict[str, str | int]] | None | MediaEntryExtension: ...

    def thumbnail(
        self,
        thumbnail: dict[str, str | int] | list[dict[str, str | int]] | None = None,
        replace: bool = False,
        group: str = "default",
        **kwargs: str | int,
    ) -> list[dict[str, str | int]] | None | MediaEntryExtension: ...
