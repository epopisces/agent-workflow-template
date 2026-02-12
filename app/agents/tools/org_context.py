"""Organizational Context Agent Tool.

This agent retrieves organizational context from knowledge stores:
- Instructions file (high-level org context)
- Notes index and note files (detailed documentation)
- URL index (as last resort, triggers URL scraping)

It helps other agents understand organizational context when answering questions.
"""

import logging
from pathlib import Path
from typing import Annotated

import yaml
from agent_framework import ChatAgent
from agent_framework.ollama import OllamaChatClient
from pydantic import Field

from app.config import get_config, load_instructions
from app.metrics import track_tool_call

# Logger for Org Context
logger = logging.getLogger("workflow.org_context")

# Fallback instructions if file not found
_FALLBACK_INSTRUCTIONS = """You are an Organizational Context specialist. Your job is to retrieve and synthesize
organizational context from the knowledge base to help answer questions.

Use the available tools to find information:
- get_instructions_context: Get high-level org context
- search_knowledge: Search across all knowledge sources
- get_notes_index: List available notes
- read_note: Read a specific note
- get_url_index: List indexed URLs

Be thorough - if a note exists on a topic, READ IT and include the content."""


# ============================================================================
# Helper Functions
# ============================================================================

def _get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


# ============================================================================
# Context Retrieval Tools
# ============================================================================

@track_tool_call("org_context")
def get_instructions_context() -> str:
    """Get the high-level organizational context from the context file.
    
    This is the PRIMARY source of organizational context. Always check this first.
    
    Returns:
        The contents of the context file, or an error message.
    """
    logger.info("[TOOL CALL] get_instructions_context")
    config = get_config()
    
    try:
        project_root = _get_project_root()
        context_path = project_root / config.knowledge.context_file
        
        if not context_path.exists():
            logger.warning(f"Context file not found: {context_path}")
            return "No organizational context file found. The organization context has not been set up yet."
        
        with open(context_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"[TOOL RESULT] get_instructions_context: {len(content)} chars")
        return f"=== Organizational Context ===\n\n{content}"
        
    except Exception as e:
        logger.error(f"Failed to read context file: {e}")
        return f"Error reading context file: {e}"


@track_tool_call("org_context")
def get_notes_index() -> str:
    """Get the index of all available notes with their metadata.
    
    Use this to understand what detailed documentation is available,
    then use read_note to get specific note contents.
    
    Returns:
        A formatted list of available notes with summaries and tags.
    """
    logger.info("[TOOL CALL] get_notes_index")
    config = get_config()
    
    try:
        project_root = _get_project_root()
        all_notes = []
        
        # Check each topic's index
        for topic, topic_config in config.knowledge.notes_topics.items():
            index_path = project_root / topic_config.directory / "_index.yaml"
            
            if not index_path.exists():
                continue
                
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = yaml.safe_load(f) or {}
            
            notes = index_data.get("notes", [])
            for note in notes:
                all_notes.append({
                    "topic": topic,
                    "filename": note.get("filename", ""),
                    "title": note.get("title", "Untitled"),
                    "domain": note.get("domain", "general"),
                    "category": note.get("category", "general"),
                    "summary": note.get("summary", ""),
                    "tags": note.get("tags", []),
                    "created": note.get("created", ""),
                    "confidence": note.get("confidence", 1.0),
                    "relevance": note.get("relevance", 1.0),
                })
        
        if not all_notes:
            logger.info("[TOOL RESULT] get_notes_index: no notes found")
            return "No notes found in the knowledge base."
        
        # Format output
        output_lines = ["=== Available Notes ===\n"]
        for note in all_notes:
            tags_str = ", ".join(note["tags"]) if note["tags"] else "none"
            output_lines.append(f"**{note['title']}**")
            output_lines.append(f"  - File: {note['filename']}")
            output_lines.append(f"  - Topic: {note['topic']} | Domain: {note['domain']} | Category: {note['category']}")
            output_lines.append(f"  - Tags: {tags_str}")
            output_lines.append(f"  - Summary: {note['summary']}")
            output_lines.append(f"  - Created: {note['created']} | Confidence: {note['confidence']} | Relevance: {note['relevance']}")
            output_lines.append("")
        
        result = "\n".join(output_lines)
        logger.info(f"[TOOL RESULT] get_notes_index: {len(all_notes)} notes")
        return result
        
    except Exception as e:
        logger.error(f"Failed to read notes index: {e}")
        return f"Error reading notes index: {e}"


