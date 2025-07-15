from calculators.exposure_calculator import calculate_unified_transmission_exposure
from calculators.test_calculator import calculate_test_risk


def approx(a, b, tol=1e-12):
    return abs(a - b) <= tol


def test_calculate_test_risk_simple():
    # Symptomatic user, Metrix negative
    result = calculate_test_risk(
        symptoms="yes",
        test_types=["Metrix"],
        test_results=["negative"],
        covid_cautious="Moderately",
        covid_prevalence_input="",
        positivity_rate_input="",
        prior_probability_input="",
        advanced_flag="true",
    )

    # Expected value for this fixed input (Symptomatic users unadjusted by caution)
    assert approx(result["risk"], 0.009005223029357037)
    low, high = result["advanced_risk"]
    assert low <= result["risk"] <= high


def test_exposure_calculator_defaults():
    # All empty strings should use defaults and not raise error
    result = calculate_unified_transmission_exposure(*[""] * 15)
    assert "error" not in result
    # The risk should be a reasonable small positive number
    assert result["risk"] > 0
    assert result["risk"] < 0.01  # Should be less than 1%


def test_exposure_calculator_invalid():
    result = calculate_unified_transmission_exposure("abc", *[""] * 14)
    assert result == {"error": "Invalid input; please enter numeric values."}
