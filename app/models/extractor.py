from typing import Any, ClassVar
from pydantic import BaseModel, Field

from app.models.feed import Feed


class ExtractorConfig(BaseModel):
    feed_defaults: Feed = Feed()

    plugin: str = Field(
        ...,
        description="The plugin to use for this extractor, in the format 'package:ClassName'",
    )

    config: Any = Field(
        ...,
        description="The configuration to pass to the plugin when instantiating it",
    )


class SourceDocument(BaseModel):
    url: str = Field(..., description="The final URL of the downloaded document")
    content: str = Field(..., description="The downloaded document content")
    content_type: str | None = Field(
        None, description="The Content-Type reported by the source server"
    )


class Extractor(BaseModel):
    url: str = Field(..., description="URL to fetch the data from")
    autoconfigure_instructions: ClassVar[str] = ""

    async def extract(
        self, document: SourceDocument, config: ExtractorConfig
    ) -> Feed:
        raise NotImplementedError(
            "Extractor subclasses must implement the extract method"
        )
