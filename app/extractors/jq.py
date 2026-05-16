import jq

from pydantic import Field, field_validator

from app.models.extractor import Extractor, ExtractorConfig
from app.models.feed import Feed

from app.settings import settings


class JqExtractor(Extractor):
    url: str

    root_selector: jq.CompiledProgram = Field(
        ..., description="jq expression to select the root of the JSON data"
    )

    article_selector: jq.CompiledProgram = Field(
        ..., description="jq expression to select articles from the JSON data"
    )

    async def extract(self, config: ExtractorConfig) -> Feed:

        async with settings.http.get_async_client() as client:
            response = await client.get(self.url)
            _ = response.raise_for_status()
            data = response.json()

        doc = self.root_selector.input(data).first()

        articles = self.article_selector.input(doc).all()

        breakpoint()

        return config.feed_defaults

    @field_validator("root_selector", "article_selector", mode="before")
    def validate_root_selector(cls, value: str) -> jq.CompiledProgram:
        try:
            return jq.compile(value)
        except Exception as e:
            raise ValueError(f"Invalid jq expression: {e}")
