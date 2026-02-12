# Multi-Agent Workflow Assistant - MVP
---

Use this template as a springboard for building a multi-agent workflow application using the Microsoft Agent Framework.  Out of the box this is a locally-hosted Python application that uses the Microsoft Agent Framework to provide augmented chatbot capabilities through a coordinator agent that orchestrates specialized tool agents.

It is currently in a Minimum Viable Product (MVP) state, and additional features will be added presently.

## Features (MVP)

- **Coordinator Agent**: Central agent that communicates with users and routes tasks
- **URL Scraper Agent Tool**: Fetches and analyzes web content from URLs
- **CLI Interface**: Simple command-line chat interface
- **Ollama Integration**: Local LLM inference optimized for consumer hardware

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) installed and running
- 8GB RAM minimum (for running local models)

## Quick Start

### 1. Install Ollama

Download and install Ollama from [ollama.com](https://ollama.com/).

### 2. Pull a Model

For systems with 8GB RAM and integrated graphics, we recommend `qwen3:4b` or `llama3.2:3b`:

```bash
ollama pull llama3.2:3b
```

Other lightweight options:
- `phi3:mini` - Fast, good for simple tasks
- `qwen3:4b` - Good tool calling support

### 3. Install Dependencies

```bash
# Create virtual environment
uv venv --python=3.13.11

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install package with dependencies (--pre required for agent-framework preview)
uv pip install -e ".[dev]" --pre
```

### 4. Configure

Copy the example environment file:

```bash
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

Edit `.env` to match your Ollama setup:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL_ID=llama3.2:3b
```

### 5. Run

```bash
# Make sure Ollama is running
ollama serve

# In another terminal, start the CLI
python -m app.cli
```

Or use the entry point:

```bash
workflow
```

### Web Interface (Streamlit)

For a browser-based experience:

```bash
# Using the entry point
workflow-web

# Or directly with streamlit
streamlit run app/web.py
```

The web interface includes:
- **Chat tab**: Conversational interface with message history
- **Knowledge Base tab**: Browse instructions, indexed URLs, and notes
- **Metrics tab**: View session statistics and metrics files
- **Sidebar**: Connection status, log level control, and quick metrics

## Usage

### CLI Commands

Once running, you can:

1. **Ask questions**: Type any question and press Enter
2. **Analyze URLs**: Paste a URL to fetch and analyze its content
3. **Commands**:
   - `/new` - Start a new conversation
   - `/config` - Show current configuration
   - `/loglevel [level]` - Set logging level (DEBUG, INFO, WARNING, ERROR)
   - `/help` - Show help message
   - `/quit` - Exit the application

### Example

```
You: Is there anything useful at https://kubernetes.io/docs/concepts/overview/ for my DevOps team?
```

# Customizing the Template

---

# Roadmap

---

## Planned Improvements

### Knowledge Base Enhancements
- [ ] **Improve "show full note" reliability**: When org_context finds a relevant note, ensure it automatically reads and returns the full content without requiring additional user prompts. Currently, the LLM may offer to show a note but fail to call the `read_note` tool on follow-up requests.
- [ ] **Note search improvements**: Better keyword matching and relevance scoring for note searches

### User Experience
- [ ] **Reduce conversational friction**: The assistant should act proactively on clear intent rather than asking for confirmation (e.g., "Do I have notes on X?" should immediately search, not ask if user wants to search)
- [ ] **Consistent follow-up actions**: Only offer actions that tools can actually perform

---


# Changelog
---

### 2026-02-12 (Claude Opus 4.6)
- **Changed**: Reorganized knowledge folder structure for unified knowledge management
  - Moved `notes/` under `knowledge/notes/` — all knowledge under one tree
  - Renamed `knowledge/instructions.md` → `knowledge/context.md` (avoids confusion with agent instructions)
  - Moved `knowledge/url_index.yaml` → `knowledge/sources/url_index.yaml` (separates provenance from content)
  - Updated all config paths (`context_file`, `url_index_file`, `notes_topics.default.directory`)
- **Added**: `knowledge_retrieval.py` — traditional function-based tool (not agent-as-tool)
  - `get_available_tags()`: Collects all unique tags from notes index and URL index with counts
  - `search_by_tags(tags)`: Returns matching notes/URLs with summaries for given tags
- **Changed**: Made repo a proper GitHub template by separating sample/example files from runtime-generated data
  - Created `.sample` copies of knowledge files; added runtime-generated files to `.gitignore`

### 2026-02-03 (Claude Opus 4.5)
- **Fixed**: "Event loop is closed" error when sending multiple messages in Streamlit web UI
  - Implemented persistent event loop stored in session state instead of creating/closing per message
- **Added**: "Response complete" INFO-level log when coordinator finishes streaming response
  - Shows total character count and chunk count for visibility
- **Optimized**: URL scraper performance improvements for better responsiveness
  - Connection pooling with HTTP/2 support (reuses connections across requests)
  - Reduced default timeout from 30s to 10s (sufficient for most sites)
  - Switched from `html.parser` to `lxml` for 5-10x faster HTML parsing
- **Added**: Dependencies `lxml>=5.0.0` and `httpx[http2]` to pyproject.toml

### 2026-01-22 (Claude Opus 4.5)
- **Added**: Streamlit web interface (`app/web.py`) as alternative to CLI
  - Chat interface with message history
  - Sidebar with connection status, session controls, log level selector, and metrics
  - Knowledge Base Explorer tab to view instructions, indexed URLs, and notes
  - Metrics Dashboard tab showing session stats and metrics files
  - Run with `workflow-web` or `streamlit run app/web.py`
- **Added**: "Reload Config" button in web UI sidebar to apply config.yaml changes at runtime
  - Reloads config singleton, reinitializes coordinator with new model settings
  - Displays toast notification with new model name
- **Added**: `reload_config()` function in `app/config.py` to refresh cached configuration
- **Added**: Agent instructions now loaded from external markdown files in `config/instructions/`
  - Users can customize agent behavior by editing `coordinator.md`, `org_context.md`, `url_scraper.md`, `knowledge_ingestion.md`
  - Supports template variables (e.g., `{confidence_threshold}`) that are filled at runtime
  - Falls back to embedded defaults if instruction files are missing
- **Added**: `load_instructions()` helper function in `app/config.py` for loading instruction files
- **Added**: `instructions_file` field to `AgentConfig` model
- **Added**: Metrics tracking for tool function calls via `@track_tool_call` decorator
  - All tool functions in `org_context`, `url_scraper`, and `knowledge_ingestion` now record metrics
  - Includes operation duration, input/output lengths, success/failure status
  - Metrics appear alongside coordinator metrics in daily `.jsonl` files
- **Fixed**: Updated agent-framework API from `create_agent()` to `as_agent()` to match latest version

### 2026-01-12 (Claude Opus 4.5)
- **Fixed**: Coordinator now immediately searches knowledge base when user asks about notes/documentation instead of asking for permission
- **Fixed**: Updated org_context agent instructions to automatically read full notes when found, rather than just summarizing
- **Added**: "Don't offer what you can't do" guidance in coordinator instructions
- **Added**: Roadmap section with planned improvements for note retrieval reliability

### 2026-01-27 (Claude Opus 4.5)
- **Added**: Streamlit frontend
- **Added**: Knowledge ingestion decision guidelines for when to use each tool function
- **Added**: Enhance CoordinatorAgent logging
- **Fixed**: Implement persistent event loop to maintain conversation state across multiple user inputs
