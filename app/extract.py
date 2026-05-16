from pathlib import Path
import toml

from asyncio import EventLoop

from app.models.feed import Feed
from app.settings import settings
from app.models.extractor import ExtractorConfig


class Extractors:
    def __init__(self):
        self.extractors: dict[str, Path] = {
            path.stem: path
            for base_path in settings.config_paths
            for path in (base_path / "feeds").glob("*.toml")
        }

    def get(self, name: str) -> Feed:
        """Get the RSS feed for a specific extractor name."""
        path = self.extractors.get(name)
        if path is None:
            raise ValueError(f"No extractor found with name '{name}'")

        with path.open() as f:
            config = toml.load(f)

        extractor_config = ExtractorConfig.model_validate(config)

        pkg_name, class_name = extractor_config.plugin.split(":")

        pkg = __import__(pkg_name, fromlist=[class_name])
        extractor_cls = getattr(pkg, class_name)

        extractor = extractor_cls(**extractor_config.config)

        return EventLoop().run_until_complete(extractor.extract(extractor_config))


extractors = Extractors()
