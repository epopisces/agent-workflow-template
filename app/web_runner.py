"""Web runner for Streamlit application.

This module provides an entry point to launch the Streamlit web interface.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch the Streamlit web interface."""
    # Get the path to the web.py module
    web_module = Path(__file__).parent / "web.py"
    
    # Build the streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(web_module),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    
    # Run streamlit
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except FileNotFoundError:
        print("Error: Streamlit not found. Install with: pip install streamlit")
        sys.exit(1)


if __name__ == "__main__":
    main()
