"""Knowledge Retrieval Tool Functions.

Traditional (non-agent) tool functions for querying the knowledge base.
These are lightweight, direct functions — not agent-as-tool wrappers.

Functions:
- get_available_tags: Collect all unique tags from notes index and URL index.
- search_by_tags: Return matching notes/URLs (with summaries) for given tags.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import Field

from app.config import get_config
from app.metrics import track_tool_call

# Logger for Knowledge Retrieval
logger = logging.getLogger("workflow.knowledge_retrieval")


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class TagInfo:
    """Aggregated tag with source counts."""
    tag: str
    note_count: int = 0
    url_count: int = 0

    @property
    def total_count(self) -> int:
        return self.note_count + self.url_count


@dataclass
class KnowledgeMatch:
    """A knowledge item matching a tag search."""
    source_type: str  # "note" or "url"
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)
    # Note-specific
    filename: str | None = None
    domain: str | None = None
    category: str | None = None
    # URL-specific
    url: str | None = None


# ============================================================================
# Helpers
# ============================================================================

def _get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


def _load_notes_index() -> list[dict]:
    """Load all notes from all topic indexes.

    Returns:
        List of note entry dicts from _index.yaml files.
    """
    config = get_config()
    project_root = _get_project_root()
    all_notes: list[dict] = []

    for _topic, topic_config in config.knowledge.notes_topics.items():
        index_path = project_root / topic_config.directory / "_index.yaml"
        if not index_path.exists():
            continue
        with open(index_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        all_notes.extend(data.get("notes", []))

    return all_notes


def _load_url_index() -> list[dict]:
    """Load all URLs from the URL index.

    Returns:
        List of URL entry dicts.
    """
    config = get_config()
    project_root = _get_project_root()
    index_path = project_root / config.knowledge.url_index_file

    if not index_path.exists():
        return []

    with open(index_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data.get("urls", [])


# ============================================================================
# Public Tool Functions
# ============================================================================

@track_tool_call("knowledge_retrieval")
def get_available_tags() -> str:
    """Get all unique tags across the knowledge base (notes and URLs).

    Returns a formatted list of tags with counts showing how many notes
    and URLs use each tag.  This is useful for discovering what knowledge
    is available before doing a targeted search.

    Returns:
        Formatted string of available tags with source counts.
    """
    logger.info("[TOOL CALL] get_available_tags")

    try:
        notes = _load_notes_index()
        urls = _load_url_index()

        tag_map: dict[str, TagInfo] = {}

        for note in notes:
            for tag in note.get("tags", []):
                tag_lower = tag.lower().strip()
                if tag_lower not in tag_map:
                    tag_map[tag_lower] = TagInfo(tag=tag_lower)
                tag_map[tag_lower].note_count += 1

        for url_entry in urls:
            for tag in url_entry.get("tags", []):
                tag_lower = tag.lower().strip()
                if tag_lower not in tag_map:
                    tag_map[tag_lower] = TagInfo(tag=tag_lower)
                tag_map[tag_lower].url_count += 1

        if not tag_map:
            logger.info("[TOOL RESULT] get_available_tags: no tags found")
            return "No tags found in the knowledge base."

        # Sort by total count descending, then alphabetically
        sorted_tags = sorted(
            tag_map.values(),
            key=lambda t: (-t.total_count, t.tag),
        )

        lines = ["=== Available Knowledge Tags ===\n"]
        for info in sorted_tags:
            sources = []
            if info.note_count:
                sources.append(f"{info.note_count} note{'s' if info.note_count > 1 else ''}")
            if info.url_count:
                sources.append(f"{info.url_count} URL{'s' if info.url_count > 1 else ''}")
            lines.append(f"  - **{info.tag}** ({', '.join(sources)})")

        result = "\n".join(lines)
        logger.info(f"[TOOL RESULT] get_available_tags: {len(tag_map)} unique tags")
        return result

    except Exception as e:
        logger.error(f"Failed to get available tags: {e}")
        return f"Error retrieving tags: {e}"


@track_tool_call("knowledge_retrieval")
def search_by_tags(
    tags: Annotated[str, Field(description="Comma-separated list of tags to search for (e.g., 'python,agents')")],
) -> str:
    """Search the knowledge base for notes and URLs matching one or more tags.

    Returns file paths (for notes) or URLs with their summaries for every
    item that has at least one of the requested tags.

    Args:
        tags: Comma-separated tag names to search for.

    Returns:
        Formatted string of matching knowledge items with summaries.
    """
    logger.info(f"[TOOL CALL] search_by_tags: {tags}")

    try:
        search_tags = {t.strip().lower() for t in tags.split(",") if t.strip()}
        if not search_tags:
            return "No tags provided. Pass a comma-separated list of tags to search for."

        notes = _load_notes_index()
        urls = _load_url_index()
        config = get_config()
        matches: list[KnowledgeMatch] = []

        # Match notes
        for note in notes:
            note_tags = {t.lower().strip() for t in note.get("tags", [])}
            matched_tags = search_tags & note_tags
            if matched_tags:
                # Determine the file path relative to project root
                # Notes live under the topic directory
                topic_dir = None
                for _topic, topic_config in config.knowledge.notes_topics.items():
                    topic_dir = topic_config.directory
                    break  # use first match for path display
                filepath = f"{topic_dir}/{note.get('filename', '')}" if topic_dir else note.get("filename", "")

                matches.append(KnowledgeMatch(
                    source_type="note",
                    title=note.get("title", "Untitled"),
                    summary=note.get("summary", ""),
                    tags=sorted(note_tags),
                    filename=filepath,
                    domain=note.get("domain"),
                    category=note.get("category"),
                ))

        # Match URLs
        for url_entry in urls:
            url_tags = {t.lower().strip() for t in url_entry.get("tags", [])}
            matched_tags = search_tags & url_tags
            if matched_tags:
                matches.append(KnowledgeMatch(
                    source_type="url",
                    title=url_entry.get("title", "Untitled"),
                    summary=url_entry.get("summary", ""),
                    tags=sorted(url_tags),
                    url=url_entry.get("url"),
                    domain=url_entry.get("domain"),
                ))

        if not matches:
            logger.info(f"[TOOL RESULT] search_by_tags: no matches for {search_tags}")
            return f"No knowledge items found matching tags: {', '.join(sorted(search_tags))}"

        # Format output
        lines = [f"=== Knowledge matching tags: {', '.join(sorted(search_tags))} ===\n"]

        note_matches = [m for m in matches if m.source_type == "note"]
        url_matches = [m for m in matches if m.source_type == "url"]

        if note_matches:
            lines.append("**Notes:**\n")
            for m in note_matches:
                lines.append(f"  - **{m.title}**")
                lines.append(f"    File: {m.filename}")
                lines.append(f"    Domain: {m.domain} | Category: {m.category}")
                lines.append(f"    Tags: {', '.join(m.tags)}")
                lines.append(f"    Summary: {m.summary}")
                lines.append("")

        if url_matches:
            lines.append("**URLs:**\n")
            for m in url_matches:
                lines.append(f"  - **{m.title}**")
                lines.append(f"    URL: {m.url}")
                lines.append(f"    Domain: {m.domain}")
                lines.append(f"    Tags: {', '.join(m.tags)}")
                lines.append(f"    Summary: {m.summary}")
                lines.append("")

        result = "\n".join(lines)
        logger.info(f"[TOOL RESULT] search_by_tags: {len(matches)} matches ({len(note_matches)} notes, {len(url_matches)} URLs)")
        return result

    except Exception as e:
        logger.error(f"Failed to search by tags: {e}")
        return f"Error searching by tags: {e}"
