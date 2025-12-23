# Knowledge Ingestion Agent

## Purpose
Processes content and stores it in organizational knowledge stores:
- **Instructions File**: High-level org context summaries
- **Org URL Index**: Index of org-relevant URLs with metadata
- **User Notes Files**: Local markdown files with frontmatter and index

Supports confidence/relevance scoring with human-in-the-loop review for content below configured thresholds.

### Owner/Maintainer
- Name: [Your Name]

### Version
0.1.0

---

## Implementation Status

### Stage
- [ ] Planned
- [ ] WIP (In Progress)
- [x] Complete
- [ ] Deprecated
- [ ] Maintenance

### Last Updated
2024.12.22 - Initial implementation complete

### Key Milestones
- Initial implementation: Complete
- Tool registration pattern: Complete
- Human-in-the-loop support: Complete
- Multiple knowledge stores: Complete
- Topic-based note organization: Complete

---

## Agent Characteristics

### Input Types
- **Natural language request**: Query describing what content to ingest and where to store it
- **Structured content**: URL metadata, notes content, instructions updates

### Output Types
- **Status messages**: Success/failure status with details
- **Review requests**: When confidence/relevance below thresholds, requests human approval

### Context & Knowledge Stores
- **Instructions File** (`knowledge/instructions.md`): High-level org context
- **URL Index** (`knowledge/url_index.yaml`): Indexed URLs with metadata
- **Notes** (`notes/`): Topic-organized markdown files with frontmatter
- **Notes Index** (`notes/_index.yaml`): Index of notes per topic

### Memory Model
- **Type**: Persistent (file-based)
- **Description**: All ingested content is persisted to local files with indexes
- **Storage**: Local filesystem in configurable directories

---

## Tool Usage

### Tools Used by This Agent

| Tool Name | Purpose | Required |
|-----------|---------|----------|
| add_url_to_index | Add URLs with metadata to the URL index | Yes |
| update_instructions_file | Update org context in instructions file | Yes |
| create_note | Create markdown notes with frontmatter | Yes |
| get_knowledge_status | Check status of all knowledge stores | Yes |

### Capabilities as a Tool
When registered as a tool for other agents:

#### Function Signature
```python
async def run(self, query: str) -> str:
    """Run the knowledge ingestion agent with a query.
    
    Args:
        query: The query/request for the agent (e.g., "Store this URL as relevant to engineering")
        
    Returns:
        The agent's response with status of ingestion operation.
    """

async def run_stream(self, query: str):
    """Run the knowledge ingestion agent with streaming output.
    
    Args:
        query: The query/request for the agent.
        
    Yields:
        Text chunks from the agent's response.
    """
```

#### Tool Registration Details
- **Tool ID**: `knowledge_ingestion`
- **Handler Method**: `KnowledgeIngestionAgent.as_tool()`
- **Required Parameters**: 
  - `request` (str): Description of what content to ingest and target store
- **Optional Parameters**: None
- **Return Format**: Plain text string with status message

**Tool Description**:
> "Process and store content in organizational knowledge stores (URL index, instructions file, or notes). Use this tool when you need to save information for future reference."

---

## Human-in-the-Loop Support

The agent implements human-in-the-loop review based on confidence and relevance scores:

### Thresholds (Configurable in `config/config.yaml`)
- **confidence_threshold**: Default 0.7 (content with lower confidence requires approval)
- **relevance_threshold**: Default 0.6 (content with lower relevance requires approval)

### Review Flow
1. Content is submitted with confidence/relevance scores
2. If either score is below threshold, the tool returns `REVIEW_REQUIRED`
3. Agent informs user of review requirement
4. User confirms/rejects the ingestion
5. On confirmation, agent re-invokes the tool (or user can adjust scores)

### Example Review Message
```
REVIEW_REQUIRED: Cannot add URL without human approval. 
Reasons: confidence (0.65) below threshold (0.7).
Please confirm you want to add URL 'Example Page' (https://example.com) with domain='engineering'.
To proceed, call this tool again after user confirmation with adjusted scores or explicit approval.
```

---

## Configuration

### Config File Location
`config/config.yaml` under the `knowledge:` section

### Configuration Options

```yaml
knowledge:
  # Thresholds for human review
  confidence_threshold: 0.7
  relevance_threshold: 0.6
  
  # File paths
  instructions_file: "knowledge/instructions.md"
  url_index_file: "knowledge/url_index.yaml"
  
  # Notes topics configuration
  notes_topics:
    default:
      directory: "notes"
      template: "config/templates/note_template.md"
      description: "General notes and documentation"
      frontmatter_defaults:
        category: "general"
        priority: "medium"
        reviewed: false
```

