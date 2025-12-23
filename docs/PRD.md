# Product Requirements Document: Multi-Agent Workflow Assistant

## 1. Elevator Pitch

A locally-hosted Python/Streamlit application that enables individual end users to process web content, files, and text through a coordinator agent that orchestrates specialized tool agents. Users ask questions like "Is this URL useful for my team?" and receive polished, context-aware responses written in their personal style—ready to share with peers. The modular plugin architecture allows easy addition of new tool agents, while flexible model configuration supports local Ollama models, hosted APIs, or Azure AI Foundry.

## 2. Who Is This App For

- **Primary User**: Individual end users working on their local workstation
- **Use Case**: Personal productivity tool for processing information, generating team-ready communications, and building organizational knowledge
- **Deployment**: Local-first (single user), with potential future web hosting for individual (non-collaborative) use
- **Technical Comfort**: Users comfortable with local model hosting (Ollama) and configuration files

## 3. Functional Requirements

### Core Architecture
- **Coordinator Agent**: Central agent that communicates with the user, routes tasks to tool agents, parses responses, and determines if additional agents are needed or if results are ready for the user
- **Plugin-Based Tool Agents**: Modular agents in separate folders, registered via a tool registration pattern (agent-as-tool workflow per Microsoft Agent Framework)
  - **Third-party Integration**: Future support for integrating external APIs as tools
- **Flexible Model Backend**: Configuration-driven model selection supporting Ollama (local), hosted APIs, and Azure AI Foundry
- **Context & Environment State**: Maintains conversation history, organizational knowledge, and user style examples for context-aware responses

### Initial Tool Agents

| Agent | Purpose |
|-------|---------|
| **URL Scraper Agent** | Fetches and parses web content from provided URLs |
| **Org Context Agent** | Retrieves relevant organizational knowledge to contextualize responses |
| **Writer Agent** | Transforms content into the user's personal style/voice |
| **Knowledge Ingestion Agent** | Processes new content and updates organizational knowledge stores |

### Knowledge Sources
- **Instructions File**: Local file with high-level org context summaries
- **Org URL Index**: Index of org-relevant URLs with metadata (domain of knowledge, context, content summary)
- **User Notes Files**: Local markdown files with frontmatter (both agent and user-generated)
  - **User Notes Index**: Index of Local markdown files with metadata (domain of knowledge, context, content summary)
- **Style Examples**: 1-to-1 input/output pairs (source URLs/chats → user-written documentation)
- **Future**: Vector database for mature RAG implementation

### Conversation Management
- Persistent chat threads stored locally
- Ability to resume past conversation threads
- Thread history browsable and selectable

### Supported Input Types
- User chat (with or without URLs)
- Plain text files (.txt)
- Markdown files (.md)
- PDF (future state—PDF processing agent)
- Images (.png, .jpg, future state—image processing agent)

## 4. User Stories

### Information Processing
> *As a user, I want to include a URL in a chat and ask questions related to it such as "Is there anything useful here for my team?" so that I can quickly assess and share relevant content.*

### Knowledge Building
> *As a user, I want to ingest a new document into my org knowledge base so that future queries can reference it.*

### Styled Output
> *As a user, I want responses written in my voice and style so that I can share them directly with peers without heavy editing.*

### Conversation Continuity
> *As a user, I want to resume a previous chat thread so that I can continue working on a topic without losing context.*

### File Input
> *As a user, I want to drag-and-drop a markdown file into the chat so that the agents can process its contents.*

### Model Flexibility
> *As a user, I want to switch between local Ollama models and cloud-hosted models via configuration so that I can balance speed, cost, and capability.*

## 5. User Interface

### Layout
- **Streamlit-based single-page app**
- **Left Sidebar**: Thread list (past conversations), new chat button, settings access
- **Main Area**: Chat interface with message history
- **Input Area**: Text input with drag-and-drop zone for files/images

### Key UI Elements

| Component | Description |
|-----------|-------------|
| **Chat Input** | Text field for user messages |
| **Drop Zone** | Drag-and-drop area for files and images (visual indicator on drag) |
| **Thread List** | Scrollable list of past conversations with timestamps/previews |
| **New Chat Button** | Creates a fresh conversation thread |
| **Settings Panel** | Model selection, knowledge source paths (future iteration) |

### Agent Visibility
- **Initial**: Agent activity logged to console/file for debugging
- **Future**: In-UI panel showing which agents are invoked and their reasoning chain

### Visual Style
- Clean, minimal interface
- Focus on readability of chat messages
- Clear visual distinction between user input and agent responses
