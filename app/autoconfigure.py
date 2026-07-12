import json
import re
import traceback

from dataclasses import dataclass
from typing import Any

import instructor
import litellm
from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.extract import extractors, fetch_document
from app.models.extractor import Extractor, ExtractorConfig, SourceDocument
from app.models.feed import Feed
from app.render import OutputFormat
from app.settings import settings


_HTML_CHAR_LIMIT = 80_000
_JSON_ARRAY_SAMPLE = 3

_SYSTEM_PROMPT = """\
You are configuring a Feedwright extractor. Return only a configuration matching the
provided Pydantic response model. The configuration will be executed against the exact
document below. If execution or feed validation fails, you will receive the candidate
and validation errors and must return a corrected configuration.

The configuration URL must be the requested source URL. A successful feed must have an
id, title, description, and at least one article. Every article must have a title and
either an id or link. The result must render as both RSS and Atom.

When available in the source, include normalized date selectors for both feed-level and
article-level dates: feed.publish_date, feed.last_build_date, article.publish_date,
and article.update_date. Prefer selectors that extract ISO 8601 datetimes (e.g.
"2024-05-20T14:30:00Z") and, where necessary, use attributes such as <time datetime=>
or JSON fields with ISO strings. Also include TTL selectors as integers when appropriate.

Include structured categories and people where present: feed.categories (term, scheme),
feed.authors/feed.contributors, and article.categories/article.authors. Use the
existing Person and Category shapes (name, email, uri; term, scheme). If only simple
strings are available for categories, provide selectors that return those strings and
the system will convert them to Category objects.

If a date string cannot be parsed by common ISO or RFC formats, return the selector
anyway; the system will attempt to normalize it. Always prefer stable selectors
(attributes, canonical links, or JMESPath expressions) over fragile text scraping.
"""


class AutoConfigureRequest(BaseModel):
    url: str
    plugin: str = "app.extractors.parsel:ParselExtractor"
    max_attempts: int = Field(4, ge=1, le=10)


class ValidationIssue(BaseModel):
    code: str
    message: str
    stack_trace: str | None = Field(default=None, exclude=True)


class AttemptReport(BaseModel):
    attempt: int
    errors: list[ValidationIssue]


class AutoConfigureResult(BaseModel):
    plugin: str
    config: dict[str, Any]  # pyright: ignore[reportExplicitAny]
    attempts: int
    article_count: int


class AutoConfigureError(Exception):
    pass


class AiConfigurationError(AutoConfigureError):
    pass


class InvalidPluginError(AutoConfigureError):
    pass


class ProviderError(AutoConfigureError):
    pass


class SourceFetchError(AutoConfigureError):
    pass


class ValidationExhaustedError(AutoConfigureError):
    def __init__(self, reports: list[AttemptReport]):
        super().__init__(
            f"No valid extractor was produced after {len(reports)} attempts"
        )
        self.reports = reports


@dataclass
class Candidate:
    extractor: Extractor
    feed: Feed | None
    report: AttemptReport

    @property
    def valid(self) -> bool:
        return not self.report.errors and self.feed is not None


def _trim_json_arrays(value: Any) -> Any:  # pyright: ignore[reportExplicitAny]
    if isinstance(value, list):
        return [_trim_json_arrays(item) for item in value[:_JSON_ARRAY_SAMPLE]]
    if isinstance(value, dict):
        return {key: _trim_json_arrays(item) for key, item in value.items()}
    return value


def _preprocess_document(document: SourceDocument) -> str:
    content_type = (document.content_type or "").lower()
    if "json" in content_type:
        try:
            parsed = json.loads(document.content)
        except json.JSONDecodeError:
            return document.content[:_HTML_CHAR_LIMIT]
        return json.dumps(_trim_json_arrays(parsed), indent=2, ensure_ascii=False)

    content = re.sub(
        r"<(script|style|svg)\b[^>]*>.*?</\1>",
        "",
        document.content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    content = re.sub(r"[ \t]{2,}", " ", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    if len(content) > _HTML_CHAR_LIMIT:
        content = content[:_HTML_CHAR_LIMIT] + "\n\n[... document truncated ...]"
    return content.strip()


def _exception_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return json.dumps(exc.detail, ensure_ascii=False, default=str)
    if isinstance(exc, ValidationError):
        return json.dumps(exc.errors(), ensure_ascii=False, default=str)
    return f"{type(exc).__name__}: {exc}"


def _validate_feed(feed: Feed) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not feed.id.strip():
        issues.append(
            ValidationIssue(code="missing_feed_id", message="Feed id is empty")
        )
    if feed.title is None or not feed.title.strip():
        issues.append(
            ValidationIssue(code="missing_feed_title", message="Feed title is empty")
        )
    if not feed.description.strip():
        issues.append(
            ValidationIssue(
                code="missing_feed_description", message="Feed description is empty"
            )
        )
    if not feed.articles:
        issues.append(
            ValidationIssue(
                code="no_articles", message="The extractor returned zero articles"
            )
        )

    for index, article in enumerate(feed.articles):
        if article.title is None or not article.title.strip():
            issues.append(
                ValidationIssue(
                    code="missing_article_title",
                    message=f"Article {index + 1} has no title",
                )
            )
        if not article.id and not article.links:
            issues.append(
                ValidationIssue(
                    code="missing_article_identifier",
                    message=f"Article {index + 1} has neither an id nor a link",
                )
            )

    for format in (OutputFormat.rss, OutputFormat.atom):
        try:
            _ = format.render(feed)
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    code=f"invalid_{format.value}",
                    message=_exception_message(exc),
                    stack_trace=traceback.format_exc(),
                )
            )
    return issues


