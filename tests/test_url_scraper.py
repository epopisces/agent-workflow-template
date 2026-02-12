"""Tests for URL Scraper tool function."""

import pytest
from unittest.mock import patch, MagicMock

import httpx

from app.agents.tools.url_scraper import fetch_url


class TestFetchUrl:
    """Tests for the fetch_url tool function."""
    
    def test_fetch_url_invalid_url(self, mock_get_config):
        """Test handling of invalid URL format."""
        result = fetch_url("not-a-valid-url")
        assert "Error: Invalid URL format" in result
    
    def test_fetch_url_empty_url(self, mock_get_config):
        """Test handling of empty URL."""
        result = fetch_url("")
        assert "Error" in result
    
    def test_fetch_url_success(self, mock_get_config, mock_html_response):
        """Test successful URL fetch and parse."""
        mock_response = MagicMock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = fetch_url("https://example.com/test")
        
        assert "URL: https://example.com/test" in result
        assert "Title: Test Page - DevOps Guide" in result
        assert "Kubernetes Best Practices" in result
        # Nav and footer should be removed
        assert "Navigation menu" not in result
        assert "Footer content" not in result
    
    def test_fetch_url_timeout(self, mock_get_config):
        """Test handling of timeout errors."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client
            
            result = fetch_url("https://example.com/slow")
        
        assert "Error: Request timed out" in result
    
    def test_fetch_url_http_error(self, mock_get_config):
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            ))
            mock_client_class.return_value = mock_client
            
            result = fetch_url("https://example.com/notfound")
        
        assert "Error: HTTP 404" in result
    
    def test_fetch_url_content_truncation(self, mock_get_config):
        """Test that long content is truncated."""
        # Create content longer than max_content_length (1000 in mock_config)
        long_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Long Page</title></head>
        <body>
        <main>
        {"x" * 2000}
        </main>
        </body>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.text = long_content
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = fetch_url("https://example.com/long")
        
        assert "[Content truncated...]" in result
    
    def test_fetch_url_extracts_main_content(self, mock_get_config):
        """Test that main content area is preferred."""
        html_with_main = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body>
        <div>Sidebar content</div>
        <main>
            <p>This is the main content.</p>
        </main>
        <div>Other content</div>
        </body>
        </html>
        """
        
        mock_response = MagicMock()
        mock_response.text = html_with_main
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get = MagicMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = fetch_url("https://example.com/main")
        
        assert "main content" in result
