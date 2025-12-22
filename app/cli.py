# Copyright (c) 2024. All rights reserved.
"""Command Line Interface for Multi-Agent Workflow.

Simple CLI chat interface for interacting with the Coordinator agent.
"""

import asyncio
import logging
import sys

from app.agents.coordinator import CoordinatorAgent
from app.config import get_config
from app.logging_config import setup_logging, LOGGER_ROOT

# CLI logger
logger = logging.getLogger("workflow.cli")


def print_welcome():
    """Print welcome message and instructions."""
    print("\n" + "=" * 60)
    print("  Multi-Agent Workflow Assistant (MVP)")
    print("=" * 60)
    print("\nCommands:")
    print("  /new     - Start a new conversation")
    print("  /config  - Show current configuration")
    print("  /debug   - Toggle DEBUG logging (see agent handoffs)")
    print("  /quit    - Exit the application")
    print("  /help    - Show this help message")
    print("\nTip: Paste a URL to analyze its content!")
    print("-" * 60 + "\n")


def print_config():
    """Print current configuration."""
    config = get_config()
    root_logger = logging.getLogger(LOGGER_ROOT)
    print("\n--- Configuration ---")
    print(f"Ollama Host: {config.models.ollama.host}")
    print(f"Model: {config.models.ollama.model_id}")
    print(f"Scraper Timeout: {config.scraper.timeout}s")
    print(f"Log Level: {logging.getLevelName(root_logger.level)}")
    print("-" * 20 + "\n")


def toggle_debug():
    """Toggle between DEBUG and INFO logging levels."""
    root_logger = logging.getLogger(LOGGER_ROOT)
    if root_logger.level == logging.DEBUG:
        root_logger.setLevel(logging.INFO)
        for handler in root_logger.handlers:
            handler.setLevel(logging.INFO)
        print("\n--- Logging set to INFO ---\n")
        logger.info("Logging level changed to INFO")
    else:
        root_logger.setLevel(logging.DEBUG)
        for handler in root_logger.handlers:
            handler.setLevel(logging.DEBUG)
        print("\n--- Logging set to DEBUG (agent handoffs visible) ---\n")
        logger.info("Logging level changed to DEBUG")


async def chat_loop(coordinator: CoordinatorAgent):
    """Main chat loop.
    
    Args:
        coordinator: The coordinator agent instance.
    """
    print_welcome()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                command = user_input.lower()
                
                if command == "/quit" or command == "/exit":
                    logger.info("User requested exit")
                    print("\nGoodbye!")
                    break
                elif command == "/new":
                    coordinator.new_thread()
                    print("\n--- New conversation started ---\n")
                    continue
                elif command == "/config":
                    print_config()
                    continue
                elif command == "/debug":
                    toggle_debug()
                    continue
                elif command == "/help":
                    print_welcome()
                    continue
                else:
                    print(f"Unknown command: {user_input}")
                    print("Type /help for available commands.\n")
                    continue
            
            # Process user message with streaming output
            print("\nAssistant: ", end="", flush=True)
            
            try:
                async for chunk in coordinator.run_stream(user_input):
                    print(chunk, end="", flush=True)
                print("\n")
            except Exception as e:
                logger.error(f"Error during agent execution: {e}", exc_info=True)
                print(f"\n\nError: {e}")
                print("Make sure Ollama is running and the model is available.")
                print(f"Try: ollama pull {get_config().models.ollama.model_id}\n")
                
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type /quit to exit.\n")
        except EOFError:
            logger.info("EOF received, exiting")
            print("\nGoodbye!")
            break


async def async_main():
    """Async main entry point."""
    config = get_config()
    
    # Setup logging from config
    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
    )
    logger.info("Multi-Agent Workflow CLI starting")
    
    print(f"\nConnecting to Ollama at {config.models.ollama.host}...")
    print(f"Using model: {config.models.ollama.model_id}")
    print(f"Logging level: {config.logging.level} (use /debug to toggle)")
    
    try:
        coordinator = CoordinatorAgent()
        await chat_loop(coordinator)
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        print(f"\nError initializing agent: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is running: ollama serve")
        print(f"2. Pull the model: ollama pull {config.models.ollama.model_id}")
        print("3. Check your .env or config/config.yaml settings")
        sys.exit(1)
    
    logger.info("CLI shutdown complete")


def main():
    """Main entry point for CLI."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
