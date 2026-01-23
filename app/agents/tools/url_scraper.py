# Copyright (c) 2024. All rights reserved.
"""URL Scraper Agent Tool.

This agent fetches and parses web content from URLs. It is designed to be used
as an agent-as-tool by the Coordinator agent.
"""

import asyncio
import logging
from typing import Annotated
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from agent_framework import ChatAgent
from agent_framework.ollama import OllamaChatClient
from pydantic import Field

from app.config import get_config, load_instructions
from app.metrics import track_tool_call

# Logger for URL scraper
logger = logging.getLogger("workflow.url_scraper")

# Fallback instructions if file not found
_FALLBACK_INSTRUCTIONS = """You are a URL content extraction specialist.
Use the fetch_url tool to retrieve content from URLs, then summarize the content.
Always use the fetch_url tool when a URL is provided."""


@track_tool_call("url_scraper")
def fetch_url(
    url: Annotated[str, Field(description="The URL to fetch and parse content from.")]
) -> str:
    """Fetch and parse web content from a URL.
    
    This tool fetches the HTML content from a URL and extracts the main text content,
    removing scripts, styles, and navigation elements.
    
    Args:
        url: The URL to fetch content from.
        
    Returns:
        The extracted text content from the webpage, or an error message.
    """
    logger.info(f"[TOOL CALL] fetch_url invoked with URL: {url}")
    config = get_config()
    
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning(f"Invalid URL format: {url}")
            return f"Error: Invalid URL format: {url}"
    except Exception as e:
        logger.error(f"URL parse error: {e}")
        return f"Error: Could not parse URL: {e}"
    
    logger.debug(f"Fetching URL: {url}")
    
    # Fetch content synchronously (tool functions should be sync)
    try:
        with httpx.Client(
            timeout=config.scraper.timeout,
            follow_redirects=True,
            headers={"User-Agent": config.scraper.user_agent}
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            html_content = response.text
        logger.debug(f"Fetched {len(html_content)} bytes from {url}")
    except httpx.TimeoutException:
        logger.error(f"Request timeout after {config.scraper.timeout}s: {url}")
        return f"Error: Request timed out after {config.scraper.timeout} seconds"
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code}: {url}")
        return f"Error: HTTP {e.response.status_code} - {e.response.reason_phrase}"
    except httpx.RequestError as e:
        logger.error(f"Request error for {url}: {e}")
        return f"Error: Could not fetch URL: {e}"
    
    # Parse HTML and extract text
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            element.decompose()
        
        # Try to find main content area
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find(class_=["content", "main-content", "post-content"]) or
            soup.find("body")
        )
        
        if main_content:
            # Get text with some formatting preserved
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
        
        # Clean up multiple newlines and whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        # Truncate if too long
        if len(text) > config.scraper.max_content_length:
            logger.debug(f"Content truncated from {len(text)} to {config.scraper.max_content_length} chars")
            text = text[:config.scraper.max_content_length] + "\n\n[Content truncated...]"
        
        # Get title
        title = soup.title.string if soup.title else "No title"
        
        logger.info(f"[TOOL RESULT] fetch_url completed: '{title}' ({len(text)} chars)")
        return f"URL: {url}\nTitle: {title}\n\nContent:\n{text}"
        
    except Exception as e:
        logger.error(f"HTML parse error for {url}: {e}")
        return f"Error: Could not parse HTML content: {e}"


class URLScraperAgent:
    """URL Scraper Agent that can be used as a tool by other agents.
    
    This agent specializes in fetching and summarizing web content.
    It uses the `fetch_url` tool to retrieve content and then
    processes/summarizes it using an LLM.
    """
    
    def __init__(self, chat_client: OllamaChatClient | None = None):
        """Initialize the URL Scraper Agent.
        
        Args:
            chat_client: Optional OllamaChatClient. If not provided, 
                        creates one using config settings.
        """
        logger.info("Initializing URLScraperAgent")
        config = get_config()
        
        if chat_client is None:
            logger.debug(f"Creating OllamaChatClient for URLScraperAgent: {config.models.ollama.model_id}")
            chat_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
        
        # Load instructions from file or use fallback
        instructions = load_instructions(config.agents.url_scraper.instructions_file)
        if instructions is None:
            logger.warning("Using fallback instructions for url_scraper")
            instructions = _FALLBACK_INSTRUCTIONS
        
        self._agent = chat_client.as_agent(
            name=config.agents.url_scraper.name,
            description=config.agents.url_scraper.description,
            instructions=instructions,
            tools=[fetch_url],
        )
        logger.debug("URLScraperAgent initialized with fetch_url tool")
    
    @property
    def agent(self) -> ChatAgent:
        """Get the underlying ChatAgent."""
        return self._agent
    
    def as_tool(
        self,
        name: str = "url_scraper",
        description: str = "Fetch and analyze content from a URL. Use this tool when you need to retrieve and understand web page content.",
        arg_name: str = "request",
        arg_description: str = "A request describing what URL to fetch and optionally what to look for in the content."
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
        logger.debug(f"Converting URLScraperAgent to tool: {name}")
        return self._agent.as_tool(
            name=name,
            description=description,
            arg_name=arg_name,
            arg_description=arg_description,
        )
    
    async def run(self, query: str) -> str:
        """Run the URL scraper agent with a query.
        
        Args:
            query: The query/request for the agent.
            
        Returns:
            The agent's response.
        """
        logger.info(f"[AGENT HANDOFF] URLScraperAgent received request: {query[:80]}{'...' if len(query) > 80 else ''}")
        result = await self._agent.run(query)
        logger.info(f"[AGENT HANDOFF] URLScraperAgent completed: {len(result.text)} chars response")
        return result.text
    
    async def run_stream(self, query: str):
        """Run the URL scraper agent with streaming output.
        
        Args:
            query: The query/request for the agent.
            
        Yields:
            Text chunks from the agent's response.
        """
        logger.info(f"[AGENT HANDOFF] URLScraperAgent received request (streaming): {query[:80]}{'...' if len(query) > 80 else ''}")
        chunk_count = 0
        async for chunk in self._agent.run_stream(query):
            if chunk.text:
                chunk_count += 1
                yield chunk.text
        logger.info(f"[AGENT HANDOFF] URLScraperAgent stream completed: {chunk_count} chunks")
