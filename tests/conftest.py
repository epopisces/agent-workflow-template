# Copyright (c) 2024. All rights reserved.
"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import AppConfig, OllamaConfig, ModelsConfig, AgentsConfig, AgentConfig, ScraperConfig, LoggingConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return AppConfig(
        models=ModelsConfig(
            ollama=OllamaConfig(
                host="http://localhost:11434",
                model_id="test-model"
            )
        ),
        agents=AgentsConfig(
            coordinator=AgentConfig(
                name="TestCoordinator",
                description="Test coordinator"
            ),
            url_scraper=AgentConfig(
                name="TestScraper",
                description="Test scraper"
            )
        ),
        scraper=ScraperConfig(
            timeout=10,
            user_agent="TestAgent/1.0",
            max_content_length=1000
        ),
        logging=LoggingConfig(
            level="WARNING",  # Suppress logs during tests
            file=None
        )
    )


@pytest.fixture
def mock_get_config(mock_config):
    """Patch get_config to return mock configuration."""
    with patch("app.config.get_config", return_value=mock_config):
        yield mock_config


@pytest.fixture
def mock_html_response():
    """Sample HTML response for testing URL scraper."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page - DevOps Guide</title>
    </head>
    <body>
        <nav>Navigation menu here</nav>
        <main>
            <h1>Kubernetes Best Practices</h1>
            <p>This is a guide about Kubernetes deployment strategies.</p>
            <h2>Key Points</h2>
            <ul>
                <li>Use namespaces for isolation</li>
                <li>Implement resource limits</li>
                <li>Configure health checks</li>
            </ul>
            <p>These practices help ensure reliable deployments.</p>
        </main>
        <footer>Footer content</footer>
    </body>
    </html>
    """


@pytest.fixture
def mock_chat_response():
    """Create a mock chat response."""
    response = MagicMock()
    response.text = "This is a test response from the agent."
    return response


@pytest.fixture
def mock_chat_client(mock_chat_response):
    """Create a mock OllamaChatClient."""
    client = MagicMock()
    agent = MagicMock()
    
    # Mock run method
    agent.run = AsyncMock(return_value=mock_chat_response)
    
    # Mock run_stream method
    async def mock_stream(*args, **kwargs):
        chunk = MagicMock()
        chunk.text = "Test streaming response"
        yield chunk
    
    agent.run_stream = mock_stream
    agent.get_new_thread = MagicMock(return_value=MagicMock())
    agent.as_tool = MagicMock(return_value=MagicMock())
    
    client.create_agent = MagicMock(return_value=agent)
    
    return client
