# Copyright (c) 2024. All rights reserved.
"""Streamlit Web Interface for Multi-Agent Workflow.

A web-based chat interface for interacting with the Coordinator agent,
with additional panels for configuration, metrics, and knowledge base viewing.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import yaml

from app.agents.coordinator import CoordinatorAgent
from app.config import get_config, load_config, reload_config, AppConfig
from app.logging_config import setup_logging, LOGGER_ROOT
from app.metrics import configure_metrics, get_metrics_collector

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="Multi-Agent Workflow Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Logger for web interface
logger = logging.getLogger("workflow.web")


# =============================================================================
# Session State Initialization
# =============================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "coordinator" not in st.session_state:
        st.session_state.coordinator = None
    
    if "config" not in st.session_state:
        st.session_state.config = None
    
    if "log_level" not in st.session_state:
        st.session_state.log_level = "INFO"
    
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    if "metrics_enabled" not in st.session_state:
        st.session_state.metrics_enabled = True
    
    if "total_queries" not in st.session_state:
        st.session_state.total_queries = 0
    
    if "session_start" not in st.session_state:
        st.session_state.session_start = datetime.now()
    
    if "event_loop" not in st.session_state:
        st.session_state.event_loop = None


def get_or_create_event_loop():
    """Get or create a persistent event loop for async operations."""
    if st.session_state.event_loop is None or st.session_state.event_loop.is_closed():
        loop = asyncio.new_event_loop()
        st.session_state.event_loop = loop
    return st.session_state.event_loop


def initialize_app():
    """Initialize the application (config, logging, coordinator)."""
    if st.session_state.initialized:
        return True
    
    try:
        # Load configuration
        config = get_config()
        st.session_state.config = config
        
        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
        )
        st.session_state.log_level = config.logging.level
        
        # Configure metrics
        configure_metrics(
            metrics_dir=config.metrics.directory,
            enabled=config.metrics.enabled,
        )
        st.session_state.metrics_enabled = config.metrics.enabled
        
        # Initialize coordinator
        st.session_state.coordinator = CoordinatorAgent()
        st.session_state.initialized = True
        
        logger.info("Streamlit app initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize app: {e}", exc_info=True)
        st.error(f"Failed to initialize: {e}")
        return False


# =============================================================================
# Helper Functions
# =============================================================================

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def load_knowledge_status() -> dict:
    """Load current knowledge base status."""
    config = st.session_state.config
    if not config:
        return {}
    
    project_root = get_project_root()
    status = {
        "instructions": {"exists": False, "size": 0, "updated": None},
        "url_index": {"exists": False, "count": 0},
        "notes": {"exists": False, "count": 0, "files": []},
    }
    
    # Instructions file
    instructions_path = project_root / config.knowledge.instructions_file
    if instructions_path.exists():
        stat = instructions_path.stat()
        status["instructions"] = {
            "exists": True,
            "size": stat.st_size,
            "updated": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
    
    # URL index
    url_index_path = project_root / config.knowledge.url_index_file
    if url_index_path.exists():
        try:
            with open(url_index_path, "r", encoding="utf-8") as f:
                url_data = yaml.safe_load(f) or {}
            urls = url_data.get("urls", [])
            status["url_index"] = {
                "exists": True,
                "count": len(urls),
                "urls": urls[:10],  # First 10 for display
            }
        except Exception:
            pass
    
    # Notes
    for topic, topic_config in config.knowledge.notes_topics.items():
        notes_dir = project_root / topic_config.directory
        index_path = notes_dir / "_index.yaml"
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = yaml.safe_load(f) or {}
                notes = index_data.get("notes", [])
                status["notes"] = {
                    "exists": True,
                    "count": len(notes),
                    "files": notes[:10],  # First 10 for display
                }
            except Exception:
                pass
    
    return status


def get_metrics_summary() -> dict:
    """Get current metrics summary."""
    collector = get_metrics_collector()
    return collector.get_summary()


def set_log_level(level: str):
    """Set the logging level."""
    root_logger = logging.getLogger(LOGGER_ROOT)
    level_int = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(level_int)
    for handler in root_logger.handlers:
        handler.setLevel(level_int)
    st.session_state.log_level = level.upper()
    logger.info(f"Log level changed to {level}")


async def process_message(user_input: str) -> str:
    """Process a user message and return the response."""
    config = st.session_state.config
    coordinator = st.session_state.coordinator
    metrics_collector = get_metrics_collector()
    
    start_time = time.time()
    output_text = ""
    chunk_count = 0
    
    try:
        async for chunk in coordinator.run_stream(user_input):
            output_text += chunk
            chunk_count += 1
        
        # Record metrics
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
        
        st.session_state.total_queries += 1
        return output_text
        
    except Exception as e:
        duration = time.time() - start_time
        metrics_collector.record(
            operation="query",
            agent="coordinator",
            duration_seconds=duration,
            success=False,
            error_message=str(e),
            input_length=len(user_input),
            model=config.models.ollama.model_id,
        )
        raise


# =============================================================================
# UI Components
# =============================================================================

def render_sidebar():
    """Render the sidebar with configuration and status."""
    config = st.session_state.config
    
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Connection Status
        st.subheader("🔌 Connection")
        if st.session_state.initialized:
            st.success(f"Connected to Ollama")
            st.caption(f"Host: `{config.models.ollama.host}`")
            st.caption(f"Model: `{config.models.ollama.model_id}`")
            
            # Reload config button
            if st.button("🔄 Reload Config", use_container_width=True, help="Reload config.yaml and reinitialize agents"):
                try:
                    # Force reload from disk
                    new_config = reload_config()
                    logger.info(f"Config reloaded, new model: {new_config.models.ollama.model_id}")
                    
                    # Update session state
                    st.session_state.config = new_config
                    st.session_state.initialized = False  # Force reinitialization
                    st.session_state.coordinator = None
                    st.session_state.messages = []
                    
                    # Reinitialize with new config
                    st.session_state.coordinator = CoordinatorAgent()
                    st.session_state.initialized = True
                    
                    logger.info(f"Coordinator reinitialized with model: {new_config.models.ollama.model_id}")
                    st.toast(f"✅ Config reloaded! Model: {new_config.models.ollama.model_id}")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Failed to reload config: {e}", exc_info=True)
                    st.error(f"Failed to reload: {e}")
        else:
            st.error("Not connected")
        
        st.divider()
        
        # Session Controls
        st.subheader("💬 Conversation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 New Chat", use_container_width=True):
                st.session_state.coordinator.new_thread()
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        
        st.divider()
        
        # Logging Level
        st.subheader("📝 Logging")
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        current_level = st.session_state.log_level
        new_level = st.selectbox(
            "Log Level",
            log_levels,
            index=log_levels.index(current_level) if current_level in log_levels else 1,
            key="log_level_select",
        )
        if new_level != current_level:
            set_log_level(new_level)
            st.toast(f"Log level set to {new_level}")
        
        st.divider()
        
        # Session Metrics
        st.subheader("📊 Session Metrics")
        metrics = get_metrics_summary()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Queries", st.session_state.total_queries)
            st.metric("Success", metrics.get("successful", 0))
        with col2:
            st.metric("Failed", metrics.get("failed", 0))
            avg_time = metrics.get("average_time_seconds", 0)
            st.metric("Avg Time", f"{avg_time:.1f}s")
        
        # Session duration
        duration = datetime.now() - st.session_state.session_start
        minutes = int(duration.total_seconds() // 60)
        st.caption(f"Session duration: {minutes}m")
        
        st.divider()
        
        # Knowledge Base Status
        st.subheader("📚 Knowledge Base")
        kb_status = load_knowledge_status()
        
        # Instructions
        instr = kb_status.get("instructions", {})
        if instr.get("exists"):
            st.caption(f"✅ Instructions: {instr.get('size', 0)} bytes")
        else:
            st.caption("❌ No instructions file")
        
        # URLs
        urls = kb_status.get("url_index", {})
        if urls.get("exists"):
            st.caption(f"✅ URLs indexed: {urls.get('count', 0)}")
        else:
            st.caption("❌ No URLs indexed")
        
        # Notes
        notes = kb_status.get("notes", {})
        if notes.get("exists"):
            st.caption(f"✅ Notes: {notes.get('count', 0)}")
        else:
            st.caption("❌ No notes")


def render_chat():
    """Render the main chat interface."""
    st.title("🤖 Multi-Agent Workflow Assistant")
    
    # Tips
    with st.expander("💡 Tips", expanded=False):
        st.markdown("""
        **What can I do?**
        - 🔗 **Analyze URLs**: Paste a URL to fetch and summarize its content
        - 📝 **Store knowledge**: Share information to save to the knowledge base
        - 🔍 **Search notes**: Ask about stored notes and documentation
        - 💬 **General chat**: Ask questions and get help
        
        **Examples:**
        - "Analyze https://example.com/docs"
        - "Save this: Our team uses Python and Terraform"
        - "Do I have any notes on Kubernetes?"
        """)
    
    # Chat messages container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message...", disabled=st.session_state.processing):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process and display assistant response
        with st.chat_message("assistant"):
            st.session_state.processing = True
            
            with st.spinner("Thinking..."):
                try:
                    # Run async function using persistent event loop
                    loop = get_or_create_event_loop()
                    asyncio.set_event_loop(loop)
                    response = loop.run_until_complete(process_message(prompt))
                    
                    st.markdown(response)
                    
                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                    })
                    
                except Exception as e:
                    error_msg = str(e)
                    if "invalid character" in error_msg and "escape code" in error_msg:
                        st.error("""
                        **Tool Call Error**: The model generated malformed JSON.
                        
                        This is common with smaller models. Try:
                        - Using a more capable model (qwen3:8b recommended)
                        - Rephrasing your request more simply
                        """)
                    else:
                        st.error(f"Error: {e}")
                        st.info("Make sure Ollama is running and the model is available.")
                
                finally:
                    st.session_state.processing = False


def render_knowledge_explorer():
    """Render the knowledge base explorer tab."""
    st.header("📚 Knowledge Base Explorer")
    
    kb_status = load_knowledge_status()
    project_root = get_project_root()
    config = st.session_state.config
    
    tab1, tab2, tab3 = st.tabs(["📋 Instructions", "🔗 URL Index", "📝 Notes"])
    
    with tab1:
        st.subheader("Organizational Instructions")
        instructions_path = project_root / config.knowledge.instructions_file
        if instructions_path.exists():
            with open(instructions_path, "r", encoding="utf-8") as f:
                content = f.read()
            st.markdown(content)
        else:
            st.info("No instructions file found. Use the chat to add organizational context.")
    
    with tab2:
        st.subheader("Indexed URLs")
        urls = kb_status.get("url_index", {}).get("urls", [])
        if urls:
            for url_entry in urls:
                with st.expander(f"🔗 {url_entry.get('title', 'Untitled')}", expanded=False):
                    st.markdown(f"**URL:** [{url_entry.get('url')}]({url_entry.get('url')})")
                    st.markdown(f"**Domain:** {url_entry.get('domain', 'general')}")
                    st.markdown(f"**Context:** {url_entry.get('context', '')}")
                    st.markdown(f"**Summary:** {url_entry.get('summary', '')}")
                    tags = url_entry.get("tags", [])
                    if tags:
                        st.markdown(f"**Tags:** {', '.join(tags)}")
        else:
            st.info("No URLs indexed yet. Analyze a URL in the chat to add it.")
    
    with tab3:
        st.subheader("Notes")
        notes = kb_status.get("notes", {}).get("files", [])
        if notes:
            for note in notes:
                with st.expander(f"📝 {note.get('title', 'Untitled')}", expanded=False):
                    st.markdown(f"**File:** `{note.get('filename')}`")
                    st.markdown(f"**Domain:** {note.get('domain', 'general')}")
                    st.markdown(f"**Summary:** {note.get('summary', '')}")
                    tags = note.get("tags", [])
                    if tags:
                        st.markdown(f"**Tags:** {', '.join(tags)}")
                    st.markdown(f"**Created:** {note.get('created', 'Unknown')}")
                    
                    # Read full note button
                    if st.button(f"View Full Note", key=f"view_{note.get('filename')}"):
                        for topic, topic_config in config.knowledge.notes_topics.items():
                            note_path = project_root / topic_config.directory / note.get("filename")
                            if note_path.exists():
                                with open(note_path, "r", encoding="utf-8") as f:
                                    st.markdown(f.read())
                                break
        else:
            st.info("No notes found. Use the chat to create notes.")


def render_metrics_dashboard():
    """Render the metrics dashboard tab."""
    st.header("📊 Metrics Dashboard")
    
    config = st.session_state.config
    project_root = get_project_root()
    metrics_dir = project_root / config.metrics.directory
    
    # Session metrics
    col1, col2, col3, col4 = st.columns(4)
    metrics = get_metrics_summary()
    
    with col1:
        st.metric("Total Operations", metrics.get("total_operations", 0))
    with col2:
        st.metric("Successful", metrics.get("successful", 0))
    with col3:
        st.metric("Failed", metrics.get("failed", 0))
    with col4:
        st.metric("Avg Duration", f"{metrics.get('average_time_seconds', 0):.2f}s")
    
    st.divider()
    
    # Recent metrics files
    st.subheader("📁 Metrics Files")
    if metrics_dir.exists():
        files = sorted(metrics_dir.glob("*.jsonl"), reverse=True)[:10]
        if files:
            for f in files:
                stat = f.stat()
                size_kb = stat.st_size / 1024
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                st.caption(f"📄 `{f.name}` - {size_kb:.1f} KB - {modified}")
        else:
            st.info("No metrics files yet.")
    else:
        st.info("Metrics directory not found.")


# =============================================================================
# Main App
# =============================================================================

def main():
    """Main Streamlit application."""
    # Initialize session state
    init_session_state()
    
    # Initialize app (config, coordinator, etc.)
    if not initialize_app():
        st.error("Failed to initialize application. Check your configuration.")
        st.stop()
    
    # Render sidebar
    render_sidebar()
    
    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📚 Knowledge Base", "📊 Metrics"])
    
    with tab1:
        render_chat()
    
    with tab2:
        render_knowledge_explorer()
    
    with tab3:
        render_metrics_dashboard()


if __name__ == "__main__":
    main()
