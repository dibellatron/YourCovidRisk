"""
Viral load distributions for infected individuals.

Uses empirical Omicron data from Liu et al. (2023) for symptom-specific distributions.
All distributions are in log₁₀ RNA copies·mL⁻¹ units.

Reference: Liu L, et al. Viral loads and duration of viral shedding in adult patients 
hospitalized with COVID-19 during the Omicron wave in Shanghai. 
Front Microbiol. 2023;14:1158932. DOI: 10.3389/fmicb.2023.1158932
"""

import numpy as np
from scipy import stats
from typing import Tuple, Dict, Any
from calculators.viral_load_unit_conversion import convert_ct_to_log_rna_copies


def get_omicron_viral_load_distribution(
    symptom_status: str, 
    assay_params: Dict[str, float] = None
) -> Tuple[float, float, str]:
    """
    Get log-normal distribution parameters for Omicron using empirical data.
    
    Args:
        symptom_status: "symptomatic" or "asymptomatic"
        assay_params: Assay calibration parameters (optional)
    
    Returns: (mu, sigma, data_quality) for LogNormal(mu, sigma²) in log₁₀ RNA copies·mL⁻¹
    
    Data sources:
    - Symptomatic mean Ct 25.9 from China BA.2 study (n=157)
    - Asymptomatic mean Ct 30.1 from China BA.2 study (n=157)
    - Conservative variance estimates to avoid over-specification
    """
    if symptom_status.lower() in ["symptomatic", "yes"]:
        ct_mean = 25.9  # Empirical Omicron data
        ct_std = 5.0    # Conservative estimate
        data_quality = "EMPIRICAL_MEAN"
    else:  # asymptomatic
        ct_mean = 30.1  # Empirical Omicron data
        ct_std = 5.5    # Slightly wider, conservative
        data_quality = "EMPIRICAL_MEAN"
    
    # Convert to log₁₀ RNA copies·mL⁻¹
    mu = convert_ct_to_log_rna_copies(ct_mean, assay_params)
    sigma = ct_std / 3.3  # Convert Ct std to log₁₀ scale
    
    return mu, sigma, data_quality


def create_viral_load_distribution(symptom_status: str) -> stats.lognorm:
    """
    Create a scipy lognormal distribution object for viral loads.
    
    Args:
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: scipy.stats.lognorm distribution in log₁₀ RNA copies·mL⁻¹
    """
    mu, sigma, _ = get_omicron_viral_load_distribution(symptom_status)
    
    # scipy.stats.lognorm uses (s, scale) parameterization where:
    # - s = sigma (shape parameter)
    # - scale = exp(mu) (scale parameter)
    # For our log₁₀ distribution: X ~ LogNormal(mu, sigma²) in log₁₀ scale
    # Convert to natural log scale for scipy: mu_ln = mu * ln(10), sigma_ln = sigma * ln(10)
    
    mu_ln = mu * np.log(10)
    sigma_ln = sigma * np.log(10)
    
    return stats.lognorm(s=sigma_ln, scale=np.exp(mu_ln))


def viral_load_pdf(v: np.ndarray, symptom_status: str) -> np.ndarray:
    """
    Probability density function for viral loads.
    
    Args:
        v: Array of viral load values in log₁₀ RNA copies·mL⁻¹
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: Array of probability densities
    """
    mu, sigma, _ = get_omicron_viral_load_distribution(symptom_status)
    
    # LogNormal PDF in log₁₀ scale
    # f(v) = (1 / (v * sigma * sqrt(2π))) * exp(-0.5 * ((log₁₀(v) - mu) / sigma)²)
    # But since v is already in log₁₀ scale, we use normal PDF directly
    
    return stats.norm.pdf(v, loc=mu, scale=sigma)


def viral_load_cdf(v: np.ndarray, symptom_status: str) -> np.ndarray:
    """
    Cumulative distribution function for viral loads.
    
    Args:
        v: Array of viral load values in log₁₀ RNA copies·mL⁻¹
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: Array of cumulative probabilities
    """
    mu, sigma, _ = get_omicron_viral_load_distribution(symptom_status)
    return stats.norm.cdf(v, loc=mu, scale=sigma)


