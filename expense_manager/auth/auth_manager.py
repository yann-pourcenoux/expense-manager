"""Authentication manager for SQLite-based authentication.

This module handles authentication with SQLite, including:
- User signup
- User login
- User logout
- Session management
"""

import hashlib
import uuid
from typing import Any, Dict

from expense_manager.db.db_manager import DatabaseManager


class AuthManager:
    """Manager for SQLite-based authentication operations.

    This class handles authentication-related operations, including user signup,
    login, and session management.
    """

    def __init__(self) -> None:
        """Initialize DatabaseManager for authentication operations."""
        self.db_manager = DatabaseManager()
        self.current_user = None

    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def signup(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user and create a profile.

        Args:
            email (str): User's email address
            password (str): User's password

        Returns:
            Dict[str, Any]: Dict containing user data or error message
        """
        try:
            # Check if user already exists
            existing_user = self.db_manager.get_user_by_email(email)
            if existing_user.get("user"):
                return {"error": "Email already registered"}

            # Create a new user
            user_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)

            user_result = self.db_manager.create_user(user_id, email, password_hash)

            if user_result.get("error"):
                return {"error": user_result["error"]}

            user = user_result["user"]

            # Create a user profile with display name derived from email
            display_name = email.split("@")[0]  # Use part before @ as display name
            profile_result = self.db_manager.create_profile(user_id, display_name)

            # Check if profile creation succeeded
            if profile_result.get("error"):
                # If profile creation failed, we should return the error
                # but we don't want to fail the whole signup
                return {
                    "user": user,
                    "profile_error": profile_result["error"],
                }

            return {
                "user": user,
                "profile": profile_result.get("profile"),
            }

        except Exception as e:
            return {"error": str(e)}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login an existing user.

        Args:
            email (str): User's email address
            password (str): User's password

        Returns:
            Dict[str, Any]: Dict containing user data or error message
        """
        try:
            # Get user by email
            user_result = self.db_manager.get_user_by_email(email)

            if not user_result.get("user"):
                return {"error": "Invalid email or password"}

            user = user_result["user"]

            # Verify password
            password_hash = self._hash_password(password)
            if password_hash != user["password_hash"]:
                return {"error": "Invalid email or password"}

            # Store current user
            self.current_user = user

            return {"user": user}

        except Exception as e:
            return {"error": str(e)}

    def logout(self) -> None:
        """Log out the current user."""
        self.current_user = None

    def get_user(self) -> Dict[str, Any] | None:
        """Get the current user if logged in.

        Returns:
            Dict[str, Any] | None: User data if logged in, None otherwise
        """
        return self.current_user
