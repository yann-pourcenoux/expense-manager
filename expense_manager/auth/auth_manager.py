"""Authentication manager for Supabase authentication.

This module handles authentication with Supabase, including:
- User signup
- User login
- User logout
- Session management
"""

import os
from typing import Any, Dict

from dotenv import load_dotenv
from supabase import Client, create_client

from expense_manager.db.db_manager import DatabaseManager

# Load environment variables
load_dotenv()


class AuthManager:
    """Manager for Supabase authentication operations.

    This class handles authentication-related operations with Supabase,
    including user signup, login, and session management.
    """

    def __init__(self) -> None:
        """Initialize Supabase client with environment variables."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase credentials not found. Please set SUPABASE_URL and "
                "SUPABASE_KEY environment variables."
            )

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.db_manager = DatabaseManager()

    def signup(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user with Supabase and create a profile.

        Args:
            email (str): User's email address
            password (str): User's password

        Returns:
            Dict[str, Any]: Dict containing user data or error message
        """
        try:
            data = self.client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                }
            )

            if data.user:
                user_id = data.user.id

                # Create a user profile with display name derived from email
                display_name = email.split("@")[0]  # Use part before @ as display name
                profile_result = self.db_manager.create_profile(user_id, display_name)

                # Check if profile creation succeeded
                if profile_result.get("error"):
                    # If profile creation failed, we should return the error
                    # but we don't want to fail the whole signup
                    return {
                        "user": data.user,
                        "session": data.session,
                        "profile_error": profile_result["error"],
                    }

                return {
                    "user": data.user,
                    "session": data.session,
                    "profile": profile_result.get("profile"),
                }

            return {"error": "Failed to create user"}

        except Exception as e:
            return {"error": str(e)}

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login an existing user with Supabase.

        Args:
            email (str): User's email address
            password (str): User's password

        Returns:
            Dict[str, Any]: Dict containing user data or error message
        """
        try:
            data = self.client.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )

            if data.user:
                return {"user": data.user, "session": data.session}
            return {"error": "Login failed"}

        except Exception as e:
            return {"error": str(e)}

    def logout(self) -> None:
        """Log out the current user."""
        try:
            self.client.auth.sign_out()
        except Exception:
            # If there's an error logging out, we still want to clear the session
            pass

    def get_user(self) -> Dict[str, Any] | None:
        """Get the current user if logged in.

        Returns:
            Dict[str, Any] | None: User data if logged in, None otherwise
        """
        try:
            session = self.client.auth.get_session()
            if session and session.user:
                return dict(session.user.model_dump())
            return None
        except Exception:
            return None