@track_tool_call("org_context")
def read_note(
    filename: Annotated[str, Field(description="The filename of the note to read (e.g., '20251227-my-note.md')")]
) -> str:
    """Read the full content of a specific note file.
    
    Use get_notes_index first to find relevant notes, then use this to read them.
    
    Args:
        filename: The filename of the note to read.
        
    Returns:
        The full content of the note, or an error message.
    """
    logger.info(f"[TOOL CALL] read_note: {filename}")
    config = get_config()
    
    try:
        project_root = _get_project_root()
        
        # Search for the note in all topic directories
        for topic, topic_config in config.knowledge.notes_topics.items():
            note_path = project_root / topic_config.directory / filename
            
            if note_path.exists():
                with open(note_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                logger.info(f"[TOOL RESULT] read_note: {filename} ({len(content)} chars)")
                return f"=== Note: {filename} ===\n\n{content}"
        
        logger.warning(f"Note not found: {filename}")
        return f"Note not found: {filename}. Use get_notes_index to see available notes."
        
    except Exception as e:
        logger.error(f"Failed to read note {filename}: {e}")
        return f"Error reading note: {e}"


@track_tool_call("org_context")
def get_url_index() -> str:
    """Get the index of organizational URLs with metadata.
    
    Use this to find URLs that have been indexed as relevant to the organization.
    Only use fetch_indexed_url if the information is not available in instructions or notes.
    
    Returns:
        A formatted list of indexed URLs with context and summaries.
    """
    logger.info("[TOOL CALL] get_url_index")
    config = get_config()
    
    try:
        project_root = _get_project_root()
        index_path = project_root / config.knowledge.url_index_file
        
        if not index_path.exists():
            logger.info("[TOOL RESULT] get_url_index: no index found")
            return "No URL index found. No URLs have been indexed yet."
        
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = yaml.safe_load(f) or {}
        
        urls = index_data.get("urls", [])
        
        if not urls:
            logger.info("[TOOL RESULT] get_url_index: no URLs in index")
            return "URL index is empty. No URLs have been indexed yet."
        
        # Format output
        output_lines = ["=== Indexed URLs ===\n"]
        for url_entry in urls:
            tags_str = ", ".join(url_entry.get("tags", [])) if url_entry.get("tags") else "none"
            output_lines.append(f"**{url_entry.get('title', 'Untitled')}**")
            output_lines.append(f"  - URL: {url_entry.get('url', '')}")
            output_lines.append(f"  - Domain: {url_entry.get('domain', 'general')}")
            output_lines.append(f"  - Context: {url_entry.get('context', '')}")
            output_lines.append(f"  - Summary: {url_entry.get('summary', '')}")
            output_lines.append(f"  - Tags: {tags_str}")
            output_lines.append("")
        
        result = "\n".join(output_lines)
        logger.info(f"[TOOL RESULT] get_url_index: {len(urls)} URLs")
        return result
        
    except Exception as e:
        logger.error(f"Failed to read URL index: {e}")
        return f"Error reading URL index: {e}"


@track_tool_call("org_context")
def search_knowledge(
    query: Annotated[str, Field(description="Search terms to find in notes and instructions")]
) -> str:
    """Search across all knowledge sources for relevant content.
    
    Searches the instructions file and all notes for the given query terms.
    Returns matching content with context.
    
    Args:
        query: The search terms to look for.
        
    Returns:
        Matching content from knowledge sources.
    """
    logger.info(f"[TOOL CALL] search_knowledge: {query}")
    config = get_config()
    
    try:
        project_root = _get_project_root()
        results = []
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        # Search context file
        context_path = project_root / config.knowledge.context_file
        if context_path.exists():
            with open(context_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if any(term in content.lower() for term in query_terms):
                # Find relevant sections
                sections = content.split("\n## ")
                matching_sections = []
                for section in sections:
                    if any(term in section.lower() for term in query_terms):
                        matching_sections.append(section[:500] + "..." if len(section) > 500 else section)
                
                if matching_sections:
                    results.append("=== From Org Context ===")
                    results.extend(matching_sections[:3])  # Limit to 3 sections
                    results.append("")
        
        # Search notes
        for topic, topic_config in config.knowledge.notes_topics.items():
            notes_dir = project_root / topic_config.directory
            if not notes_dir.exists():
                continue
                
            for note_file in notes_dir.glob("*.md"):
                if note_file.name == "_index.yaml":
                    continue
                    
                with open(note_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if any(term in content.lower() for term in query_terms):
                    # Extract relevant portion
                    preview = content[:800] + "..." if len(content) > 800 else content
                    results.append(f"=== From Note: {note_file.name} ===")
                    results.append(preview)
                    results.append("")
        
        if not results:
            logger.info(f"[TOOL RESULT] search_knowledge: no results for '{query}'")
            return f"No matching content found for: {query}"
        
        result = "\n".join(results)
        logger.info(f"[TOOL RESULT] search_knowledge: found matches for '{query}'")
        return result
        
    except Exception as e:
        logger.error(f"Failed to search knowledge: {e}")
        return f"Error searching knowledge: {e}"


# ============================================================================
# Org Context Agent
# ============================================================================

class OrgContextAgent:
    """Organizational Context Agent that retrieves context from knowledge stores.
    
    This agent provides organizational context to help answer questions by:
    1. Reading the instructions file (primary high-level context)
    2. Searching and reading notes (detailed documentation)
    3. Checking the URL index (last resort for external info)
    
    It does NOT fetch URLs directly - if URL content is needed, it should
    be delegated to the URL scraper agent.
    """
    
    def __init__(
        self,
        chat_client: OllamaChatClient | None = None,
        url_scraper_tool = None,
    ):
        """Initialize the Org Context Agent.
        
        Args:
            chat_client: Optional OllamaChatClient. If not provided,
                        creates one using config settings.
            url_scraper_tool: Optional URL scraper tool for fetching indexed URLs.
        """
        logger.info("Initializing OrgContextAgent")
        config = get_config()
        
        if chat_client is None:
            logger.debug(f"Creating OllamaChatClient for OrgContextAgent: {config.models.ollama.model_id}")
            chat_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
        
        # Build tools list
        tools = [
            get_instructions_context,
            get_notes_index,
            read_note,
            get_url_index,
            search_knowledge,
        ]
        
        # Add URL scraper if provided (for fetching indexed URLs as last resort)
        if url_scraper_tool:
            tools.append(url_scraper_tool)
            url_scraper_instruction = """
### 6. fetch_indexed_url (LAST RESORT)
If you absolutely need live content from an indexed URL, use the url_scraper tool. Only do this if:
- The information is not in instructions or notes
- The URL is in the URL index (use get_url_index first)
- The user specifically needs current/live information"""
        else:
            url_scraper_instruction = """
Note: URL fetching is not available. If the user needs live URL content,
inform them they can use the main assistant to fetch URLs."""
        
        # Load instructions from file or use fallback
        instructions = load_instructions(
            config.agents.org_context.instructions_file,
            url_scraper_instruction=url_scraper_instruction
        )
        if instructions is None:
            logger.warning("Using fallback instructions for org_context")
            instructions = _FALLBACK_INSTRUCTIONS
        
        self._agent = chat_client.as_agent(
            name=config.agents.org_context.name,
            description=config.agents.org_context.description,
            instructions=instructions,
            tools=tools,
        )
        logger.debug("OrgContextAgent initialized with knowledge retrieval tools")
    
    @property
    def agent(self) -> ChatAgent:
        """Get the underlying ChatAgent."""
        return self._agent
    
    def as_tool(
        self,
        name: str = "org_context",
        description: str = "Retrieve organizational context from the knowledge base (instructions, notes, indexed URLs). Use this tool when you need to understand organizational context, team structure, processes, or find documented information.",
        arg_name: str = "query",
        arg_description: str = "A question or topic to find organizational context for."
    ):
        """Convert this agent to a tool that can be used by other agents.
        
        Args:
            name: Tool name.
            description: Tool description.
            arg_name: Name of the argument.
            arg_description: Description of the argument.
            
        Returns:
            A tool that can be passed to another agent.
        """
        logger.debug(f"Converting OrgContextAgent to tool: {name}")
        return self._agent.as_tool(
            name=name,
            description=description,
            arg_name=arg_name,
            arg_description=arg_description,
        )
    
    async def run(self, query: str) -> str:
        """Run the org context agent with a query.
        
        Args:
            query: The query/request for the agent.
            
        Returns:
            The agent's response.
        """
        logger.info(f"[AGENT HANDOFF] OrgContextAgent received request: {query[:80]}{'...' if len(query) > 80 else ''}")
        result = await self._agent.run(query)
        logger.info(f"[AGENT HANDOFF] OrgContextAgent completed: {len(result.text)} chars response")
        return result.text
    
    async def run_stream(self, query: str):
        """Run the org context agent with streaming output.
        
        Args:
            query: The query/request for the agent.
            
        Yields:
            Text chunks from the agent's response.
        """
        logger.info(f"[AGENT HANDOFF] OrgContextAgent received request (streaming): {query[:80]}{'...' if len(query) > 80 else ''}")
        chunk_count = 0
        async for chunk in self._agent.run_stream(query):
            if chunk.text:
                chunk_count += 1
                yield chunk.text
        logger.info(f"[AGENT HANDOFF] OrgContextAgent stream completed: {chunk_count} chunks")
