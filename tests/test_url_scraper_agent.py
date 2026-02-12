"""Tests for URL Scraper Agent."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.agents.tools.url_scraper import URLScraperAgent


class TestURLScraperAgent:
    """Tests for URLScraperAgent class."""
    
    def test_init_with_default_client(self, mock_get_config):
        """Test agent initialization with default client."""
        with patch("app.agents.tools.url_scraper.OllamaChatClient") as mock_client_class:
            mock_client = MagicMock()
            mock_agent = MagicMock()
            mock_client.as_agent = MagicMock(return_value=mock_agent)
            mock_client_class.return_value = mock_client
            
            agent = URLScraperAgent()
            
            mock_client_class.assert_called_once_with(
                host="http://localhost:11434",
                model_id="test-model"
            )
            mock_client.as_agent.assert_called_once()
    
    def test_init_with_custom_client(self, mock_get_config, mock_chat_client):
        """Test agent initialization with provided client."""
        agent = URLScraperAgent(chat_client=mock_chat_client)
        
        mock_chat_client.as_agent.assert_called_once()
        # Verify the agent was configured with the fetch_url tool
        call_kwargs = mock_chat_client.as_agent.call_args[1]
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1
    
    def test_as_tool(self, mock_get_config, mock_chat_client):
        """Test converting agent to tool."""
        agent = URLScraperAgent(chat_client=mock_chat_client)
        
        tool = agent.as_tool(
            name="custom_scraper",
            description="Custom description"
        )
        
        mock_chat_client.as_agent.return_value.as_tool.assert_called_once_with(
            name="custom_scraper",
            description="Custom description",
            arg_name="request",
            arg_description="A request describing what URL to fetch and optionally what to look for in the content."
        )
    
    @pytest.mark.asyncio
    async def test_run(self, mock_get_config, mock_chat_client):
        """Test running the agent."""
        agent = URLScraperAgent(chat_client=mock_chat_client)
        
        result = await agent.run("Fetch https://example.com")
        
        assert result == "This is a test response from the agent."
    
    @pytest.mark.asyncio
    async def test_run_stream(self, mock_get_config, mock_chat_client):
        """Test streaming output from agent."""
        agent = URLScraperAgent(chat_client=mock_chat_client)
        
        chunks = []
        async for chunk in agent.run_stream("Fetch https://example.com"):
            chunks.append(chunk)
        
        assert len(chunks) == 1
        assert chunks[0] == "Test streaming response"
    
    def test_agent_property(self, mock_get_config, mock_chat_client):
        """Test accessing underlying agent."""
        scraper = URLScraperAgent(chat_client=mock_chat_client)
        
        agent = scraper.agent
        
        assert agent is mock_chat_client.as_agent.return_value
