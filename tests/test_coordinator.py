# Copyright (c) 2024. All rights reserved.
"""Tests for Coordinator Agent."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.agents.coordinator import CoordinatorAgent


class TestCoordinatorAgent:
    """Tests for CoordinatorAgent class."""
    
    def test_init_with_defaults(self, mock_get_config):
        """Test coordinator initialization with default settings."""
        with patch("app.agents.coordinator.OllamaChatClient") as mock_client_class:
            mock_client = MagicMock()
            mock_agent = MagicMock()
            mock_agent.get_new_thread = MagicMock(return_value=MagicMock())
            mock_client.as_agent = MagicMock(return_value=mock_agent)
            mock_client_class.return_value = mock_client
            
            with patch("app.agents.coordinator.URLScraperAgent") as mock_scraper_class:
                mock_scraper = MagicMock()
                mock_scraper.as_tool = MagicMock(return_value=MagicMock())
                mock_scraper_class.return_value = mock_scraper
                
                coordinator = CoordinatorAgent()
                
                # Should create 2 clients (one for coordinator, one for scraper)
                assert mock_client_class.call_count == 2
                mock_client.as_agent.assert_called()
    
    def test_init_with_custom_client(self, mock_get_config, mock_chat_client):
        """Test coordinator with provided client."""
        mock_scraper = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=MagicMock())
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        mock_chat_client.as_agent.assert_called_once()
        # Verify the scraper tool was added
        call_kwargs = mock_chat_client.as_agent.call_args[1]
        assert "tools" in call_kwargs
    
    def test_new_thread(self, mock_get_config, mock_chat_client):
        """Test creating new conversation thread."""
        mock_scraper = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=MagicMock())
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        # Get initial thread
        initial_call_count = mock_chat_client.as_agent.return_value.get_new_thread.call_count
        
        # Create new thread
        coordinator.new_thread()
        
        assert mock_chat_client.as_agent.return_value.get_new_thread.call_count == initial_call_count + 1
    
    @pytest.mark.asyncio
    async def test_run(self, mock_get_config, mock_chat_client):
        """Test running coordinator with a query."""
        mock_scraper = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=MagicMock())
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        result = await coordinator.run("What's at https://example.com?")
        
        assert result == "This is a test response from the agent."
        mock_chat_client.as_agent.return_value.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_stream(self, mock_get_config, mock_chat_client):
        """Test streaming output from coordinator."""
        mock_scraper = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=MagicMock())
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        chunks = []
        async for chunk in coordinator.run_stream("Analyze https://example.com"):
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert chunks[0] == "Test streaming response"
    
    def test_agent_property(self, mock_get_config, mock_chat_client):
        """Test accessing underlying agent."""
        mock_scraper = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=MagicMock())
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        agent = coordinator.agent
        
        assert agent is mock_chat_client.as_agent.return_value


class TestCoordinatorInstructions:
    """Tests for coordinator agent configuration."""
    
    def test_coordinator_has_scraper_tool(self, mock_get_config, mock_chat_client):
        """Test that coordinator is configured with URL scraper tool."""
        mock_scraper = MagicMock()
        mock_tool = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=mock_tool)
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        # Verify as_tool was called
        mock_scraper.as_tool.assert_called_once()
        
        # Verify tool was passed to as_agent
        call_kwargs = mock_chat_client.as_agent.call_args[1]
        assert mock_tool in call_kwargs["tools"]
    
    def test_coordinator_instructions_mention_url(self, mock_get_config, mock_chat_client):
        """Test that coordinator instructions include URL handling guidance."""
        mock_scraper = MagicMock()
        mock_scraper.as_tool = MagicMock(return_value=MagicMock())
        
        coordinator = CoordinatorAgent(
            chat_client=mock_chat_client,
            url_scraper=mock_scraper
        )
        
        call_kwargs = mock_chat_client.as_agent.call_args[1]
        instructions = call_kwargs["instructions"]
        
        assert "url_scraper" in instructions.lower() or "url" in instructions.lower()
