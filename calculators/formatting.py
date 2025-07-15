"""
Formatting helpers for percentage-based risk display.
"""
def format_percent(p: float) -> str:
    """
    Formats a probability (0..1) as a percentage string with variable precision:
    - Uses fewer decimals for mid-range values, more for extremes near 0 or 100.
    - Caps very low values as '< 0.0000001%' and very high as '> 99.999999%'.
    """
    percent = p * 100.0
    # Very high end
    if percent >= 99.999999:
        return "> 99.999999%"
    if percent >= 99.99999:
        return f"{percent:.6f}%"
    if percent >= 99.9999:
        return f"{percent:.5f}%"
    if percent >= 99.999:
        return f"{percent:.4f}%"
    if percent >= 99.99:
        return f"{percent:.3f}%"
    if percent >= 99.9:
        return f"{percent:.2f}%"
    # Mid-range
    if percent >= 0.1:
        return f"{percent:.1f}%"
    # Low end
    if percent >= 0.01:
        return f"{percent:.2f}%"
    if percent >= 0.001:
        return f"{percent:.3f}%"
    if percent >= 0.0001:
        return f"{percent:.4f}%"
    if percent >= 0.00001:
        return f"{percent:.5f}%"
    if percent >= 0.000001:
        return f"{percent:.6f}%"
    if percent >= 0.0000001:
        return f"{percent:.7f}%"
    # Very low end
    return "< 0.0000001%"


def format_confidence_interval(lower: float, upper: float) -> tuple[str, str]:
    """
    Formats a confidence interval using the same rounding scheme as format_percent().
    If the lower and upper bounds are identical after rounding, uses one more significant figure.
    
    Args:
        lower: Lower bound of confidence interval (0..1)
        upper: Upper bound of confidence interval (0..1)
    
    Returns:
        Tuple of (formatted_lower, formatted_upper) strings
    """
    # First, format using the standard scheme
    lower_formatted = format_percent(lower)
    upper_formatted = format_percent(upper)
    
    # If they're the same, we need to use one more significant figure
    if lower_formatted == upper_formatted:
        # Get the current precision level and add one more decimal place
        lower_percent = lower * 100.0
        upper_percent = upper * 100.0
        
        # Determine precision level needed (one more than format_percent would use)
        if lower_percent >= 99.99999 or upper_percent >= 99.99999:
            # Already at max precision, can't go higher
            return (lower_formatted, upper_formatted)
        elif lower_percent >= 99.9999 or upper_percent >= 99.9999:
            # format_percent uses 6 digits, use 7
            lower_formatted = f"{lower_percent:.7f}%"
            upper_formatted = f"{upper_percent:.7f}%"
        elif lower_percent >= 99.999 or upper_percent >= 99.999:
            # format_percent uses 5 digits, use 6
            lower_formatted = f"{lower_percent:.6f}%"
            upper_formatted = f"{upper_percent:.6f}%"
        elif lower_percent >= 99.99 or upper_percent >= 99.99:
            # format_percent uses 4 digits, use 5
            lower_formatted = f"{lower_percent:.5f}%"
            upper_formatted = f"{upper_percent:.5f}%"
        elif lower_percent >= 99.9 or upper_percent >= 99.9:
            # format_percent uses 3 digits, use 4
            lower_formatted = f"{lower_percent:.4f}%"
            upper_formatted = f"{upper_percent:.4f}%"
        elif lower_percent >= 99.0 or upper_percent >= 99.0:
            # format_percent uses 2 digits, use 3
            lower_formatted = f"{lower_percent:.3f}%"
            upper_formatted = f"{upper_percent:.3f}%"
        elif lower_percent >= 0.1 or upper_percent >= 0.1:
            # format_percent uses 1 digit, use 2
            lower_formatted = f"{lower_percent:.2f}%"
            upper_formatted = f"{upper_percent:.2f}%"
        elif lower_percent >= 0.01 or upper_percent >= 0.01:
            # format_percent uses 2 digits, use 3
            lower_formatted = f"{lower_percent:.3f}%"
            upper_formatted = f"{upper_percent:.3f}%"
        elif lower_percent >= 0.001 or upper_percent >= 0.001:
            # format_percent uses 3 digits, use 4
            lower_formatted = f"{lower_percent:.4f}%"
            upper_formatted = f"{upper_percent:.4f}%"
        elif lower_percent >= 0.0001 or upper_percent >= 0.0001:
            # format_percent uses 4 digits, use 5
            lower_formatted = f"{lower_percent:.5f}%"
            upper_formatted = f"{upper_percent:.5f}%"
        elif lower_percent >= 0.00001 or upper_percent >= 0.00001:
            # format_percent uses 5 digits, use 6
            lower_formatted = f"{lower_percent:.6f}%"
            upper_formatted = f"{upper_percent:.6f}%"
        elif lower_percent >= 0.000001 or upper_percent >= 0.000001:
            # format_percent uses 6 digits, use 7
            lower_formatted = f"{lower_percent:.7f}%"
            upper_formatted = f"{upper_percent:.7f}%"
        elif lower_percent >= 0.0000001 or upper_percent >= 0.0000001:
            # format_percent uses 7 digits, use 8
            lower_formatted = f"{lower_percent:.8f}%"
            upper_formatted = f"{upper_percent:.8f}%"
        # For very low values, we've already hit the limit
    
    return (lower_formatted, upper_formatted)


def format_ci_filter(bounds_tuple):
    """
    Jinja2 filter wrapper for format_confidence_interval().
    Takes a tuple (lower, upper) and returns a tuple of formatted strings.
    """
    if isinstance(bounds_tuple, (list, tuple)) and len(bounds_tuple) == 2:
        return format_confidence_interval(bounds_tuple[0], bounds_tuple[1])
    else:
        raise ValueError("ci_format filter expects a tuple/list of (lower, upper) bounds")