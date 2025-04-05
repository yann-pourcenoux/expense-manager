"""Profile management page for the Expense Manager.

This module provides a UI for users to view and update their profile information.
"""

from typing import Callable

import streamlit as st

from expense_manager.db.db_manager import DatabaseManager


def display_profile_setup(on_complete: Callable[[], None]) -> None:
    """Display the profile setup form for first-time users.

    Args:
        on_complete (Callable[[], None]): Function to call when profile setup
            is complete
    """
    st.title("🙋 Set Up Your Profile")

    st.markdown("""
    Welcome to the Expense Manager! Please set up your profile information.

    This information will be used to personalize your experience and
    will appear when you share expenses with others.
    """)

    # Get current user ID from session state
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Default display name (email username is set during signup)
    default_display_name = ""

    # Get existing profile if available
    db_manager = DatabaseManager()
    profile_result = db_manager.get_profile(user_id)

    if profile_result.get("profile"):
        default_display_name = profile_result["profile"]["display_name"]

    # Profile form
    with st.form("profile_setup_form"):
        display_name = st.text_input(
            "Display Name",
            value=default_display_name,
            help="This is how you'll appear to others on the platform",
        )

        # Add additional profile fields as needed
        # For example:
        # profile_image = st.file_uploader("Profile Picture", type=["jpg", "png"])
        # currency = st.selectbox("Preferred Currency", ["USD", "EUR", "GBP", "JPY"])

        submit_button = st.form_submit_button("Save Profile")

        if submit_button:
            if not display_name:
                st.error("Please enter a display name")
            else:
                with st.spinner("Saving profile..."):
                    # Update profile
                    result = db_manager.update_profile(user_id, display_name)

                    if result.get("error"):
                        st.error(f"Failed to update profile: {result['error']}")
                    else:
                        st.success("Profile updated successfully!")

                        # Mark profile as set up
                        st.session_state.profile_setup_complete = True

                        # Call the completion callback
                        on_complete()


def display_profile_manager() -> None:
    """Display the profile management page for existing users."""
    st.title("👤 Profile Management")

    # Get current user ID from session state
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Get existing profile if available
    db_manager = DatabaseManager()
    profile_result = db_manager.get_profile(user_id)

    if profile_result.get("error"):
        st.error(f"Failed to load profile: {profile_result['error']}")
        return

    profile = profile_result.get("profile", {})

    # Show current profile info
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Your Information")
        st.write(f"Display Name: {profile.get('display_name', 'Not set')}")
        email = (
            st.session_state.user.email
            if hasattr(st.session_state.user, "email")
            else st.session_state.user["email"]
        )
        st.write(f"Email: {email}")

    # Edit profile form
    st.subheader("Edit Profile")
    with st.form("edit_profile_form"):
        new_display_name = st.text_input(
            "Display Name",
            value=profile.get("display_name", ""),
            help="This is how you'll appear to others on the platform",
        )

        # Add additional profile fields as needed

        submit_button = st.form_submit_button("Update Profile")

        if submit_button:
            if not new_display_name:
                st.error("Please enter a display name")
            else:
                with st.spinner("Updating profile..."):
                    # Update profile
                    result = db_manager.update_profile(user_id, new_display_name)

                    if result.get("error"):
                        st.error(f"Failed to update profile: {result['error']}")
                    else:
                        st.success("Profile updated successfully!")

    # Add password change section
    st.subheader("Change Password")
    with st.form("change_password_form"):
        current_password = st.text_input(
            "Current Password",
            type="password",
            help="Enter your current password for verification",
        )

        new_password = st.text_input(
            "New Password",
            type="password",
            help="Enter your new password",
        )

        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            help="Confirm your new password",
        )

        submit_button = st.form_submit_button("Change Password")

        if submit_button:
            if not current_password or not new_password or not confirm_password:
                st.error("Please fill in all password fields")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            else:
                with st.spinner("Updating password..."):
                    # Get the auth manager
                    from expense_manager.auth.auth_manager import AuthManager

                    auth_manager = AuthManager()

                    # Update password
                    result = auth_manager.change_password(
                        user_id, current_password, new_password
                    )

                    if result.get("error"):
                        st.error(f"Failed to update password: {result['error']}")
                    else:
                        st.success("Password updated successfully!")
