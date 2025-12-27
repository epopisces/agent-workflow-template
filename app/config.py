# Copyright (c) 2024. All rights reserved.
"""Configuration management for Multi-Agent Workflow."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Logger for this module
logger = logging.getLogger("workflow.config")


class OllamaConfig(BaseModel):
    """Ollama model configuration."""
    host: str = Field(default="http://localhost:11434")
    model_id: str = Field(default="qwen2.5:1.5b")


class ModelsConfig(BaseModel):
    """Models configuration."""
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)


class AgentConfig(BaseModel):
    """Individual agent configuration."""
    name: str
    description: str


class AgentsConfig(BaseModel):
    """Agents configuration."""
    coordinator: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="Coordinator",
            description="Central agent that orchestrates tool agents"
        )
    )
    url_scraper: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="URLScraper",
            description="Fetches and parses web content from URLs"
        )
    )
    knowledge_ingestion: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="KnowledgeIngestion",
            description="Processes and stores content into organizational knowledge stores"
        )
    )
    org_context: AgentConfig = Field(
        default_factory=lambda: AgentConfig(
            name="OrgContext",
            description="Retrieves organizational context from knowledge stores"
        )
    )


class ScraperConfig(BaseModel):
    """Web scraper configuration."""
    timeout: int = Field(default=30)
    user_agent: str = Field(default="MultiAgentWorkflow/0.1")
    max_content_length: int = Field(default=50000)


class NoteTopicConfig(BaseModel):
    """Configuration for a single notes topic."""
    directory: str = Field(description="Directory path for notes in this topic")
    template: str = Field(description="Path to the template file for this topic")
    description: str = Field(default="", description="Description of this topic")
    frontmatter_defaults: dict[str, str | int | bool] = Field(
        default_factory=dict,
        description="Default frontmatter values for notes in this topic"
    )


class KnowledgeConfig(BaseModel):
    """Knowledge ingestion configuration."""
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which human review is required"
    )
    relevance_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Relevance threshold below which human review is required"
    )
    instructions_file: str = Field(
        default="knowledge/instructions.md",
        description="Path to the instructions file with org context"
    )
    url_index_file: str = Field(
        default="knowledge/url_index.yaml",
        description="Path to the URL index file"
    )
    notes_topics: dict[str, NoteTopicConfig] = Field(
        default_factory=lambda: {
            "default": NoteTopicConfig(
                directory="notes",
                template="config/templates/note_template.md",
                description="General notes and documentation",
                frontmatter_defaults={
                    "category": "general",
                    "priority": "medium",
                    "reviewed": False
                }
            )
        },
        description="Notes configuration by topic"
    )


class MetricsConfig(BaseModel):
    """Metrics collection configuration."""
    enabled: bool = Field(default=True, description="Enable/disable metrics collection")
    directory: str = Field(default="metrics", description="Directory to store metrics files")


class ProgressConfig(BaseModel):
    """Progress indicator configuration."""
    enabled: bool = Field(default=True, description="Enable progress indicators")
    style: str = Field(default="dots", description="Style: spinner, dots, elapsed, message")
    update_interval: float = Field(default=2.0, description="Seconds between updates")
    show_elapsed: bool = Field(default=True, description="Show elapsed time")
    streaming_idle_threshold: float = Field(
        default=5.0,
        description="Seconds of idle before showing 'still working' in streaming mode"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    file: str | None = Field(default=None)


class AppConfig(BaseModel):
    """Application configuration."""
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    progress: ProgressConfig = Field(default_factory=ProgressConfig)


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config.yaml. Defaults to config/config.yaml.
        
    Returns:
        AppConfig instance with merged configuration.
    """
    # Load environment variables from .env file
    load_dotenv()
    logger.debug("Loaded environment variables from .env file")
    
    # Determine config path
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    else:
        config_path = Path(config_path)
    
    logger.debug(f"Loading configuration from: {config_path}")
    
    # Load YAML config if exists
    config_data: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded YAML config with keys: {list(config_data.keys())}")
    else:
        logger.warning(f"Config file not found: {config_path}, using defaults")
    
    # Override with environment variables
    if "models" not in config_data:
        config_data["models"] = {}
    if "ollama" not in config_data["models"]:
        config_data["models"]["ollama"] = {}
    
    # Environment variables take precedence
    if os.getenv("OLLAMA_HOST"):
        config_data["models"]["ollama"]["host"] = os.getenv("OLLAMA_HOST")
        logger.debug(f"Using OLLAMA_HOST from environment: {os.getenv('OLLAMA_HOST')}")
    if os.getenv("OLLAMA_MODEL_ID"):
        config_data["models"]["ollama"]["model_id"] = os.getenv("OLLAMA_MODEL_ID")
        logger.debug(f"Using OLLAMA_MODEL_ID from environment: {os.getenv('OLLAMA_MODEL_ID')}")
    
    config = AppConfig(**config_data)
    logger.info(f"Configuration loaded: model={config.models.ollama.model_id}, host={config.models.ollama.host}")
    return config


# Global config instance (lazy loaded)
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance.
    
    Returns:
        AppConfig instance.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config
