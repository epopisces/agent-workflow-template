"""Tests for Knowledge Ingestion Agent."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from app.config import (
    AppConfig,
    KnowledgeConfig,
    NoteTopicConfig,
    AgentsConfig,
    AgentConfig,
    ModelsConfig,
    OllamaConfig,
)


@pytest.fixture
def temp_knowledge_dir():
    """Create a temporary directory for knowledge files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_knowledge_dir):
    """Create a mock configuration for testing."""
    return AppConfig(
        models=ModelsConfig(
            ollama=OllamaConfig(host="http://localhost:11434", model_id="test-model")
        ),
        agents=AgentsConfig(
            coordinator=AgentConfig(name="Coordinator", description="Test coordinator"),
            url_scraper=AgentConfig(name="URLScraper", description="Test scraper"),
            knowledge_ingestion=AgentConfig(
                name="KnowledgeIngestion",
                description="Test knowledge ingestion"
            ),
        ),
        knowledge=KnowledgeConfig(
            confidence_threshold=0.7,
            relevance_threshold=0.6,
            context_file=str(temp_knowledge_dir / "context.md"),
            url_index_file=str(temp_knowledge_dir / "url_index.yaml"),
            notes_topics={
                "default": NoteTopicConfig(
                    directory=str(temp_knowledge_dir / "notes"),
                    template="config/templates/note_template.md",
                    description="Test notes",
                    frontmatter_defaults={
                        "category": "general",
                        "priority": "medium",
                        "reviewed": False,
                    },
                )
            },
        ),
    )


