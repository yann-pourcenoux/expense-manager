"""Configuration management for Expense Manager.

This module provides functionality to load configuration profiles
from YAML files.
"""

from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(profile: str = "development") -> Dict[str, Any]:
    """Load configuration from a profile YAML file.

    Args:
        profile (str): The name of the configuration profile to load
            ('development' or 'production')

    Returns:
        Dict[str, Any]: The configuration dictionary

    Raises:
        ValueError: If an invalid profile is specified
    """
    # Validate profile
    if profile not in ["development", "production"]:
        raise ValueError(
            f"Invalid profile: {profile}. Must be 'development' or 'production'"
        )

    # Get the config directory path (project_root/config/)
    config_dir = Path(__file__).parent.parent / "config"
    config_dir.mkdir(exist_ok=True)

    # Build the path to the config file
    config_path = config_dir / f"{profile}.yaml"

    # If the config file doesn't exist, raise an error
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration profile '{profile}' not found at {config_path}"
        )

    # Load the config file
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config
