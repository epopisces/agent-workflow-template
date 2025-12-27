# Copyright (c) 2024. All rights reserved.
"""Progress Tracker for Agent Operations.

Provides visual feedback during long-running agent processes by displaying
periodic status updates to keep users informed that work is in progress.
"""

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Callable

# Logger for progress tracking
logger = logging.getLogger("workflow.progress")


class ProgressStyle(Enum):
    """Style of progress indicator to display."""
    SPINNER = "spinner"
    DOTS = "dots"
    ELAPSED = "elapsed"
    MESSAGE = "message"


@dataclass
class ProgressConfig:
    """Configuration for progress tracking."""
    style: ProgressStyle = ProgressStyle.DOTS
    update_interval: float = 2.0  # seconds between updates
    show_elapsed: bool = True
    messages: list[str] = field(default_factory=lambda: [
        "Working",
        "Still processing",
        "Please wait",
        "Almost there",
        "Continuing analysis",
    ])


# Spinner characters for visual feedback
SPINNER_CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
DOT_SEQUENCE = [".", "..", "...", "...."]


class ProgressTracker:
    """Tracks and displays progress for long-running operations.
    
    Provides visual feedback to users during agent operations that may
    take significant time to complete.
    """
    
    def __init__(
        self,
        config: ProgressConfig | None = None,
        output_func: Callable[[str], None] | None = None,
    ):
        """Initialize the progress tracker.
        
        Args:
            config: Progress display configuration.
            output_func: Function to output progress messages.
                        Defaults to sys.stderr.write with flush.
        """
        self._config = config or ProgressConfig()
        self._output = output_func or self._default_output
        self._task: asyncio.Task | None = None
        self._start_time: float | None = None
        self._is_running = False
        self._operation_name: str = "Processing"
        self._spinner_idx = 0
        self._dot_idx = 0
        self._message_idx = 0
        
    def _default_output(self, text: str) -> None:
        """Default output function using stderr."""
        sys.stderr.write(text)
        sys.stderr.flush()
        
    def _format_elapsed(self) -> str:
        """Format elapsed time string."""
        if self._start_time is None:
            return ""
        elapsed = time.time() - self._start_time
        if elapsed < 60:
            return f"{elapsed:.0f}s"
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes}m {seconds}s"
    
    def _get_progress_text(self) -> str:
        """Generate progress text based on style."""
        elapsed_str = f" ({self._format_elapsed()})" if self._config.show_elapsed else ""
        
        if self._config.style == ProgressStyle.SPINNER:
            char = SPINNER_CHARS[self._spinner_idx % len(SPINNER_CHARS)]
            self._spinner_idx += 1
            return f"\r{char} {self._operation_name}{elapsed_str}    "
            
        elif self._config.style == ProgressStyle.DOTS:
            dots = DOT_SEQUENCE[self._dot_idx % len(DOT_SEQUENCE)]
            self._dot_idx += 1
            return f"\r{self._operation_name}{dots}{elapsed_str}    "
            
        elif self._config.style == ProgressStyle.ELAPSED:
            return f"\r{self._operation_name}{elapsed_str}    "
            
        elif self._config.style == ProgressStyle.MESSAGE:
            message = self._config.messages[self._message_idx % len(self._config.messages)]
            self._message_idx += 1
            return f"\r{message}{elapsed_str}    "
            
        return f"\r{self._operation_name}{elapsed_str}    "
    
    async def _progress_loop(self) -> None:
        """Internal loop that displays progress updates."""
        try:
            while self._is_running:
                self._output(self._get_progress_text())
                await asyncio.sleep(self._config.update_interval)
        except asyncio.CancelledError:
            pass
        finally:
            # Clear the progress line
            self._output("\r" + " " * 50 + "\r")
    
    async def start(self, operation_name: str = "Processing") -> None:
        """Start displaying progress updates.
        
        Args:
            operation_name: Name of the operation being tracked.
        """
        if self._is_running:
            logger.warning("Progress tracker already running")
            return
            
        self._operation_name = operation_name
        self._start_time = time.time()
        self._is_running = True
        self._spinner_idx = 0
        self._dot_idx = 0
        self._message_idx = 0
        
        logger.debug(f"Starting progress tracker for: {operation_name}")
        self._task = asyncio.create_task(self._progress_loop())
    
    async def stop(self) -> float:
        """Stop displaying progress updates.
        
        Returns:
            Total elapsed time in seconds.
        """
        self._is_running = False
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            
        logger.debug(f"Progress tracker stopped. Elapsed: {elapsed:.2f}s")
        return elapsed
    
    @asynccontextmanager
    async def track(self, operation_name: str = "Processing") -> AsyncIterator[None]:
        """Context manager for tracking progress.
        
        Args:
            operation_name: Name of the operation being tracked.
            
        Yields:
            Nothing, just provides progress display during execution.
            
        Example:
            async with tracker.track("Analyzing URL"):
                result = await agent.run(query)
        """
        await self.start(operation_name)
        try:
            yield
        finally:
            await self.stop()


class StreamingProgressTracker:
    """Progress tracker that works with streaming responses.
    
    Shows progress only when there's a pause in streaming output,
    without interrupting the stream display.
    """
    
    def __init__(
        self,
        idle_threshold: float = 3.0,
        update_interval: float = 2.0,
    ):
        """Initialize streaming progress tracker.
        
        Args:
            idle_threshold: Seconds of idle time before showing progress.
            update_interval: Seconds between progress updates when idle.
        """
        self._idle_threshold = idle_threshold
        self._update_interval = update_interval
        self._last_activity = time.time()
        self._task: asyncio.Task | None = None
        self._is_running = False
        self._start_time: float | None = None
        
    def _format_elapsed(self) -> str:
        """Format elapsed time string."""
        if self._start_time is None:
            return ""
        elapsed = time.time() - self._start_time
        if elapsed < 60:
            return f"{elapsed:.0f}s"
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes}m {seconds}s"
    
    async def _idle_monitor(self) -> None:
        """Monitor for idle periods and show status."""
        try:
            while self._is_running:
                await asyncio.sleep(self._update_interval)
                idle_time = time.time() - self._last_activity
                if idle_time >= self._idle_threshold:
                    elapsed = self._format_elapsed()
                    sys.stderr.write(f"\n[Still working... {elapsed}]\n")
                    sys.stderr.flush()
        except asyncio.CancelledError:
            pass
    
    def activity(self) -> None:
        """Record activity (call when streaming data is received)."""
        self._last_activity = time.time()
    
    async def start(self) -> None:
        """Start monitoring for idle periods."""
        self._is_running = True
        self._start_time = time.time()
        self._last_activity = time.time()
        self._task = asyncio.create_task(self._idle_monitor())
        logger.debug("Started streaming progress monitor")
    
    async def stop(self) -> float:
        """Stop monitoring and return elapsed time."""
        self._is_running = False
        elapsed = time.time() - self._start_time if self._start_time else 0.0
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            
        return elapsed
    
    @asynccontextmanager
    async def monitor(self) -> AsyncIterator["StreamingProgressTracker"]:
        """Context manager for monitoring streaming progress.
        
        Yields:
            Self, so caller can mark activity during streaming.
            
        Example:
            async with tracker.monitor() as progress:
                async for chunk in stream:
                    progress.activity()
                    print(chunk)
        """
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
