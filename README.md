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

For systems with 8GB RAM and integrated graphics, we recommend `qwen2.5:3b` or `llama3.2:3b`:

```bash
ollama pull llama3.2:3b
```

Other lightweight options:
- `phi3:mini` - Fast, good for simple tasks
- `qwen2.5:3b` - Good tool calling support

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

## Usage

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
