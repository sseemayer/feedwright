import asyncio
import hjson  # pyright: ignore[reportMissingTypeStubs]
import json
import logging
import re
import toml
import yaml

from fastapi import HTTPException, status
from pathlib import Path
from typing import Any, Callable, cast


from app.models.feed import Feed
from app.settings import settings
from app.models.extractor import Extractor, ExtractorConfig

logger = logging.getLogger(__name__)


_GENERATE_CONFIG_SYSTEM_PROMPT = """\
You are an expert web scraping configuration generator for the Feedwright extraction system.

Your task is to analyse the provided document and produce a valid ParselExtractor configuration \
that extracts a structured RSS/Atom-style feed from it.

## Selector types

Every selector field must use exactly one of these forms:

| Form | When to use |
|------|-------------|
| `{"constant": "<value>"}` | The value is static and known in advance (e.g. feed title, base URL). |
| `{"css": "<selector>"}` | HTML documents — prefer for class/id-based targeting. |
| `{"xpath": "<expr>"}` | HTML or XML documents — use for attribute access, text nodes, or conditions. |
| `{"jmespath": "<expr>"}` | JSON documents — use for all field access. |
| `{"selectors": [<sel1>, <sel2>, ...]}` | Try each selector in order; return the first non-empty result. |

**Never** emit an empty object `{}` for a selector field — that is a no-op pass-through and \
will produce no value.

## Required vs optional fields

`id`, `title`, and `description` are **required** at the feed level — the extractor will raise \
an error at runtime if any of these resolve to an empty or missing value.  You must always \
provide selectors for all three.

The generated configuration is **validated by actually running it** against the document. \
The `articles` list must resolve to **at least one article** — if your selectors return zero \
articles the configuration will be rejected and you will be asked to fix it. \
Always include at least one `ArticlesConfig` entry with a `root` selector that matches the \
repeating item elements in the document.

## Document-type guidance

- **HTML**: Use `css` or `xpath` selectors. For text content use `::text` pseudo-element \
  (CSS) or `/text()` axis (XPath). For attributes use `::attr(<name>)` (CSS) or `/@<name>` \
  (XPath). Meta tags: `//meta[@name='description']/@content`.
- **JSON**: Use `jmespath` selectors. Iterate arrays with `data[*].field`. Convert numbers \
  to strings with `to_string(field)`. Concatenate with `join('', [a, b])`.
- **XML**: Use `xpath` selectors with namespace-aware expressions where needed.

## Scoping with `root`

The optional `root` field on `ArticlesConfig`, `LinkConfig`, `ImageConfig`, and `PersonConfig` \
narrows the context.  All sibling selectors in that same config object run against **each node \
matched by `root`**, not the document root.  Always set `articles[].root` to the repeating \
element (e.g. each `<article>` tag or each JSON array item).

## CSS selector quick-reference

- Text of element: `h1::text`
- Attribute: `a::attr(href)`
- Class: `.my-class`
- Nested: `article h2::text`
- Multiple classes: `div.foo.bar::text`

**Important — CSS class matching caveat:** CSS class selectors (`.foo`) only match \
elements whose `class` attribute is *exactly* `foo` or contains `foo` as a \
space-separated token.  When an element has multiple classes such as \
`class="news news--module"`, the selector `article.news` will **not** match it \
because `news` is not the full class string.  For multi-class elements always \
prefer XPath with `contains(@class, 'news')` instead.

## XPath quick-reference

- Text node: `//h1/text()`
- Attribute: `//a/@href`
- Conditional: `//div[@class='title']/text()`
- Relative (inside root context): `.//span[@class='date']/text()`
- Multi-class match: `//article[contains(@class, 'news')]`
- Either of two classes: `//article[@class='teaser' or contains(@class, 'news')]`

## JMESPath quick-reference

- Nested key: `attributes.title`
- Array iteration: `data[*].id`
- First item: `data[0]`
- String coerce: `to_string(id)`
- Concatenation: `join('', ['https://example.com/', slug])`

## Examples

### HTML feed

```yaml
url: "https://example.com/news"
document_type: html
id: {constant: "https://example.com/news"}
title: {constant: "Example News"}
description: {xpath: "//meta[@name='description']/@content"}
articles:
  - root: {css: "article.post"}
    id: {css: "a::attr(href)"}
    title: {css: "h2::text"}
    description: {css: "p.summary::text"}
    links:
      - href: {css: "a::attr(href)"}
        title: {css: "h2::text"}
```

### JSON feed

```yaml
url: "https://api.example.com/posts"
document_type: json
id: {constant: "https://example.com/posts"}
title: {constant: "Example Posts"}
description: {constant: "Latest posts from Example."}
articles:
  - root: {jmespath: "data"}
    id: {jmespath: "to_string(id)"}
    title: {jmespath: "attributes.title"}
    description: {jmespath: "attributes.summary"}
    links:
      - href: {jmespath: "join('', ['https://example.com/posts/', slug])"}
        title: {jmespath: "attributes.title"}
```
"""


