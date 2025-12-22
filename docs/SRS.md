# Software Requirements Specification: Multi-Agent Workflow Assistant

## System Design

- **Application Type**: Single-user local-first web application
- **Runtime**: Python 3.11+ with Streamlit frontend
- **Deployment**: Local workstation (primary), optional remote hosting (future)
- **Core Pattern**: Coordinator agent orchestrating specialized tool agents via Microsoft Agent Framework

### High-Level Components
- **Streamlit UI Layer**: Chat interface, thread management, file handling
- **Coordinator Agent**: Central orchestrator for user interaction and task routing
- **Tool Agent Registry**: Plugin-based agent registration system
- **Knowledge Layer**: Vector store + markdown file index for organizational context
- **Model Abstraction**: Unified interface for Ollama (local) and Azure AI Foundry (remote)

---

## Architecture Pattern

- **Pattern**: Agent-as-Tool Workflow (Microsoft Agent Framework)
- **Style**: Modular plugin architecture with dependency injection

### Component Structure
```
app/
├── main.py                 # Streamlit entry point
├── agents/
│   ├── coordinator.py      # Central orchestrator agent
│   ├── registry.py         # Tool agent registration
│   └── tools/
│       ├── url_scraper/    # URL fetching + parsing
│       ├── org_context/    # Knowledge retrieval
│       ├── writer/         # Style transformation
│       └── knowledge_ingest/ # Content ingestion
├── services/
│   ├── model_client.py     # LLM abstraction layer
│   ├── thread_manager.py   # Conversation persistence
│   └── file_handler.py     # File processing
├── knowledge/
│   ├── vector_store.py     # ChromaDB interface
│   └── markdown_index.py   # Frontmatter file index
├── ui/
│   ├── chat.py             # Chat components
│   ├── sidebar.py          # Thread list, navigation
│   └── styles.py           # Theme configuration
└── config/
    └── config.yaml         # Model, paths, UI settings
```

### Agent Registration Pattern
- Each tool agent registers capabilities with the coordinator
- Coordinator dynamically selects agents based on task requirements
- Agents return structured responses for coordinator to parse/aggregate

---

## State Management

### Application State (Streamlit Session State)
- `st.session_state.current_thread_id`: Active conversation thread
- `st.session_state.messages`: Current thread message history
- `st.session_state.agent_status`: Current processing state (idle/thinking/processing)
- `st.session_state.pending_files`: Files queued for processing
- `st.session_state.sidebar_expanded`: UI state for sidebar
- `st.session_state.inspector_open`: Debug drawer visibility

### Persistent State (Local Storage)
- **Threads**: JSON files per thread in `data/threads/`
- **Knowledge Index**: ChromaDB collection in `data/chroma/`
- **User Config**: `config/config.yaml` for preferences
- **Style Examples**: `data/style_examples/` directory

### State Flow
```
User Action → Streamlit Callback → Session State Update → UI Re-render
                    ↓
            Persistent Storage (async where possible)
```

---

## Data Flow

### Message Processing Flow
```
1. User Input (text/files)
        ↓
2. Streamlit UI captures input
        ↓
3. Coordinator Agent receives request
        ↓
4. Coordinator analyzes intent, selects tool agents
        ↓
5. Tool Agents execute (parallel where possible):
   - URL Scraper → fetches/parses web content
   - Org Context → retrieves relevant knowledge
   - Writer → applies user style
        ↓
6. Coordinator aggregates results
        ↓
7. Response returned to UI
        ↓
8. Thread persisted to storage
```

### Knowledge Ingestion Flow
```
1. User provides content (URL/file/text)
        ↓
2. Knowledge Ingestion Agent processes
        ↓
3. Content chunked and embedded
        ↓
4. Stored in ChromaDB with metadata
        ↓
5. Markdown index updated (if file-based)
```

---

## Technical Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Streamlit 1.x |
| **Backend** | Python 3.11+ |
| **Agent Framework** | Microsoft Agent Framework |
| **Local LLM** | Ollama |
| **Remote LLM** | Azure AI Foundry |
| **Vector Store** | ChromaDB |
| **File Storage** | Local filesystem (JSON, Markdown) |
| **Web Scraping** | httpx + BeautifulSoup4 |
| **Embeddings** | sentence-transformers (local) / Azure OpenAI (remote) |
| **Config Management** | PyYAML + Pydantic |

### Dependencies
```
streamlit>=1.28
agent-framework
chromadb
ollama
azure-ai-inference
httpx
beautifulsoup4
python-frontmatter
pydantic
pyyaml
```

---

## Authentication Process

