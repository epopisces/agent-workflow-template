# Copyright (c) 2024. All rights reserved.
"""Knowledge Ingestion Agent Tool.

This agent processes content and stores it in organizational knowledge stores:
- Instructions File: High-level org context summaries
- Org URL Index: Index of org-relevant URLs with metadata
- User Notes Files: Local markdown files with frontmatter

It supports confidence/relevance scores and human-in-the-loop review for
content below configured thresholds.
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import yaml
from agent_framework import ChatAgent
from agent_framework.ollama import OllamaChatClient
from pydantic import BaseModel, Field

from app.config import get_config, load_instructions

# Logger for Knowledge Ingestion
logger = logging.getLogger("workflow.knowledge_ingestion")

# Fallback instructions if file not found
_FALLBACK_INSTRUCTIONS = """You are a Knowledge Ingestion specialist. Store content appropriately:
- URLs go to the URL index (add_url_to_index)
- High-level summaries go to the instructions file (update_instructions_file)
- Detailed notes go to topic-specific note files (create_note)

Always use get_knowledge_status first to understand the current state."""


# ============================================================================
# Data Models
# ============================================================================

class URLIndexEntry(BaseModel):
    """Entry in the URL index."""
    url: str
    title: str
    domain: str = Field(description="Domain of knowledge (e.g., 'engineering', 'hr', 'finance')")
    context: str = Field(description="Brief context about why this URL is relevant")
    summary: str = Field(description="Content summary")
    tags: list[str] = Field(default_factory=list)
    added_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)


class NoteMetadata(BaseModel):
    """Frontmatter metadata for a note file."""
    title: str
    created: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    updated: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    domain: str = Field(default="general", description="Domain of knowledge")
    category: str = Field(default="general")
    tags: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    source_url: str | None = Field(default=None)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    reviewed: bool = Field(default=False)
    priority: str = Field(default="medium")


class NotesIndexEntry(BaseModel):
    """Entry in the notes index."""
    filename: str
    title: str
    domain: str
    category: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    created: str
    updated: str
    confidence: float = Field(default=1.0)
    relevance: float = Field(default=1.0)


@dataclass
class IngestionResult:
    """Result of a knowledge ingestion operation."""
    success: bool
    message: str
    requires_review: bool = False
    review_reason: str | None = None
    stored_path: str | None = None


@dataclass
class HumanReviewRequest:
    """Request for human review of content before ingestion."""
    content_type: str  # 'url', 'note', 'instruction'
    content_preview: str
    confidence: float
    relevance: float
    proposed_action: str
    metadata: dict


# ============================================================================
# Storage Tools
# ============================================================================

def _get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def _ensure_directory(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def add_url_to_index(
    url: Annotated[str, Field(description="The URL to add to the index")],
    title: Annotated[str, Field(description="Title of the page")],
    domain: Annotated[str, Field(description="Domain of knowledge (e.g., 'engineering', 'hr', 'finance')")],
    context: Annotated[str, Field(description="Brief context about why this URL is relevant to the org")],
    summary: Annotated[str, Field(description="Summary of the content")],
    tags: Annotated[str, Field(description="Comma-separated list of tags")] = "",
    confidence: Annotated[float, Field(description="Confidence score 0.0-1.0")] = 1.0,
    relevance: Annotated[float, Field(description="Relevance score 0.0-1.0")] = 1.0,
) -> str:
    """Add a URL entry to the organizational URL index.
    
    This tool stores URLs with metadata for future reference by agents.
    
    Args:
        url: The URL to index.
        title: Page title.
        domain: Knowledge domain.
        context: Why this URL is relevant.
        summary: Content summary.
        tags: Comma-separated tags.
        confidence: Confidence in the content quality (0.0-1.0).
        relevance: Relevance to the organization (0.0-1.0).
        
    Returns:
        Status message indicating success or failure.
    """
    logger.info(f"[TOOL CALL] add_url_to_index: {url}")
    config = get_config()
    
    # Check thresholds - if below, return request for review
    if confidence < config.knowledge.confidence_threshold or relevance < config.knowledge.relevance_threshold:
        review_reasons = []
        if confidence < config.knowledge.confidence_threshold:
            review_reasons.append(f"confidence ({confidence:.2f}) below threshold ({config.knowledge.confidence_threshold})")
        if relevance < config.knowledge.relevance_threshold:
            review_reasons.append(f"relevance ({relevance:.2f}) below threshold ({config.knowledge.relevance_threshold})")
        
        logger.info(f"[TOOL RESULT] add_url_to_index requires review: {', '.join(review_reasons)}")
        return f"REVIEW_REQUIRED: Cannot add URL without human approval. Reasons: {', '.join(review_reasons)}. " \
               f"Please confirm you want to add URL '{title}' ({url}) with domain='{domain}'. " \
               f"To proceed, call this tool again after user confirmation with adjusted scores or explicit approval."
    
    try:
        project_root = _get_project_root()
        index_path = project_root / config.knowledge.url_index_file
        _ensure_directory(index_path.parent)
        
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        
        # Create entry
        entry = URLIndexEntry(
            url=url,
            title=title,
            domain=domain,
            context=context,
            summary=summary,
            tags=tag_list,
            confidence=confidence,
            relevance=relevance,
        )
        
        # Load existing index or create new
        index_data: list[dict] = []
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or {}
                index_data = existing.get("urls", [])
        
        # Check for duplicate URL
        for existing_entry in index_data:
            if existing_entry.get("url") == url:
                logger.info(f"[TOOL RESULT] URL already in index, updating: {url}")
                existing_entry.update(entry.model_dump())
                break
        else:
            index_data.append(entry.model_dump())
        
        # Write back
        with open(index_path, "w", encoding="utf-8") as f:
            yaml.dump({"urls": index_data}, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"[TOOL RESULT] add_url_to_index completed: {url}")
        return f"Successfully added URL to index: {title} ({url}). Domain: {domain}, Tags: {tag_list}"
        
    except Exception as e:
        logger.error(f"Failed to add URL to index: {e}")
        return f"Error adding URL to index: {e}"


def update_instructions_file(
    section: Annotated[str, Field(description="Section header to update (e.g., 'Team Structure', 'Processes')")],
    content: Annotated[str, Field(description="The content to add or update under this section")],
    action: Annotated[Literal["append", "replace"], Field(description="Whether to append to or replace the section")] = "append",
    confidence: Annotated[float, Field(description="Confidence score 0.0-1.0")] = 1.0,
    relevance: Annotated[float, Field(description="Relevance score 0.0-1.0")] = 1.0,
) -> str:
    """Update the organizational instructions file with new context.
    
    The instructions file contains high-level org context summaries organized by sections.
    
    Args:
        section: The section header to update.
        content: Content to add under this section.
        action: Whether to 'append' to existing content or 'replace' it.
        confidence: Confidence in the content accuracy (0.0-1.0).
        relevance: Relevance to the organization (0.0-1.0).
        
    Returns:
        Status message indicating success or failure.
    """
    logger.info(f"[TOOL CALL] update_instructions_file: section='{section}', action={action}")
    config = get_config()
    
    # Check thresholds
    if confidence < config.knowledge.confidence_threshold or relevance < config.knowledge.relevance_threshold:
        review_reasons = []
        if confidence < config.knowledge.confidence_threshold:
            review_reasons.append(f"confidence ({confidence:.2f}) below threshold ({config.knowledge.confidence_threshold})")
        if relevance < config.knowledge.relevance_threshold:
            review_reasons.append(f"relevance ({relevance:.2f}) below threshold ({config.knowledge.relevance_threshold})")
        
        logger.info(f"[TOOL RESULT] update_instructions_file requires review: {', '.join(review_reasons)}")
        return f"REVIEW_REQUIRED: Cannot update instructions without human approval. Reasons: {', '.join(review_reasons)}. " \
               f"Please confirm you want to {action} section '{section}'. Content preview: {content[:200]}..."
    
    try:
        project_root = _get_project_root()
        instructions_path = project_root / config.knowledge.instructions_file
        _ensure_directory(instructions_path.parent)
        
        # Load existing file or create template
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        else:
            file_content = f"# Organizational Instructions\n\nLast Updated: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        # Find or create section
        section_header = f"## {section}"
        section_pattern = rf"(## {re.escape(section)})\n(.*?)(?=\n## |\Z)"
        
        if section_header in file_content:
            if action == "replace":
                # Replace existing section
                file_content = re.sub(
                    section_pattern,
                    f"{section_header}\n\n{content}\n",
                    file_content,
                    flags=re.DOTALL
                )
            else:  # append
                # Append to existing section
                def append_content(match):
                    return f"{match.group(1)}\n{match.group(2).rstrip()}\n\n{content}\n"
                file_content = re.sub(section_pattern, append_content, file_content, flags=re.DOTALL)
        else:
            # Add new section at end
            file_content = file_content.rstrip() + f"\n\n{section_header}\n\n{content}\n"
        
        # Update timestamp
        file_content = re.sub(
            r"Last Updated: \d{4}-\d{2}-\d{2}",
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}",
            file_content
        )
        
        # Write back
        with open(instructions_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        logger.info(f"[TOOL RESULT] update_instructions_file completed: section='{section}'")
        return f"Successfully updated instructions file section: {section} (action: {action})"
        
    except Exception as e:
        logger.error(f"Failed to update instructions file: {e}")
        return f"Error updating instructions file: {e}"


def create_note(
    title: Annotated[str, Field(description="Title of the note")],
    content: Annotated[str, Field(description="Main content of the note in markdown format")],
    topic: Annotated[str, Field(description="Topic/category key from config (e.g., 'default')")] = "default",
    domain: Annotated[str, Field(description="Domain of knowledge (e.g., 'engineering', 'processes')")] = "general",
    category: Annotated[str, Field(description="Category for the note")] = "general",
    tags: Annotated[str, Field(description="Comma-separated list of tags")] = "",
    summary: Annotated[str, Field(description="Brief summary of the note")] = "",
    source_url: Annotated[str | None, Field(description="Source URL if content was extracted from web")] = None,
    confidence: Annotated[float, Field(description="Confidence score 0.0-1.0")] = 1.0,
    relevance: Annotated[float, Field(description="Relevance score 0.0-1.0")] = 1.0,
) -> str:
    """Create a new note file with frontmatter metadata.
    
    Notes are stored in topic-specific directories with YAML frontmatter for metadata.
    
    Args:
        title: Note title (used for filename).
        content: Markdown content of the note.
        topic: Topic key for organizing notes.
        domain: Knowledge domain.
        category: Note category.
        tags: Comma-separated tags.
        summary: Brief summary.
        source_url: Optional source URL.
        confidence: Confidence in content accuracy (0.0-1.0).
        relevance: Relevance to organization (0.0-1.0).
        
    Returns:
        Status message with file path or error.
    """
    logger.info(f"[TOOL CALL] create_note: title='{title}', topic={topic}")
    config = get_config()
    
    # Check thresholds
    if confidence < config.knowledge.confidence_threshold or relevance < config.knowledge.relevance_threshold:
        review_reasons = []
        if confidence < config.knowledge.confidence_threshold:
            review_reasons.append(f"confidence ({confidence:.2f}) below threshold ({config.knowledge.confidence_threshold})")
        if relevance < config.knowledge.relevance_threshold:
            review_reasons.append(f"relevance ({relevance:.2f}) below threshold ({config.knowledge.relevance_threshold})")
        
        logger.info(f"[TOOL RESULT] create_note requires review: {', '.join(review_reasons)}")
        return f"REVIEW_REQUIRED: Cannot create note without human approval. Reasons: {', '.join(review_reasons)}. " \
               f"Note title: '{title}', domain: '{domain}'. Content preview: {content[:200]}..."
    
    try:
        project_root = _get_project_root()
        
        # Get topic config
        if topic not in config.knowledge.notes_topics:
            logger.warning(f"Topic '{topic}' not found, using 'default'")
            topic = "default"
        
        topic_config = config.knowledge.notes_topics[topic]
        notes_dir = project_root / topic_config.directory
        _ensure_directory(notes_dir)
        
        # Generate filename from title
        safe_title = re.sub(r'[^\w\s-]', '', title.lower())
        safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
        filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}.md"
        filepath = notes_dir / filename
        
        # Handle duplicate filenames
        counter = 1
        while filepath.exists():
            filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}-{counter}.md"
            filepath = notes_dir / filename
            counter += 1
        
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        
        # Merge with topic defaults
        defaults = topic_config.frontmatter_defaults
        
        # Create metadata
        metadata = NoteMetadata(
            title=title,
            domain=domain,
            category=category or defaults.get("category", "general"),
            tags=tag_list,
            summary=summary,
            source_url=source_url,
            confidence=confidence,
            relevance=relevance,
            reviewed=defaults.get("reviewed", False),
            priority=defaults.get("priority", "medium"),
        )
        
        # Build file content with frontmatter
        frontmatter = yaml.dump(metadata.model_dump(exclude_none=True), default_flow_style=False, sort_keys=False)
        file_content = f"---\n{frontmatter}---\n\n{content}"
        
        # Write file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        # Update notes index
        _update_notes_index(topic, metadata, filename)
        
        relative_path = filepath.relative_to(project_root)
        logger.info(f"[TOOL RESULT] create_note completed: {relative_path}")
        return f"Successfully created note: {relative_path}"
        
    except Exception as e:
        logger.error(f"Failed to create note: {e}")
        return f"Error creating note: {e}"


def _update_notes_index(topic: str, metadata: NoteMetadata, filename: str) -> None:
    """Update the notes index for a topic after creating/updating a note."""
    config = get_config()
    project_root = _get_project_root()
    
    topic_config = config.knowledge.notes_topics.get(topic, config.knowledge.notes_topics["default"])
    notes_dir = project_root / topic_config.directory
    index_path = notes_dir / "_index.yaml"
    
    # Load existing index
    index_data: list[dict] = []
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or {}
            index_data = existing.get("notes", [])
    
    # Create index entry
    entry = NotesIndexEntry(
        filename=filename,
        title=metadata.title,
        domain=metadata.domain,
        category=metadata.category,
        summary=metadata.summary,
        tags=metadata.tags,
        created=metadata.created,
        updated=metadata.updated,
        confidence=metadata.confidence,
        relevance=metadata.relevance,
    )
    
    # Update or add entry
    for i, existing_entry in enumerate(index_data):
        if existing_entry.get("filename") == filename:
            index_data[i] = entry.model_dump()
            break
    else:
        index_data.append(entry.model_dump())
    
    # Write index
    with open(index_path, "w", encoding="utf-8") as f:
        yaml.dump({
            "topic": topic,
            "description": topic_config.description,
            "notes": index_data
        }, f, default_flow_style=False, sort_keys=False)


def get_knowledge_status() -> str:
    """Get the current status of all knowledge stores.
    
    Returns a summary of the instructions file, URL index, and notes indexes.
    
    Returns:
        Status summary of all knowledge stores.
    """
    logger.info("[TOOL CALL] get_knowledge_status")
    config = get_config()
    project_root = _get_project_root()
    
    status_parts = []
    
    # Instructions file status
    instructions_path = project_root / config.knowledge.instructions_file
    if instructions_path.exists():
        with open(instructions_path, "r", encoding="utf-8") as f:
            content = f.read()
        sections = re.findall(r"^## (.+)$", content, re.MULTILINE)
        status_parts.append(f"Instructions File: {len(sections)} sections - {', '.join(sections)}")
    else:
        status_parts.append("Instructions File: Not created yet")
    
    # URL index status
    url_index_path = project_root / config.knowledge.url_index_file
    if url_index_path.exists():
        with open(url_index_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        url_count = len(data.get("urls", []))
        status_parts.append(f"URL Index: {url_count} URLs indexed")
    else:
        status_parts.append("URL Index: Not created yet")
    
    # Notes status by topic
    for topic, topic_config in config.knowledge.notes_topics.items():
        notes_dir = project_root / topic_config.directory
        index_path = notes_dir / "_index.yaml"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            note_count = len(data.get("notes", []))
            status_parts.append(f"Notes ({topic}): {note_count} notes in {topic_config.directory}/")
        else:
            status_parts.append(f"Notes ({topic}): No notes yet in {topic_config.directory}/")
    
    # Thresholds info
    status_parts.append(f"\nThresholds - Confidence: {config.knowledge.confidence_threshold}, Relevance: {config.knowledge.relevance_threshold}")
    
    result = "\n".join(status_parts)
    logger.info(f"[TOOL RESULT] get_knowledge_status completed")
    return result


# ============================================================================
# Knowledge Ingestion Agent
# ============================================================================

class KnowledgeIngestionAgent:
    """Knowledge Ingestion Agent that stores content in organizational knowledge stores.
    
    This agent processes content and determines the appropriate storage location:
    - URLs go to the URL index
    - High-level summaries go to the instructions file
    - Detailed notes go to topic-specific note files
    
    It supports confidence/relevance scoring and will request human review for
    content below configured thresholds.
    """
    
    def __init__(self, chat_client: OllamaChatClient | None = None):
        """Initialize the Knowledge Ingestion Agent.
        
        Args:
            chat_client: Optional OllamaChatClient. If not provided,
                        creates one using config settings.
        """
        logger.info("Initializing KnowledgeIngestionAgent")
        config = get_config()
        
        if chat_client is None:
            logger.debug(f"Creating OllamaChatClient for KnowledgeIngestionAgent: {config.models.ollama.model_id}")
            chat_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
        
        # Load instructions from file or use fallback
        instructions = load_instructions(
            config.agents.knowledge_ingestion.instructions_file,
            confidence_threshold=config.knowledge.confidence_threshold,
            relevance_threshold=config.knowledge.relevance_threshold,
            topics=self._format_topics(config)
        )
        if instructions is None:
            logger.warning("Using fallback instructions for knowledge_ingestion")
            instructions = _FALLBACK_INSTRUCTIONS
        
        self._agent = chat_client.create_agent(
            name=config.agents.knowledge_ingestion.name,
            description=config.agents.knowledge_ingestion.description,
            instructions=instructions,
            tools=[
                add_url_to_index,
                update_instructions_file,
                create_note,
                get_knowledge_status,
            ],
        )
        logger.debug("KnowledgeIngestionAgent initialized with knowledge storage tools")
    
    def _format_topics(self, config) -> str:
        """Format topics configuration for agent instructions."""
        lines = []
        for topic, topic_config in config.knowledge.notes_topics.items():
            lines.append(f"- **{topic}**: {topic_config.description} (directory: {topic_config.directory}/)")
        return "\n".join(lines)
    
    @property
    def agent(self) -> ChatAgent:
        """Get the underlying ChatAgent."""
        return self._agent
    
    def as_tool(
        self,
        name: str = "knowledge_ingestion",
        description: str = "Process and store content in organizational knowledge stores. Use this tool when users share context about themselves, their role, their workflow, tools they use, or organizational information. User/role context goes to the INSTRUCTIONS FILE. Detailed documentation goes to NOTES.",
        arg_name: str = "request",
        arg_description: str = "A request describing what content to ingest. For user context (role, skills, tools, workflow), specify 'update instructions file'. For detailed docs, specify 'create note'."
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
        logger.debug(f"Converting KnowledgeIngestionAgent to tool: {name}")
        return self._agent.as_tool(
            name=name,
            description=description,
            arg_name=arg_name,
            arg_description=arg_description,
        )
    
    async def run(self, query: str) -> str:
        """Run the knowledge ingestion agent with a query.
        
        Args:
            query: The query/request for the agent.
            
        Returns:
            The agent's response.
        """
        logger.info(f"[AGENT HANDOFF] KnowledgeIngestionAgent received request: {query[:80]}{'...' if len(query) > 80 else ''}")
        result = await self._agent.run(query)
        logger.info(f"[AGENT HANDOFF] KnowledgeIngestionAgent completed: {len(result.text)} chars response")
        return result.text
    
    async def run_stream(self, query: str):
        """Run the knowledge ingestion agent with streaming output.
        
        Args:
            query: The query/request for the agent.
            
        Yields:
            Text chunks from the agent's response.
        """
        logger.info(f"[AGENT HANDOFF] KnowledgeIngestionAgent received request (streaming): {query[:80]}{'...' if len(query) > 80 else ''}")
        chunk_count = 0
        async for chunk in self._agent.run_stream(query):
            if chunk.text:
                chunk_count += 1
                yield chunk.text
        logger.info(f"[AGENT HANDOFF] KnowledgeIngestionAgent stream completed: {chunk_count} chunks")
