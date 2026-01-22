# Multi-Agent Workflow Assistant - AI Coding Instructions

When taking actions to modify or extend code, add a brief summary of actions taken to the changelog section of the README.md file in the root of the repository, with a date stamp and the model(s) used.  The summary can be merged with existing entries of the same date stamp.

## Architecture Overview

This is a **Microsoft Agent Framework** application using a coordinator pattern:

```
CLI (app/cli.py) → CoordinatorAgent → Tool Agents (url_scraper, knowledge_ingestion, org_context)
```

- **CoordinatorAgent** ([app/agents/coordinator.py](../app/agents/coordinator.py)): Central orchestrator that receives user queries and delegates to specialized tool agents. Each tool agent gets its own `OllamaChatClient` instance to avoid state sharing.
- **Tool Agents** ([app/agents/tools/](../app/agents/tools/)): Wrapped as tools via `.as_tool()` method; they're agent-as-tool patterns, not direct function calls.
- **Local LLM**: Uses Ollama for inference—all agents share the same model but have separate client instances.

## Key Patterns

### Agent-as-Tool Pattern
Tool agents expose themselves via `as_tool()`:
```python
self._agent = chat_client.create_agent(
    tools=[url_scraper.as_tool(), knowledge_ingestion.as_tool()],
)
```

### Configuration via Pydantic + YAML
- Config models in [app/config.py](../app/config.py) use Pydantic `BaseModel`
- Runtime config from [config/config.yaml](../config/config.yaml) merged with env vars (`.env`)
- Access config via `get_config()` singleton—never instantiate `AppConfig` directly

### Tool Functions Must Be Synchronous
Functions registered as tools (e.g., `fetch_url` in url_scraper) must be **sync**, not async:
```python
def fetch_url(url: Annotated[str, Field(description="...")]) -> str:
    # Sync httpx client, not async
    with httpx.Client(...) as client:
        response = client.get(url)
```

### Knowledge Store Structure
- `knowledge/instructions.md`: High-level org context (edited by knowledge_ingestion agent)
- `knowledge/url_index.yaml`: Indexed URLs with metadata
- `notes/`: Markdown files with YAML frontmatter, indexed by `_index.yaml`

## Development Workflow

### Setup
```bash
uv venv --python=3.13.11
.venv\Scripts\activate  # Windows
uv pip install -e ".[dev]" --pre  # --pre required for agent-framework preview
```

### Running
```bash
ollama serve  # Terminal 1
python -m app.cli  # Terminal 2 (or: workflow)
```

### Testing
```bash
pytest  # Uses pytest-asyncio with asyncio_mode="auto"
```

Tests use fixture-based mocking from [tests/conftest.py](../tests/conftest.py):
- `mock_config`: Returns `AppConfig` with test values
- `mock_get_config`: Patches `app.config.get_config` globally
- `mock_chat_client`: Mocked `OllamaChatClient` with async methods

### Logging Hierarchy
All loggers under `workflow.*` namespace:
- `workflow.cli`, `workflow.coordinator`, `workflow.url_scraper`, etc.
- Set level via `/loglevel debug` in CLI or `logging.level` in config.yaml

## Adding New Tool Agents

1. Create tool module in `app/agents/tools/new_tool.py`
2. Define sync tool functions with `Annotated[type, Field(description=...)]` signatures
3. Create agent class wrapping the tool:
   ```python
   class NewToolAgent:
       def __init__(self, chat_client: OllamaChatClient | None = None):
           self._agent = chat_client.create_agent(tools=[tool_function])
       
       def as_tool(self):
           return self._agent.as_tool()
   ```
4. Register in `CoordinatorAgent.__init__()` with its own client instance
5. Update coordinator's instructions to describe when to use the new tool

## Dependencies

- `agent-framework-ollama`: Microsoft Agent Framework with Ollama provider (**preview package**)
- `httpx`: HTTP client (sync for tools)
- `beautifulsoup4`: HTML parsing
- `pydantic`: Config validation and tool parameter schemas
- `pyyaml`: YAML config/knowledge store parsing

## Common Issues

- **JSON escaping errors on tool calls**: Use larger model (qwen2.5:7b+ recommended over 1.5b)
- **Slow responses**: Model inference is local; expect 5-15s depending on hardware
- **Config not loading**: Ensure `.env` exists and `OLLAMA_HOST`/`OLLAMA_MODEL_ID` are set
