import hjson
import toml
import yaml

from pathlib import Path
from typing import Any, Callable


from app.models.feed import Feed
from app.settings import settings
from app.models.extractor import ExtractorConfig


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
    def __init__(self):
        self.extractors: dict[str, Path] = {
            path.stem: path
            for base_path in settings.config_paths
            for extension in [f"*.{ext}" for ext in EXTENSION_TO_PARSER.keys()]
            for path in (base_path / "feeds").glob(extension)
        }

    async def get(self, name: str) -> Feed:
        """Get the RSS feed for a specific extractor name."""
        path = self.extractors.get(name)
        if path is None:
            raise ValueError(f"No extractor found with name '{name}'")

        parser = EXTENSION_TO_PARSER.get(path.suffix[1:])
        if parser is None:
            raise ValueError(f"No parser registered for extension '{path.suffix}'")

        config = parser(path)

        extractor_config = ExtractorConfig.model_validate(config)

        pkg_name, class_name = extractor_config.plugin.split(":")

        pkg = __import__(pkg_name, fromlist=[class_name])  # pyright: ignore[reportAny]
        extractor_cls = getattr(pkg, class_name)  # pyright: ignore[reportAny]

        extractor = extractor_cls(**extractor_config.config)  # pyright: ignore[reportAny]

        return await extractor.extract(extractor_config)  # pyright: ignore[reportAny]


extractors = Extractors()
