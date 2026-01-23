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
from app.metrics import configure_metrics, get_metrics_collector
from app.progress_tracker import (
    StreamingProgressTracker,
    ProgressConfig,
    ProgressStyle,
)

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
    print("  /metrics - Show current session metrics")
    print("  /loglevel <level> - Set logging level (e.g., /loglevel debug)")
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
    print(f"Metrics: {'enabled' if config.metrics.enabled else 'disabled'}")
    print(f"Progress Indicators: {'enabled' if config.progress.enabled else 'disabled'}")
    print("-" * 20 + "\n")


def set_log_level(level_name: str):
    """Set logging level dynamically."""
    root_logger = logging.getLogger(LOGGER_ROOT)
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        print(f"\nInvalid log level: {level_name}\n")
        return
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)
    print(f"\n--- Logging set to {logging.getLevelName(level)} ---\n")
    logger.info(f"Logging level changed to {logging.getLevelName(level)}")


def print_metrics():
    """Print current session metrics."""
    collector = get_metrics_collector()
    summary = collector.get_summary()
    print("\n--- Session Metrics ---")
    print(f"Total Operations: {summary['total_operations']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total Time: {summary['total_time_seconds']:.2f}s")
    print(f"Average Time: {summary['average_time_seconds']:.2f}s")
    print("-" * 22 + "\n")


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
                elif command.startswith("/loglevel "):
                    level_name = command.split(" ", 1)[-1].strip()
                    set_log_level(level_name)
                    continue
                elif command == "/help":
                    print_welcome()
                    continue
                elif command == "/metrics":
                    print_metrics()
                    continue
                else:
                    print(f"Unknown command: {user_input}")
                    print("Type /help for available commands.\n")
                    continue
            
            # Process user message with streaming output and progress tracking
            config = get_config()
            metrics_collector = get_metrics_collector()
            
            print("\nAssistant: ", end="", flush=True)
            
            # Create progress tracker for streaming
            progress_tracker = StreamingProgressTracker(
                idle_threshold=config.progress.streaming_idle_threshold,
                update_interval=config.progress.update_interval,
            ) if config.progress.enabled else None
            
            try:
                import time
                start_time = time.time()
                output_text = ""
                chunk_count = 0
                
                # Start progress monitoring if enabled
                if progress_tracker:
                    await progress_tracker.start()
                
                async for chunk in coordinator.run_stream(user_input):
                    print(chunk, end="", flush=True)
                    output_text += chunk
                    chunk_count += 1
                    # Mark activity to reset idle timer
                    if progress_tracker:
                        progress_tracker.activity()
                
                # Stop progress tracking
                if progress_tracker:
                    await progress_tracker.stop()
                
                print()  # Blank line for spacing after response
                
                # Record metrics (automatically appends to daily log)
                duration = time.time() - start_time
                metrics_collector.record(
                    operation="query",
                    agent="coordinator",
                    duration_seconds=duration,
                    success=True,
                    input_length=len(user_input),
                    output_length=len(output_text),
                    chunk_count=chunk_count,
                    model=config.models.ollama.model_id,
                )
                
            except Exception as e:
                # Stop progress tracking on error
                if progress_tracker:
                    await progress_tracker.stop()
                
                # Record failed metric (automatically appends to daily log)
                duration = time.time() - start_time if 'start_time' in dir() else 0
                metrics_collector.record(
                    operation="query",
                    agent="coordinator",
                    duration_seconds=duration,
                    success=False,
                    error_message=str(e),
                    input_length=len(user_input),
                    model=config.models.ollama.model_id,
                )
                
                # Check for common Ollama JSON escaping errors with small models
                error_msg = str(e)
                if "invalid character" in error_msg and "escape code" in error_msg:
                    logger.error(f"Tool call JSON error: {e}", exc_info=True)
                    print(f"\n\nError: The model generated malformed JSON for a tool call.")
                    print("This is common with smaller models when handling complex content.")
                    print("\nSuggestions:")
                    print("  1. Try a more capable model: ollama pull qwen3:8b")
                    print("  2. Update config.yaml: model_id: \"qwen3:8b\"")
                    print("  3. Or try: llama3.2:3b, mistral:7b, or qwen3:4b")
                    print("\nYou can also try rephrasing your request more simply.\n")
                else:
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
    
    # Configure metrics collection
    configure_metrics(
        metrics_dir=config.metrics.directory,
        enabled=config.metrics.enabled,
    )
    if config.metrics.enabled:
        logger.info(f"Metrics collection enabled: {config.metrics.directory}")
    
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
    
    # Save session metrics on shutdown
    metrics_collector = get_metrics_collector()
    metrics_file = metrics_collector.save_session()
    if metrics_file:
        print(f"\nSession metrics saved to: {metrics_file}")
    
    logger.info("CLI shutdown complete")


def main():
    """Main entry point for CLI."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
