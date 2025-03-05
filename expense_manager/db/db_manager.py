"""Database manager for interacting with Supabase database.

This module handles all interactions with the Supabase database for expense data,
including creating, reading, updating, and deleting expenses.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()


class DatabaseManager:
    """Manager for Supabase database operations.

    This class handles all database operations related to expenses, including
    creating, reading, updating, and deleting expense records.
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
        self.expenses_table = "expenses"
        self.categories_table = "categories"
        self.profiles_table = "profiles"

    def create_expense(
        self,
        user_id: int,
        amount: float,
        category_id: str,
        date: datetime,
        name: str,
        payer_id: int,
        description: str = "",
        is_shared: bool = False,
        split_with_users: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Create a new expense record.

        Args:
            user_id (int): ID of the user creating the expense (reporter)
            amount (float): Amount of the expense
            category_id (str): ID of the expense category
            date (datetime): Date of the expense
            name (str): Name of the expense
            payer_id (int): ID of the user who paid for the expense
            description (str, optional): Description of the expense. Defaults to "".
            is_shared (bool, optional): Whether this expense is shared.
                Defaults to False.
            split_with_users (List[int] | None): List of user IDs to split with.
                Defaults to None.

        Returns:
            Dict[str, Any]: Response containing created expense or error
        """
        try:
            # Convert string IDs to their appropriate types
            # For category_id, convert string to int since it's an int8 in the database
            try:
                # Convert category_id to integer if it's a numeric string
                int_category_id = int(category_id)
            except ValueError:
                return {"error": f"Invalid category ID format: {category_id}"}

            data = (
                self.client.table(self.expenses_table)
                .insert(
                    {
                        "reporter_id": user_id,  # int8 type
                        "payer_id": payer_id,  # int8 type
                        "amount": amount,
                        "category_id": int_category_id,  # int8 type
                        "date": date.isoformat(),
                        "name": name,
                        "description": description,
                        "is_shared": is_shared,
                    }
                )
                .execute()
            )

            if not data.data:
                return {"error": "Failed to create expense"}

            expense = data.data[0]
            expense_id = expense["id"]

            # If expense is shared, create expense split records
            if is_shared and split_with_users:
                # Add the expense creator to the split as well
                if user_id not in split_with_users:
                    split_with_users.append(user_id)

                split_records = []
                for split_user_id in split_with_users:
                    split_records.append(
                        {"expense_id": expense_id, "user_id": split_user_id}
                    )

                if split_records:
                    split_data = (
                        self.client.table("expenses_split")
                        .insert(split_records)
                        .execute()
                    )

                    if not split_data.data:
                        # If split creation fails, we should still return the expense
                        # but with a warning
                        return {
                            "expense": expense,
                            "warning": "Expense created but split records failed",
                        }

            return {"expense": expense}

        except Exception as e:
            return {"error": str(e)}

    def get_expenses(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[str] = None,
        include_shared: bool = True,
    ) -> Dict[str, Any]:
        """Get expenses for a user with optional filters.

        Args:
            user_id (int): ID of the user
            start_date (datetime | None, optional): Start date filter. Defaults to None.
            end_date (datetime | None, optional): End date filter. Defaults to None.
            category_id (str | None, optional): Category ID filter. Defaults to None.
            include_shared (bool, optional): Whether to include shared expenses.
                Defaults to True.

        Returns:
            Dict[str, Any]: Dictionary containing expenses or error
        """
        try:
            # First get all expenses where the user is the reporter
            query = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("reporter_id", user_id)
            )

            if start_date:
                query = query.gte("date", start_date.isoformat())

            if end_date:
                query = query.lte("date", end_date.isoformat())

            if category_id:
                try:
                    # Convert category_id to integer
                    int_category_id = int(category_id)
                    query = query.eq("category_id", int_category_id)
                except ValueError:
                    return {"error": f"Invalid category ID format: {category_id}"}

            direct_expenses_data = query.execute()

            # If shared expenses are requested, get all expenses where user is part of
            # the split
            shared_expenses = []
            if include_shared:
                shared_query = (
                    self.client.table("expenses_split")
                    .select("expense_id")
                    .eq("user_id", user_id)
                    .execute()
                )

                if shared_query.data:
                    # Get all expense IDs that the user is part of
                    shared_expense_ids = [
                        item["expense_id"] for item in shared_query.data
                    ]

                    # Get the actual expense details
                    if shared_expense_ids:
                        in_query = (
                            self.client.table(self.expenses_table)
                            .select("*")
                            .in_("id", shared_expense_ids)
                        )

                        if start_date:
                            in_query = in_query.gte("date", start_date.isoformat())

                        if end_date:
                            in_query = in_query.lte("date", end_date.isoformat())

                        if category_id:
                            in_query = in_query.eq("category_id", category_id)

                        shared_expenses_data = in_query.execute()

                        if shared_expenses_data.data:
                            # Only add expenses where the user is not the reporter to
                            # void duplicates
                            shared_expenses = [
                                exp
                                for exp in shared_expenses_data.data
                                if exp["reporter_id"] != user_id
                            ]

            # Combine direct and shared expenses
            all_expenses = (
                direct_expenses_data.data + shared_expenses
                if direct_expenses_data.data
                else shared_expenses
            )

            return {"expenses": all_expenses}

        except Exception as e:
            return {"error": str(e)}

    def update_expense(
        self, expense_id: int, user_id: int, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing expense record.

        Args:
            expense_id (int): ID of the expense to update
            user_id (int): ID of the user who owns the expense
            updates (Dict[str, Any]): Dictionary of fields to update

        Returns:
            Dict[str, Any]: Dictionary containing updated expense or error
        """
        try:
            # Ensure the expense belongs to the user
            expense_check = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("id", expense_id)
                .eq("reporter_id", user_id)  # Using reporter_id instead of user_id
                .execute()
            )

            if not expense_check.data:
                return {"error": "Expense not found or unauthorized"}

            # Process updates to ensure correct data types
            processed_updates = updates.copy()

            # If date is in updates and is a datetime, convert to string
            if "date" in processed_updates and isinstance(
                processed_updates["date"], datetime
            ):
                processed_updates["date"] = processed_updates["date"].isoformat()

            # If category_id is in updates, convert to integer
            if "category_id" in processed_updates:
                try:
                    processed_updates["category_id"] = int(
                        processed_updates["category_id"]
                    )
                except ValueError:
                    return {
                        "error": f"Invalid category ID format: {processed_updates['category_id']}"
                    }

            # Handle payer_id special case
            if "payer_id" in processed_updates and processed_updates["payer_id"] == 1:
                processed_updates["payer_id"] = user_id

            data = (
                self.client.table(self.expenses_table)
                .update(processed_updates)
                .eq("id", expense_id)
                .eq("reporter_id", user_id)  # Using reporter_id instead of user_id
                .execute()
            )

            if data.data:
                return {"expense": data.data[0]}
            return {"error": "Failed to update expense"}

        except Exception as e:
            return {"error": str(e)}

    def delete_expense(self, expense_id: int, user_id: int) -> Dict[str, Any]:
        """Delete an expense record.

        Args:
            expense_id (int): ID of the expense to delete
            user_id (int): ID of the user who owns the expense

        Returns:
            Dict[str, Any]: Dictionary containing result or error
        """
        try:
            # Ensure the expense belongs to the user
            expense_check = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("id", expense_id)
                .eq("reporter_id", user_id)  # Using reporter_id instead of user_id
                .execute()
            )

            if not expense_check.data:
                return {"error": "Expense not found or unauthorized"}

            data = (
                self.client.table(self.expenses_table)
                .delete()
                .eq("id", expense_id)
                .eq("reporter_id", user_id)  # Using reporter_id instead of user_id
                .execute()
            )

            if data.data:
                return {"success": True, "message": "Expense deleted successfully"}
            return {"error": "Failed to delete expense"}

        except Exception as e:
            return {"error": str(e)}

    def get_categories(self) -> Dict[str, Any]:
        """Get all available expense categories.

        Returns:
            Dict[str, Any]: Dictionary containing categories or error
        """
        try:
            data = self.client.table(self.categories_table).select("*").execute()

            if data.data is not None:
                return {"categories": data.data}
            return {"error": "Failed to fetch categories"}

        except Exception as e:
            return {"error": str(e)}

    def create_category(self, name: str, color: str | None = None) -> Dict[str, Any]:
        """Create a new expense category.

        Args:
            name (str): Name of the category
            color (str | None, optional): Color for the category. Defaults to None.
                If None, no color will be assigned in the database.

        Returns:
            Dict[str, Any]: Dictionary containing created category or error
        """
        try:
            category_data = {"name": name}
            # Only include color if specified
            if color:
                category_data["color"] = color

            data = (
                self.client.table(self.categories_table).insert(category_data).execute()
            )

            if data.data:
                return {"category": data.data[0]}
            return {"error": "Failed to create category"}

        except Exception as e:
            return {"error": str(e)}

    def get_expense_splits(self, expense_id: int) -> Dict[str, Any]:
        """Get all users who are part of an expense split.

        Args:
            expense_id (int): ID of the expense

        Returns:
            Dict[str, Any]: Dictionary containing split user IDs or error
        """
        try:
            data = (
                self.client.table("expenses_split")
                .select("user_id")
                .eq("expense_id", expense_id)
                .execute()
            )

            if data.data is not None:
                user_ids = [item["user_id"] for item in data.data]
                return {"user_ids": user_ids}
            return {"error": "Failed to fetch expense splits"}

        except Exception as e:
            return {"error": str(e)}

    def update_expense_splits(
        self, expense_id: int, user_id: int, split_with_users: List[int]
    ) -> Dict[str, Any]:
        """Update the users who are part of an expense split.

        Args:
            expense_id (int): ID of the expense
            user_id (int): ID of the user who owns the expense
            split_with_users (List[int]): List of user IDs to split with

        Returns:
            Dict[str, Any]: Dictionary containing result or error
        """
        try:
            # Ensure the expense belongs to the user
            expense_check = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("id", expense_id)
                .eq("reporter_id", user_id)
                .execute()
            )

            if not expense_check.data:
                return {"error": "Expense not found or unauthorized"}

            # Delete existing splits
            delete_data = (
                self.client.table("expenses_split")
                .delete()
                .eq("expense_id", expense_id)
                .execute()
            )

            # Only continue if deletion was successful or there were no records
            # to delete
            if delete_data.data is not None or not delete_data.data:
                # Add the expense creator to the split as well
                if user_id not in split_with_users:
                    split_with_users.append(user_id)

                # Create new split records
                split_records = []
                for split_user_id in split_with_users:
                    split_records.append(
                        {"expense_id": expense_id, "user_id": split_user_id}
                    )

                if split_records:
                    insert_data = (
                        self.client.table("expenses_split")
                        .insert(split_records)
                        .execute()
                    )

                    if insert_data.data:
                        return {
                            "success": True,
                            "message": "Expense splits updated successfully",
                        }

            return {"error": "Failed to update expense splits"}

        except Exception as e:
            return {"error": str(e)}

    def get_monthly_income(
        self, user_id: int, month_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get monthly income for a user.

        Args:
            user_id (int): ID of the user
            month_date (datetime | None, optional): Month to get income for.
                Defaults to current month.

        Returns:
            Dict[str, Any]: Dictionary containing income record or error
        """
        try:
            if not month_date:
                month_date = datetime.now().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                # Ensure we're using the first day of the month
                month_date = month_date.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )

            data = (
                self.client.table("monthly_income")
                .select("*")
                .eq("user_id", user_id)
                .eq("month_date", month_date.isoformat())
                .execute()
            )

            if data.data:
                return {"income": data.data[0]}
            return {"income": None}  # No income record found for this month

        except Exception as e:
            return {"error": str(e)}

    def set_monthly_income(
        self, user_id: int, amount: float, month_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Set or update monthly income for a user.

        Args:
            user_id (int): ID of the user
            amount (float): Income amount
            month_date (datetime | None, optional): Month to set income for.
                Defaults to current month.

        Returns:
            Dict[str, Any]: Dictionary containing income record or error
        """
        try:
            if not month_date:
                month_date = datetime.now().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                # Ensure we're using the first day of the month
                month_date = month_date.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )

            # Check if there's already an income record for this month
            existing_data = (
                self.client.table("monthly_income")
                .select("id")
                .eq("user_id", user_id)
                .eq("month_date", month_date.isoformat())
                .execute()
            )

            if existing_data.data:
                # Update existing record
                income_id = existing_data.data[0]["id"]
                data = (
                    self.client.table("monthly_income")
                    .update({"amount": amount})
                    .eq("id", income_id)
                    .execute()
                )
            else:
                # Create new record
                data = (
                    self.client.table("monthly_income")
                    .insert(
                        {
                            "user_id": user_id,
                            "amount": amount,
                            "month_date": month_date.isoformat(),
                        }
                    )
                    .execute()
                )

            if data.data:
                return {"income": data.data[0]}
            return {"error": "Failed to set monthly income"}

        except Exception as e:
            return {"error": str(e)}

    def get_income_history(self, user_id: int, limit: int = 12) -> Dict[str, Any]:
        """Get income history for a user.

        Args:
            user_id (int): ID of the user
            limit (int, optional): Maximum number of records to return. Defaults to 12.

        Returns:
            Dict[str, Any]: Dictionary containing income history or error
        """
        try:
            data = (
                self.client.table("monthly_income")
                .select("*")
                .eq("user_id", user_id)
                .order("month_date", desc=True)
                .limit(limit)
                .execute()
            )

            if data.data is not None:
                return {"income_history": data.data}
            return {"error": "Failed to fetch income history"}

        except Exception as e:
            return {"error": str(e)}

    def update_category(
        self, category_id: int, name: str, color: str | None = None
    ) -> Dict[str, Any]:
        """Update an existing expense category.

        Args:
            category_id (int): ID of the category to update
            name (str): New name for the category
            color (str | None, optional): New color for the category. Defaults to None.
                If None, color will not be updated.

        Returns:
            Dict[str, Any]: Dictionary containing updated category or error
        """
        try:
            update_data = {"name": name}
            # Only include color if specified
            if color is not None:
                update_data["color"] = color

            data = (
                self.client.table(self.categories_table)
                .update(update_data)
                .eq("id", category_id)
                .execute()
            )

            if data.data:
                return {"category": data.data[0]}
            return {"error": "Failed to update category"}

        except Exception as e:
            return {"error": str(e)}

    def delete_category(self, category_id: int) -> Dict[str, Any]:
        """Delete a category.

        Args:
            category_id (int): ID of the category to delete

        Returns:
            Dict[str, Any]: Dictionary containing result or error
        """
        try:
            # Check if there are any expenses using this category
            expenses_check = (
                self.client.table(self.expenses_table)
                .select("count", count="exact")
                .eq("category_id", category_id)
                .execute()
            )

            if expenses_check.count > 0:
                return {
                    "error": f"Cannot delete category. It's used by "
                    f"{expenses_check.count} expenses."
                }

            # Delete the category
            data = (
                self.client.table(self.categories_table)
                .delete()
                .eq("id", category_id)
                .execute()
            )

            if data.data:
                return {"success": True, "message": "Category deleted successfully"}
            return {"error": "Failed to delete category"}

        except Exception as e:
            return {"error": str(e)}

    def create_profile(
        self, user_id: str, display_name: str | None = None
    ) -> Dict[str, Any]:
        """Create a new user profile record.

        Args:
            user_id (str): ID of the user (from auth.users)
            display_name (str | None, optional): Display name for the user.
                Defaults to None, which will use a default name format.

        Returns:
            Dict[str, Any]: Response containing created profile or error
        """
        try:
            # If display_name is not provided, use a default based on user ID
            if not display_name:
                # Just use a default format based on user_id
                # This avoids the need to query the auth API
                display_name = (
                    f"User_{user_id[:8]}"  # First 8 chars of UUID as fallback
                )

            data = (
                self.client.table(self.profiles_table)
                .insert(
                    {
                        "user_id": user_id,
                        "display_name": display_name,
                    }
                )
                .execute()
            )

            if not data.data:
                return {"error": "Failed to create user profile"}

            return {"profile": data.data[0]}

        except Exception as e:
            return {"error": str(e)}

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get a user profile by user ID.

        Args:
            user_id (str): ID of the user (from auth.users)

        Returns:
            Dict[str, Any]: Response containing profile or error
        """
        try:
            data = (
                self.client.table(self.profiles_table)
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            if data.data and len(data.data) > 0:
                return {"profile": data.data[0]}

            return {"profile": None}

        except Exception as e:
            return {"error": str(e)}

    def update_profile(self, user_id: str, display_name: str) -> Dict[str, Any]:
        """Update a user profile.

        Args:
            user_id (str): ID of the user (from auth.users)
            display_name (str): New display name for the user

        Returns:
            Dict[str, Any]: Response containing updated profile or error
        """
        try:
            # Check if profile exists
            existing_profile = self.get_profile(user_id)

            if existing_profile.get("error"):
                return existing_profile

            if existing_profile.get("profile"):
                # Update existing profile
                profile_id = existing_profile["profile"]["id"]
                data = (
                    self.client.table(self.profiles_table)
                    .update({"display_name": display_name})
                    .eq("id", profile_id)
                    .execute()
                )

                if data.data:
                    return {"profile": data.data[0]}
                return {"error": "Failed to update profile"}
            else:
                # Create new profile
                return self.create_profile(user_id, display_name)

        except Exception as e:
            return {"error": str(e)}

    def get_all_profiles(self) -> Dict[str, Any]:
        """Get all user profiles from the database.

        Returns:
            Dict[str, Any]: Dictionary containing all profiles or error
        """
        try:
            data = self.client.table(self.profiles_table).select("*").execute()

            if data.data is not None:
                return {"profiles": data.data}
            return {"profiles": []}

        except Exception as e:
            return {"error": str(e)}
