"""Data models for the expense manager application.

This module contains Pydantic models for validating and structuring data
throughout the application.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field


class ExpenseCreate(BaseModel):
    """Model for creating a new expense.

    This model validates the data required to create a new expense.
    """

    amount: float = Field(..., description="Amount of the expense")
    category_id: int = Field(..., description="ID of the category")
    payment_source_id: int = Field(..., description="ID of the payment source")
    date: datetime = Field(..., description="Date of the expense")
    name: str = Field("", description="Name of the expense")
    description: str = Field("", description="Description of the expense")
    payer_id: int = Field(..., description="ID of the profile who paid")
    beneficiary_id: int | None = Field(None, description="ID of the beneficiary")
    is_shared: bool = Field(False, description="Whether this is a shared expense")


class Expense(BaseModel):
    """Model representing an expense.

    This model represents an expense in the system.
    """

    id: int = Field(..., description="Unique ID of the expense")
    amount: float = Field(..., description="Amount of the expense")
    category_id: int = Field(..., description="ID of the category")
    payment_source_id: int = Field(..., description="ID of the payment source")
    date: datetime = Field(..., description="Date of the expense")
    name: str = Field("", description="Name of the expense")
    description: str = Field("", description="Description of the expense")
    payer_id: int = Field(..., description="ID of the profile who paid")
    beneficiary_id: int | None = Field(None, description="ID of the beneficiary")
    is_shared: bool = Field(False, description="Whether this is a shared expense")
    created_at: datetime = Field(
        ..., description="Timestamp of when the expense was created"
    )


class ExpenseUpdate(BaseModel):
    """Model for updating an existing expense.

    This model validates the data for updating an expense, with all fields optional.
    """

    amount: float | None = Field(None, description="Amount of the expense", ge=0)
    category_id: int | None = Field(None, description="ID of the expense category")
    date: datetime | None = Field(None, description="Date of the expense")
    name: str | None = Field(None, description="Name of the expense")
    description: str | None = Field(None, description="Description of the expense")
    is_shared: bool | None = Field(
        None, description="Whether this expense is shared with others"
    )
    split_with_users: List[int] | None = Field(
        None, description="List of user IDs to split the expense with"
    )
    payer_id: int | None = Field(None, description="ID of the user who paid")
    beneficiary_id: int | None = Field(None, description="ID of the beneficiary user")


class Category(BaseModel):
    """Model representing an expense category.

    This model represents a category that expenses can be classified under.
    """

    id: int = Field(..., description="Unique ID of the category")
    name: str = Field(..., description="Name of the category")
    description: str = Field("", description="Description of the category")
    created_at: datetime = Field(
        ..., description="Timestamp of when the category was created"
    )


class CategoryCreate(BaseModel):
    """Model for creating a new expense category.

    This model validates the data required to create a new category.
    """

    name: str = Field(..., description="Name of the category")
    description: str = Field("", description="Description of the category")


class User(BaseModel):
    """Model representing a user.

    This model represents a user in the system.
    """

    id: str = Field(..., description="Unique ID of the user")
    email: EmailStr = Field(..., description="Email address of the user")
    created_at: datetime = Field(
        ..., description="Timestamp of when the user was created"
    )


class Profile(BaseModel):
    """Model representing a user profile.

    This model represents a user's profile in the system.
    """

    id: int = Field(..., description="Unique ID of the profile")
    user_id: str = Field(..., description="ID of the user")
    display_name: str = Field(..., description="Display name of the user")
    created_at: datetime = Field(
        ..., description="Timestamp of when the profile was created"
    )


class Transfer(BaseModel):
    """Model representing a money transfer between users.

    This model represents a direct transfer of money between two users.
    """

    id: int = Field(..., description="Unique ID of the transfer")
    source_id: int = Field(..., description="ID of the user sending the money")
    beneficiary_id: int = Field(..., description="ID of the user receiving the money")
    amount: float = Field(..., description="Amount of money transferred")
    created_at: datetime = Field(
        ..., description="Timestamp of when the transfer was created"
    )


class TransferCreate(BaseModel):
    """Model for creating a new transfer.

    This model represents the data needed to create a new transfer.
    """

    source_id: int = Field(..., description="ID of the user sending the money")
    beneficiary_id: int = Field(..., description="ID of the user receiving the money")
    amount: float = Field(..., description="Amount of money to transfer")


class ExpenseSummary(BaseModel):
    """Model for expense summaries.

    This model represents summarized expense data for visualization.
    """

    total: float = Field(..., description="Total amount spent")
    by_category: List[dict] = Field(
        ..., description="Breakdown of expenses by category"
    )
    by_date: List[dict] = Field(..., description="Breakdown of expenses by date")


class ExpenseSplit(BaseModel):
    """Model representing an expense split.

    This model represents how an expense is split between users.
    """

    id: int = Field(..., description="Unique ID of the expense split")
    expense_id: int = Field(..., description="ID of the expense being split")
    user_id: int = Field(..., description="ID of the user participating in the split")
    amount: float = Field(..., description="Amount of the split")
    created_at: datetime = Field(
        ..., description="Timestamp of when the split was created"
    )


class MonthlyIncome(BaseModel):
    """Model representing monthly income for a user.

    This model represents a monthly income record for a user.
    """

    id: int = Field(..., description="Unique ID of the income record")
    user_id: int = Field(..., description="ID of the user")
    amount: float = Field(..., description="Income amount")
    month_date: datetime = Field(
        ..., description="First day of the month this income applies to"
    )
    created_at: datetime = Field(
        ..., description="Timestamp of when the income record was created"
    )


class MonthlyIncomeCreate(BaseModel):
    """Model for creating/updating monthly income.

    This model validates the data required to create or update monthly income.
    """

    amount: float = Field(..., description="Income amount", ge=0)
    month_date: datetime = Field(
        default_factory=lambda: datetime.now().replace(day=1),
        description="Month this income applies to (will be set to 1st day of month)",
    )


class PaymentSource(BaseModel):
    """Model representing a payment source.

    This model represents a payment source that can be used for expenses.
    """

    id: int = Field(..., description="Unique ID of the payment source")
    name: str = Field(..., description="Name of the payment source")
    user_id: str = Field(..., description="ID of the user who owns this payment source")
    created_at: datetime = Field(
        ..., description="Timestamp of when the payment source was created"
    )


def format_currency(amount: float) -> str:
    """Format a number as Swedish Krona currency.

    Args:
        amount (float): The amount to format

    Returns:
        str: The formatted currency string (e.g. "123,45 kr")
    """
    # Format amount with comma as decimal separator and space as thousands separator
    # This follows Swedish currency formatting conventions
    formatted_number = (
        "{:,.2f}".format(amount).replace(",", "X").replace(".", ",").replace("X", " ")
    )

    # Add the kr symbol with space as per Swedish format
    return f"{formatted_number} kr"
