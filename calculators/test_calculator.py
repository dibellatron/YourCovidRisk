"""Module for calculating Covid risk based on test results and additional inputs.

This file previously contained both the calculation logic *and* a standalone
Flask application.  To keep imports lightweight and avoid accidental side
effects, the web‑specific code has been removed; only the pure calculation
function remains.  All logic is *identical* to the original implementation –
no behavioural changes were made.

IMPORTANT: This Python file is the source of truth for all calculation explanations
and text content. The frontend JavaScript (static/js/calculations/calculationDisplay.js) 
should only handle the display logic, while the actual text content is generated here.
Any text changes should be made in this file, not in the JavaScript.
"""

# No third‑party imports required – standard library only.
from typing import Any, Dict, List, Tuple, Optional

from flask import url_for

from calculators.formatting import format_percent
from calculators.test_performance_data import get_performance, TEST_PERFORMANCE
from calculators.monte_carlo_ci import calculate_monte_carlo_ci_uniform, calculate_monte_carlo_ci_beta, calculate_min_max_range, calculate_monte_carlo_ci_full_uncertainty, calculate_monte_carlo_ci_prevalence_uncertainty, calculate_monte_carlo_ci_error_state_bayesian_fast, get_positivity_uncertainty_params
from calculators.bayesian_test_integration import create_bayesian_calculator

# Mapping of state codes to prevalence CSV region names
REGION_MAP = {
    # Northeast
    "MD": "Northeast", "PA": "Northeast", "DE": "Northeast", "NY": "Northeast",
    "MA": "Northeast", "VT": "Northeast", "CT": "Northeast", "NJ": "Northeast", 
    "ME": "Northeast", "NH": "Northeast", "RI": "Northeast",
    # South
    "AL": "South", "AR": "South", "TX": "South", "KY": "South", "GA": "South",
    "VA": "South", "TN": "South", "LA": "South", "FL": "South", "DC": "South",
    "NC": "South", "SC": "South", "MS": "South", "OK": "South", "WV": "South",
    # Midwest
    "NE": "Midwest", "OH": "Midwest", "IA": "Midwest", "WI": "Midwest",
    "MO": "Midwest", "MI": "Midwest", "IL": "Midwest", "MN": "Midwest",
    "IN": "Midwest", "KS": "Midwest", "ND": "Midwest", "SD": "Midwest",
    # West
    "AK": "West", "WA": "West", "NM": "West", "CA": "West", "OR": "West",
    "ID": "West", "MT": "West", "NV": "West", "UT": "West", "CO": "West",
    "WY": "West", "HI": "West", "AZ": "West",
}

# States for which Walgreens positivity data is available (covid_current.csv)
POS_STATES = {
    "AL",
    "AR",
    "AZ",
    "CA",
    "CO",
    "DE",
    "FL",
    "GA",
    "IL",
    "IN",
    "MD",
    "MI",
    "MN",
    "MO",
    "MS",
    "NC",
    "NE",
    "NJ",
    "NM",
    "NY",
    "OH",
    "OK",
    "PA",
    "SC",
    "TN",
    "TX",
    "VA",
    "WA",
    "WI",
}


