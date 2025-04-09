"""Payment source management page.

This module provides a Streamlit page for managing payment sources, including
adding, editing, and deleting payment sources.
"""

from typing import Any, Dict

import streamlit as st

from expense_manager.db.db_manager import DatabaseManager


def display_payment_source_manager() -> None:
    """Display the payment source management interface."""
    st.title("Manage Payment Sources")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to manage payment sources.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user ID from session
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Initialize session state variables if not exist
    if "editing_payment_source_id" not in st.session_state:
        st.session_state.editing_payment_source_id = None
    if "editing_payment_source" not in st.session_state:
        st.session_state.editing_payment_source = None
    if "deleting_payment_source_id" not in st.session_state:
        st.session_state.deleting_payment_source_id = None
    if "deleting_payment_source_name" not in st.session_state:
        st.session_state.deleting_payment_source_name = None
    if "payment_source_added" not in st.session_state:
        st.session_state.payment_source_added = False

    # Show success message if payment source was added
    if st.session_state.payment_source_added:
        st.success("Payment source created successfully!")
        st.session_state.payment_source_added = False

    # Display add payment source form
    display_add_payment_source_form(db_manager, user_id)

    # Add a separator between sections
    st.markdown("---")

    # Display payment source list below
    display_payment_source_list(db_manager, user_id)


def set_edit_payment_source(
    payment_source_id: str, payment_source: Dict[str, Any]
) -> None:
    """Set the payment source to edit in session state.

    Args:
        payment_source_id (str): ID of the payment source to edit
        payment_source (Dict[str, Any]): Payment source data
    """
    st.session_state.editing_payment_source_id = payment_source_id
    st.session_state.editing_payment_source = payment_source


def set_delete_payment_source(payment_source_id: str, payment_source_name: str) -> None:
    """Set the payment source to delete in session state.

    Args:
        payment_source_id (str): ID of the payment source to delete
        payment_source_name (str): Name of the payment source
    """
    st.session_state.deleting_payment_source_id = payment_source_id
    st.session_state.deleting_payment_source_name = payment_source_name


def clear_edit_state() -> None:
    """Clear the edit state in session state."""
    st.session_state.editing_payment_source_id = None
    st.session_state.editing_payment_source = None


def clear_delete_state() -> None:
    """Clear the delete state in session state."""
    st.session_state.deleting_payment_source_id = None
    st.session_state.deleting_payment_source_name = None


def display_add_payment_source_form(db_manager: DatabaseManager, user_id: str) -> None:
    """Display form for adding a new payment source.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_id (str): ID of the current user
    """
    st.header("Add New Payment Source")

    with st.form("add_payment_source_form"):
        # Payment source name
        payment_source_name = st.text_input(
            "Payment Source Name",
            help=(
                "Enter a descriptive name for the payment source (e.g., 'Cash', "
                "'Credit Card', 'Bank Account')"
            ),
        )

        # Submit button
        submitted = st.form_submit_button("Add Payment Source")

        if submitted:
            if not payment_source_name:
                st.error("Payment source name is required.")
                return

            # Create payment source
            result = db_manager.create_payment_source(payment_source_name, user_id)

            if "error" in result:
                st.error(f"Error creating payment source: {result['error']}")
            else:
                # Set flag for success message on next rerun
                st.session_state.payment_source_added = True
                # Clear the form
                st.session_state.add_payment_source_name = ""
                st.rerun()


def display_payment_source_list(db_manager: DatabaseManager, user_id: str) -> None:
    """Display a list of payment sources with edit/delete options.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_id (str): ID of the current user
    """
    st.header("Your Payment Sources")

    # Get all payment sources
    payment_sources_result = db_manager.get_payment_sources(user_id)
    payment_sources = payment_sources_result.get("payment_sources", [])

    if not payment_sources:
        st.info("No payment sources found. Add some payment sources to get started!")
        return

    # Calculate columns based on number of payment sources (3 columns by default)
    num_columns = 3
    columns = st.columns(num_columns)

    # Display each payment source in card-like format
    for i, payment_source in enumerate(payment_sources):
        col_idx = i % num_columns
        with columns[col_idx]:
            with st.container(border=True):
                # Display in a simple format
                st.write(f"**{payment_source['name']}**")

                # Edit button with callback
                if st.button("Edit", key=f"edit_{payment_source['id']}"):
                    set_edit_payment_source(payment_source["id"], payment_source)

                # Delete button with callback
                if st.button("Delete", key=f"delete_{payment_source['id']}"):
                    set_delete_payment_source(
                        payment_source["id"], payment_source["name"]
                    )

    # Handle payment source editing
    if st.session_state.editing_payment_source_id:
        display_edit_payment_source_form(
            db_manager, st.session_state.editing_payment_source
        )

    # Handle payment source deletion with confirmation
    if st.session_state.deleting_payment_source_id:
        st.warning(
            f"Are you sure you want to delete the payment source "
            f"'{st.session_state.deleting_payment_source_name}'? This cannot be undone."
        )
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Yes, Delete"):
                result = db_manager.delete_payment_source(
                    st.session_state.deleting_payment_source_id
                )

                if "error" in result:
                    st.error(f"Error deleting payment source: {result['error']}")
                else:
                    st.toast("Payment source deleted successfully!")
                    clear_delete_state()
                    st.rerun()

        with col2:
            if st.button("Cancel"):
                clear_delete_state()
                st.rerun()


def display_edit_payment_source_form(
    db_manager: DatabaseManager, payment_source: Dict[str, Any]
) -> None:
    """Display form for editing an existing payment source.

    Args:
        db_manager (DatabaseManager): Database manager instance
        payment_source (Dict[str, Any]): Payment source data to edit
    """
    st.subheader(f"Edit Payment Source: {payment_source['name']}")

    with st.form("edit_payment_source_form"):
        # Payment source name
        payment_source_name = st.text_input(
            "Payment Source Name",
            value=payment_source["name"],
            help="Enter a descriptive name for the payment source",
        )

        # Submit button
        submitted = st.form_submit_button("Update Payment Source")

        if submitted:
            if not payment_source_name:
                st.error("Payment source name is required.")
                return

            # Update payment source
            result = db_manager.update_payment_source(
                payment_source_id=payment_source["id"], name=payment_source_name
            )

            if "error" in result:
                st.error(f"Error updating payment source: {result['error']}")
            else:
                st.success("Payment source updated successfully!")
                clear_edit_state()
                st.rerun()

    # Cancel button outside the form
    if st.button("Cancel Editing"):
        clear_edit_state()
        st.rerun()
