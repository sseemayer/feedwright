from __future__ import annotations

from datetime import datetime
from typing import Any

from lxml.etree import _Element, _ElementTree

def xml_fromstring(xmlstring: str | bytes) -> _Element: ...
def xml_elem(name: str, parent: _Element | None = None, **kwargs: Any) -> _Element: ...
def ensure_format(
    val: dict[str, Any] | list[dict[str, Any]] | None,
    allowed: set[str],
    required: set[str],
    allowed_values: dict[str, set[str]] | None = None,
    defaults: dict[str, Any] | None = None,
) -> list[dict[str, Any]]: ...
def formatRFC2822(date: datetime) -> str: ...
