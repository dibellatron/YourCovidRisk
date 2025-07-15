"""Module for tracking and recording calculation steps for the test calculator.

This module provides helper functions to track the calculation steps for the
"Explain calculation" feature in the Covid Test Calculator.
"""

from typing import Any, Dict, List


def create_calculation_data(
    symptoms: str,
    covid_cautious: str,
    initial_risk: float,
    prior_manual: bool,
    caution_adjusted_risk: float,
    tests_data: List[Dict[str, Any]],
    final_risk: float,
) -> Dict[str, Any]:
    """
    Create a structured object with all calculation steps for display.

    Parameters:
    -----------
    symptoms : str
        Whether the user has symptoms ('yes' or 'no')
    covid_cautious : str
        The user's selected caution level (text)
    initial_risk : float
        The starting probability before any adjustments
    prior_manual : bool
        Whether the prior probability was manually specified
    caution_adjusted_risk : float
        The risk after caution level adjustment
    tests_data : List[Dict[str, Any]]
        List of test objects with their impact on the calculation
    final_risk : float
        The final calculated risk

    Returns:
    --------
    Dict[str, Any]
        Object with all calculation steps for the frontend
    """
    # Create simple, hardcoded calculation data that definitely works
    return {
        "step1": {
            "title": "Starting probability (prior)",
            "detail": f"Your starting probability was {initial_risk * 100:.4f}%.",
        },
        "step2": {
            "title": "Adjustments based on caution level",
            "detail": f"After adjusting for your caution level ({covid_cautious}), your probability became {caution_adjusted_risk * 100:.4f}%.",
        },
        "step3": {
            "title": "Test result(s) impact",
            "tests": [
                {
                    "type": test.get("testType", "Unknown"),
                    "result": test.get("testResult", "unknown"),
                    "before": test.get("priorRisk", 0) * 100,
                    "after": test.get("updatedRisk", 0) * 100,
                }
                for test in tests_data
            ],
        },
        "step4": {
            "title": "Final probability",
            "detail": f"Your final probability of infection is {final_risk * 100:.4f}%.",
        },
    }


def track_test_impact(
    test_type: str,
    test_result: str,
    sensitivity: float,
    specificity: float,
    prior_risk: float,
    updated_risk: float,
) -> Dict[str, Any]:
    """
    Create an object that tracks the impact of a single test on the risk calculation.

    Parameters:
    -----------
    test_type : str
        The type of test used
    test_result : str
        Whether the result was positive or negative
    sensitivity : float
        The test's sensitivity (true positive rate)
    specificity : float
        The test's specificity (true negative rate)
    prior_risk : float
        The risk before this test was applied
    updated_risk : float
        The risk after this test was applied

    Returns:
    --------
    Dict[str, Any]
        Object with test impact data
    """
    return {
        "testType": test_type,
        "testResult": test_result,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "priorRisk": prior_risk,
        "updatedRisk": updated_risk,
    }
