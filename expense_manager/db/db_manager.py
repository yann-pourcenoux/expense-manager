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

        # Assert that there are only two users
        assert (
            len(self.client.table(self.profiles_table).select("*").execute().data) == 2
        ), "This works only with two users in the household."

    def add_expense(
        self,
        reporter_id: int,
        amount: float,
        category_id: int,
        date: datetime,
        name: str,
        payer_id: int,
        description: str = "",
        is_shared: bool = False,
        beneficiary_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a new expense to the database."""
        # 1. Create the expense
        expense_data = {
            "reporter_id": reporter_id,
            "payer_id": payer_id,
            "amount": amount,
            "category_id": category_id,
            "date": date.isoformat(),
            "name": name,
            "description": description,
            "is_shared": is_shared,
            "beneficiary_id": beneficiary_id,
        }

        data = self.client.table(self.expenses_table).insert(expense_data).execute()

        if not data.data:
            raise Exception("Failed to create expense")

        expense = data.data[0]
        expense_id = expense["id"]

        # 2. Create the record in the split table
        if not is_shared:
            split_with_users = [beneficiary_id]
        else:
            # Select all profiles
            split_with_users = [
                profile["id"] for profile in self.get_all_profiles()["profiles"]
            ]

        expense_split_data = [
            {
                "expense_id": expense_id,
                "user_id": user_id,
                "amount": amount / len(split_with_users),
            }
            for user_id in split_with_users
        ]
        for expense_split in expense_split_data:
            data = self.client.table("expenses_split").insert(expense_split).execute()
            if not data.data:
                raise Exception("Failed to create expense split")
        return expense

    def get_expenses_for_balance(self) -> list[dict]:
        """"""

        expenses = self.client.table(self.expenses_table).select("*").execute()

        if expenses.data is not None:
            expenses = [
                expense
                for expense in expenses.data
                if expense["is_shared"]
                or expense["payer_id"] != expense["beneficiary_id"]
            ]

        return expenses

    def get_expenses_for_list(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
    ) -> list[dict]:
        """"""

        # Select the expenses that:
        # - are shared
        # - the user is the payer
        # - the user is the beneficiary
        shared_expenses = (
            self.client.table(self.expenses_table).select("*").eq("is_shared", True)
        )

        payer_expenses = (
            self.client.table(self.expenses_table).select("*").eq("payer_id", user_id)
        )

        beneficiary_expenses = (
            self.client.table(self.expenses_table)
            .select("*")
            .eq("beneficiary_id", user_id)
        )

        # Apply common filters to each query
        if start_date is not None:
            shared_expenses = shared_expenses.gte("date", start_date.isoformat())
            payer_expenses = payer_expenses.gte("date", start_date.isoformat())
            beneficiary_expenses = beneficiary_expenses.gte(
                "date", start_date.isoformat()
            )

        if end_date is not None:
            shared_expenses = shared_expenses.lte("date", end_date.isoformat())
            payer_expenses = payer_expenses.lte("date", end_date.isoformat())
            beneficiary_expenses = beneficiary_expenses.lte(
                "date", end_date.isoformat()
            )

        if category_id is not None:
            shared_expenses = shared_expenses.eq("category_id", category_id)
            payer_expenses = payer_expenses.eq("category_id", category_id)
            beneficiary_expenses = beneficiary_expenses.eq("category_id", category_id)

        # Execute the queries
        shared_result = shared_expenses.execute()
        payer_result = payer_expenses.execute()
        beneficiary_result = beneficiary_expenses.execute()

        # Combine and deduplicate results
        all_expenses = []
        expense_ids = set()

        for result in [shared_result, payer_result, beneficiary_result]:
            if result.data:
                for expense in result.data:
                    if expense["id"] not in expense_ids:
                        all_expenses.append(expense)
                        expense_ids.add(expense["id"])

        return all_expenses

    def update_expense(
        self,
        expense_id: int,
        user_id: int,
        updates: Dict[str, Any],
        split_with_users: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Update an existing expense record.

        Args:
            expense_id (int): ID of the expense to update
            user_id (int): ID of the user making the update
            updates (Dict[str, Any]): Dictionary of fields to update
            split_with_users (List[int] | None): List of user IDs to split the
                expense with. Only used if is_shared is true. Defaults to None.

        Returns:
            Dict[str, Any]: Dictionary containing updated expense or error
        """
        try:
            # Get the expense to update
            expense_check = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("id", expense_id)
                .execute()
            )

            if not expense_check.data:
                return {"error": "Expense not found"}

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
                        "error": (
                            f"Invalid category ID format: "
                            f"{processed_updates['category_id']}"
                        )
                    }

            # Handle payer_id special case
            if "payer_id" in processed_updates and processed_updates["payer_id"] == 1:
                processed_updates["payer_id"] = user_id

            # Update the expense record
            data = (
                self.client.table(self.expenses_table)
                .update(processed_updates)
                .eq("id", expense_id)
                .execute()
            )

            if not data.data:
                return {"error": "Failed to update expense"}

            # If the expense is shared and we have split_with_users, update the splits
            is_shared = processed_updates.get(
                "is_shared", expense_check.data[0].get("is_shared", False)
            )
            if is_shared and split_with_users is not None:
                # Update the expense splits
                self.update_expense_splits(expense_id, user_id, split_with_users)

            return {"expense": data.data[0]}

        except Exception as e:
            return {"error": str(e)}

    def delete_expense(self, expense_id: int, user_id: int) -> Dict[str, Any]:
        """Delete an expense record.

        Args:
            expense_id (int): ID of the expense to delete
            user_id (int): ID of the user making the deletion

        Returns:
            Dict[str, Any]: Dictionary containing result or error
        """
        try:
            # Get expense to delete
            expense_check = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("id", expense_id)
                .execute()
            )

            if not expense_check.data:
                return {"error": "Expense not found"}

            # Delete the expense
            data = (
                self.client.table(self.expenses_table)
                .delete()
                .eq("id", expense_id)
                .execute()
            )

            if data.data:
                # Also delete any splits associated with this expense
                self.client.table("expenses_split").delete().eq(
                    "expense_id", expense_id
                ).execute()
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
            Dict[str, Any]: Dictionary containing split user IDs, amounts, or error
        """
        try:
            data = (
                self.client.table("expenses_split")
                .select("*")  # Select all fields to get amount also
                .eq("expense_id", expense_id)
                .execute()
            )

            if data.data is not None:
                # Return both user IDs and their split amounts
                user_ids = [item["user_id"] for item in data.data]
                split_details = [
                    {"user_id": item["user_id"], "amount": item.get("amount", 0)}
                    for item in data.data
                ]
                return {"user_ids": user_ids, "split_details": split_details}
            return {"error": "Failed to fetch expense splits"}

        except Exception as e:
            return {"error": str(e)}

    def update_expense_splits(
        self, expense_id: int, user_id: int, split_with_users: List[int]
    ) -> Dict[str, Any]:
        """Update the users who are part of an expense split.

        Args:
            expense_id (int): ID of the expense
            user_id (int): ID of the user making the update
            split_with_users (List[int]): List of user IDs to split with

        Returns:
            Dict[str, Any]: Dictionary containing result or error
        """
        try:
            # Get the expense to update
            expense_check = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("id", expense_id)
                .execute()
            )

            if not expense_check.data:
                return {"error": "Expense not found"}

            # Get the expense amount for splitting
            expense_amount = expense_check.data[0].get("amount", 0)

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

                # Calculate per-person split amount (evenly distributed)
                per_person_amount = round(expense_amount / len(split_with_users), 2)

                # Create new split records
                split_records = []
                for split_user_id in split_with_users:
                    split_records.append(
                        {
                            "expense_id": expense_id,
                            "user_id": split_user_id,
                            "amount": per_person_amount,
                        }  # Store the split amount for each user
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
                # Check if it's a date object (not datetime)
                if hasattr(month_date, "hour"):
                    # It's a datetime object
                    month_date = month_date.replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )
                else:
                    # It's a date object
                    month_date = month_date.replace(day=1)
                    # Convert to datetime for consistent handling
                    month_date = datetime.combine(month_date, datetime.min.time())

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
                # Check if it's a date object (not datetime)
                if hasattr(month_date, "hour"):
                    # It's a datetime object
                    month_date = month_date.replace(
                        day=1, hour=0, minute=0, second=0, microsecond=0
                    )
                else:
                    # It's a date object
                    month_date = month_date.replace(day=1)
                    # Convert to datetime for consistent handling
                    month_date = datetime.combine(month_date, datetime.min.time())

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

    def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Calculate the balance between a user and all other users.

        This helps track how much users owe each other based on shared expenses
        and expenses where one user is the beneficiary but another is the payer.

        Args:
            user_id (int): ID of the user

        Returns:
            Dict[str, Any]: Dictionary containing balance information or error
        """
        try:
            # Get all expenses where user is involved

            # 1. Get expenses where user is the payer for someone else
            paid_for_others_query = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("payer_id", user_id)
                .neq("beneficiary_id", user_id)
                .eq("is_shared", False)
                .execute()
            )

            # 2. Get expenses where someone else paid for the user
            others_paid_query = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("beneficiary_id", user_id)
                .neq("payer_id", user_id)
                .eq("is_shared", False)
                .execute()
            )

            # 3. Get shared expenses where user is the payer
            shared_paid_query = (
                self.client.table(self.expenses_table)
                .select("*")
                .eq("payer_id", user_id)
                .eq("is_shared", True)
                .execute()
            )

            # 4. Get shared expenses where user participates but is not the payer
            shared_query = (
                self.client.table("expenses_split")
                .select("expense_id, amount")
                .eq("user_id", user_id)
                .execute()
            )

            # Process the results to calculate balances
            user_balances = {}

            # Process paid for others
            if paid_for_others_query.data:
                for expense in paid_for_others_query.data:
                    beneficiary_id = expense.get("beneficiary_id")
                    if beneficiary_id:
                        if beneficiary_id not in user_balances:
                            user_balances[beneficiary_id] = {
                                "owes_user": 0,
                                "user_owes": 0,
                            }
                        user_balances[beneficiary_id]["owes_user"] += int(
                            expense.get("amount", 0)
                        )

            # Process others paid for user
            if others_paid_query.data:
                for expense in others_paid_query.data:
                    payer_id = expense.get("payer_id")
                    if payer_id:
                        if payer_id not in user_balances:
                            user_balances[payer_id] = {"owes_user": 0, "user_owes": 0}
                        user_balances[payer_id]["user_owes"] += int(
                            expense.get("amount", 0)
                        )

            # Process shared expenses where user is the payer
            if shared_paid_query.data:
                for expense in shared_paid_query.data:
                    expense_id = expense.get("id")
                    if expense_id:
                        # Get the splits for this expense
                        splits_result = self.get_expense_splits(expense_id)
                        if "split_details" in splits_result:
                            for split in splits_result["split_details"]:
                                split_user_id = split.get("user_id")
                                if split_user_id and split_user_id != user_id:
                                    if split_user_id not in user_balances:
                                        user_balances[split_user_id] = {
                                            "owes_user": 0,
                                            "user_owes": 0,
                                        }
                                    # Other user owes their split amount to current user
                                    user_balances[split_user_id]["owes_user"] += int(
                                        split.get("amount", 0)
                                    )

            # Process shared expenses where user participates but is not the payer
            shared_expense_ids = (
                [item["expense_id"] for item in shared_query.data]
                if shared_query.data
                else []
            )
            if shared_expense_ids:
                # Get the full expense details
                in_query = (
                    self.client.table(self.expenses_table)
                    .select("*")
                    .in_("id", shared_expense_ids)
                    .execute()
                )

                if in_query.data:
                    for expense in in_query.data:
                        payer_id = expense.get("payer_id")
                        if payer_id and payer_id != user_id:
                            if payer_id not in user_balances:
                                user_balances[payer_id] = {
                                    "owes_user": 0,
                                    "user_owes": 0,
                                }
                            # Find the user's split amount for this expense
                            user_split_amount = 0
                            for split in shared_query.data:
                                if split["expense_id"] == expense["id"]:
                                    user_split_amount = int(split.get("amount", 0))
                                    break

                            # Current user owes their split amount to the payer
                            user_balances[payer_id]["user_owes"] += user_split_amount

            # Create the final result
            balance_list = []
            for other_user_id, balance in user_balances.items():
                net_balance = balance["owes_user"] - balance["user_owes"]
                # Convert float values to int for consistency
                balance["owes_user"] = int(balance["owes_user"])
                balance["user_owes"] = int(balance["user_owes"])
                balance_list.append(
                    {
                        "user_id": other_user_id,
                        "owes_user": balance["owes_user"],
                        "user_owes": balance["user_owes"],
                        "net_balance": net_balance,
                    }
                )

            return {"balances": balance_list}

        except Exception as e:
            return {"error": str(e)}
