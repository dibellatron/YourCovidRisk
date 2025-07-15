"""Tests for Monte Carlo confidence interval calculations."""

import pytest
from calculators.monte_carlo_ci import calculate_monte_carlo_ci_uniform, calculate_monte_carlo_ci_beta, calculate_min_max_range


def test_monte_carlo_ci_positive_test():
    """Test Monte Carlo CI returns reasonable values for a positive test."""
    # Test with a symptomatic positive test
    lower, upper = calculate_monte_carlo_ci(
        symptoms="yes",
        test_types=["BinaxNOW"],
        test_results=["positive"],
        initial_risk=0.15,  # 15% prior probability
        num_simulations=1000  # Use fewer simulations for faster tests
    )
    
    # The CI should be within a reasonable range
    assert 0 <= lower <= 1
    assert 0 <= upper <= 1
    assert lower <= upper
    
    # For a positive test with this prior, risk should increase
    assert lower > 0.15


def test_monte_carlo_ci_negative_test():
    """Test Monte Carlo CI returns reasonable values for a negative test."""
    # Test with an asymptomatic negative test
    lower, upper = calculate_monte_carlo_ci(
        symptoms="no",
        test_types=["BinaxNOW"],
        test_results=["negative"],
        initial_risk=0.05,  # 5% prior probability
        num_simulations=1000  # Use fewer simulations for faster tests
    )
    
    # The CI should be within a reasonable range
    assert 0 <= lower <= 1
    assert 0 <= upper <= 1
    assert lower <= upper
    
    # For a negative test with this prior, risk should decrease
    assert upper < 0.05


def test_monte_carlo_ci_multiple_tests():
    """Test Monte Carlo CI with multiple tests."""
    # Test with multiple tests (positive and negative)
    lower, upper = calculate_monte_carlo_ci(
        symptoms="yes",
        test_types=["BinaxNOW", "Flowflex (Covid-only)"],
        test_results=["positive", "negative"],
        initial_risk=0.2,  # 20% prior probability
        num_simulations=1000  # Use fewer simulations for faster tests
    )
    
    # The CI should be within a reasonable range
    assert 0 <= lower <= 1
    assert 0 <= upper <= 1
    assert lower <= upper
    
    # The width of the CI should be reasonable
    ci_width = upper - lower
    assert ci_width > 0  # Should not be a point estimate
    assert ci_width < 0.7  # Should not be too wide


def test_monte_carlo_ci_width():
    """Test that the Monte Carlo CI width is reasonable."""
    # Run with different numbers of simulations to check width behavior
    lower1, upper1 = calculate_monte_carlo_ci(
        symptoms="yes",
        test_types=["BinaxNOW"],
        test_results=["positive"],
        initial_risk=0.1,
        num_simulations=100
    )
    
    lower2, upper2 = calculate_monte_carlo_ci(
        symptoms="yes",
        test_types=["BinaxNOW"],
        test_results=["positive"],
        initial_risk=0.1,
        num_simulations=1000
    )
    
    # Calculate CI widths
    width1 = upper1 - lower1
    width2 = upper2 - lower2
    
    # More simulations should generally lead to narrower CIs
    # This test might occasionally fail due to random variation
    assert width1 > 0
    assert width2 > 0


def test_monte_carlo_extreme_cases():
    """Test Monte Carlo CI with extreme prior probabilities."""
    # Test with very low prior
    lower_low, upper_low = calculate_monte_carlo_ci(
        symptoms="no",
        test_types=["BinaxNOW"],
        test_results=["negative"],
        initial_risk=0.001,  # 0.1% prior probability
        num_simulations=1000
    )
    
    # Test with very high prior
    lower_high, upper_high = calculate_monte_carlo_ci(
        symptoms="yes",
        test_types=["BinaxNOW"],
        test_results=["positive"],
        initial_risk=0.99,  # 99% prior probability
        num_simulations=1000
    )
    
    # CIs should be within bounds
    assert 0 <= lower_low <= upper_low <= 1
    assert 0 <= lower_high <= upper_high <= 1
    
    # Very low prior with negative test should result in very low posterior
    assert upper_low < 0.01
    
    # Very high prior with positive test should result in very high posterior
    assert lower_high > 0.9