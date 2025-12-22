# URL Scraper Agent

## Purpose
Fetches and parses web content from provided URLs, extracting main text content and removing scripts, styles, and navigation elements. Designed to be used as an agent-as-tool by the Coordinator agent.

### Owner/Maintainer
DevOps Team

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
2025.12.21 - Initial implementation complete

### Key Milestones
- Initial implementation: Complete
- Tool registration pattern: Complete
- Error handling: Complete
- Content truncation: Complete

---

## Agent Characteristics

### Input Types
- **URL string**: Direct URL to fetch (via `fetch_url` tool)
- **Natural language request**: Query describing what URL to fetch and what to look for (via agent interface)

### Output Types
- **Formatted text**: URL, title, and extracted content
- **Error messages**: Clear descriptions of timeout, HTTP errors, or parsing failures

### Context & Knowledge Stores
- None (stateless agent)

### Memory Model
- **Type**: Stateless
- **Description**: No persistent memory between requests. Each URL fetch is independent.
- **Storage**: N/A

---

## Tool Usage

### Tools Used by This Agent
| Tool Name | Purpose | Required |
|-----------|---------|----------|
| fetch_url | Synchronous HTTP fetcher and HTML parser | Yes |

### Capabilities as a Tool
When registered as a tool for other agents:

#### Function Signature
```python
async def run(self, query: str) -> str:
    """Run the URL scraper agent with a query.
    
    Args:
        query: The query/request for the agent (e.g., "Fetch https://example.com and summarize")
        
    Returns:
        The agent's response with fetched and analyzed content.
    """

async def run_stream(self, query: str):
    """Run the URL scraper agent with streaming output.
    
    Args:
        query: The query/request for the agent.
        
    Yields:
        Text chunks from the agent's response.
    """
```

#### Tool Registration Details
- **Tool ID**: `url_scraper`
- **Handler Method**: `URLScraperAgent.as_tool()`
- **Required Parameters**: 
  - `request` (str): Description of what URL to fetch and what to look for
- **Optional Parameters**: None
- **Return Format**: Plain text string with URL, title, and content

**Tool Description**:
> "Fetch and analyze content from a URL. Use this tool when you need to retrieve and understand web page content."

### Usage Examples

#### Example 1: Direct URL Fetch
```
Input: "Fetch https://docs.python.org/3/library/asyncio.html and summarize"
Output: 
URL: https://docs.python.org/3/library/asyncio.html
Title: asyncio — Asynchronous I/O

Content:
asyncio is a library to write concurrent code using the async/await syntax.
asyncio is used as a foundation for multiple Python asynchronous frameworks...
[Analysis of key points for DevOps use cases]
```

#### Example 2: Content Analysis
```
Input: "Is there anything useful here for my DevOps team? https://example.com/kubernetes-best-practices"
Output:
URL: https://example.com/kubernetes-best-practices
Title: Kubernetes Best Practices for Production

Content:
[Extracted content]

Yes, this article contains several useful practices for DevOps teams:
1. Pod security policies
2. Resource limits and requests
3. Health check configuration
...
```

---

## Dependencies

### Python Packages
- `httpx`: HTTP client for fetching URLs
- `beautifulsoup4`: HTML parsing and content extraction
- `agent_framework`: Microsoft Agent Framework for agent implementation
- `pydantic`: Field annotations for tool parameters

### External Services
- Ollama server: LLM backend for content analysis and summarization
  - Configuration: `config.models.ollama.host` and `config.models.ollama.model_id`

### Other Agents
- None (can be used independently or as a tool)

---

## Configuration

### Environment Variables
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
```

### Config File Settings
```yaml
scraper:
  timeout: 30  # Request timeout in seconds
  user_agent: "Mozilla/5.0 (compatible; WorkflowBot/1.0)"
  max_content_length: 10000  # Maximum characters to return

agents:
  url_scraper:
    name: "URLScraperAgent"
    description: "Fetches and analyzes web content from URLs"

models:
  ollama:
    host: "http://localhost:11434"
    model_id: "llama3.2:latest"