class TestAddUrlToIndex:
    """Tests for add_url_to_index tool."""
    
    def test_add_url_above_threshold(self, mock_config, temp_knowledge_dir):
        """Test adding URL with scores above threshold."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import add_url_to_index
                
                result = add_url_to_index(
                    url="https://example.com",
                    title="Example Page",
                    domain="engineering",
                    context="Test context",
                    summary="Test summary",
                    tags="python, testing",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                assert "Successfully added URL" in result
                assert "Example Page" in result
                
                # Verify file was created
                index_path = temp_knowledge_dir / "url_index.yaml"
                assert index_path.exists()
                
                with open(index_path) as f:
                    data = yaml.safe_load(f)
                
                assert len(data["urls"]) == 1
                assert data["urls"][0]["url"] == "https://example.com"
                assert data["urls"][0]["domain"] == "engineering"
                assert "python" in data["urls"][0]["tags"]
    
    def test_add_url_below_confidence_threshold(self, mock_config, temp_knowledge_dir):
        """Test that URLs below confidence threshold require review."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import add_url_to_index
                
                result = add_url_to_index(
                    url="https://example.com",
                    title="Example Page",
                    domain="engineering",
                    context="Test context",
                    summary="Test summary",
                    confidence=0.5,  # Below threshold
                    relevance=0.8,
                )
                
                assert "REVIEW_REQUIRED" in result
                assert "confidence" in result
    
    def test_add_url_below_relevance_threshold(self, mock_config, temp_knowledge_dir):
        """Test that URLs below relevance threshold require review."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import add_url_to_index
                
                result = add_url_to_index(
                    url="https://example.com",
                    title="Example Page",
                    domain="engineering",
                    context="Test context",
                    summary="Test summary",
                    confidence=0.9,
                    relevance=0.4,  # Below threshold
                )
                
                assert "REVIEW_REQUIRED" in result
                assert "relevance" in result
    
    def test_update_existing_url(self, mock_config, temp_knowledge_dir):
        """Test updating an existing URL entry."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import add_url_to_index
                
                # Add initial URL
                add_url_to_index(
                    url="https://example.com",
                    title="Original Title",
                    domain="engineering",
                    context="Original context",
                    summary="Original summary",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                # Update same URL
                result = add_url_to_index(
                    url="https://example.com",
                    title="Updated Title",
                    domain="engineering",
                    context="Updated context",
                    summary="Updated summary",
                    confidence=0.95,
                    relevance=0.85,
                )
                
                # Verify only one entry exists
                index_path = temp_knowledge_dir / "url_index.yaml"
                with open(index_path) as f:
                    data = yaml.safe_load(f)
                
                assert len(data["urls"]) == 1
                assert data["urls"][0]["title"] == "Updated Title"


class TestUpdateInstructionsFile:
    """Tests for update_instructions_file tool."""
    
    def test_create_new_section(self, mock_config, temp_knowledge_dir):
        """Test creating a new section in instructions file."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import update_instructions_file
                
                result = update_instructions_file(
                    section="Team Structure",
                    content="Engineering team has 5 members.",
                    action="append",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                assert "Successfully updated" in result
                
                context_path = temp_knowledge_dir / "context.md"
                assert context_path.exists()
                
                with open(context_path) as f:
                    content = f.read()
                
                assert "## Team Structure" in content
                assert "Engineering team has 5 members." in content
    
    def test_append_to_existing_section(self, mock_config, temp_knowledge_dir):
        """Test appending to an existing section."""
        # Create initial file
        context_path = temp_knowledge_dir / "context.md"
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text("# Instructions\n\nLast Updated: 2024-01-01\n\n## Team Structure\n\nExisting content.\n")
        
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import update_instructions_file
                
                result = update_instructions_file(
                    section="Team Structure",
                    content="New content appended.",
                    action="append",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                with open(context_path) as f:
                    content = f.read()
                
                assert "Existing content." in content
                assert "New content appended." in content
    
    def test_replace_section(self, mock_config, temp_knowledge_dir):
        """Test replacing a section's content."""
        # Create initial file
        context_path = temp_knowledge_dir / "context.md"
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text("# Instructions\n\nLast Updated: 2024-01-01\n\n## Team Structure\n\nOld content to replace.\n")
        
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import update_instructions_file
                
                result = update_instructions_file(
                    section="Team Structure",
                    content="Completely new content.",
                    action="replace",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                with open(context_path) as f:
                    content = f.read()
                
                assert "Old content to replace." not in content
                assert "Completely new content." in content


class TestCreateNote:
    """Tests for create_note tool."""
    
    def test_create_note_with_frontmatter(self, mock_config, temp_knowledge_dir):
        """Test creating a note with proper frontmatter."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import create_note
                
                result = create_note(
                    title="Test Note",
                    content="# Test Content\n\nThis is a test note.",
                    topic="default",
                    domain="engineering",
                    category="documentation",
                    tags="test, demo",
                    summary="A test note for testing",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                assert "Successfully created note" in result
                
                # Find the created note
                notes_dir = temp_knowledge_dir / "notes"
                note_files = list(notes_dir.glob("*.md"))
                assert len(note_files) == 1
                
                with open(note_files[0]) as f:
                    content = f.read()
                
                # Verify frontmatter
                assert "title: Test Note" in content
                assert "domain: engineering" in content
                assert "category: documentation" in content
                assert "# Test Content" in content
    
    def test_create_note_updates_index(self, mock_config, temp_knowledge_dir):
        """Test that creating a note updates the index."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import create_note
                
                create_note(
                    title="Indexed Note",
                    content="Content here",
                    topic="default",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                index_path = temp_knowledge_dir / "notes" / "_index.yaml"
                assert index_path.exists()
                
                with open(index_path) as f:
                    data = yaml.safe_load(f)
                
                assert len(data["notes"]) == 1
                assert data["notes"][0]["title"] == "Indexed Note"
    
    def test_create_note_below_threshold(self, mock_config, temp_knowledge_dir):
        """Test that notes below threshold require review."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import create_note
                
                result = create_note(
                    title="Low Confidence Note",
                    content="Content here",
                    topic="default",
                    confidence=0.5,  # Below threshold
                    relevance=0.8,
                )
                
                assert "REVIEW_REQUIRED" in result
    
    def test_fallback_to_default_topic(self, mock_config, temp_knowledge_dir):
        """Test that unknown topics fall back to default."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import create_note
                
                result = create_note(
                    title="Unknown Topic Note",
                    content="Content here",
                    topic="nonexistent",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                # Should succeed using default topic
                assert "Successfully created note" in result


class TestGetKnowledgeStatus:
    """Tests for get_knowledge_status tool."""
    
    def test_status_with_empty_stores(self, mock_config, temp_knowledge_dir):
        """Test status when no knowledge has been stored."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import get_knowledge_status
                
                result = get_knowledge_status()
                
                assert "Not created yet" in result or "No notes yet" in result
    
    def test_status_with_populated_stores(self, mock_config, temp_knowledge_dir):
        """Test status after adding content."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion._get_project_root", return_value=temp_knowledge_dir):
                from app.agents.tools.knowledge_ingestion import (
                    add_url_to_index,
                    create_note,
                    get_knowledge_status,
                )
                
                # Add some content
                add_url_to_index(
                    url="https://example.com",
                    title="Test",
                    domain="test",
                    context="test",
                    summary="test",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                create_note(
                    title="Test Note",
                    content="Test content",
                    confidence=0.9,
                    relevance=0.8,
                )
                
                result = get_knowledge_status()
                
                assert "1 URLs indexed" in result
                assert "1 notes" in result


class TestKnowledgeIngestionAgent:
    """Tests for KnowledgeIngestionAgent class."""
    
    def test_agent_initialization(self, mock_config):
        """Test agent initializes correctly."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion.OllamaChatClient") as mock_client:
                mock_agent = MagicMock()
                mock_client.return_value.as_agent.return_value = mock_agent
                
                from app.agents.tools.knowledge_ingestion import KnowledgeIngestionAgent
                
                agent = KnowledgeIngestionAgent()
                
                # Verify agent was created with correct parameters
                mock_client.return_value.as_agent.assert_called_once()
                call_kwargs = mock_client.return_value.as_agent.call_args[1]
                
                assert call_kwargs["name"] == "KnowledgeIngestion"
                assert len(call_kwargs["tools"]) == 4  # 4 tools registered
    
    def test_as_tool(self, mock_config):
        """Test agent can be converted to tool."""
        with patch("app.agents.tools.knowledge_ingestion.get_config", return_value=mock_config):
            with patch("app.agents.tools.knowledge_ingestion.OllamaChatClient") as mock_client:
                mock_agent = MagicMock()
                mock_client.return_value.as_agent.return_value = mock_agent
                
                from app.agents.tools.knowledge_ingestion import KnowledgeIngestionAgent
                
                agent = KnowledgeIngestionAgent()
                tool = agent.as_tool()
                
                mock_agent.as_tool.assert_called_once()
