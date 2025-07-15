"""Utility helpers for safe, consistent type conversion.

These helpers **never throw** – they return a tuple (typed_value, error_msg).
If conversion succeeds, *error_msg* is the empty string.  Otherwise the
*default* is returned together with an appropriate message.  Using a common
routine avoids scattering try/except blocks through the calculation code and
keeps behaviour uniform.
"""

from typing import Optional, Tuple


def _strip(value: Optional[str]) -> str:
    return value.strip() if isinstance(value, str) else ""


def safe_float(value: Optional[str], default: float) -> Tuple[float, str]:
    """Convert *value* to float, else return *default* and an error string."""
    txt = _strip(value)
    if txt == "":
        return default, ""
    try:
        return float(txt), ""
    except ValueError:
        return default, f"Invalid float: {value!r}"


def safe_int(value: Optional[str], default: int) -> Tuple[int, str]:
    """Convert *value* to int, else return *default* and an error string."""
    txt = _strip(value)
    if txt == "":
        return default, ""
    try:
        return int(txt), ""
    except ValueError:
        return default, f"Invalid int: {value!r}"
