"""
Shared validation utilities.
Used by Pydantic models and the Voice Agent logic.
"""
import re
from typing import Optional

def normalize_phone_number(phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to E.164 format.
    
    Examples:
        "555-123-4567"      -> "+15551234567"
        "+1 (555) 123-4567" -> "+15551234567"
        "15551234567"       -> "+15551234567"
    """
    if not phone:
        return None

    # Remove all non-digit characters
    clean_number = re.sub(r'\D', '', phone)

    # Validation: Must have at least 10 digits
    if len(clean_number) < 10:
        # In a real API, you might want to log this or allow it but flag it.
        # For now, strict validation is safer.
        raise ValueError(f"Phone number too short: {phone}")

    # US/Canada numbers (10 digits) -> Add +1
    if len(clean_number) == 10:
        return f"+1{clean_number}"

    # US/Canada with prefix (11 digits starting with 1) -> Add +
    elif len(clean_number) == 11 and clean_number.startswith('1'):
        return f"+{clean_number}"

    # International (Assume it's correct if > 10 digits)
    elif len(clean_number) > 10:
        return f"+{clean_number}"

    # Fallback
    return f"+1{clean_number}"

def normalize_name(name: str) -> str:
    """
    Normalize person name for consistency.
    "  john   smith  " -> "John Smith"
    """
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")
        
    # Strip whitespace, replace multiple spaces with one, and Title Case
    # Note: re.sub(r'\s+', ' ', ...) handles tabs/newlines too
    normalized = re.sub(r'\s+', ' ', name.strip()).title()
    
    return normalized