def get_viral_load_stats(symptom_status: str) -> Dict[str, float]:
    """
    Get summary statistics for the viral load distribution.
    
    Args:
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: Dictionary with mean, std, percentiles in log₁₀ RNA copies·mL⁻¹
    """
    mu, sigma, data_quality = get_omicron_viral_load_distribution(symptom_status)
    
    # For normal distribution in log₁₀ scale
    percentiles = [5, 25, 50, 75, 95]
    pctile_values = stats.norm.ppf([p/100 for p in percentiles], loc=mu, scale=sigma)
    
    return {
        'mean': mu,
        'std': sigma,
        'data_quality': data_quality,
        'percentiles': dict(zip(percentiles, pctile_values)),
        'empirical_ct_mean': 25.9 if symptom_status.lower() in ["symptomatic", "yes"] else 30.1
    }


def validate_viral_load_distributions():
    """Run validation tests for viral load distributions."""
    
    # Test 1: Mean values should match empirical Ct data
    mu_symp, sigma_symp, _ = get_omicron_viral_load_distribution("symptomatic")
    mu_asymp, sigma_asymp, _ = get_omicron_viral_load_distribution("asymptomatic")
    
    # Convert back to Ct to verify
    ct_symp = convert_ct_to_log_rna_copies(25.9)
    ct_asymp = convert_ct_to_log_rna_copies(30.1)
    
    assert abs(mu_symp - ct_symp) < 1e-10, f"Symptomatic mean mismatch: {mu_symp} vs {ct_symp}"
    assert abs(mu_asymp - ct_asymp) < 1e-10, f"Asymptomatic mean mismatch: {mu_asymp} vs {ct_asymp}"
    
    # Test 2: Symptomatic should have higher mean viral load (lower Ct)
    assert mu_symp > mu_asymp, "Symptomatic should have higher viral load than asymptomatic"
    
    # Test 3: Difference should match empirical data (4.2 Ct cycles ≈ 4.2/3.3 log₁₀)
    # Note: Lower Ct = higher viral load, so symptomatic (lower Ct) should have higher viral load
    # The conversion formula: log10(copies) = log10(ref) + (ct_ref - ct)/slope
    # So lower Ct gives higher log10(copies), which is correct
    ct_diff = 30.1 - 25.9  # Ct difference (asymptomatic - symptomatic)
    expected_viral_load_diff = ct_diff / 3.3  # Higher Ct difference → higher viral load difference
    actual_diff = mu_symp - mu_asymp  # Symptomatic should be higher
    assert abs(actual_diff - expected_viral_load_diff) < 0.001, f"Expected diff {expected_viral_load_diff}, got {actual_diff}"
    
    # Test 4: PDF integration should sum to ~1
    v_range = np.linspace(0, 10, 1000)  # log₁₀ RNA copies from 1 to 10^10
    pdf_symp = viral_load_pdf(v_range, "symptomatic")
    integral_symp = np.trapz(pdf_symp, v_range)
    assert abs(integral_symp - 1.0) < 0.01, f"PDF integration error: {integral_symp}"
    
    # Test 5: CDF should go from 0 to 1
    cdf_low = viral_load_cdf(np.array([-5]), "symptomatic")[0]
    cdf_high = viral_load_cdf(np.array([15]), "symptomatic")[0]
    assert cdf_low < 0.01, f"CDF at low end should be ~0, got {cdf_low}"
    assert cdf_high > 0.99, f"CDF at high end should be ~1, got {cdf_high}"
    
    print("All viral load distribution validation tests passed!")


if __name__ == "__main__":
    validate_viral_load_distributions()
    
    # Print summary statistics
    for status in ["symptomatic", "asymptomatic"]:
        print(f"\n{status.title()} viral load distribution:")
        stats_dict = get_viral_load_stats(status)
        print(f"  Mean: {stats_dict['mean']:.3f} log₁₀ RNA copies/mL")
        print(f"  Std:  {stats_dict['std']:.3f} log₁₀ RNA copies/mL")
        print(f"  Empirical Ct mean: {stats_dict['empirical_ct_mean']}")
        print(f"  Percentiles: {stats_dict['percentiles']}")