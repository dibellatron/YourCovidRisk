"""
Unit conversion system for viral load measurements.

Converts between different viral load units:
- TCID₅₀/mL (50% tissue culture infectious dose per mL)
- Genome equivalents/mL (RNA copies/mL)
- Ct values (PCR cycle threshold)

All conversions standardize to log₁₀ RNA copies·mL⁻¹ for internal calculations.
"""

import numpy as np
from typing import Union, Dict, Any


def convert_lod_to_log_rna_copies(
    lod_value: float, 
    lod_units: str, 
    variant: str = "general"
) -> float:
    """
    Convert LoD from any units to log₁₀ RNA copies·mL⁻¹.
    
    Args:
        lod_value: Limit of detection value
        lod_units: "TCID50_per_mL", "ge_per_mL", or "Ct"
        variant: "general" or "omicron" (affects TCID50 conversion ratio)
    
    Returns: log₁₀ RNA copies·mL⁻¹
    
    Conversion ratios based on empirical literature:
    - General SARS-CoV-2: 1 TCID₅₀ ≈ 10⁴ RNA copies
    - Omicron: 1 TCID₅₀ ≈ 10⁵ RNA copies (conservative estimate)
    - Ct conversion: log₁₀(copies) = log₁₀(copies_ref) + (ct_ref - Ct)/slope
    """
    if lod_units == "ge_per_mL":
        return np.log10(lod_value)
    elif lod_units == "TCID50_per_mL":
        if variant == "omicron":
            copies_per_tcid50 = 1e5  # Conservative Omicron estimate
        else:
            copies_per_tcid50 = 1e4  # General SARS-CoV-2
        rna_copies = lod_value * copies_per_tcid50
        return np.log10(rna_copies)
    elif lod_units == "Ct":
        # Default calibration: Ct 30 ↔ 10⁴ copies/mL, slope +3.3
        ct_ref = 30  # Reference Ct
        copies_ref = 1e4  # copies/mL at reference
        slope = 3.3  # cycles per log₁₀
        log_copies = np.log10(copies_ref) + (ct_ref - lod_value) / slope
        return log_copies
    else:
        raise ValueError(f"Unknown LoD units: {lod_units}")


def convert_ct_to_log_rna_copies(
    ct_values: Union[float, np.ndarray], 
    assay_params: Dict[str, float] = None
) -> Union[float, np.ndarray]:
    """
    Convert Ct values to log₁₀ RNA copies·mL⁻¹.
    
    We anchor the Ct→copies curve by fixing Ct 30 = 10⁴ copies·mL⁻¹; all calibrations 
    derive the intercept from that anchor and a slope of +3.3 cycles per log₁₀.
    
    Formula: log₁₀(copies) = log₁₀(copies_ref) + (ct_ref - Ct)/slope
    
    Args:
        ct_values: Scalar Ct value or array of Ct values
        assay_params: Dict with 'ct_ref', 'copies_ref', 'slope' for assay calibration
    
    Returns: Scalar or array of log₁₀ RNA copies·mL⁻¹ (matches input type)
    """
    if assay_params is None:
        # Default calibration: Ct 30 ↔ 10⁴ copies/mL, slope +3.3
        assay_params = {'ct_ref': 30, 'copies_ref': 1e4, 'slope': 3.3}
    
    ct_ref = assay_params['ct_ref']
    copies_ref = assay_params['copies_ref']
    slope = assay_params['slope']
    
    return np.log10(copies_ref) + (ct_ref - ct_values) / slope


def standardize_lod_from_test_data(test_name: str, test_data: Dict[str, Any]) -> float:
    """
    Convert LoD from test performance data to standardized log₁₀ RNA copies·mL⁻¹.
    
    Args:
        test_name: Name of the test
        test_data: Test performance data containing 'lod_95' field
        
    Returns: LoD in log₁₀ RNA copies·mL⁻¹
    """
    lod_95 = test_data.get('lod_95')
    if lod_95 is None:
        raise ValueError(f"No LoD data available for test: {test_name}")
    
    # Determine units based on test type (from the implementation plan)
    molecular_tests = ["Lucira", "Metrix", "Pluslife"]
    
    if test_name in molecular_tests:
        # These are in genome equivalents/mL
        lod_units = "ge_per_mL"
    else:
        # All other tests are in TCID₅₀/mL
        lod_units = "TCID50_per_mL"
    
    return convert_lod_to_log_rna_copies(lod_95, lod_units, variant="general")


def validate_unit_conversion():
    """Run validation tests for unit conversion functions."""
    
    # Test 1: Round-trip Ct conversion
    test_ct = 30.0
    log_copies = convert_ct_to_log_rna_copies(test_ct)
    expected_log_copies = 4.0  # log₁₀(10⁴) = 4
    assert abs(log_copies - expected_log_copies) < 1e-10, f"Expected {expected_log_copies}, got {log_copies}"
    
    # Test 2: Ct slope relationship
    ct_25 = 25.0
    ct_30 = 30.0
    log_25 = convert_ct_to_log_rna_copies(ct_25)
    log_30 = convert_ct_to_log_rna_copies(ct_30)
    # 5 cycle difference should be 5/3.3 ≈ 1.515 log₁₀ difference
    expected_diff = 5.0 / 3.3
    actual_diff = log_25 - log_30
    assert abs(actual_diff - expected_diff) < 0.001, f"Expected {expected_diff}, got {actual_diff}"
    
    # Test 3: TCID₅₀ conversion
    lod_tcid50 = 1000.0
    log_copies_general = convert_lod_to_log_rna_copies(lod_tcid50, "TCID50_per_mL", "general")
    log_copies_omicron = convert_lod_to_log_rna_copies(lod_tcid50, "TCID50_per_mL", "omicron")
    # Should differ by exactly 1 log₁₀ (10x difference in conversion ratio)
    assert abs((log_copies_omicron - log_copies_general) - 1.0) < 1e-10
    
    # Test 4: Genome equivalents (should be identity)
    ge_value = 1e6
    log_copies_ge = convert_lod_to_log_rna_copies(ge_value, "ge_per_mL")
    expected_log_ge = np.log10(ge_value)
    assert abs(log_copies_ge - expected_log_ge) < 1e-10
    
    print("All unit conversion validation tests passed!")


if __name__ == "__main__":
    validate_unit_conversion()