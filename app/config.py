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


class ScraperConfig(BaseModel):
    """Web scraper configuration."""
    timeout: int = Field(default=30)
    user_agent: str = Field(default="MultiAgentWorkflow/0.1")
    max_content_length: int = Field(default=50000)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    file: str | None = Field(default=None)


class AppConfig(BaseModel):
    """Application configuration."""
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


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