### Adding Custom Topics

Add new topics under `notes_topics`:

```yaml
notes_topics:
  default:
    # ... default config ...
  
  engineering:
    directory: "notes/engineering"
    template: "config/templates/tech_note_template.md"
    description: "Engineering and technical documentation"
    frontmatter_defaults:
      category: "technical"
      priority: "high"
      reviewed: false
```

---

## Data Formats

### URL Index Entry Schema
```yaml
url: "https://example.com/page"
title: "Page Title"
domain: "engineering"          # Knowledge domain
context: "Why this is relevant"
summary: "Content summary"
tags: ["tag1", "tag2"]
added_date: "2024-12-22T10:30:00"
confidence: 0.95
relevance: 0.85
```

### Note Frontmatter Schema
```yaml
title: "Note Title"
created: "2024-12-22"
updated: "2024-12-22"
domain: "general"
category: "documentation"
tags: ["tag1", "tag2"]
summary: "Brief summary"
source_url: "https://example.com"  # Optional
confidence: 0.9
relevance: 0.8
reviewed: false
priority: "medium"
```

### Notes Index Entry Schema
```yaml
filename: "20241222-note-title.md"
title: "Note Title"
domain: "general"
category: "documentation"
summary: "Brief summary"
tags: ["tag1", "tag2"]
created: "2024-12-22"
updated: "2024-12-22"
confidence: 0.9
relevance: 0.8
```

---

## Usage Examples

### Example 1: Store a URL
```python
agent = KnowledgeIngestionAgent()
result = await agent.run("""
Store this URL in the knowledge base:
URL: https://docs.python.org/3/library/asyncio.html
Title: Python asyncio Documentation
Domain: engineering
Context: Official Python documentation for async programming
Summary: Comprehensive guide to Python's asyncio library including coroutines, tasks, and event loops.
Confidence: 0.95
Relevance: 0.85
Tags: python, async, documentation
""")
```

### Example 2: Update Instructions
```python
result = await agent.run("""
Add the following to the organizational instructions under "Development Processes":
All code changes must go through code review before merging. 
Reviews require at least one approval from a senior engineer.
Confidence: 1.0
Relevance: 1.0
""")
```

### Example 3: Create a Note
```python
result = await agent.run("""
Create a note documenting our meeting about Q1 planning:
Title: Q1 2025 Planning Meeting Notes
Domain: planning
Category: meeting-notes
Summary: Key decisions from Q1 planning session
Content:
## Attendees
- Team lead, engineering manager, product owner

## Key Decisions
1. Focus on API performance improvements
2. Migrate to new database by end of Q1
3. Hire 2 additional engineers

## Action Items
- [ ] Draft migration plan by Jan 15
- [ ] Post job listings by Jan 5
""")
```

### Example 4: Check Knowledge Status
```python
result = await agent.run("What's the current state of our knowledge stores?")
# Returns summary of instructions file sections, URL count, and notes count
```

---

## Integration with Coordinator

To register with the Coordinator agent, add to `coordinator.py`:

```python
from app.agents.tools.knowledge_ingestion import KnowledgeIngestionAgent

# In __init__:
if knowledge_ingestion is None:
    knowledge_client = OllamaChatClient(
        host=config.models.ollama.host,
        model_id=config.models.ollama.model_id,
    )
    knowledge_ingestion = KnowledgeIngestionAgent(chat_client=knowledge_client)

# Add to tools list:
tools=[url_scraper.as_tool(), knowledge_ingestion.as_tool()]
```

---

## Testing

### Test File Location
`tests/test_knowledge_ingestion.py`

### Key Test Scenarios
1. Add URL to index (above threshold)
2. Add URL requiring review (below threshold)
3. Update instructions file (append and replace)
4. Create note with frontmatter
5. Notes index update
6. Get knowledge status
7. Duplicate URL handling
8. Invalid topic fallback to default

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| File write failure | Returns error message, logs exception |
| Invalid topic | Falls back to 'default' topic with warning |
| Duplicate URL | Updates existing entry instead of creating duplicate |
| Below threshold | Returns REVIEW_REQUIRED message |
| YAML parse error | Returns error message, preserves existing data |

---

## Future Enhancements

- [ ] Vector database integration for semantic search
- [ ] Automatic relevance scoring based on content analysis
- [ ] Note versioning and history
- [ ] Bulk import functionality
- [ ] Export to external systems
- [ ] Tag taxonomy management
- [ ] Cross-reference linking between notes
- [ ] In-memory caching of specific data for performance