### Local Mode (Primary)
- **No authentication required** for single-user local deployment
- File system permissions govern access to knowledge stores

### Model Provider Authentication
- **Ollama**: No auth (localhost)
- **Azure AI Foundry**: 
  - API key stored in environment variable `AZURE_AI_KEY`
  - Endpoint configured in `config.yaml`
  - Optional: Azure DefaultCredential for managed identity

### Configuration Security
```yaml
# config.yaml (secrets via env vars)
models:
  azure:
    endpoint: ${AZURE_AI_ENDPOINT}
    api_key: ${AZURE_AI_KEY}
    deployment: "gpt-4o"
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2"
```

### Future Considerations
- Optional basic auth for remote-hosted instances
- API key management for third-party tool integrations

---

## Route Design

### Streamlit Page Structure (Single-Page App)
- **No traditional routing**—Streamlit manages view state internally

### Logical Views (via Session State)
| View State | Component | Trigger |
|------------|-----------|---------|
| `chat` | Main chat interface | Default / thread selection |
| `settings` | Configuration panel | Settings icon click |
| `inspector` | Agent debug drawer | Ctrl+I / status click |

### Navigation Flow
```
App Load → Load last thread OR new chat
    ↓
Sidebar: Thread selection → Switch current_thread_id → Reload messages
    ↓
New Chat → Clear messages → Generate new thread_id
    ↓
Settings → Modal overlay → Update config.yaml
```

### URL Parameters (Optional)
- `?thread={thread_id}` for direct thread access (future bookmarking)

---

## API Design

### Internal Service APIs (Python Interfaces)

#### Model Client Interface
```python
class ModelClient(Protocol):
    async def complete(self, messages: list[Message], tools: list[Tool]) -> Response
    async def embed(self, text: str) -> list[float]
```

#### Agent Interface
```python
class ToolAgent(Protocol):
    name: str
    description: str
    async def execute(self, context: AgentContext) -> AgentResult
```

#### Thread Manager Interface
```python
class ThreadManager:
    def create_thread() -> str
    def load_thread(thread_id: str) -> Thread
    def save_thread(thread: Thread) -> None
    def list_threads() -> list[ThreadSummary]
    def delete_thread(thread_id: str) -> None
```

### External API Integrations

#### Ollama (Local)
- **Endpoint**: `http://localhost:11434/api/chat`
- **Method**: POST (streaming)

#### Azure AI Foundry
- **Endpoint**: `https://{resource}.inference.ai.azure.com`
- **Auth**: Bearer token or API key
- **SDK**: `azure-ai-inference`

### Future REST API (Optional Remote Hosting)
```
POST /api/chat          # Send message
GET  /api/threads       # List threads
GET  /api/threads/{id}  # Get thread
DELETE /api/threads/{id} # Delete thread
POST /api/ingest        # Ingest knowledge
```

---

## Knowledge Store Design

### Storage Architecture
```
data/
├── chroma/                    # Vector database
│   └── org_knowledge/         # Main collection
├── threads/                   # Conversation history
│   └── {thread_id}.json
├── knowledge/
│   ├── instructions.md        # High-level org context
│   ├── org_urls.yaml          # URL index with metadata
│   └── notes/                 # User markdown notes
│       └── *.md (with frontmatter)
└── style_examples/
    └── {example_id}/
        ├── input.md           # Source content
        └── output.md          # User-written version
```

### ChromaDB Collection Schema
```python
collection: "org_knowledge"
document: str           # Text chunk
embedding: list[float]  # Vector representation
metadata: {
    "source_type": "url" | "file" | "note",
    "source_path": str,
    "domain": str | None,
    "title": str,
    "ingested_at": datetime,
    "tags": list[str]
}
```

### Markdown Frontmatter Schema
```yaml
---
title: "Document Title"
tags: [devops, kubernetes, internal]
created: 2025-01-15
updated: 2025-01-20
source_url: "https://..."  # optional
---
# Content here...
```

### URL Index Schema (org_urls.yaml)
```yaml
urls:
  - url: "https://internal.docs/guide"
    domain: "internal.docs"
    title: "Internal Guide"
    context: "Team onboarding documentation"
    last_indexed: 2025-01-15
    tags: [onboarding, internal]
```

### Query Strategy
1. **Semantic search**: ChromaDB similarity search on user query
2. **Metadata filter**: Narrow by source_type, domain, tags
3. **Recency boost**: Prefer recently updated content
4. **Hybrid retrieval**: Combine vector results with keyword matches (future)

---

*Document Version: 1.0*  
*Last Updated: December 2025*
