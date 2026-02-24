"""
Validation utility functions.

Provides input validation for various data types.
"""

import re
from typing import Any


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_schedule_expression(expression: str, schedule_type: str = "cron") -> bool:
    """
    Validate schedule expression based on type.

    Args:
        expression: Schedule expression to validate
        schedule_type: Type of schedule (cron, daily, weekly, monthly)

    Returns:
        True if valid, False otherwise
    """
    if not expression:
        return False

    if schedule_type == "daily":
        # Format: "HH:MM"
        pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
        return re.match(pattern, expression) is not None

    elif schedule_type == "weekly":
        # Format: "MON HH:MM" or "0-6 HH:MM"
        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        parts = expression.split()
        if len(parts) != 2:
            return False
        day_valid = parts[0] in days or (parts[0].isdigit() and 0 <= int(parts[0]) <= 6)
        time_valid = re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", parts[1]) is not None
        return day_valid and time_valid

    elif schedule_type == "monthly":
        # Format: "DD HH:MM"
        pattern = r"^(0?[1-9]|[12]\d|3[01]) ([01]\d|2[0-3]):([0-5]\d)$"
        return re.match(pattern, expression) is not None

    elif schedule_type == "cron":
        # Standard 5-part cron expression
        parts = expression.split()
        if len(parts) != 5:
            return False
        # Basic validation - each part should be valid
        # minute, hour, day, month, day_of_week
        try:
            for part in parts:
                if "*" in part or "," in part or "-" in part or "/" in part:
                    continue
                if part.isdigit():
                    continue
                return False
            return True
        except ValueError:
            return False

    return False


def validate_username(username: str) -> tuple[bool, str | None]:
    """
    Validate username format.

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 50:
        return False, "Username must be at most 50 characters"

    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores"

    return True, None


def validate_password(password: str) -> tuple[bool, str | None]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 6:
        return False, "Password must be at least 6 characters"

    if len(password) > 100:
        return False, "Password must be at most 100 characters"

    return True, None


def sanitize_search_term(term: str) -> str:
    """
    Sanitize search term to prevent SQL injection.

    Args:
        term: Search term to sanitize

    Returns:
        Sanitized search term
    """
    # Remove dangerous characters
    term = re.sub(r"[;\'\"\\]", "", term)
    # Limit length
    if len(term) > 100:
        term = term[:100]
    return term.strip()


def validate_json_parameters(params: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate JSON parameters against schema.

    Args:
        params: Parameters to validate
        schema: Schema definition with allowed parameters and types

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(params, dict):
        return False, "Parameters must be a JSON object"

    for key, value in params.items():
        if key not in schema:
            # Allow extra parameters if not strictly validated
            continue

        expected_type = schema[key].get("type")
        if expected_type and not isinstance(value, expected_type):
            return False, f"Parameter '{key}' must be of type {expected_type.__name__}"

        # Check range if specified
        if "min" in schema[key] and value < schema[key]["min"]:
            return False, f"Parameter '{key}' must be at least {schema[key]['min']}"

        if "max" in schema[key] and value > schema[key]["max"]:
            return False, f"Parameter '{key}' must be at most {schema[key]['max']}"

    return True, None
