#!/usr/bin/env python3
"""Script to run the Expense Manager Streamlit app.

This script allows running the app with different configuration profiles.
"""

import subprocess
from pathlib import Path


def run_streamlit(profile="default"):
    """Run the Streamlit app with the specified profile.

    Args:
        profile (str): Configuration profile to use
    """
    # Get the app path
    app_path = Path(__file__).parent / "expense_manager" / "app.py"

    # Get port from config (for display purposes only)
    from expense_manager.config import load_config

    config = load_config(profile)
    port = config["server"]["port"]

    print(f"Starting Expense Manager with profile '{profile}' on port {port}")

    # Build the command
    cmd = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--",  # Pass remaining args to the app
        "--profile",
        profile,
    ]

    # Run the command
    subprocess.run(cmd)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Expense Manager with configuration profile"
    )
    parser.add_argument(
        "--profile", type=str, default="default", help="Configuration profile to use"
    )

    args = parser.parse_args()
    run_streamlit(args.profile)
