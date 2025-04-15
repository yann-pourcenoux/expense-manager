"""Transfer management page.

This module provides a Streamlit page for managing transfers between users,
including creating, viewing, and deleting transfer records.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from expense_manager.db.db_manager import DatabaseManager
from expense_manager.utils.models import format_currency


def get_profile_id(db_manager: DatabaseManager, user_uuid: str) -> int | None:
    """Get profile ID from user UUID.

    Args:
        db_manager (DatabaseManager): Database manager instance
        user_uuid (str): User UUID from auth.users

    Returns:
        int | None: Profile ID if found, None otherwise
    """
    profile_result = db_manager.get_profile(user_uuid)
    if "error" in profile_result:
        st.error(f"Error getting profile: {profile_result['error']}")
        return None
    return profile_result.get("profile", {}).get("id")


def display_transfer_manager() -> None:
    """Display the transfer management interface."""
    st.title("💰 Transfers")

    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to manage your transfers.")
        return

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get user UUID from session
    user_uuid = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )

    # Get profile ID from user UUID
    profile_id = get_profile_id(db_manager, user_uuid)
    if profile_id is None:
        st.error("Could not find your profile. Please try logging in again.")
        return

    # Initialize session state if not exists
    if "transfer_filter_start_date" not in st.session_state:
        st.session_state.transfer_filter_start_date = (
            datetime.now() - timedelta(days=30)
        ).date()
    if "transfer_filter_end_date" not in st.session_state:
        st.session_state.transfer_filter_end_date = datetime.now().date()

    # Display transfers interface
    st.subheader("Transfers")
    tabs = st.tabs(["Add Transfer", "View Transfers"])

    # Add Transfer tab
    with tabs[0]:
        display_add_transfer_form(db_manager, profile_id)

    # View Transfers tab
    with tabs[1]:
        display_transfer_list(db_manager, profile_id)


def display_add_transfer_form(db_manager: DatabaseManager, profile_id: int) -> None:
    """Display form for adding a new transfer.

    Args:
        db_manager (DatabaseManager): Database manager instance
        profile_id (int): ID of the current user's profile
    """
    st.header("Add New Transfer")

    # Get all profiles for selection
    profiles_result = db_manager.get_all_profiles()
    if "error" in profiles_result:
        st.error(f"Error getting profiles: {profiles_result['error']}")
        return

    profiles = profiles_result.get("profiles", [])

    # Create options for source and beneficiary dropdowns
    profile_options = {f"{p['display_name']}": p["id"] for p in profiles}

    # Find the current user's display name for default selection
    current_user_display = None
    for display_name, pid in profile_options.items():
        if pid == profile_id:
            current_user_display = display_name
            break

    # Transfer form
    with st.form("transfer_form", clear_on_submit=True):
        # Source selection (who is sending the money)
        source = st.selectbox(
            "From",
            options=list(profile_options.keys()),
            index=list(profile_options.keys()).index(current_user_display)
            if current_user_display
            else 0,
            key="transfer_source",
            help="Who is sending the money?",
        )
        source_id = profile_options[source]

        # Beneficiary selection (who is receiving the money)
        beneficiary_options = {name: pid for name, pid in profile_options.items()}

        # If the current user is the source, default to the other user
        if source_id == profile_id and len(beneficiary_options) > 0:
            default_beneficiary = next(iter(beneficiary_options.keys()))
        else:
            default_beneficiary = None

        beneficiary = st.selectbox(
            "To",
            options=list(beneficiary_options.keys()),
            index=0
            if default_beneficiary is None
            else list(beneficiary_options.keys()).index(default_beneficiary),
            key="transfer_beneficiary",
            help="Who is receiving the money?",
        )
        beneficiary_id = beneficiary_options[beneficiary]

        # Date field
        date = st.date_input(
            "Date",
            value=datetime.now(),
            help="When did this transfer happen?",
        )

        amount = st.number_input(
            "Amount",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            key="transfer_amount",
            help="How much money is being transferred?",
        )

        submitted = st.form_submit_button("Create Transfer")

        if submitted:
            if not source or not beneficiary or not amount:
                st.error("Please fill in all required fields")
            else:
                # Convert date input to datetime
                transfer_date = datetime.combine(date, datetime.min.time())

                result = db_manager.create_transfer(
                    source_id=source_id,
                    beneficiary_id=beneficiary_id,
                    amount=amount,
                    date=transfer_date,
                )

                if "error" in result:
                    st.error(f"Error creating transfer: {result['error']}")
                else:
                    st.success("Transfer created successfully!")


def display_transfer_list(db_manager: DatabaseManager, profile_id: int) -> None:
    """Display a list of transfers with filtering options.

    Args:
        db_manager (DatabaseManager): Database manager instance
        profile_id (int): ID of the current user's profile
    """
    st.header("Your Transfers")

    # Get transfers
    transfers_result = db_manager.get_transfers()
    if "error" in transfers_result:
        st.error(f"Error getting transfers: {transfers_result['error']}")
        return

    transfers = transfers_result.get("transfers", [])

    if not transfers:
        st.info(
            "No transfers found for the selected date range. Add some transfers to get "
            "started!"
        )
        return

    # Convert to DataFrame for display
    df = pd.DataFrame(transfers)
    df["amount"] = df["amount"].apply(format_currency)

    # Get all profiles for display in expense list
    profiles_result = db_manager.get_all_profiles()
    profiles = profiles_result.get("profiles", [])

    # Create a mapping of profile IDs to display names
    profile_names = {p["id"]: p["display_name"] for p in profiles}

    if profile_names:
        df["source_name"] = df["source_id"].map(profile_names)
        df["source_name"] = df["source_name"].fillna("Unknown")
        df["beneficiary_name"] = df["beneficiary_id"].map(profile_names)
        df["beneficiary_name"] = df["beneficiary_name"].fillna("Unknown")

    # Display transfers in a table
    st.dataframe(
        df[["date", "source_name", "beneficiary_name", "amount"]],
        hide_index=True,
        column_config={
            "date": "Date",
            "source_name": "From",
            "beneficiary_name": "To",
            "amount": "Amount",
        },
        use_container_width=True,
    )

    # Delete functionality
    st.subheader("Delete Transfer")

    # Create a mapping of transfer IDs to descriptive labels
    transfer_options = {}
    for transfer in transfers:
        date_str = pd.to_datetime(transfer["date"]).strftime("%Y-%m-%d")
        amount_str = format_currency(transfer["amount"])
        source_name = profile_names[transfer["source_id"]]
        beneficiary_name = profile_names[transfer["beneficiary_id"]]

        # Create a descriptive label
        label = f"{date_str} - {source_name} → {beneficiary_name} - {amount_str}"

        transfer_options[label] = transfer["id"]

    # Select transfer to delete
    selected_transfer_label = st.selectbox(
        "Select Transfer to Delete", options=list(transfer_options.keys())
    )
    selected_transfer_id = transfer_options[selected_transfer_label]

    # Delete button
    if st.button(
        "Delete Transfer", type="primary", help="This action cannot be undone"
    ):
        result = db_manager.delete_transfer(
            transfer_id=selected_transfer_id, user_id=profile_id
        )
        if "error" in result:
            st.error(f"Error deleting transfer: {result['error']}")
        else:
            st.success("Transfer deleted successfully!")
            # Refresh the page
            st.rerun()
