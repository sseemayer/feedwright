# feedwright

Feedwright converts various information sources into RSS and atom feeds using a flexible configuration system. You can create one configuration file per feed, specifying which elements from a HTML, XML or JSON document to extract as articles, links, and so on.

## AI auto-configuration

Install the optional AI dependencies and configure any LiteLLM-supported provider:

```bash
uv sync --extra ai
export FEEDWRIGHT_AI__MODEL=openai/gpt-4.1-mini
export FEEDWRIGHT_AI__KEY=...
# Optional for an OpenAI-compatible endpoint:
export FEEDWRIGHT_AI__URL=https://provider.example/v1
```

Generate a validated configuration non-interactively:

```bash
uv run feedwright feed generate-config \
  https://example.com/news \
  app.extractors.parsel:ParselExtractor
```

For a human-in-the-loop session that can refine and save the result:

```bash
uv run feedwright feed configure
```

The REST endpoint is available only when the AI dependencies are installed. It always
requires a separately configured admin bearer token:

```bash
export FEEDWRIGHT_REQUIRE_ADMIN_TOKEN=secret
curl -X POST http://localhost:8000/feed/generate-config \
  -H 'Authorization: Bearer secret' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/news","plugin":"app.extractors.parsel:ParselExtractor"}'
```