```

### Default Behavior
- Follows HTTP redirects automatically
- Removes scripts, styles, navigation, headers, footers, asides, and forms
- Prioritizes main content areas (`<main>`, `<article>`, `.content`, `.main-content`)
- Truncates content at 10,000 characters by default
- Returns clear error messages for timeouts, HTTP errors, or parse failures

---

## Integration

### Coordinator Handoff
**When coordinator routes to this agent:**
- Receives: Natural language query (e.g., "Fetch https://example.com and tell me if it's useful for DevOps")
- Expected behavior: 
  1. Parse the query to identify URL(s)
  2. Call `fetch_url` tool to retrieve content
  3. Analyze and summarize the content using LLM
  4. Return formatted response with key findings
- Returns to coordinator: Plain text summary with URL, title, and analysis

### Error Handling
- **Timeout behavior**: Returns error message after configured timeout (default 30s)
- **Invalid input**: Validates URL format and returns clear error for malformed URLs
- **External service failure**: 
  - HTTP errors: Returns status code and reason phrase
  - Network errors: Returns descriptive error message
  - Parse errors: Returns error with context

### Logging & Observability
- **Log level**: INFO for tool calls and completions, DEBUG for fetch/parse details
- **Key log points**: 
  - `[TOOL CALL] fetch_url invoked with URL: {url}`
  - `[TOOL RESULT] fetch_url completed: {title} ({chars} chars)`
  - `[AGENT HANDOFF] URLScraperAgent received request: {query}`
  - `[AGENT HANDOFF] URLScraperAgent completed: {chars} chars response`
- **Metrics**: Response length, chunk count (for streaming)

---

## Dev Notes

### Architecture Decisions
- **Synchronous tool, async agent**: `fetch_url` is synchronous (simpler error handling), but agent interface is async (framework requirement)
- **HTML parsing over API**: Uses BeautifulSoup for maximum flexibility with varied webpage structures
- **Content truncation**: Prevents LLM context overflow while preserving most relevant content
- **Separate client instances**: Each agent gets its own OllamaChatClient to avoid state sharing

### Known Limitations
- Text-only extraction (no support for images, PDFs, or multimedia)
- No JavaScript execution (SPAs may not render properly)
- Basic content prioritization (may not work well for all webpage layouts)
- Fixed truncation length (doesn't consider semantic boundaries)
- No caching (fetches same URL multiple times if requested)

### Testing Strategy
- Unit tests: `tests/test_url_scraper.py`
  - Mock httpx responses for various scenarios
  - Test HTML parsing logic
  - Validate error handling paths
- Integration tests: `tests/test_url_scraper_agent.py`
  - Test agent initialization
  - Test tool registration
  - Test with real Ollama instance (if available)
- Mocking external dependencies: 
  - Use `pytest-httpx` for HTTP mocking
  - Mock OllamaChatClient for isolated agent tests

### Future Enhancements
- PDF processing support
- Image extraction and analysis
- JavaScript rendering (Playwright/Selenium integration)
- Content caching layer
- Semantic chunking for large documents
- Metadata extraction (author, publish date, keywords)
- Domain-specific parsing (GitHub, Stack Overflow, documentation sites)
- Integration with org URL index for known sources

### Related Issues/PRs
- N/A (initial implementation)

---

## Troubleshooting

### Common Issues & Solutions
| Issue | Solution |
|-------|----------|
| `Request timed out` | Increase `scraper.timeout` in config.yaml or check network connectivity |
| `HTTP 403/401 errors` | Some sites block automated requests; consider adding cookies or authentication |
| `Could not parse HTML content` | Website may have malformed HTML; check manually and consider preprocessing |
| `Content truncated` | Increase `scraper.max_content_length` if full content is needed |
| `No content extracted` | Website structure may not match expected patterns; debug with `.find()` calls |

### Debugging Tips
- Set log level to DEBUG to see fetch and parse details: `/loglevel=debug`
- Test `fetch_url` tool independently before using full agent
- Check HTML source manually to understand webpage structure
- Use `response.text[:500]` to inspect raw HTML

### Performance Considerations
- Timeout setting affects responsiveness (balance between patience and UX)
- Large content extraction can slow LLM processing
- Multiple concurrent fetches may trigger rate limiting
- Consider implementing request queuing for high-volume usage

---

## References

### Related Documentation
- [PRD](../PRD.md): Product requirements and use cases
- [Agent Framework Docs](https://github.com/microsoft/agent-framework): Microsoft Agent Framework documentation

### Code Files
- [app/agents/tools/url_scraper.py](../../app/agents/tools/url_scraper.py): Implementation
- [tests/test_url_scraper.py](../../tests/test_url_scraper.py): Unit tests
- [tests/test_url_scraper_agent.py](../../tests/test_url_scraper_agent.py): Integration tests
- [app/config.py](../../app/config.py): Configuration schema
