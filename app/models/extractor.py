from typing import Any
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

    def concretize(self) -> "Extractor":
        package, type = self.plugin.rsplit(":", 1)
        cls = __import__(package).__dict__[type]
        return cls.model_validate(self.config)


class Extractor(BaseModel):
    async def extract(self, config: ExtractorConfig) -> Feed:
        raise NotImplementedError(
            "Extractor subclasses must implement the extract method"
        )