def _agent_validation_feedback(report: AttemptReport) -> str:
    errors = [
        {
            "code": issue.code,
            "message": issue.message,
            **({"stack_trace": issue.stack_trace} if issue.stack_trace else {}),
        }
        for issue in report.errors
    ]
    return json.dumps(
        {"attempt": report.attempt, "errors": errors},
        indent=2,
        ensure_ascii=False,
    )


class AutoConfigureSession:
    def __init__(
        self,
        request: AutoConfigureRequest,
        document: SourceDocument,
        extractor_class: type[Extractor],
    ):
        self.request = request
        self.document = document
        self.extractor_class = extractor_class
        self.attempt = 0
        self.reports: list[AttemptReport] = []
        self.messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": "\n\n".join(
                    part
                    for part in (
                        _SYSTEM_PROMPT,
                        extractor_class.autoconfigure_instructions,
                    )
                    if part
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate an extractor configuration for {request.url}.\n\n"
                    f"Content-Type: {document.content_type or 'unknown'}\n\n"
                    f"{_preprocess_document(document)}"
                ),
            },
        ]

    @classmethod
    async def create(cls, request: AutoConfigureRequest) -> "AutoConfigureSession":
        if not settings.ai.model:
            raise AiConfigurationError(
                "FEEDWRIGHT_AI__MODEL must be configured for auto-generation"
            )
        try:
            extractor_class = extractors.get_extractor_class(request.plugin)
        except (AttributeError, ImportError, TypeError, ValueError) as exc:
            raise InvalidPluginError(
                f"Could not load extractor plugin '{request.plugin}': {exc}"
            ) from exc

        if not issubclass(extractor_class, Extractor):
            raise InvalidPluginError(
                f"Plugin '{request.plugin}' is not an Extractor subclass"
            )

        try:
            document = await fetch_document(request.url)
        except Exception as exc:
            raise SourceFetchError(
                f"Could not download '{request.url}': {_exception_message(exc)}"
            ) from exc
        return cls(request, document, extractor_class)

    async def generate(self, feedback: str | None = None) -> Candidate:
        if feedback:
            self.messages.append(
                {
                    "role": "user",
                    "content": f"Additional user feedback:\n\n{feedback}",
                }
            )

        self.attempt += 1
        client = instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)
        completion_args: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
            "model": settings.ai.model,
            "response_model": self.extractor_class,
            "max_retries": 3,
            "messages": self.messages,
        }
        if settings.ai.key:
            completion_args["api_key"] = settings.ai.key
        if settings.ai.url:
            completion_args["base_url"] = settings.ai.url

        try:
            extractor = await client.chat.completions.create(**completion_args)
        except Exception as exc:
            raise ProviderError(f"AI provider request failed: {exc}") from exc

        if not isinstance(extractor, Extractor):
            raise ProviderError("AI provider returned an unexpected response type")

        extractor = extractor.model_copy(update={"url": self.request.url})
        config = extractor.model_dump(mode="json", exclude_none=True)
        wrapper = ExtractorConfig(plugin=self.request.plugin, config=config)
        issues: list[ValidationIssue] = []
        feed: Feed | None = None
        try:
            feed = await extractor.extract(self.document, wrapper)
            issues.extend(_validate_feed(feed))
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    code="extraction_failed",
                    message=_exception_message(exc),
                    stack_trace=traceback.format_exc(),
                )
            )

        report = AttemptReport(attempt=self.attempt, errors=issues)
        self.reports.append(report)
        self.messages.append(
            {
                "role": "assistant",
                "content": extractor.model_dump_json(exclude_none=True),
            }
        )
        if issues:
            self.messages.append(
                {
                    "role": "user",
                    "content": (
                        "The candidate failed validation. Correct the configuration using "
                        "these errors:\n\n" + _agent_validation_feedback(report)
                    ),
                }
            )

        return Candidate(extractor=extractor, feed=feed, report=report)


async def autoconfigure(request: AutoConfigureRequest) -> AutoConfigureResult:
    session = await AutoConfigureSession.create(request)
    for _ in range(request.max_attempts):
        candidate = await session.generate()
        if candidate.valid and candidate.feed is not None:
            return AutoConfigureResult(
                plugin=request.plugin,
                config=candidate.extractor.model_dump(mode="json", exclude_none=True),
                attempts=session.attempt,
                article_count=len(candidate.feed.articles),
            )
    raise ValidationExhaustedError(session.reports)
