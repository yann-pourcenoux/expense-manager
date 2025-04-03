"""Command line interface helpers for the expense manager."""

import subprocess
import sys
from pathlib import Path


def run_app() -> None:
    """Run the Streamlit application.

    This function executes the Streamlit command to run the expense manager app.
    It finds the correct path to app.py and launches it using streamlit run.

    It also handles profile selection:
      - `run` - Runs with development profile (default)
      - `run dev` - Runs with development profile
      - `run prod` - Runs with production profile

    Returns:
        None
    """
    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"

    # Check if a profile argument was provided
    profile = "development"  # Default to development profile
    if len(sys.argv) > 1:
        profile_arg = sys.argv[1]
        # Support common shorthand
        if profile_arg == "dev":
            profile = "development"
        elif profile_arg == "prod":
            profile = "production"
        else:
            print(f"Invalid profile: {profile_arg}. Must be 'dev' or 'prod'")
            sys.exit(1)

    # Load config to get port
    from expense_manager.config import load_config

    try:
        config = load_config(profile)
        port = config["server"]["port"]
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Execute the streamlit run command
    # We use sys.executable to ensure we're using the right Python interpreter
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--",  # Pass remaining args to the app
        "--profile",
        profile,
    ]

    try:
        print(f"Starting Expense Manager with profile '{profile}' on port {port}")
        # Exit with the same return code as the subprocess
        sys.exit(subprocess.call(cmd))
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)