def calculate_test_risk(
    symptoms: str,
    test_types: list,
    test_results: list,
    covid_exposure: str,
    covid_prevalence_input: str,
    positivity_rate_input: str,
    prior_probability_input: str,
    advanced_flag: str,
    manual_prior: bool = False,
    state: str = "",
    calculate_monte_carlo: bool = False,
    prevalence_from_pmc: bool = False,
    positivity_from_walgreens: bool = False,
    used_national_positivity_fallback: bool = False,
    error_correlation: Optional[float] = None,
) -> dict:
    """
    Calculate the Covid risk based on test information and other inputs.

    Parameters are unchanged from the original implementation.  See
    app.py for usage.
    """

    # Prepare tests list
    tests = [
        {"test_type": tt, "test_result": tr} for tt, tr in zip(test_types, test_results)
    ]

    # All tests now have confidence intervals
    has_confidence_intervals = True

    # Helper function to get PMC prevalence data
    def get_pmc_prevalence(state_code):
        """Get COVID prevalence from PMC data based on state."""
        import os
        import csv
        
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        csv_path = os.path.join(root_dir, "PMC", "Prevalence", "prevalence_current.csv")
        
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                row = next(reader, None)
                region = REGION_MAP.get(state_code.upper() if state_code else "", "National")
                if row and region in row:
                    val = row[region]
                    if val.endswith("%"):
                        val = val[:-1]
                    return float(val)
        except (FileNotFoundError, KeyError, ValueError):
            pass
        
        return 1.0  # Fallback to 1.0% if data unavailable

    # Process advanced parameters only if advanced mode is enabled
    if advanced_flag == "true":
        if not covid_prevalence_input:
            calc_covid_prevalence = get_pmc_prevalence(state)
        else:
            calc_covid_prevalence = float(covid_prevalence_input)

        if not positivity_rate_input:
            calc_positivity_rate = 15.0  # Will be overridden if we can read from CSV
        else:
            calc_positivity_rate = float(positivity_rate_input)
            
        # Use manual prior probability if provided (will be handled in main logic below)
    else:
        # Advanced mode is disabled, use PMC data for prevalence
        calc_covid_prevalence = get_pmc_prevalence(state)
        if not positivity_rate_input:
            calc_positivity_rate = 15.0  # Fallback value
        else:
            calc_positivity_rate = float(positivity_rate_input)

    # Store the raw prevalence for step 1 display (before any adjustments)
    raw_prevalence = None
    
    # Handle "I'm not sure" symptom option by calculating both pathways
    is_unsure_symptoms = symptoms.lower() == "i'm not sure"
    
    # Check if manual prior is provided (helper variable for cleaner logic)
    manual_prior_provided = (advanced_flag == "true" and 
                           prior_probability_input != "" and 
                           prior_probability_input is not None)
    
    # For unsure symptoms, we'll calculate both symptomatic and asymptomatic risks separately
    if is_unsure_symptoms:
        if manual_prior_provided:
            # Case 1: Manual prior provided - use for both pathways, skip automatic calculation
            manual_prior_value = float(prior_probability_input) / 100.0
            symptomatic_risk = manual_prior_value
            asymptomatic_risk = manual_prior_value
            symptomatic_risk_old = manual_prior_value
            asymptomatic_risk_old = manual_prior_value
            
            # Store values (no exposure adjustment when manual prior is used)
            symptomatic_risk_pre_exposure = symptomatic_risk
            asymptomatic_risk_pre_exposure = asymptomatic_risk
            symptomatic_risk_old_pre_exposure = symptomatic_risk_old
            asymptomatic_risk_old_pre_exposure = asymptomatic_risk_old
            
            original_initial_risk = manual_prior_value
        else:
            # Case 2: No manual prior - calculate both pathways automatically
            # Calculate symptomatic pathway
            symptomatic_risk = calc_positivity_rate / 100.0
            symptomatic_risk_old = symptomatic_risk
            
            # Calculate asymptomatic pathway (uses both prevalence AND positivity rate)
            raw_prevalence = calc_covid_prevalence / 100.0
            
            # OLD METHOD for asymptomatic
            asymptomatic_risk_old = (0.32 * calc_covid_prevalence) / (
                100 - 0.68 * calc_covid_prevalence
            )
            
            # NEW METHOD for asymptomatic
            p = calc_covid_prevalence / 100.0  # Overall Covid prevalence
            a = 0.32  # Asymptomatic rate among infected
            r = calc_positivity_rate / 100.0  # Positivity rate P(Covid | symptomatic)
            
            # Calculate s = P(symptomatic | uninfected) using back-solve formula
            if r > 0 and (1 - p) > 0:
                s = (p * (1 - a) * (1 - r)) / (r * (1 - p))
                s = max(0, min(1, s))
            else:
                s = 0
            
            # Apply corrected formula for asymptomatic
            numerator = p * a
            denominator = numerator + (1 - p) * (1 - s)
            asymptomatic_risk = numerator / denominator if denominator > 0 else asymptomatic_risk_old
            
            # Store values for later averaging (before exposure adjustment)
            symptomatic_risk_pre_exposure = symptomatic_risk
            asymptomatic_risk_pre_exposure = asymptomatic_risk
            symptomatic_risk_old_pre_exposure = symptomatic_risk_old
            asymptomatic_risk_old_pre_exposure = asymptomatic_risk_old
            
            # For step 1 display, we'll show both pathways
            original_initial_risk = (symptomatic_risk + asymptomatic_risk) / 2.0
        
    # Compute the initial risk (only use manual prior if advanced mode is enabled)
    elif manual_prior_provided:
        initial_risk = float(prior_probability_input) / 100.0
        initial_risk_old = initial_risk
        original_initial_risk = initial_risk  # For manual prior, this is the entered value
    else:
        if symptoms.lower() == "yes":
            # For symptomatic users, use positivity rate directly
            initial_risk = calc_positivity_rate / 100.0
            initial_risk_old = initial_risk
            original_initial_risk = initial_risk  # For symptomatic, this is the positivity rate
        else:
            # For asymptomatic users, implement both old and new methods
            raw_prevalence = calc_covid_prevalence / 100.0  # Store raw prevalence (e.g., 1.0%)
            
            # OLD METHOD: Naive Bayesian calculation assuming P(asymptomatic | uninfected) = 1
            initial_risk_old = (0.32 * calc_covid_prevalence) / (
                100 - 0.68 * calc_covid_prevalence
            )
            
            # NEW METHOD: Corrected Bayesian calculation using positivity rate
            p = calc_covid_prevalence / 100.0  # Overall Covid prevalence
            a = 0.32  # Asymptomatic rate among infected
            r = calc_positivity_rate / 100.0  # Positivity rate P(Covid | symptomatic)
            
            # Calculate s = P(symptomatic | uninfected) using back-solve formula
            # s = (p × (1 - a) × (1 - r)) / (r × (1 - p))
            if r > 0 and (1 - p) > 0:
                s = (p * (1 - a) * (1 - r)) / (r * (1 - p))
                # Ensure s is between 0 and 1
                s = max(0, min(1, s))
            else:
                s = 0  # Fallback if calculation would be invalid
            
            # Apply corrected formula: P(Covid | asymptomatic) = (p × a) / (p × a + (1 - p) × (1 - s))
            numerator = p * a
            denominator = numerator + (1 - p) * (1 - s)
            initial_risk = numerator / denominator if denominator > 0 else initial_risk_old
            
            original_initial_risk = raw_prevalence  # Store raw prevalence for step 1 display
    
    # Handle exposure adjustment for unsure symptoms case
    if is_unsure_symptoms:
        if manual_prior_provided:
            # Manual prior case: no exposure adjustment, use the manual prior values directly
            initial_risk = (symptomatic_risk_pre_exposure + asymptomatic_risk_pre_exposure) / 2.0
            initial_risk_old = (symptomatic_risk_old_pre_exposure + asymptomatic_risk_old_pre_exposure) / 2.0
            
            # Set variables needed for Bayesian calculation (no adjustment applied)
            asymptomatic_risk_adjusted = asymptomatic_risk_pre_exposure
            asymptomatic_risk_old_adjusted = asymptomatic_risk_old_pre_exposure
        else:
            # Automatic calculation case: apply exposure adjustment only to asymptomatic pathway
            exposure_multiplier = {"Much more": 5.0, "Somewhat more": 2.0, "About average": 1.0, 
                                   "Somewhat less": 0.5, "Much less": 0.1, "Almost none": 0.01}.get(covid_exposure, 1.0)
            
            # Apply exposure adjustment to asymptomatic pathway only
            asymptomatic_risk_adjusted = asymptomatic_risk_pre_exposure * exposure_multiplier
            asymptomatic_risk_old_adjusted = asymptomatic_risk_old_pre_exposure * exposure_multiplier
            
            # Calculate the arithmetic mean of symptomatic and (exposure-adjusted) asymptomatic risks
            initial_risk = (symptomatic_risk_pre_exposure + asymptomatic_risk_adjusted) / 2.0
            initial_risk_old = (symptomatic_risk_old_pre_exposure + asymptomatic_risk_old_adjusted) / 2.0
        
        # For step display purposes
        step1_risk = initial_risk
        step1_risk_old = initial_risk_old
    else:
        # Store the risk after step 1 (after asymptomatic adjustment) but before step 2 (caution adjustment)
        step1_risk = initial_risk
        step1_risk_old = initial_risk_old

        # Adjust risk based on covid exposure level only for asymptomatic users,
        # and not when using a manual prior probability
        if not manual_prior_provided and symptoms.lower() == "no":
            if covid_exposure == "Much more":
                initial_risk *= 5.0
                initial_risk_old *= 5.0
            elif covid_exposure == "Somewhat more":
                initial_risk *= 2.0
                initial_risk_old *= 2.0
            elif covid_exposure == "About average":
                # No adjustment needed (1.0x)
                pass
            elif covid_exposure == "Somewhat less":
                initial_risk *= 0.5
                initial_risk_old *= 0.5
            elif covid_exposure == "Much less":
                initial_risk *= 0.1
                initial_risk_old *= 0.1
            elif covid_exposure == "Almost none":
                initial_risk *= 0.01
                initial_risk_old *= 0.01

    basic_risk = initial_risk
    basic_risk_old = initial_risk_old

    # ------------------------------------------------------------------
    # Compute the basic risk using Bayesian models (naive for single tests, 
    # Error State Bayesian for multiple tests)
    # ------------------------------------------------------------------
    if is_unsure_symptoms:
        # For "I'm not sure", calculate both symptomatic and asymptomatic pathways then average
        bayesian_calc = create_bayesian_calculator(error_correlation)
        
        # Calculate symptomatic pathway
        symptomatic_basic_risk, symptomatic_test_impacts = bayesian_calc.calculate_test_impacts(
            prior_probability=symptomatic_risk_pre_exposure,
            test_types=test_types,
            test_results=test_results,
            symptomatic=True
        )
        
        # Calculate asymptomatic pathway (with exposure adjustment)
        asymptomatic_basic_risk, asymptomatic_test_impacts = bayesian_calc.calculate_test_impacts(
            prior_probability=asymptomatic_risk_adjusted,
            test_types=test_types,
            test_results=test_results,
            symptomatic=False
        )
        
        # Average the final results
        basic_risk = (symptomatic_basic_risk + asymptomatic_basic_risk) / 2.0
        
        # For test_impacts, we'll use the symptomatic values for display purposes
        # (since the user interface expects a single set of impacts)
        test_impacts = symptomatic_test_impacts
        symptomatic = True  # For display purposes in explanations
    else:
        symptomatic = symptoms.lower() == "yes"
        
        # Create Bayesian calculator
        bayesian_calc = create_bayesian_calculator(error_correlation)
        
        # Calculate test impacts using appropriate model
        basic_risk, test_impacts = bayesian_calc.calculate_test_impacts(
            prior_probability=initial_risk,
            test_types=test_types,
            test_results=test_results,
            symptomatic=symptomatic
        )
    
    # For backward compatibility with old method calculation
    # (used in Monte Carlo scenarios)
    if is_unsure_symptoms:
        # Calculate old method for both symptomatic and asymptomatic pathways, then average
        symptomatic_risk_old_final = symptomatic_risk_pre_exposure
        asymptomatic_risk_old_final = asymptomatic_risk_adjusted
        
        # Apply tests to symptomatic pathway
        for tt, tr in zip(test_types, test_results):
            perf = get_performance(tt, True)  # symptomatic=True
            sensitivity = perf["sens"]
            specificity = perf["spec"]

            if tr == "positive":
                numerator_old = sensitivity * symptomatic_risk_old_final
                denominator_old = numerator_old + (1 - specificity) * (1 - symptomatic_risk_old_final)
                symptomatic_risk_old_final = numerator_old / denominator_old if denominator_old != 0 else 1.0
            elif tr == "negative":
                numerator_old = (1 - sensitivity) * symptomatic_risk_old_final
                denominator_old = numerator_old + specificity * (1 - symptomatic_risk_old_final)
                symptomatic_risk_old_final = numerator_old / denominator_old if denominator_old != 0 else 0.0
        
        # Apply tests to asymptomatic pathway
        for tt, tr in zip(test_types, test_results):
            perf = get_performance(tt, False)  # symptomatic=False
            sensitivity = perf["sens"]
            specificity = perf["spec"]

            if tr == "positive":
                numerator_old = sensitivity * asymptomatic_risk_old_final
                denominator_old = numerator_old + (1 - specificity) * (1 - asymptomatic_risk_old_final)
                asymptomatic_risk_old_final = numerator_old / denominator_old if denominator_old != 0 else 1.0
            elif tr == "negative":
                numerator_old = (1 - sensitivity) * asymptomatic_risk_old_final
                denominator_old = numerator_old + specificity * (1 - asymptomatic_risk_old_final)
                asymptomatic_risk_old_final = numerator_old / denominator_old if denominator_old != 0 else 0.0
        
        # Average the final old method results
        basic_risk_old = (symptomatic_risk_old_final + asymptomatic_risk_old_final) / 2.0
        symptomatic_old = True  # For display purposes
    else:
        basic_risk_old = basic_risk
        symptomatic_old = symptomatic
        for tt, tr in zip(test_types, test_results):
            perf = get_performance(tt, symptomatic_old)
            sensitivity = perf["sens"]
            specificity = perf["spec"]

            # Apply test to old method
            if tr == "positive":
                numerator_old = sensitivity * basic_risk_old
                denominator_old = numerator_old + (1 - specificity) * (1 - basic_risk_old)
                basic_risk_old = numerator_old / denominator_old if denominator_old != 0 else 1.0
            elif tr == "negative":
                numerator_old = (1 - sensitivity) * basic_risk_old
                denominator_old = numerator_old + specificity * (1 - basic_risk_old)
                basic_risk_old = numerator_old / denominator_old if denominator_old != 0 else 0.0

    risk = basic_risk
    risk_old = basic_risk_old

    # Advanced risk calculation: compute risk interval over all combinations
    risk_possibilities = [initial_risk]

    for tt, tr in zip(test_types, test_results):
        new_risks = []

        perf = get_performance(tt, symptomatic)
        sens_low, sens_high = perf["sens_low"], perf["sens_high"]
        spec_low, spec_high = perf["spec_low"], perf["spec_high"]

        for p in risk_possibilities:
            if tr == "positive":
                denom1 = sens_low * p + (1 - spec_low) * (1 - p)
                denom2 = sens_low * p + (1 - spec_high) * (1 - p)
                denom3 = sens_high * p + (1 - spec_low) * (1 - p)
                denom4 = sens_high * p + (1 - spec_high) * (1 - p)

                r1 = (sens_low * p) / denom1 if denom1 != 0 else 1.0
                r2 = (sens_low * p) / denom2 if denom2 != 0 else 1.0
                r3 = (sens_high * p) / denom3 if denom3 != 0 else 1.0
                r4 = (sens_high * p) / denom4 if denom4 != 0 else 1.0
                new_risks.extend([r1, r2, r3, r4])
            elif tr == "negative":
                denom1 = (1 - sens_high) * p + spec_high * (1 - p)
                denom2 = (1 - sens_high) * p + spec_low * (1 - p)
                denom3 = (1 - sens_low) * p + spec_high * (1 - p)
                denom4 = (1 - sens_low) * p + spec_low * (1 - p)

                r1 = ((1 - sens_high) * p) / denom1 if denom1 != 0 else 0.0
                r2 = ((1 - sens_high) * p) / denom2 if denom2 != 0 else 0.0
                r3 = ((1 - sens_low) * p) / denom3 if denom3 != 0 else 0.0
                r4 = ((1 - sens_low) * p) / denom4 if denom4 != 0 else 0.0
                new_risks.extend([r1, r2, r3, r4])
        risk_possibilities = new_risks

    if risk_possibilities:
        risk_low = min(risk_possibilities)
        risk_high = max(risk_possibilities)
        advanced_risk = (risk_low, risk_high)
    else:
        advanced_risk = (initial_risk, initial_risk)
    
    # Calculate all uncertainty methods if requested
    monte_carlo_risk = None
    monte_carlo_beta_risk = None
    monte_carlo_full_risk = None
    monte_carlo_prevalence_risk = None
    min_max_range = None
    
    # Set template variables for Monte Carlo (need these before Monte Carlo calculations)
    if advanced_flag == "true":
        template_covid_prevalence = covid_prevalence_input
        template_positivity_rate = positivity_rate_input
        template_prior_probability = prior_probability_input
    else:
        template_covid_prevalence = ""
        template_positivity_rate = ""
        template_prior_probability = ""
    
    
    if calculate_monte_carlo and has_confidence_intervals:
        # Extract positivity uncertainty parameters
        import os
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        csv_pos_path = os.path.join(root_dir, "Walgreens", "walgreens_clean", "covid_current.csv")
        positivity_uncertainty_params = get_positivity_uncertainty_params(state, csv_pos_path)
        
        # Determine if manual prior was provided (only when advanced mode is enabled)
        manual_prior_value = None
        if advanced_flag == "true" and prior_probability_input and prior_probability_input.strip():
            manual_prior_value = float(prior_probability_input) / 100.0
        
        # Handle "I'm not sure" case with mixture Monte Carlo approach
        if is_unsure_symptoms:
            # Most statistically rigorous approach: run separate Monte Carlo simulations for both 
            # symptomatic and asymptomatic cases, then average the results
            region = REGION_MAP.get(state.upper() if state else "", "National")
            
            if len(test_types) > 1:
                # Multiple tests: Use Error State Bayesian for both scenarios
                symptomatic_mc = calculate_monte_carlo_ci_error_state_bayesian_fast(
                    "yes",  # Symptomatic scenario
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    region=region,
                    error_correlation=error_correlation or 0.3,
                    num_simulations=2000,
                    confidence_levels=[0.51, 0.99]
                )
                
                asymptomatic_mc = calculate_monte_carlo_ci_error_state_bayesian_fast(
                    "no",  # Asymptomatic scenario
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    region=region,
                    error_correlation=error_correlation or 0.3,
                    num_simulations=2000,
                    confidence_levels=[0.51, 0.99]
                )
                
                # Average the results from both scenarios
                if symptomatic_mc and asymptomatic_mc:
                    monte_carlo_prevalence_risk = {}
                    for confidence_level in [0.51, 0.99]:
                        # Convert to string key to match template expectations
                        str_key = str(confidence_level)
                        if str_key in symptomatic_mc and str_key in asymptomatic_mc:
                            symp_lower, symp_upper = symptomatic_mc[str_key]
                            asymp_lower, asymp_upper = asymptomatic_mc[str_key]
                            # Average the bounds
                            averaged_lower = (symp_lower + asymp_lower) / 2
                            averaged_upper = (symp_upper + asymp_upper) / 2
                            monte_carlo_prevalence_risk[str_key] = (averaged_lower, averaged_upper)
                else:
                    monte_carlo_prevalence_risk = None
                monte_carlo_full_risk = None
                
            else:
                # Single test: Use existing methods for both scenarios then average
                symptomatic_full = calculate_monte_carlo_ci_full_uncertainty(
                    "yes",  # Symptomatic scenario
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    confidence_levels=[0.51, 0.99]
                )
                
                asymptomatic_full = calculate_monte_carlo_ci_full_uncertainty(
                    "no",  # Asymptomatic scenario
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    confidence_levels=[0.51, 0.99]
                )
                
                # Average the results from both scenarios
                if symptomatic_full and asymptomatic_full:
                    monte_carlo_full_risk = {}
                    for confidence_level in [0.51, 0.99]:
                        # Convert to string key to match template expectations
                        str_key = str(confidence_level)
                        if str_key in symptomatic_full and str_key in asymptomatic_full:
                            symp_lower, symp_upper = symptomatic_full[str_key]
                            asymp_lower, asymp_upper = asymptomatic_full[str_key]
                            # Average the bounds
                            averaged_lower = (symp_lower + asymp_lower) / 2
                            averaged_upper = (symp_upper + asymp_upper) / 2
                            monte_carlo_full_risk[str_key] = (averaged_lower, averaged_upper)
                else:
                    monte_carlo_full_risk = None
                
                # Also do prevalence uncertainty method
                symptomatic_prev = calculate_monte_carlo_ci_prevalence_uncertainty(
                    "yes",  # Symptomatic scenario
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    region=region,
                    confidence_levels=[0.51, 0.99]
                )
                
                asymptomatic_prev = calculate_monte_carlo_ci_prevalence_uncertainty(
                    "no",  # Asymptomatic scenario
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    region=region,
                    confidence_levels=[0.51, 0.99]
                )
                
                # Average the results from both scenarios
                if symptomatic_prev and asymptomatic_prev:
                    monte_carlo_prevalence_risk = {}
                    for confidence_level in [0.51, 0.99]:
                        # Convert to string key to match template expectations
                        str_key = str(confidence_level)
                        if str_key in symptomatic_prev and str_key in asymptomatic_prev:
                            symp_lower, symp_upper = symptomatic_prev[str_key]
                            asymp_lower, asymp_upper = asymptomatic_prev[str_key]
                            # Average the bounds
                            averaged_lower = (symp_lower + asymp_lower) / 2
                            averaged_upper = (symp_upper + asymp_upper) / 2
                            monte_carlo_prevalence_risk[str_key] = (averaged_lower, averaged_upper)
                else:
                    monte_carlo_prevalence_risk = None
        else:
            # Standard case (not "I'm not sure"): use existing logic
            # Choose appropriate Monte Carlo method based on number of tests
            region = REGION_MAP.get(state.upper() if state else "", "National")
            
            if len(test_types) > 1:
                # Multiple tests: Use Error State Bayesian
                monte_carlo_prevalence_risk = calculate_monte_carlo_ci_error_state_bayesian_fast(
                    symptoms,
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    region=region,
                    error_correlation=error_correlation or 0.3,
                    num_simulations=2000,  # Increased for better stability
                    confidence_levels=[0.51, 0.99]
                )
                monte_carlo_full_risk = None
                
            else:
                # Single test: Use existing methods (no Error State modeling needed)
                
                # Method 4: Full Uncertainty Propagation - Most complete analysis including positivity rate uncertainty
                # Combines Beta distributions for test performance with Beta distributions for positivity rates
                # based on testing volume from covid_current.csv, providing the most comprehensive uncertainty analysis
                monte_carlo_full_risk = calculate_monte_carlo_ci_full_uncertainty(
                    symptoms,
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    confidence_levels=[0.51, 0.99]
                )
                
                # Method 5: Enhanced Prevalence Uncertainty - Incorporates full Bayesian prevalence distributions
                # Uses PrevalenceEstimator from wastewater modeling to generate probability distributions
                # based on regional wastewater levels, providing scientifically-grounded prevalence uncertainty
                region = REGION_MAP.get(state.upper() if state else "", "National")
                monte_carlo_prevalence_risk = calculate_monte_carlo_ci_prevalence_uncertainty(
                    symptoms,
                    test_types,
                    test_results,
                    template_covid_prevalence,
                    template_positivity_rate,
                    positivity_uncertainty_params,
                    covid_exposure,
                    manual_prior_value,
                    region=region,
                    confidence_levels=[0.51, 0.99]
                )
        
        # Keep other methods commented out for potential future use:
        
        # Method 1: Min-Max Range - Shows absolute bounds using extreme test performance values
        # Uses only sens_low/sens_high and spec_low/spec_high bounds for most conservative range
        # min_max_range = calculate_min_max_range(
        #     symptoms, 
        #     test_types, 
        #     test_results,
        #     initial_risk
        # )
        
        # Method 2: Uniform Monte Carlo - Original method sampling uniformly between published bounds
        # Uses uniform distributions between sens_low/sens_high and spec_low/spec_high
        # monte_carlo_risk = calculate_monte_carlo_ci_uniform(
        #     symptoms, 
        #     test_types, 
        #     test_results,
        #     initial_risk,
        #     confidence_levels=[0.501, 0.95, 0.99, 0.999]
        # )
        
        # Method 3: Beta Monte Carlo - Uses proper statistical distributions from study sample sizes
        # Creates Beta distributions using k/n values from clinical studies for more realistic uncertainty
        # monte_carlo_beta_risk = calculate_monte_carlo_ci_beta(
        #     symptoms, 
        #     test_types, 
        #     test_results,
        #     initial_risk,
        #     confidence_levels=[0.501, 0.95, 0.99, 0.999]
        # )

    # Template variables already set earlier before Monte Carlo calculations

    # Create detailed calculation steps

    # Build detailed calculation steps with formulas and contextual explanations
    # Use hard-coded list of states with positivity data

    if manual_prior_provided:
        # The exact wording here is important - the frontend JS uses it to detect manual prior mode
        formatted_prior = format_percent(original_initial_risk)
        step1_detail = (
            f"We use the entered prior probability of <strong>{formatted_prior}</strong> as the starting probability."
        )
    elif is_unsure_symptoms:
        # Simple approach for "I'm not sure" case - just show methodology and results summary
        symptomatic_final = format_percent(symptomatic_basic_risk)
        asymptomatic_final = format_percent(asymptomatic_basic_risk)
        final_average = format_percent(risk)
        
        # Create simple, clean explanation
        step1_detail = (
            f"<strong>Step 0: Methodology</strong><br>"
            f"Since you're unsure about your symptom status, we calculate your probability under both scenarios and average them, treating you as 50% likely to be symptomatic and 50% likely to be asymptomatic.<br><br>"
            f"<strong>Step 1: Results Summary</strong><br>"
            f"• <strong>If you are symptomatic:</strong> {symptomatic_final} probability of having COVID<br>"
            f"• <strong>If you are asymptomatic:</strong> {asymptomatic_final} probability of having COVID<br>"
            f"• <strong>Your averaged probability of having COVID:</strong> {final_average}<br><br>"
            f"For detailed step-by-step explanations of how these individual probabilities were calculated, please select \"Yes\" or \"No\" for symptoms to see the full calculations."
        )
    elif symptoms.lower() == "yes":
        p_prior = format_percent(original_initial_risk)
        
        # Check if user manually entered a positivity rate in advanced settings
        if positivity_rate_input and not positivity_from_walgreens:
            # User provided a positivity rate
            step1_detail = (
                f"For symptomatic individuals, we use the entered positivity rate of {p_prior} for the starting probability."
            )
        else:
            # Default behavior using Walgreens data
            base = (
                "For symptomatic individuals, we use the local test positivity rate from "
                'the <a href="https://www.walgreens.com/healthcare-solutions/covid-19-index" '
                'target="_blank" rel="noopener">Walgreens Respiratory Index</a> '
                "for the starting probability."
            )
            if not state:
                state_note = f" Since no state was selected, we use the national positivity rate of {p_prior}."
            elif state.upper() in POS_STATES and positivity_from_walgreens and not used_national_positivity_fallback:
                state_note = (
                    f" Since {state} was selected, we use its positivity rate of {p_prior}."
                )
            else:
                state_note = (
                    f" Positivity data is not currently available for {state}, so we use "
                    f"the national positivity rate of {p_prior}."
                )
            step1_detail = f"{base}{state_note}"
    else:
        # For asymptomatic individuals
        X = calc_covid_prevalence
        adjusted = X * 0.32
        asymp_link = (
            '<a href="https://europepmc.org/article/PMC/PMC9321237" target="_blank" rel="noopener">'
            "about 32% of currently infected individuals are asymptomatic</a>"
        )
        p_prev = format_percent(X / 100)
        # Use the actual formula result for display
        p_adj = format_percent(step1_risk)
        
        # Helper function to format intermediate calculations to 2 decimal places
        def format_intermediate_percent(value):
            """Format percentage with exactly 2 decimal places for intermediate calculations"""
            percent = value * 100
            return f"{percent:.2f}%"
        
        # Calculate intermediate values for detailed explanation (using 2 decimal places)
        prob_covid_and_asymp = format_intermediate_percent((0.32 * X) / 100)  # P(Covid and asymptomatic)
        prob_covid_and_symp = format_intermediate_percent((0.68 * X) / 100)   # P(Covid and symptomatic)
        positivity_rate_display = format_intermediate_percent(calc_positivity_rate / 100)
        
        # Calculate derived values for explanation
        # Convert to decimals for proper calculation
        prevalence_decimal = X / 100  # Convert from percentage to decimal
        positivity_decimal = calc_positivity_rate / 100  # Convert from percentage to decimal
        
        # P(Covid and symptomatic) as decimal = 0.68 × prevalence
        prob_covid_and_symp_decimal = 0.68 * prevalence_decimal
        
        # P(symptomatic) = P(Covid and symptomatic) / P(Covid | symptomatic)
        total_symptomatic_decimal = prob_covid_and_symp_decimal / positivity_decimal if positivity_decimal > 0 else 0
        
        # P(asymptomatic) = 1 - P(symptomatic)
        total_asymptomatic_decimal = 1 - total_symptomatic_decimal
        
        total_symptomatic_display = format_intermediate_percent(total_symptomatic_decimal)
        total_asymptomatic_display = format_intermediate_percent(total_asymptomatic_decimal)
        
        # Check if user manually entered a Covid prevalence value in advanced settings
        if covid_prevalence_input and not prevalence_from_pmc:
            # User provided a Covid prevalence value
            if positivity_rate_input and not positivity_from_walgreens:
                # User provided both prevalence and positivity rate
                step1_detail = (
                    f"For asymptomatic individuals—i.e., individuals without Covid-like symptoms—we start with the entered local Covid prevalence of {p_prev}. "
                    f"Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                    f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                    f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                    f"Next, the entered test positivity rate of {positivity_rate_display} provides an estimate of the proportion of people with Covid-like symptoms who actually have Covid. "
                    f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people are currently experiencing Covid-like symptoms. "
                    f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people are asymptomatic. "
                    f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                )
            else:
                # User provided prevalence but using default positivity rate
                step1_detail = (
                    f"For asymptomatic individuals—i.e., individuals without Covid-like symptoms—we start with the entered local Covid prevalence of {p_prev}. "
                    f"Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                    f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                    f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                    f"Next, we use the national test positivity rate of {positivity_rate_display} from the "
                    f'<a href="https://www.walgreens.com/healthcare-solutions/covid-19-index" target="_blank" rel="noopener">Walgreens Respiratory Index</a> '
                    f"as an estimate of the proportion of people with Covid-like symptoms who actually have Covid. "
                    f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people are currently experiencing Covid-like symptoms. "
                    f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people are asymptomatic. "
                    f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                )
        else:
            # Default behavior using PMC model
            base = (
                "For asymptomatic individuals—i.e., individuals without Covid-like symptoms—we start with the local Covid prevalence estimated by "
                '<a href="https://www.pmc19.com/data/index.php" target="_blank" rel="noopener">the PMC model</a>.'
            )
            
            if not state:
                # No state selected
                if positivity_from_walgreens:
                    # Using national data for both prevalence and positivity
                    state_note = (
                        f" Since no state was selected, we use the PMC's national estimate of {p_prev}. "
                        f"Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                        f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                        f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                        f"Next, we use the national test positivity rate of {positivity_rate_display} from the "
                        f'<a href="https://www.walgreens.com/healthcare-solutions/covid-19-index" target="_blank" rel="noopener">Walgreens Respiratory Index</a> '
                        f"as an estimate of the proportion of people with Covid-like symptoms who actually have Covid. "
                        f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people are currently experiencing Covid-like symptoms. "
                        f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people are asymptomatic. "
                        f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                    )
                else:
                    # User provided positivity rate but no state
                    state_note = (
                        f" Since no state was selected, we use the PMC's national estimate of {p_prev}. "
                        f"Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                        f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                        f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                        f"Next, the entered test positivity rate of {positivity_rate_display} provides an estimate of the proportion of people with Covid-like symptoms who actually have Covid. "
                        f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people are currently experiencing Covid-like symptoms. "
                        f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people are asymptomatic. "
                        f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                    )
            else:
                # State selected
                region = REGION_MAP.get(state.upper(), "National")
                if state.upper() in POS_STATES and positivity_from_walgreens and not used_national_positivity_fallback:
                    # State has positivity data available and was looked up (not user-entered)
                    state_note = (
                        f" Since {state} was selected and is in the {region}, we use the PMC's estimate of {p_prev} "
                        f"for the {region}. Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                        f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                        f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                        f"Next, the local test positivity rate of {positivity_rate_display} from the "
                        f'<a href="https://www.walgreens.com/healthcare-solutions/covid-19-index" target="_blank" rel="noopener">Walgreens Respiratory Index</a> '
                        f"provides an estimate of the proportion of people in {state} with Covid-like symptoms who actually have Covid. "
                        f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people in {state} are currently experiencing Covid-like symptoms. "
                        f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people in {state} are asymptomatic. "
                        f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                    )
                elif positivity_from_walgreens and (state.upper() not in POS_STATES or used_national_positivity_fallback):
                    # State selected but no positivity data available for that state, or fallback used
                    state_note = (
                        f" Since {state} was selected and is in the {region}, we use the PMC's estimate of {p_prev} "
                        f"for the {region}. Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                        f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                        f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                        f"Positivity data is not currently available for {state}, so we use the national positivity rate of {positivity_rate_display} from the "
                        f'<a href="https://www.walgreens.com/healthcare-solutions/covid-19-index" target="_blank" rel="noopener">Walgreens Respiratory Index</a> '
                        f"as an estimate of the proportion of people with Covid-like symptoms who actually have Covid. "
                        f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people are currently experiencing Covid-like symptoms. "
                        f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people are asymptomatic. "
                        f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                    )
                else:
                    # State selected and user provided positivity rate
                    state_note = (
                        f" Since {state} was selected and is in the {region}, we use the PMC's estimate of {p_prev} "
                        f"for the {region}. Since {asymp_link}, the probability you have Covid <em>and</em> are asymptomatic is "
                        f"32% × {p_prev} = {prob_covid_and_asymp}. Further, 68% of people who have Covid <em>are</em> symptomatic, so the probability that you have Covid and are <em>not</em> asymptomatic is "
                        f"68% × {p_prev} = {prob_covid_and_symp}.<br><br>"
                        f"Next, the entered test positivity rate of {positivity_rate_display} provides an estimate of the proportion of people with Covid-like symptoms who actually have Covid. "
                        f"So, about {prob_covid_and_symp} ÷ {positivity_rate_display} = {total_symptomatic_display} of people are currently experiencing Covid-like symptoms. "
                        f"This means that 100% - {total_symptomatic_display} = {total_asymptomatic_display} of people are asymptomatic. "
                        f"So, the prior probability that you have Covid, <em>given</em> that you are asymptomatic, is {prob_covid_and_asymp} ÷ {total_asymptomatic_display} ≈ {p_adj}."
                    )
            step1_detail = f"{base}{state_note}"

    if manual_prior_provided or symptoms.lower() == "yes" or is_unsure_symptoms:
        if is_unsure_symptoms:
            step2_detail = ""  # Hide step 2 for "I'm not sure" case
        else:
            step2_detail = "No exposure level adjustment was applied (manual prior or symptomatic branch)."
    else:
        mult = {"Much more": 5.0, "Somewhat more": 2.0, "About average": 1.0, "Somewhat less": 0.5, "Much less": 0.1, "Almost none": 0.01}.get(
            covid_exposure, 1.0
        )
        try:
            faq_url = url_for("faq")
        except RuntimeError:
            faq_url = "#faq"
        # step1_risk is the result of step 1 (after 0.32 adjustment for asymptomatic)
        # initial_risk is what will be used in step 3 (after exposure level adjustment)
        
        if covid_exposure == "About average":
            step2_detail = (
                f"Now we adjust the prior further by taking into account your recent exposure level, as described in the "
                f"<a href='{faq_url}'>FAQ</a>. Since you reported having "
                f"<strong>{covid_exposure.lower()}</strong> potential Covid exposure recently compared to the average person, "
                f"we keep this prior at <strong>{format_percent(initial_risk)}</strong>."
            )
        else:
            # Format multiplier without unnecessary decimals
            if mult == int(mult):
                mult_str = str(int(mult))
            else:
                mult_str = f"{mult:.2f}".rstrip('0').rstrip('.')
            
            # Special case for "Almost none" -> "almost no" for better grammar
            exposure_text = covid_exposure.lower()
            if covid_exposure == "Almost none":
                exposure_text = "almost no"
            
            step2_detail = (
                f"Now we adjust the prior further by taking into account your recent exposure level, as described in the "
                f"<a href='{faq_url}'>FAQ</a>. Since you reported having "
                f"<strong>{exposure_text}</strong> potential Covid exposure recently compared to the average person, "
                f"we adjust the prior to "
                f"{format_percent(step1_risk)} × {mult_str} = "
                f"<strong>{format_percent(initial_risk)}</strong>."
            )

    # Step 3: detailed Bayes narrative, per FAQ and test chaining (use caution-adjusted prior)
    try:
        faq_url = url_for("faq")
    except RuntimeError:
        faq_url = "#faq"
    step3_lines: List[str] = []
    # Get whether the user is symptomatic or asymptomatic
    user_symptom_state = "symptomatic" if symptomatic else "asymptomatic"

    # Get explanation text from Bayesian calculator
    explanation = bayesian_calc.get_explanation_text(test_impacts)
    model_info = bayesian_calc.get_model_info(len(test_impacts))
    
    # Introduction to Bayes' theorem section - ALWAYS use simple format
    test_name = test_impacts[0].get("testType", "test")
    sens = test_impacts[0].get("sensitivity", 0.0)
    spec = test_impacts[0].get("specificity", 0.0)
    step3_lines.append(
        f"<div class='calculation-intro'>"
        f"<p>Now we update this prior using <a href='https://en.wikipedia.org/wiki/Bayes%27_theorem' target='_blank' rel='noopener'>Bayes' theorem</a>, "
        f"taking into account {test_name}'s sensitivity and specificity for {user_symptom_state} individuals—"
        f"<strong>{format_percent(sens)}</strong> and <strong>{format_percent(spec)}</strong>, respectively. "
        f"(See the <a href='{faq_url}#test-sensitivities-specificities'>FAQ</a> for a list of test sensitivities and specificities by symptom status.)</p>"
    )
    
    step3_lines.append("</div>")

    # Formulas explanation section
    step3_lines.append(
        "<div class='bayes-formulas'>"
        "<h5>Bayes' Theorem</h5>"
        "<ul>"
        "<li class='formula-item'>"
        "<div><strong>If test result is positive:</strong></div>"
        "<div class='formula-wrapper'>"
        "<div class='equation-row'>"
        "<div class='equation-label'>(+)</div>"
        "<div class='equation-content'>Updated probability = <span class='fraction'><span class='numerator'>sensitivity × prior</span>"
        "<span class='denominator'>sensitivity × prior + (1 – specificity) × (1 – prior)</span></span></div>"
        "</div>"
        "</div>"
        "</li>"
        "<li class='formula-item'>"
        "<div><strong>If test result is negative:</strong></div>"
        "<div class='formula-wrapper'>"
        "<div class='equation-row'>"
        "<div class='equation-label'>(-)</div>"
        "<div class='equation-content'>Updated probability = <span class='fraction'><span class='numerator'>(1 – sensitivity) × prior</span>"
        "<span class='denominator'>(1 – sensitivity) × prior + specificity × (1 – prior)</span></span></div>"
        "</div>"
        "</div>"
        "</div>"
        "</li>"
        "</ul>"
        "<style>"
        ".bayes-formulas ul {"
        "  padding-left: 20px;"
        "  margin-top: 15px;"
        "}"
        ".formula-item {"
        "  margin-bottom: 20px;"
        "}"
        ".formula-wrapper {"
        "  margin-top: 8px;"
        "  overflow-x: auto;"
        "  -webkit-overflow-scrolling: touch;"
        "  max-width: 100%;"
        "}"
        ".equation-row {"
        "  display: flex;"
        "  justify-content: space-between;"
        "  align-items: center;"
        "  position: relative;"
        "  padding-right: 45px;"
        "  min-width: fit-content;"
        "}"
        ".equation-content {"
        "  font-family: 'Courier New', monospace;"
        "  white-space: nowrap;"
        "}"
        ".equation-label {"
        "  color: #4338ca;"
        "  font-weight: 600;"
        "  padding-right: 10px;"
        "  flex-shrink: 0;"
        "}"
        ".fraction {"
        "  display: inline-block;"
        "  vertical-align: middle;"
        "  text-align: center;"
        "  font-family: 'Courier New', monospace;"
        "}"
        ".numerator, .denominator {"
        "  display: block;"
        "  padding: 0 4px;"
        "  white-space: nowrap;"
        "}"
        ".numerator {"
        "  border-bottom: 1px solid #000;"
        "  margin-bottom: 1px;"
        "}"
        "/* Test calculation styles */  "
        ".next-test-transition p {"
        "  line-height: 1.5;"
        "  margin-bottom: 10px;"
        "}"
        ".test-calculation {"
        "  line-height: 1.5;"
        "}"
        ".test-calculation h5 {"
        "  margin-top: 0;"
        "  margin-bottom: 12px;"
        "  color: var(--primary-dark);"
        "}"
        "/* Adjust for smaller screens */"
        "@media (max-width: 480px) {"
        "  .bayes-formulas ul {"
        "    padding-left: 15px;"
        "  }"
        "  .equation-content {"
        "    font-size: 0.9em;"
        "  }"
        "  .equation-label {"
        "    font-size: 0.9em;"
        "  }"
        "  .fraction {"
        "    font-size: 0.9em;"
        "  }"
        "  .next-test-transition p {"
        "    font-size: 0.95em;"
        "  }"
        "}"
        "</style>"
        "</div>"
    )
    current_prior = initial_risk
    for idx, impact in enumerate(test_impacts):
        sens = impact.get("sensitivity", 0.0)
        spec = impact.get("specificity", 0.0)
        result = impact.get("testResult", "").lower()
        name = impact.get("testType", f"Test {idx+1}")
        # Validate that current_prior is mathematically valid before formatting
        # Use 0.99999999 threshold to catch values that would format as "> 99.999999%"
        if current_prior >= 0.99999999:
            raise ValueError(
                f"The entered prevalence ({calc_covid_prevalence}%) is mathematically inconsistent "
                f"with the current positivity rate ({calc_positivity_rate:.2f}%) given the calculator's asymptomatic rate assumptions. "
                f"This combination leads to an impossible probability calculation (>100%). "
                f"Please enter a lower prevalence value or check your inputs."
            )
        
        # Get properly formatted display value for current_prior (for consistency with displayed values)
        # This ensures we use the same rounded value that's shown to the user (like 0.2% instead of 0.0022)
        display_prior_str = format_percent(current_prior).strip("%")
        display_prior = float(display_prior_str) / 100

        # Remove unnecessary trailing zeros (e.g., 0.4320 → 0.432)
        display_prior_str_decimal = f"{display_prior:.4f}".rstrip("0").rstrip(".")
        if display_prior_str_decimal.endswith(".0"):
            display_prior_str_decimal = display_prior_str_decimal[:-2]

        if result == "positive":
            num = sens * current_prior
            den = num + (1 - spec) * (1 - current_prior)
            updated = num / den if den else 1.0
            # Create fraction style display for the formula using the cleaned display_prior value
            numerator = f"{sens:.3f} × {display_prior_str_decimal}"
            denominator = f"{sens:.3f} × {display_prior_str_decimal} + (1 - {spec:.3f}) × (1 - {display_prior_str_decimal})"
            formula = f"<span class='fraction'><span class='numerator'>{numerator}</span><span class='denominator'>{denominator}</span></span>"
        else:
            num = (1 - sens) * current_prior
            den = num + spec * (1 - current_prior)
            updated = num / den if den else 0.0
            # Create fraction style display for the formula using the cleaned display_prior value
            numerator = f"(1 - {sens:.3f}) × {display_prior_str_decimal}"
            denominator = f"(1 - {sens:.3f}) × {display_prior_str_decimal} + {spec:.3f} × (1 - {display_prior_str_decimal})"
            formula = f"<span class='fraction'><span class='numerator'>{numerator}</span><span class='denominator'>{denominator}</span></span>"
        # Prepare the transition text for next test if needed
        transition_text = ""
        if idx > 0:
            # For tests after the first one, explain effective vs population performance
            is_effective = impact.get('isEffective', False)
            if is_effective:
                transition_text = (
                    f"<div class='next-test-transition' style='margin-bottom: 15px;'>"
                    f"<p>Next, we treat <strong>{format_percent(current_prior)}</strong> "
                    f"as the new prior and update using <strong>effective</strong> sensitivity and specificity "
                    f"for {name}—<strong>{format_percent(sens)}</strong> and <strong>{format_percent(spec)}</strong>, respectively. "
                    f"These values are updated based on previous test results. "
                    f"(See <a href='{faq_url}#multiple-test-question'>\"How does the calculator handle multiple test results?\"</a> for details.)</p>"
                    f"</div>"
                )
            else:
                transition_text = (
                    f"<div class='next-test-transition' style='margin-bottom: 15px;'>"
                    f"<p>Next, we treat <strong>{format_percent(current_prior)}</strong> "
                    f"as the new prior and update via Bayes' theorem again, using "
                    f"<strong>{name}'s</strong> sensitivity and specificity for {user_symptom_state} individuals—"
                    f"<strong>{format_percent(sens)}</strong> and <strong>{format_percent(spec)}</strong>, respectively. "
                    f"(See the <a href='{faq_url}'>FAQ</a> for a list of test sensitivities and specificities by symptom status.)</p>"
                    f"</div>"
                )

        # Format each test calculation in its own section with clear visual separation
        step3_lines.append(
            "<div class='test-calculation' style='margin-top: 20px; padding: 15px; border-left: 3px solid var(--primary); background-color: #f8fafc; border-radius: 6px;'>"
        )

        # For a single test, just show the name and result. For multiple tests, include the test number.
        if len(test_impacts) == 1:
            step3_lines.append(f"<h5>{name} ({result.upper()})</h5>")
        else:
            step3_lines.append(f"<h5>Test {idx + 1}: {name} ({result.upper()})</h5>")

        # Add transition text for tests after the first one
        if transition_text:
            step3_lines.append(transition_text)

        step3_lines.append(
            f"<p>The {name} test was <strong>{result.upper()}</strong>, so we use the "
            f"{'(+)' if result=='positive' else '(-)'} formula:</p>"
            f"<div class='calculation-formula' style='background-color: rgba(255, 255, 255, 0.7); padding: 15px; border-radius: 6px; margin: 10px 0; overflow-x: auto;'>"
            f"<div class='bayes-formula' style='font-family: monospace; font-weight: 500; margin: 0; display: flex; align-items: center;'>"
            f"<span style='padding-right: 5px;'>Updated probability =</span> {formula} <span style='padding-left: 5px;'>= <strong>{format_percent(updated)}</strong></span>"
            f"</div>"
            f"</div>"
        )
        
            
        current_prior = updated
        step3_lines.append("</div>")  # Close the test-calculation div
    step3_detail = "".join(step3_lines)
    # Determine if we should use singular or plural for test results
    test_word = "result" if len(test_impacts) == 1 else "results"
    
    # Generate the HTML for test confidence ranges
    test_confidence_ranges_html = ""
    for idx, impact in enumerate(test_impacts):
        tt = impact.get("testType", f"Test {idx+1}")
        symp_str = "yes" if symptomatic else "no"
        perf = TEST_PERFORMANCE.get(tt, {}).get(symp_str, {})
        
        # Format as percentages for display - more precise for exact values
        sens_low = perf.get("sens_low", 0)
        sens_high = perf.get("sens_high", 0)
        spec_low = perf.get("spec_low", 0)
        spec_high = perf.get("spec_high", 0)
        
        # Use simpler percentage formatting for these values to avoid special formatting
        sens_low_pct = f"{sens_low * 100:.1f}%"
        sens_high_pct = f"{sens_high * 100:.1f}%" if sens_high < 1.0 else "100.0%"
        spec_low_pct = f"{spec_low * 100:.1f}%"
        spec_high_pct = f"{spec_high * 100:.1f}%" if spec_high < 1.0 else "100.0%"
        
        test_confidence_ranges_html += f"""
        <li><strong>{tt}:</strong>
            <ul style="margin-top: 5px;">
                <li>Sensitivity: {sens_low_pct} to {sens_high_pct}</li>
                <li>Specificity: {spec_low_pct} to {spec_high_pct}</li>
            </ul>
        </li>
        """

    # Standard structure for calculation details
    if is_unsure_symptoms:
        # For "I'm not sure" case, use simplified structure
        calculation_details = {
            "step1": {"title": "Methodology and Results", "detail": step1_detail},
            "step2": {
                "title": "Additional Information", 
                "detail": step2_detail,
            },
            "step3": {
                "title": "Test Information",
                "detail": "",  # Hide step 3 content for "I'm not sure" case
                "tests": [],
                "symptoms": symptoms,
            },
            "step4": {
                "title": "Uncertainty Analysis",
                "detail": (
                    f"<p>To learn about how uncertainty ranges are calculated, "
                    f"see the <a href=\"{faq_url}#uncertainty-ranges\">FAQ</a>.</p>"
                ),
            }
        }
    else:
        calculation_details = {
            "step1": {"title": "Starting probability (prior)", "detail": step1_detail},
            "step2": {
                "title": "Adjustments based on exposure level",
                "detail": step2_detail,
            },
            "step3": {
                "title": f"Update based on test {test_word}",
                "detail": step3_detail,
                "tests": [],
                "symptoms": symptoms,
            },
            "step4": {
                "title": "Uncertainty analysis",
                "detail": (
                    f"<p>To learn about how uncertainty ranges are calculated, "
                    f"see the <a href=\"{faq_url}#uncertainty-ranges\">FAQ</a>.</p>"
                ),
            }
        }

    for i, impact in enumerate(test_impacts):
        test_entry = {
            "type": impact.get("testType") or f"Test {i+1}",
            "result": impact.get("testResult") or "unknown",
            "sensitivity": impact.get("sensitivity", 0),
            "specificity": impact.get("specificity", 0),
            "before": impact.get("priorRisk", 0) * 100,
            "after": impact.get("updatedRisk", 0) * 100,
        }
        # Always add tests to step3
        calculation_details["step3"]["tests"].append(test_entry)

    return {
        "risk": risk,
        "risk_old": risk_old,
        "advanced_risk": advanced_risk,
        "monte_carlo_risk": monte_carlo_risk,
        "monte_carlo_beta_risk": monte_carlo_beta_risk,
        "monte_carlo_full_risk": monte_carlo_full_risk,
        "monte_carlo_prevalence_risk": monte_carlo_prevalence_risk,
        "min_max_range": min_max_range,
        "symptoms": symptoms,
        "tests": tests,
        "covid_exposure": covid_exposure,
        "covid_prevalence": template_covid_prevalence,
        "positivity_rate": template_positivity_rate,
        "prior_probability": template_prior_probability,
        "has_confidence_intervals": has_confidence_intervals,
        "calculation_details": calculation_details,
    }
