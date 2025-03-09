"""Command line interface helpers for the expense manager."""

import subprocess
import sys
from pathlib import Path


def run_app() -> None:
    """Run the Streamlit application.

    This function executes the Streamlit command to run the expense manager app.
    It finds the correct path to app.py and launches it using streamlit run.

    Returns:
        None
    """
    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"

    # Execute the streamlit run command
    # We use sys.executable to ensure we're using the right Python interpreter
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]

    try:
        # Exit with the same return code as the subprocess
        sys.exit(subprocess.call(cmd))
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)