# Maximum number of characters to send to the LLM for HTML/XML documents.
# Large pages are trimmed to reduce token usage and avoid context-window truncation.
_HTML_CHAR_LIMIT = 80_000
# Maximum number of array items to retain per JSON array during pre-processing.
_JSON_ARRAY_SAMPLE = 3


def _preprocess_html(text: str) -> str:
    """Strip noise from HTML before sending to the LLM."""
    # Remove <script> and <style> blocks entirely.
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove SVG blocks.
    text = re.sub(r"<svg[^>]*>.*?</svg>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Collapse runs of whitespace to single spaces to reduce size.
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Hard-truncate if still too long.
    if len(text) > _HTML_CHAR_LIMIT:
        text = text[:_HTML_CHAR_LIMIT] + "\n\n[... document truncated ...]"
    return text.strip()


def _trim_json_arrays(obj: Any, max_items: int = _JSON_ARRAY_SAMPLE) -> Any:  # pyright: ignore[reportExplicitAny]
    """Recursively trim long arrays in a parsed JSON object to a small sample."""
    if isinstance(obj, list):
        trimmed = [_trim_json_arrays(item, max_items) for item in obj[:max_items]]
        return trimmed
    if isinstance(obj, dict):
        return {k: _trim_json_arrays(v, max_items) for k, v in obj.items()}
    return obj


def _preprocess_json(text: str) -> str:
    """Parse JSON, trim large arrays to a sample, and re-serialise."""
    try:
        parsed = json.loads(text)
        trimmed = _trim_json_arrays(parsed)
        return json.dumps(trimmed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        # Not valid JSON — return as-is (the LLM will cope).
        return text


def _preprocess_document(text: str, content_type: str) -> str:
    """Detect document type from Content-Type header and pre-process accordingly."""
    ct = content_type.lower()
    if "json" in ct:
        return _preprocess_json(text)
    # XML and HTML both benefit from the same HTML-style stripping.
    return _preprocess_html(text)


EXTENSION_TO_PARSER: dict[str, Callable[[Path], dict[str, Any]]] = {}  # pyright: ignore[reportExplicitAny]


def register_parser(extension: str | list[str]):

    if isinstance(extension, str):
        extension = [extension]

    def decorator(
        func: Callable[[Path], dict[str, Any]],  # pyright: ignore[reportExplicitAny]
    ) -> Callable[[Path], dict[str, Any]]:  # pyright: ignore[reportExplicitAny]
        for ext in extension:
            EXTENSION_TO_PARSER[ext] = func
        return func

    return decorator


@register_parser(["toml"])
def parse_toml(path: Path) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    with path.open() as f:
        return toml.load(f)


@register_parser(["json", "hjson"])
def parse_hjson(path: Path) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    with path.open() as f:
        return hjson.load(f)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]


@register_parser(["yaml", "yml"])
def parse_yaml(path: Path) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    with path.open() as f:
        return yaml.safe_load(f)  # pyright: ignore[reportAny]


class Extractors:
    @property
    def extractors(self) -> dict[str, Path]:
        return {
            path.stem: path
            for base_path in settings.config_paths
            for extension in [f"*.{ext}" for ext in EXTENSION_TO_PARSER.keys()]
            for path in (base_path / "feeds").glob(extension)
        }

    def get_extractor_class(self, plugin: str) -> type[Extractor]:
        pkg_name, class_name = plugin.split(":")

        pkg = __import__(pkg_name, fromlist=[class_name])  # pyright: ignore[reportAny]
        extractor_cls = cast(type[Extractor], getattr(pkg, class_name))  # pyright: ignore[reportAny]

        return extractor_cls

    async def get(self, name: str) -> Feed:
        """Get the RSS feed for a specific extractor name."""
        path = self.extractors.get(name)
        if path is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"No extractor found with name '{name}'"
            )

        parser = EXTENSION_TO_PARSER.get(path.suffix[1:])
        if parser is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"No parser registered for extension '{path.suffix}'",
            )

        config = parser(path)

        extractor_config = ExtractorConfig.model_validate(config)
        extractor_cls = self.get_extractor_class(extractor_config.plugin)
        extractor = extractor_cls(**extractor_config.config)  # pyright: ignore[reportAny]

        return await extractor.extract(extractor_config)

    async def generate_config(
        self,
        url: str,
        plugin: str,
        max_validation_retries: int = 3,
    ) -> Extractor:
        """Generate an extractor configuration for *url* using the configured LLM.

        The generated config is executed against the live document after each
        LLM response.  If the extraction fails or returns zero articles the
        error is appended to the conversation as a user message and the LLM is
        asked to revise its answer.  This continues for up to
        *max_validation_retries* rounds.
        """
        import instructor
        from litellm import completion

        client = instructor.from_litellm(completion, mode=instructor.Mode.JSON)

        extractor_class = self.get_extractor_class(plugin)

        http_client = settings.http.get_sync_client()
        res = http_client.get(url)
        _ = res.raise_for_status()

        content_type = res.headers.get("content-type", "text/html")
        document = _preprocess_document(res.text, content_type)

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": _GENERATE_CONFIG_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Generate a configuration to extract an RSS feed from this "
                    f"document (fetched from {url}):\n\n{document}"
                ),
            },
        ]

        last_error: Exception | None = None

        for attempt in range(1, max_validation_retries + 1):
            logger.debug(
                "generate_config validation attempt %d/%d", attempt, max_validation_retries
            )

            # Ask the LLM (with instructor's own schema-level retry built in).
            result: Extractor = client.chat.completions.create(
                model=settings.ai.model,
                api_key=settings.ai.key,
                base_url=settings.ai.url,
                response_model=extractor_class,
                max_retries=3,
                messages=messages,  # type: ignore[arg-type]
            )

            # Append the assistant's answer to the conversation so that any
            # subsequent retry has the full context.
            messages.append(
                {
                    "role": "assistant",
                    "content": result.model_dump_json(exclude_none=True),
                }
            )

            # --- Runtime validation -----------------------------------------
            # Instantiate a minimal ExtractorConfig so we can call extract().
            dummy_config = ExtractorConfig(plugin=plugin, config={})
            try:
                feed: Feed = await result.extract(dummy_config)
            except Exception as exc:
                last_error = exc
                error_msg = (
                    f"The configuration you produced was structurally valid but "
                    f"failed at runtime with the following error:\n\n"
                    f"{type(exc).__name__}: {exc}\n\n"
                    f"Please fix the selectors and return a corrected configuration."
                )
                logger.debug("generate_config extraction error (attempt %d): %s", attempt, exc)
                messages.append({"role": "user", "content": error_msg})
                continue

            # Check that at least one article was extracted.
            if not feed.articles:
                last_error = ValueError("Extraction succeeded but returned zero articles.")
                # Show the LLM the article root selectors it used so it can self-diagnose.
                used_roots = [
                    ac.model_dump(mode="json", include={"root"}, exclude_none=True)
                    for ac in result.articles  # type: ignore[attr-defined]
                ] if hasattr(result, "articles") else []
                root_info = (
                    f"\nYour `articles` root selectors were: {used_roots}"
                    if used_roots
                    else ""
                )
                error_msg = (
                    "The configuration you produced ran without errors but returned "
                    "zero articles." + root_info + "\n\n"
                    "Possible causes:\n"
                    "1. The CSS class selector does not match because the element has "
                    "multiple classes (e.g. `class=\"news news--module\"`). "
                    "Use XPath `contains(@class, 'news')` instead of CSS `.news`.\n"
                    "2. The root selector points to the wrong element type.\n"
                    "3. The document uses a different structure than expected.\n\n"
                    "Look at the `<article>` tags and their `class` attributes in the "
                    "document, then use XPath with `contains(@class, ...)` to match "
                    "them. Return a corrected configuration."
                )
                logger.debug(
                    "generate_config zero articles (attempt %d), roots: %s",
                    attempt, used_roots,
                )
                messages.append({"role": "user", "content": error_msg})
                continue

            # Success — return the validated extractor.
            return result

        # All attempts exhausted — surface the last error to the caller.
        raise ValueError(
            f"Could not generate a valid configuration after {max_validation_retries} "
            f"attempts. Last error: {last_error}"
        ) from last_error


extractors = Extractors()
