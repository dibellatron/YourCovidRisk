import pytest

from calculators.validators import safe_float, safe_int


@pytest.mark.parametrize(
    "input_str, default, expected_val, expected_err",
    [
        ("3.14", 0.0, 3.14, ""),
        ("", 1.23, 1.23, ""),
        (None, 2.5, 2.5, ""),
        ("not-a-number", 9.9, 9.9, "Invalid float: 'not-a-number'"),
    ],
)
def test_safe_float(input_str, default, expected_val, expected_err):
    value, err = safe_float(input_str, default)
    assert value == expected_val
    assert err == expected_err


@pytest.mark.parametrize(
    "input_str, default, expected_val, expected_err",
    [
        ("42", 0, 42, ""),
        ("", 7, 7, ""),
        (None, 5, 5, ""),
        ("abc", 1, 1, "Invalid int: 'abc'"),
    ],
)
def test_safe_int(input_str, default, expected_val, expected_err):
    value, err = safe_int(input_str, default)
    assert value == expected_val
    assert err == expected_err
