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

    # Initialize database manager
    db_manager = DatabaseManager()

    # Get current user's profile ID
    user_id = (
        st.session_state.user.id
        if hasattr(st.session_state.user, "id")
        else st.session_state.user["id"]
    )
    profile_id = get_profile_id(db_manager, user_id)

    if not profile_id:
        st.error("Could not get your profile ID. Please try logging out and back in.")
        return

    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Display transfers list
        st.subheader("Recent Transfers")

        # Get date range for filtering
        today = datetime.now()
        six_months_ago = today - timedelta(days=180)
        start_date = six_months_ago.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        # Get transfers
        transfers_result = db_manager.get_transfers(profile_id, start_date, end_date)
        if "error" in transfers_result:
            st.error(f"Error getting transfers: {transfers_result['error']}")
            return

        transfers = transfers_result.get("transfers", [])

        if not transfers:
            st.info("No transfers found in the last 6 months.")
        else:
            # Convert to DataFrame for display
            df = pd.DataFrame(transfers)
            df["created_at"] = pd.to_datetime(df["created_at"])
            df["amount"] = df["amount"].apply(format_currency)

            # Display transfers in a table
            st.dataframe(
                df[["created_at", "source_name", "beneficiary_name", "amount"]],
                hide_index=True,
                column_config={
                    "created_at": "Date",
                    "source_name": "From",
                    "beneficiary_name": "To",
                    "amount": "Amount",
                },
            )

            # Add delete functionality
            st.subheader("Delete Transfer")

            # Create a mapping of transfer IDs to descriptive labels
            transfer_options = {}
            for transfer in transfers:
                date_str = datetime.fromisoformat(transfer["created_at"]).strftime(
                    "%Y-%m-%d"
                )
                amount_str = format_currency(transfer["amount"])
                source_name = transfer["source_name"]
                beneficiary_name = transfer["beneficiary_name"]

                # Create a descriptive label
                label = (
                    f"{date_str} - {source_name} → {beneficiary_name} - {amount_str}"
                )
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

    with col2:
        # Create new transfer form
        st.subheader("New Transfer")

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
        with st.form("transfer_form"):
            # Source selection (who is sending the money)
            source = st.selectbox(
                "From",
                options=list(profile_options.keys()),
                index=list(profile_options.keys()).index(current_user_display)
                if current_user_display
                else 0,
                key="transfer_source",
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
            )
            beneficiary_id = beneficiary_options[beneficiary]

            amount = st.number_input(
                "Amount",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                key="transfer_amount",
            )

            submitted = st.form_submit_button("Create Transfer")

            if submitted:
                if not source or not beneficiary or not amount:
                    st.error("Please fill in all fields")
                else:
                    result = db_manager.create_transfer(
                        source_id=source_id,
                        beneficiary_id=beneficiary_id,
                        amount=amount,
                    )

                    if "error" in result:
                        st.error(f"Error creating transfer: {result['error']}")
                    else:
                        st.success("Transfer created successfully!")
                        st.rerun()
