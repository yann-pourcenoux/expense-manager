"""Database manager for interacting with SQLite database.

This module handles all interactions with the SQLite database for expense data,
including creating, reading, updating, and deleting expenses.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from sqlite_utils import Database

from expense_manager.config import load_config


class DatabaseManager:
    """Manager for SQLite database operations.

    This class handles all database operations related to expenses, including
    creating, reading, updating, and deleting expense records.
    """

    def __init__(self) -> None:
        """Initialize SQLite database connection and create tables if needed."""
        # Load configuration from session state or default
        if "config" in st.session_state:
            config = st.session_state.config
        else:
            config = load_config()

        db_path = config["database"]["path"]

        # Create directory for database if it doesn't exist
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.db = Database(db_path)

        # Table names
        self.expenses_table = "expenses"
        self.categories_table = "categories"
        self.profiles_table = "profiles"
        self.expenses_split_table = "expenses_split"
        self.monthly_income_table = "monthly_income"
        self.users_table = "users"

        # Create tables if they don't exist
        self._create_tables()

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        # Create users table
        if self.users_table not in self.db.table_names():
            self.db.create_table(
                self.users_table,
                {
                    "id": str,
                    "email": str,
                    "password_hash": str,
                    "created_at": str,
                },
                pk="id",
            )
            self.db[self.users_table].create_index(["email"], unique=True)

        # Create profiles table
        if self.profiles_table not in self.db.table_names():
            self.db.create_table(
                self.profiles_table,
                {
                    "id": int,
                    "user_id": str,
                    "display_name": str,
                    "created_at": str,
                },
                pk="id",
            )
            self.db[self.profiles_table].create_index(["user_id"], unique=True)

        # Create categories table
        if self.categories_table not in self.db.table_names():
            self.db.create_table(
                self.categories_table,
                {
                    "id": int,
                    "name": str,
                    "description": str,
                    "created_at": str,
                },
                pk="id",
            )

        # Create expenses table
        if self.expenses_table not in self.db.table_names():
            self.db.create_table(
                self.expenses_table,
                {
                    "id": int,
                    "reporter_id": int,
                    "payer_id": int,
                    "beneficiary_id": int,
                    "amount": float,
                    "category_id": int,
                    "date": str,
                    "name": str,
                    "description": str,
                    "is_shared": int,  # SQLite doesn't have bool, use int (0/1)
                    "created_at": str,
                },
                pk="id",
            )

        # Create expenses_split table
        if self.expenses_split_table not in self.db.table_names():
            self.db.create_table(
                self.expenses_split_table,
                {
                    "id": int,
                    "expense_id": int,
                    "user_id": int,
                    "amount": float,
                    "created_at": str,
                },
                pk="id",
            )
            self.db[self.expenses_split_table].create_index(["expense_id", "user_id"])

        # Create monthly_income table
        if self.monthly_income_table not in self.db.table_names():
            self.db.create_table(
                self.monthly_income_table,
                {
                    "id": int,
                    "user_id": int,
                    "amount": float,
                    "month_date": str,
                    "created_at": str,
                },
                pk="id",
            )
            self.db[self.monthly_income_table].create_index(
                ["user_id", "month_date"], unique=True
            )

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
            "is_shared": 1 if is_shared else 0,
            "beneficiary_id": beneficiary_id,
            "created_at": datetime.now().isoformat(),
        }

        expense_id = self.db[self.expenses_table].insert(expense_data).last_pk

        # Get the created expense
        expense = self.db[self.expenses_table].get(expense_id)

        if not expense:
            raise Exception("Failed to create expense")

        # 2. Create the record in the split table
        if not is_shared:
            split_with_users = [beneficiary_id]
        else:
            # Select all profiles
            profiles = self.get_all_profiles()["profiles"]
            split_with_users = [profile["id"] for profile in profiles]

        expense_split_data = []
        for user_id in split_with_users:
            if user_id is not None:  # Skip None values
                expense_split_data.append(
                    {
                        "expense_id": expense_id,
                        "user_id": user_id,
                        "amount": amount / len(split_with_users),
                        "created_at": datetime.now().isoformat(),
                    }
                )

        for expense_split in expense_split_data:
            self.db[self.expenses_split_table].insert(expense_split)

        return expense

    def _get_expenses_with_filter(
        self, where_clause: str = "", params: dict = None
    ) -> list[dict]:
        """Internal helper to get expenses with a custom WHERE clause.

        Args:
            where_clause: SQL WHERE clause (without the 'WHERE' keyword)
            params: Parameters for the query

        Returns:
            list[dict]: List of expenses matching the criteria
        """
        if params is None:
            params = {}

        # Build query
        query = f"SELECT * FROM {self.expenses_table}"
        if where_clause:
            query += f" WHERE {where_clause}"

        # Execute the query
        conn = self.db.conn
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dictionaries
        column_names = [desc[0] for desc in cursor.description]
        expenses = [dict(zip(column_names, row)) for row in rows]
        return expenses

    def get_expenses_for_balance(self) -> list[dict]:
        """Get expenses relevant for balance calculations.

        Returns:
            list[dict]: List of expenses that are either shared or have
                different payer and beneficiary
        """
        where_clause = "is_shared = 1 OR payer_id != beneficiary_id"
        return self._get_expenses_with_filter(where_clause)

    def get_expenses_for_list(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_id: Optional[int] = None,
    ) -> list[dict]:
        """Get expenses for a specific user with optional filtering.

        Args:
            user_id (int): ID of the user
            start_date (Optional[datetime], optional): Filter expenses after
                this date. Defaults to None.
            end_date (Optional[datetime], optional): Filter expenses before
                this date. Defaults to None.
            category_id (Optional[int], optional): Filter by category ID.
                Defaults to None.

        Returns:
            list[dict]: List of expenses matching the criteria
        """
        # Build the query conditions
        where_clauses = []
        params = {}

        # User is involved in expense (shared, payer, or beneficiary)
        where_clauses.append(
            "(is_shared = 1 OR payer_id = :user_id OR beneficiary_id = :user_id)"
        )
        params["user_id"] = user_id

        if start_date is not None:
            where_clauses.append("date >= :start_date")
            params["start_date"] = start_date.isoformat()

        if end_date is not None:
            where_clauses.append("date <= :end_date")
            params["end_date"] = end_date.isoformat()

        if category_id is not None:
            where_clauses.append("category_id = :category_id")
            params["category_id"] = category_id

        where_clause = " AND ".join(where_clauses)
        return self._get_expenses_with_filter(where_clause, params)

    def get_shared_expenses_for_dashboard(
        self, start_date: str, end_date: str
    ) -> list[dict]:
        """Get shared expenses for the dashboard."""
        where_clause = "is_shared = 1 AND date >= :start_date AND date <= :end_date"
        params = {"start_date": start_date, "end_date": end_date}
        return self._get_expenses_with_filter(where_clause, params)

    def update_expense(
        self,
        expense_id: int,
        user_id: int,
        updates: Dict[str, Any],
        split_with_users: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Update an existing expense."""
        # Check if expense exists and user is allowed to update it
        expense = self.db[self.expenses_table].get(expense_id)

        if not expense:
            return {"error": "Expense not found"}

        if expense["reporter_id"] != user_id:
            return {"error": "You can only update expenses you created"}

        # Update expense fields
        update_data = {}
        allowed_fields = [
            "payer_id",
            "beneficiary_id",
            "amount",
            "category_id",
            "date",
            "name",
            "description",
            "is_shared",
        ]

        for field in allowed_fields:
            if field in updates:
                # Convert boolean to integer for is_shared
                if field == "is_shared" and isinstance(updates[field], bool):
                    update_data[field] = 1 if updates[field] else 0
                else:
                    update_data[field] = updates[field]

        if update_data:
            self.db[self.expenses_table].update(expense_id, update_data)

        # Update expense_splits if requested
        if split_with_users is not None:
            if updates.get("is_shared", expense["is_shared"]):
                # If shared expense, split among all users
                all_profiles = self.get_all_profiles()["profiles"]
                split_with_users = [profile["id"] for profile in all_profiles]

            self.update_expense_splits(expense_id, user_id, split_with_users)

        # Return updated expense
        updated_expense = self.db[self.expenses_table].get(expense_id)
        return {"expense": updated_expense}

    def delete_expense(self, expense_id: int, user_id: int) -> Dict[str, Any]:
        """Delete an expense and its splits."""
        # Check if expense exists and user is allowed to delete it
        expense = self.db[self.expenses_table].get(expense_id)

        if not expense:
            return {"error": "Expense not found"}

        if expense["reporter_id"] != user_id:
            return {"error": "You can only delete expenses you created"}

        # Delete expense splits first
        self.db.execute(
            f"DELETE FROM {self.expenses_split_table} WHERE expense_id = ?",
            [expense_id],
        )

        # Delete the expense
        self.db[self.expenses_table].delete(expense_id)

        return {"success": True}

    def get_categories(self) -> Dict[str, Any]:
        """Get all expense categories."""
        categories = list(self.db[self.categories_table].rows)
        return {"categories": categories}

    def create_category(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new expense category."""
        category_data = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
        }

        category_id = self.db[self.categories_table].insert(category_data).last_pk
        category = self.db[self.categories_table].get(category_id)

        if not category:
            return {"error": "Failed to create category"}

        return {"category": category}

    def get_expense_splits(self, expense_id: int) -> Dict[str, Any]:
        """Get all splits for a specific expense."""
        conn = self.db.conn

        query = f"""
        SELECT es.*, p.display_name
        FROM {self.expenses_split_table} es
        JOIN {self.profiles_table} p ON es.user_id = p.id
        WHERE es.expense_id = ?
        """

        cursor = conn.execute(query, [expense_id])
        rows = cursor.fetchall()

        # Convert to dictionaries
        column_names = [desc[0] for desc in cursor.description]
        splits = [dict(zip(column_names, row)) for row in rows]

        return {"splits": splits}

    def update_expense_splits(
        self, expense_id: int, user_id: int, split_with_users: List[int]
    ) -> Dict[str, Any]:
        """Update the splits for an expense."""
        # Check if expense exists and user is allowed to update it
        expense = self.db[self.expenses_table].get(expense_id)

        if not expense:
            return {"error": "Expense not found"}

        if expense["reporter_id"] != user_id:
            return {"error": "You can only update expenses you created"}

        # Delete existing splits
        self.db.execute(
            f"DELETE FROM {self.expenses_split_table} WHERE expense_id = ?",
            [expense_id],
        )

        # Create new splits
        amount_per_user = expense["amount"] / len(split_with_users)

        for split_user_id in split_with_users:
            split_data = {
                "expense_id": expense_id,
                "user_id": split_user_id,
                "amount": amount_per_user,
                "created_at": datetime.now().isoformat(),
            }
            self.db[self.expenses_split_table].insert(split_data)

        return {"success": True}

    def get_monthly_income(
        self, user_id: int, month_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get the monthly income for a user for a specific month."""
        if month_date is None:
            month_date = datetime.now()

        # Format as YYYY-MM-01 for consistent monthly comparisons
        month_string = month_date.strftime("%Y-%m-01")

        conn = self.db.conn
        query = f"""
        SELECT * FROM {self.monthly_income_table}
        WHERE user_id = ? AND month_date = ?
        """

        cursor = conn.execute(query, [user_id, month_string])
        row = cursor.fetchone()

        if row:
            # Convert to dictionary
            column_names = [desc[0] for desc in cursor.description]
            income = dict(zip(column_names, row))
            return {"income": income}
        else:
            return {"income": None}

    def set_monthly_income(
        self, user_id: int, amount: float, month_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Set or update the monthly income for a user."""
        if month_date is None:
            month_date = datetime.now()

        # Format as YYYY-MM-01 for consistent monthly comparisons
        month_string = month_date.strftime("%Y-%m-01")

        # Check if income record already exists for this month
        existing = self.get_monthly_income(user_id, month_date)

        if existing.get("income"):
            # Update existing record
            income_id = existing["income"]["id"]
            self.db[self.monthly_income_table].update(income_id, {"amount": amount})
        else:
            # Create new record
            income_data = {
                "user_id": user_id,
                "amount": amount,
                "month_date": month_string,
                "created_at": datetime.now().isoformat(),
            }
            income_id = self.db[self.monthly_income_table].insert(income_data).last_pk

        # Return updated income
        income = self.db[self.monthly_income_table].get(income_id)
        return {"income": income}

    def get_income_history(self, user_id: int, limit: int = 12) -> Dict[str, Any]:
        """Get income history for a user."""
        conn = self.db.conn
        query = f"""
        SELECT * FROM {self.monthly_income_table}
        WHERE user_id = ?
        ORDER BY month_date DESC
        LIMIT ?
        """

        cursor = conn.execute(query, [user_id, limit])
        rows = cursor.fetchall()

        # Convert to dictionaries
        column_names = [desc[0] for desc in cursor.description]
        history = [dict(zip(column_names, row)) for row in rows]

        return {"history": history}

    def delete_monthly_income(self, income_id: int, user_id: int) -> Dict[str, Any]:
        """Delete a monthly income record.

        Args:
            income_id (int): ID of the income record to delete
            user_id (int): ID of the user making the request

        Returns:
            Dict[str, Any]: Result of the deletion
        """
        # Check if income record exists and belongs to the user
        income = self.db[self.monthly_income_table].get(income_id)

        if not income:
            return {"error": "Income record not found"}

        if income["user_id"] != user_id:
            return {"error": "You can only delete your own income records"}

        # Delete the income record
        self.db[self.monthly_income_table].delete(income_id)

        return {"success": True}

    def update_category(
        self, category_id: int, name: str, description: str = ""
    ) -> Dict[str, Any]:
        """Update a category's name and description."""
        # Check if category exists
        category = self.db[self.categories_table].get(category_id)

        if not category:
            return {"error": "Category not found"}

        # Update category
        update_data = {
            "name": name,
            "description": description,
        }

        self.db[self.categories_table].update(category_id, update_data)

        # Return updated category
        updated_category = self.db[self.categories_table].get(category_id)
        return {"category": updated_category}

    def delete_category(self, category_id: int) -> Dict[str, Any]:
        """Delete a category if it's not in use."""
        # Check if category exists
        category = self.db[self.categories_table].get(category_id)

        if not category:
            return {"error": "Category not found"}

        # Check if category is in use
        conn = self.db.conn
        query = f"SELECT COUNT(*) FROM {self.expenses_table} WHERE category_id = ?"
        cursor = conn.execute(query, [category_id])
        count = cursor.fetchone()[0]

        if count > 0:
            return {"error": f"Cannot delete category. It is used by {count} expenses."}

        # Delete the category
        self.db[self.categories_table].delete(category_id)
        return {"success": True}

    def create_user(
        self, user_id: str, email: str, password_hash: str
    ) -> Dict[str, Any]:
        """Create a new user in the database."""
        user_data = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.db[self.users_table].insert(user_data)
            user = self.db[self.users_table].get(user_id)
            return {"user": user}
        except sqlite3.IntegrityError:
            return {"error": "User with this email already exists"}

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Get a user by email."""
        conn = self.db.conn
        query = f"SELECT * FROM {self.users_table} WHERE email = ?"
        cursor = conn.execute(query, [email])
        row = cursor.fetchone()

        if row:
            # Convert to dictionary
            column_names = [desc[0] for desc in cursor.description]
            user = dict(zip(column_names, row))
            return {"user": user}
        else:
            return {"user": None}

    def create_profile(
        self, user_id: str, display_name: str | None = None
    ) -> Dict[str, Any]:
        """Create a user profile."""
        # Check if profile already exists
        conn = self.db.conn
        query = f"SELECT * FROM {self.profiles_table} WHERE user_id = ?"
        cursor = conn.execute(query, [user_id])
        existing_profile = cursor.fetchone()

        if existing_profile:
            column_names = [desc[0] for desc in cursor.description]
            profile = dict(zip(column_names, existing_profile))
            return {"profile": profile}

        # Create new profile
        profile_data = {
            "user_id": user_id,
            "display_name": display_name or "User",
            "created_at": datetime.now().isoformat(),
        }

        profile_id = self.db[self.profiles_table].insert(profile_data).last_pk
        profile = self.db[self.profiles_table].get(profile_id)

        if not profile:
            return {"error": "Failed to create profile"}

        return {"profile": profile}

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get a user's profile."""
        conn = self.db.conn
        query = f"SELECT * FROM {self.profiles_table} WHERE user_id = ?"
        cursor = conn.execute(query, [user_id])
        row = cursor.fetchone()

        if row:
            # Convert to dictionary
            column_names = [desc[0] for desc in cursor.description]
            profile = dict(zip(column_names, row))
            return {"profile": profile}
        else:
            return {"profile": None}

    def update_profile(self, user_id: str, display_name: str) -> Dict[str, Any]:
        """Update a user's profile."""
        # Get the profile ID
        profile_result = self.get_profile(user_id)

        if not profile_result.get("profile"):
            return {"error": "Profile not found"}

        profile_id = profile_result["profile"]["id"]

        # Update the profile
        self.db[self.profiles_table].update(profile_id, {"display_name": display_name})

        # Return updated profile
        updated_profile = self.db[self.profiles_table].get(profile_id)
        return {"profile": updated_profile}

    def get_all_profiles(self) -> Dict[str, Any]:
        """Return all profiles in the database."""
        profiles = list(self.db[self.profiles_table].rows)
        return {"profiles": profiles}

    def update_password(self, user_id: str, password_hash: str) -> Dict[str, Any]:
        """Update a user's password.

        Args:
            user_id (str): The ID of the user to update
            password_hash (str): The new password hash

        Returns:
            Dict[str, Any]: Dict containing success status or error message
        """
        try:
            # Verify user exists
            user = self.db[self.users_table].get(user_id)
            if not user:
                return {"error": "User not found"}

            # Update password
            self.db[self.users_table].update(
                user_id, {"password_hash": password_hash}, alter=True
            )

            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Calculate balance between users based on expenses."""
        # We need to calculate:
        # 1. How much this user has paid for others
        # 2. How much others have paid for this user

        conn = self.db.conn

        # 1. Total amount user has paid for others
        paid_query = f"""
        SELECT SUM(e.amount) as paid
        FROM {self.expenses_table} e
        WHERE e.payer_id = ? AND (e.is_shared = 1 OR e.beneficiary_id != ?)
        """
        cursor = conn.execute(paid_query, [user_id, user_id])
        paid_row = cursor.fetchone()
        paid = paid_row[0] if paid_row[0] is not None else 0

        # 2. Total amount others have paid for this user
        owed_query = f"""
        SELECT SUM(es.amount) as owed
        FROM {self.expenses_split_table} es
        JOIN {self.expenses_table} e ON es.expense_id = e.id
        WHERE es.user_id = ? AND e.payer_id != ?
        """
        cursor = conn.execute(owed_query, [user_id, user_id])
        owed_row = cursor.fetchone()
        owed = owed_row[0] if owed_row[0] is not None else 0

        # Calculate overall balance
        balance = paid - owed

        return {"balance": balance, "paid": paid, "owed": owed}

    def get_individual_expenses_for_dashboard(
        self, user_id: int, start_date: str, end_date: str
    ) -> list[dict]:
        """Get expenses for the dashboard where the specified user is involved.

        This pulls data from the expenses_split table to get the individual expenses
        where the user is involved, including both their own expenses and shared
        expenses with the correct split amount.

        Args:
            user_id (int): ID of the user
            start_date (str): Start date in ISO format
            end_date (str): End date in ISO format

        Returns:
            list[dict]: List of expense records with category and split amount
        """
        conn = self.db.conn

        query = f"""
        SELECT e.*, es.amount as split_amount, c.name as category_name
        FROM {self.expenses_split_table} es
        JOIN {self.expenses_table} e ON es.expense_id = e.id
        LEFT JOIN {self.categories_table} c ON e.category_id = c.id
        WHERE es.user_id = ? AND e.date >= ? AND e.date <= ?
        ORDER BY e.date DESC
        """

        cursor = conn.execute(query, [user_id, start_date, end_date])
        rows = cursor.fetchall()

        # Convert to dictionaries
        column_names = [desc[0] for desc in cursor.description]
        expenses = [dict(zip(column_names, row)) for row in rows]

        return expenses
