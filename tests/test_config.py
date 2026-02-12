"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from app.config import load_config, get_config, AppConfig


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_load_config_defaults(self):
        """Test loading config with no file and no env vars."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.config.load_dotenv"):
                config = load_config(config_path="/nonexistent/path.yaml")
        
        assert config.models.ollama.host == "http://localhost:11434"
        assert config.models.ollama.model_id == "qwen3:1.7b"
        assert config.scraper.timeout == 30
    
    def test_load_config_from_yaml(self):
        """Test loading config from YAML file."""
        yaml_content = {
            "models": {
                "ollama": {
                    "host": "http://custom:11434",
                    "model_id": "custom-model"
                }
            },
            "scraper": {
                "timeout": 60
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name
        
        try:
            with patch.dict(os.environ, {}, clear=True):
                with patch("app.config.load_dotenv"):
                    config = load_config(config_path=temp_path)
            
            assert config.models.ollama.host == "http://custom:11434"
            assert config.models.ollama.model_id == "custom-model"
            assert config.scraper.timeout == 60
        finally:
            os.unlink(temp_path)
    
    def test_load_config_env_override(self):
        """Test that environment variables override YAML config."""
        yaml_content = {
            "models": {
                "ollama": {
                    "host": "http://yaml:11434",
                    "model_id": "yaml-model"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_path = f.name
        
        try:
            env_vars = {
                "OLLAMA_HOST": "http://env:11434",
                "OLLAMA_MODEL_ID": "env-model"
            }
            with patch.dict(os.environ, env_vars, clear=True):
                with patch("app.config.load_dotenv"):
                    config = load_config(config_path=temp_path)
            
            # Env vars should take precedence
            assert config.models.ollama.host == "http://env:11434"
            assert config.models.ollama.model_id == "env-model"
        finally:
            os.unlink(temp_path)


class TestAppConfig:
    """Tests for AppConfig model."""
    
    def test_config_validation(self):
        """Test config model validation."""
        config = AppConfig()
        
        assert isinstance(config.models.ollama.host, str)
        assert isinstance(config.models.ollama.model_id, str)
        assert isinstance(config.scraper.timeout, int)
    
    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        from app.config import OllamaConfig, ModelsConfig, ScraperConfig
        
        config = AppConfig(
            models=ModelsConfig(
                ollama=OllamaConfig(
                    host="http://test:1234",
                    model_id="test-model"
                )
            ),
            scraper=ScraperConfig(
                timeout=120,
                max_content_length=100000
            )
        )
        
        assert config.models.ollama.host == "http://test:1234"
        assert config.scraper.timeout == 120
        assert config.scraper.max_content_length == 100000
