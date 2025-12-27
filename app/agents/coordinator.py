# Copyright (c) 2024. All rights reserved.
"""Coordinator Agent.

The central orchestrator that communicates with users and routes tasks
to specialized tool agents.
"""

import logging

from agent_framework import ChatAgent
from agent_framework.ollama import OllamaChatClient

from app.config import get_config
from app.agents.tools.url_scraper import URLScraperAgent
from app.agents.tools.knowledge_ingestion import KnowledgeIngestionAgent
from app.agents.tools.org_context import OrgContextAgent

# Logger for coordinator agent
logger = logging.getLogger("workflow.coordinator")


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
        
        # Create the coordinator agent with tool agents as tools
        self._agent = chat_client.create_agent(
            name=config.agents.coordinator.name,
            description=config.agents.coordinator.description,
            instructions="""You are a helpful assistant that helps the end user process information, analyze web content, and manage organizational knowledge.

Your capabilities:
1. **URL Analysis**: When users provide URLs, use the url_scraper tool to fetch and analyze the content. This is useful for:
   - Evaluating if a webpage contains useful information for a team
   - Summarizing technical documentation
   - Extracting key points from articles or blog posts

2. **Knowledge Management**: When users share information about their organization, projects, processes, or want to save useful content, use the knowledge_ingestion tool. This is useful for:
   - Storing organizational context (team structure, processes, technologies used)
   - Saving URLs with metadata for future reference
   - Creating notes from meetings, research, or documentation
   - Building up organizational knowledge over time

3. **Organizational Context**: When users ask questions that might benefit from organizational context, use the org_context tool. This retrieves:
   - High-level org context from the instructions file
   - Detailed documentation from notes
   - Information from indexed URLs (as last resort)

How to handle requests:
- If a user provides a URL or asks about web content, use the url_scraper tool
- If a user shares organizational information, context, or wants to save/remember something, use the knowledge_ingestion tool
- If a user asks questions that might need organizational context (about processes, team, tools, etc.), use the org_context tool FIRST
- After getting results from tools, synthesize the information into a helpful response
- Be concise but thorough in your responses
- If you encounter errors, explain them clearly and suggest alternatives

When to use org_context:
- User asks about organizational processes, team structure, or workflows
- User asks questions that might be answered by previously stored knowledge
- User asks about tools, technologies, or practices used in the organization
- User references something that might be documented

When to use knowledge_ingestion:
- User shares information about their organization, team, or environment
- User describes their tech stack, processes, or workflows
- User wants to save a URL or web content for future reference
- User provides context they want the system to remember
- User shares meeting notes, decisions, or documentation

**CRITICAL for knowledge_ingestion**:
When calling knowledge_ingestion, you MUST include guidance in your request:
- For user context (their role, skills, tools, workflow, preferences) → tell it to "update the instructions file"
- For detailed documentation, meeting notes, research → tell it to "create a note"

Example: If user says "I'm a DevOps engineer who uses Python and Terraform", call knowledge_ingestion with:
"The user shared their role and tools. UPDATE THE INSTRUCTIONS FILE with: DevOps Engineer, uses Python and Terraform..."

Always be helpful and provide actionable insights. When storing knowledge, confirm what was saved.""",
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
