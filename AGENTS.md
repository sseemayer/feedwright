High-signal notes for automated agents working on this repo

Keep this file minimal — include only things an agent would likely miss.

- Language / runtime
  - Python >= 3.13 is required (pyproject.toml: requires-python).
  - Run all Python commands through uv (uv run <command>) to ensure the venv is activated and the correct Python version is used.

- How to run the CLI (no install required)
  - Invoke the Typer CLI module directly from the repo root:
    - List extractors: uv run feedwright feed list
    - Get an extractor output: uv run feedwright feed get <name>
      - Output formats: json, rss, atom (use --format). Example: uv run feedwright feed get example --format json
    - Start the HTTP server (what the package's console script does): uv run feedwright server erve
  - If the package is installed, the console script is `feedwright` (entry point in pyproject.toml): feedwright feed list

- Dev server with auto-reload
  - For development prefer fastapi CLI: uv run fastapi dev

- Where extractor configs must live (easy-to-miss)
  - Extractors are discovered under each configured config path's feeds/ subdirectory.
    - Example: <config_path>/feeds/journal-frankfurt.yaml
  - Default config paths (settings.config_paths) include platform dirs AND the repo-local config folder (project_root/config). The examples/ folder in this repo is NOT scanned by default.
  - To run the shipped examples without moving files, point settings to the examples dir via env var:
    - FEEDWRIGHT_CONFIG_PATHS=examples
    - The env value is split on ':'; you can pass multiple paths like FEEDWRIGHT_CONFIG_PATHS=examples:/etc/xdg/feedwright

- Extractor file format and supported extensions
  - Each file must be a mapping with top-level keys: plugin and config (see examples/*.yaml).
  - plugin must be "module.path:ClassName" (the code uses __import__ with a colon-separated package:ClassName).
  - Supported file extensions/parsers: .yaml, .yml, .toml, .json, .hjson

- Settings / env var details agents often miss
  - All settings use env prefix FEEDWRIGHT_. Nested fields use double-underscore __ as delimiter.
    - Examples:
      - FEEDWRIGHT_REQUIRE_TOKEN=secrettoken (when set, EVERY non-doc API request must include that token)
      - FEEDWRIGHT_CONFIG_PATHS=examples
      - FEEDWRIGHT_HTTP__VERIFY_SSL=false
      - FEEDWRIGHT_AI__MODEL=<model>
      - FEEDWRIGHT_AI__KEY=<api-key>
  - .env is loaded by default (SettingsConfigDict env_file=".env"). Use it for persistent local overrides.

- Authentication middleware
  - If settings.require_token is non-empty (string), the app requires that exact string as a bearer token for all requests except OpenAPI/docs endpoints.
  - Token may be supplied as header Authorization: Bearer <token> or as query param token=<token>.

- AI "generate-config" command caveats
  - The generate-config command is only enabled if litellm and instructor are importable (they are optional extras).
  - If you want generate-config, install the ai extras: `uv sync --extra ai` and set FEEDWRIGHT_AI__MODEL and FEEDWRIGHT_AI__KEY/URL.

- Writing new extractor plugins
  - Implement a pydantic model subclassing Extractor (app.models.extractor.Extractor) and implement async def extract(self, config: ExtractorConfig) -> Feed
  - Register plugin by referring to it in feed config as module:ClassName (e.g. app.extractors.parsel:ParselExtractor)

- Version and build details agents should not break
  - Version is authored by version-pioneer into app/_version.py. CI/builds may set FEEDWRIGHT_VERSION env var (leading `v` is stripped).
  - Packaging uses hatch; pyproject.toml lists build-backend = "hatchling.build".

- Quick troubleshooting checklist (what agents often forget)
  - If no extractors appear with `feed list`, ensure files are under a feeds/ subdirectory of one of the configured config paths (see "Where extractor configs must live").
  - If generate-config is missing, check that ai extras are installed (litellm/instructor) and FEEDWRIGHT_AI__MODEL is set.
  - If server returns 401, check FEEDWRIGHT_REQUIRE_TOKEN and provide the exact token as Bearer.

If a change to runtime wiring is needed, prefer editing app/settings.py or app/cli/* rather than adding heuristics here.
