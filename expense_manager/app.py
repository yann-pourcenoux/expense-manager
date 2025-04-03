"""Main Streamlit application for the expense manager.

This module is the entry point for the Streamlit application and handles the
authentication flow for users.
"""

import argparse

import streamlit as st

from expense_manager.auth.auth_manager import AuthManager
from expense_manager.config import load_config
from expense_manager.db.db_manager import DatabaseManager
from expense_manager.pages.categories import display_category_manager
from expense_manager.pages.dashboard import (
    display_dashboard,
)
from expense_manager.pages.expenses import display_expense_manager
from expense_manager.pages.flow import display_flow_page
from expense_manager.pages.income import display_income_manager
from expense_manager.pages.profile import (
    display_profile_manager,
    display_profile_setup,
)

# Global variables for managers
auth_manager = None
db_manager = None


# Parse command line arguments
def parse_arguments():
    """Parse command line arguments for the application.

    Returns:
        argparse.Namespace: The parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Expense Manager Streamlit App")
    parser.add_argument(
        "--profile",
        type=str,
        default="development",
        choices=["development", "production"],
        help="Configuration profile to use (development or production)",
    )
    return parser.parse_args()


def main() -> None:
    """Set up the app flow based on authentication state."""
    global auth_manager, db_manager

    # Parse arguments
    args = parse_arguments()

    # Load config based on profile and store in session state
    config = load_config(args.profile)
    st.session_state.config = config

    # Configure Streamlit page
    st.set_page_config(
        page_title="Expense Manager",
        page_icon="💸",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize the authentication manager
    auth_manager = AuthManager()
    db_manager = DatabaseManager()

    # Check if user is already authenticated
    if "user" not in st.session_state:
        st.session_state.user = None

    # Initialize page state if not exists
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Manage Expenses"

    # Initialize profile setup state if not exists
    if "profile_setup_complete" not in st.session_state:
        st.session_state.profile_setup_complete = False

    # Display login/signup screen if not authenticated
    if not st.session_state.user:
        display_auth_screen()
    else:
        # Check if profile setup is needed on first login
        user_id = (
            st.session_state.user.id
            if hasattr(st.session_state.user, "id")
            else st.session_state.user["id"]
        )

        # If profile_setup_complete flag is not set, check if profile exists
        if not st.session_state.profile_setup_complete:
            profile_result = db_manager.get_profile(user_id)

            # Check if profile exists and has a display name
            if profile_result.get("profile") and profile_result["profile"].get(
                "display_name"
            ):
                # Profile exists, no need for setup
                st.session_state.profile_setup_complete = True

        # Show profile setup if needed, otherwise show main app
        if not st.session_state.profile_setup_complete:
            display_profile_setup(on_complete=lambda: st.rerun())
        else:
            # User is authenticated and profile is set up, display the main app
            display_main_app()


def display_auth_screen() -> None:
    """Display login and signup interface."""
    st.title("💸 Expense Manager")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.header("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button"):
            if email and password:
                with st.spinner("Logging in..."):
                    result = auth_manager.login(email, password)
                    if result.get("error"):
                        st.error(result["error"])
                    else:
                        st.session_state.user = result["user"]
                        st.rerun()
            else:
                st.warning("Please enter both email and password")

    with tab2:
        st.header("Sign Up")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="confirm_password"
        )

        if st.button("Sign Up", key="signup_button"):
            if email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    with st.spinner("Creating account..."):
                        result = auth_manager.signup(email, password)
                        if result.get("error"):
                            st.error(result["error"])
                        else:
                            success_message = (
                                "Account created successfully! Please log in."
                            )

                            # Check if there was an error creating the profile
                            if result.get("profile_error"):
                                success_message += f" (Note: {result['profile_error']})"

                            st.success(success_message)
            else:
                st.warning("Please fill out all fields")


def display_main_app() -> None:
    """Display the main application interface after authentication."""
    # Sidebar with navigation and user info
    with st.sidebar:
        # Get user display name if available
        user_id = (
            st.session_state.user.id
            if hasattr(st.session_state.user, "id")
            else st.session_state.user["id"]
        )
        profile_result = db_manager.get_profile(user_id)

        if profile_result.get("profile") and profile_result["profile"].get(
            "display_name"
        ):
            display_name = profile_result["profile"]["display_name"]
            st.write(f"👋 Hello, {display_name}!")
        else:
            email = (
                st.session_state.user.email
                if hasattr(st.session_state.user, "email")
                else st.session_state.user["email"]
            )
            st.write(f"Logged in as: {email}")

        # Navigation
        st.subheader("Navigation")

        # Simple navigation buttons
        st.sidebar.button(
            "📊 Dashboard",
            key="nav_dashboard",
            use_container_width=True,
            on_click=lambda: set_current_page("Dashboard"),
        )

        st.sidebar.button(
            "💰 Expenses",
            key="nav_expenses",
            use_container_width=True,
            on_click=lambda: set_current_page("Manage Expenses"),
        )

        st.sidebar.button(
            "💵 Income",
            key="nav_income",
            use_container_width=True,
            on_click=lambda: set_current_page("Income"),
        )

        st.sidebar.button(
            "📊 Flow",
            key="nav_flow",
            use_container_width=True,
            on_click=lambda: set_current_page("Flow"),
        )

        st.sidebar.button(
            "🏷️ Categories",
            key="nav_categories",
            use_container_width=True,
            on_click=lambda: set_current_page("Categories"),
        )

        st.sidebar.button(
            "👤 Profile",
            key="nav_profile",
            use_container_width=True,
            on_click=lambda: set_current_page("Profile"),
        )

        # Logout button
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout", key="logout", use_container_width=True):
            auth_manager.logout()
            st.session_state.user = None
            # Clear profile setup flag on logout
            st.session_state.profile_setup_complete = False
            st.rerun()

    # Display the selected page
    if st.session_state.current_page == "Dashboard":
        display_dashboard()
    elif st.session_state.current_page == "Manage Expenses":
        display_expense_manager()
    elif st.session_state.current_page == "Income":
        display_income_manager()
    elif st.session_state.current_page == "Flow":
        display_flow_page()
    elif st.session_state.current_page == "Categories":
        display_category_manager()
    elif st.session_state.current_page == "Profile":
        display_profile_manager()


def set_current_page(page_name: str) -> None:
    """Set the current page in session state.

    Args:
        page_name (str): Name of the page to set as current

    Returns:
        None
    """
    st.session_state.current_page = page_name
    st.rerun()


if __name__ == "__main__":
    main()
