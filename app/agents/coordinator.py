# Copyright (c) 2024. All rights reserved.
"""Coordinator Agent.

The central orchestrator that communicates with users and routes tasks
to specialized tool agents.
"""

import logging

from agent_framework import ChatAgent
from agent_framework.ollama import OllamaChatClient

from app.config import get_config, load_instructions
from app.agents.tools.url_scraper import URLScraperAgent
from app.agents.tools.knowledge_ingestion import KnowledgeIngestionAgent
from app.agents.tools.org_context import OrgContextAgent

# Logger for coordinator agent
logger = logging.getLogger("workflow.coordinator")

# Fallback instructions if file not found
_FALLBACK_INSTRUCTIONS = """You are a helpful assistant that helps the end user process information, analyze web content, and manage organizational knowledge.

Use the available tools proactively:
- url_scraper: Fetch and analyze web content
- knowledge_ingestion: Store information in the knowledge base
- org_context: Retrieve organizational context from stored knowledge

Be helpful and actionable in your responses."""


class CoordinatorAgent:
    """Coordinator Agent that orchestrates tool agents.
    
    This is the main agent that users interact with. It analyzes user requests,
    determines which tool agents to invoke, and synthesizes responses.
    """
    
    def __init__(
        self,
        chat_client: OllamaChatClient | None = None,
        url_scraper: URLScraperAgent | None = None,
        knowledge_ingestion: KnowledgeIngestionAgent | None = None,
        org_context: OrgContextAgent | None = None,
    ):
        """Initialize the Coordinator Agent.
        
        Args:
            chat_client: Optional OllamaChatClient for the coordinator.
            url_scraper: Optional URLScraperAgent. Created if not provided.
            knowledge_ingestion: Optional KnowledgeIngestionAgent. Created if not provided.
            org_context: Optional OrgContextAgent. Created if not provided.
        """
        config = get_config()
        logger.info("Initializing Coordinator Agent")
        
        # Create chat client if not provided
        if chat_client is None:
            logger.debug(f"Creating OllamaChatClient for coordinator: {config.models.ollama.model_id}")
            chat_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
        
        # Create URL scraper agent if not provided
        if url_scraper is None:
            logger.debug("Creating URLScraperAgent as tool")
            # Create with its own client to avoid sharing state
            scraper_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
            url_scraper = URLScraperAgent(chat_client=scraper_client)
        
        self._url_scraper = url_scraper
        logger.debug("URLScraperAgent registered as tool")
        
        # Create Knowledge Ingestion agent if not provided
        if knowledge_ingestion is None:
            logger.debug("Creating KnowledgeIngestionAgent as tool")
            knowledge_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
            knowledge_ingestion = KnowledgeIngestionAgent(chat_client=knowledge_client)
        
        self._knowledge_ingestion = knowledge_ingestion
        logger.debug("KnowledgeIngestionAgent registered as tool")
        
        # Create Org Context agent if not provided
        if org_context is None:
            logger.debug("Creating OrgContextAgent as tool")
            org_context_client = OllamaChatClient(
                host=config.models.ollama.host,
                model_id=config.models.ollama.model_id,
            )
            # Pass URL scraper tool so org_context can fetch indexed URLs as last resort
            org_context = OrgContextAgent(
                chat_client=org_context_client,
                url_scraper_tool=url_scraper.as_tool(),
            )
        
        self._org_context = org_context
        logger.debug("OrgContextAgent registered as tool")
        
        # Load instructions from file or use fallback
        instructions = load_instructions(config.agents.coordinator.instructions_file)
        if instructions is None:
            logger.warning("Using fallback instructions for coordinator")
            instructions = _FALLBACK_INSTRUCTIONS
        
        # Create the coordinator agent with tool agents as tools
        self._agent = chat_client.create_agent(
            name=config.agents.coordinator.name,
            description=config.agents.coordinator.description,
            instructions=instructions,
            tools=[url_scraper.as_tool(), knowledge_ingestion.as_tool(), org_context.as_tool()],
        )
        
        # Thread for conversation context
        self._thread = self._agent.get_new_thread()
        logger.info("Coordinator Agent initialized successfully")
    
    @property
    def agent(self) -> ChatAgent:
        """Get the underlying ChatAgent."""
        return self._agent
    
    def new_thread(self):
        """Start a new conversation thread."""
        self._thread = self._agent.get_new_thread()
        logger.info("Started new conversation thread")
    
    async def run(self, query: str) -> str:
        """Run the coordinator with a user query.
        
        Args:
            query: The user's question or request.
            
        Returns:
            The agent's response.
        """
        logger.info(f"Processing query: {query[:100]}{'...' if len(query) > 100 else ''}")
        logger.debug("Invoking coordinator agent")
        result = await self._agent.run(query, thread=self._thread)
        logger.debug(f"Coordinator response received: {len(result.text)} chars")
        return result.text
    
    async def run_stream(self, query: str):
        """Run the coordinator with streaming output.
        
        Args:
            query: The user's question or request.
            
        Yields:
            Text chunks from the agent's response.
        """
        logger.info(f"Processing query (streaming): {query[:100]}{'...' if len(query) > 100 else ''}")
        logger.debug("Invoking coordinator agent with streaming")
        chunk_count = 0
        try:
            async for chunk in self._agent.run_stream(query, thread=self._thread):
                if chunk.text:
                    chunk_count += 1
                    yield chunk.text
        finally:
            # Print newline before debug log to avoid appending to stream output
            print()
            logger.debug(f"Stream completed: {chunk_count} chunks")
