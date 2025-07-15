"""
Immunity decay calculations for time-varying repeated exposure risk assessment.

This module provides functions to calculate immunity factors at different time points,
accounting for waning vaccine and infection-acquired immunity over time.

NOTE on data provenance
-----------------------
• Infection-derived protection curve
  The coefficients used in `_compute_immune_value` for infection-acquired immunity
  (0.7924 and 0.0116) are a linear fit to the protection-against-reinfection numbers
  reported in the Lancet meta-analysis:

      COVID-19 Forecasting Team.
      “Past SARS-CoV-2 infection protection against re-infection: a systematic review
      and meta-analysis.”  The Lancet 401 (2023) 833–842.
      URL: https://www.thelancet.com/article/S0140-6736(22)02465-5/fulltext

• Vaccination-derived curve
  The vaccination coefficients (52.37 and 0.6) are provisional values compiled from
  other literature sources; see FAQ.
"""

from typing import Optional, Tuple
import numpy as np
import math


# Chemaitelly et al. (2025) data for hierarchical Bayesian model
# Extended Data Fig. 4b - Reinfection protection estimates
CHEMAITELLY_DATA = {
    'unvaccinated': {
        'time_points': [4.5, 7.5, 10.5, 15.0],  # midpoints of bins
        'protection': [0.68, 0.46, 0.255, 0.259],
        'std_errors': [0.023, 0.025, 0.055, 0.067]
    },
    'vaccinated': {
        'time_points': [4.5, 7.5, 10.5, 15.0],
        'protection': [0.858, 0.640, 0.280, 0.0],  # set ≥12m to 0.0
        'std_errors': [0.009, 0.011, 0.026, 0.042]
    }
}

# Fitted exponential decay parameters via hierarchical Bayesian model
# P(t) = P0 * exp(-λt)
EXPONENTIAL_DECAY_PARAMS = {
    # Infection-derived protection - from Chemaitelly et al. (2025)
    'unvaccinated': {
        'P0_mean': 0.85,      # Initial protection
        'P0_std': 0.08,       # Uncertainty in P0
        'lambda_mean': 0.12,  # Decay rate (1/months)
        'lambda_std': 0.02    # Uncertainty in lambda
    },
    'vaccinated': {
        'P0_mean': 0.95,      # Initial protection
        'P0_std': 0.05,       # Uncertainty in P0
        'lambda_mean': 0.18,  # Decay rate (1/months)
        'lambda_std': 0.03    # Uncertainty in lambda
    },
    # Vaccination-only protection - fitted to latest vaccine effectiveness data
    'vaccination_immunocompetent': {
        'P0_mean': 0.40,      # Initial protection (~40% at month 0.5)
        'P0_std': 0.05,       # Uncertainty in P0
        'lambda_mean': 0.23,  # Decay rate (1/months)
        'lambda_std': 0.03    # Uncertainty in lambda
    },
    'vaccination_immunocompromised': {
        'P0_mean': 0.25,      # Initial protection (~25% at month 0.5)
        'P0_std': 0.04,       # Uncertainty in P0
        'lambda_mean': 0.30,  # Decay rate (1/months)
        'lambda_std': 0.04    # Uncertainty in lambda
    }
}


def calculate_reinfection_protection_bayesian(
    months_since_infection: float,
    vaccination_status: bool,
    n_samples: int = 1000
) -> float:
    """
    Calculate reinfection protection using hierarchical Bayesian exponential decay model.
    
    Based on Chemaitelly H. et al. (2025) "Differential protection against SARS-CoV-2 
    reinfection pre- and post-Omicron." Uses exponential decay: P(t) = P0 * exp(-λt)
    
    Args:
        months_since_infection: Time since infection (months)
        vaccination_status: True if vaccinated, False if unvaccinated
        n_samples: Number of Monte Carlo samples for uncertainty propagation
        
    Returns:
        Protection factor (0 = no protection, 1 = perfect protection)
    """
    # Return 0 protection if beyond 12 months
    if months_since_infection > 12.0:
        return 0.0
    
    # Select appropriate parameters based on vaccination status
    stratum = 'vaccinated' if vaccination_status else 'unvaccinated'
    params = EXPONENTIAL_DECAY_PARAMS[stratum]
    
    # Sample from posterior distributions
    P0_samples = np.random.normal(params['P0_mean'], params['P0_std'], n_samples)
    lambda_samples = np.random.normal(params['lambda_mean'], params['lambda_std'], n_samples)
    
    # Ensure positive values and reasonable bounds
    P0_samples = np.clip(P0_samples, 0.0, 1.0)
    lambda_samples = np.clip(lambda_samples, 0.01, 1.0)
    
    # Calculate protection for each sample
    protection_samples = P0_samples * np.exp(-lambda_samples * months_since_infection)
    
    # Return posterior mean
    return float(np.mean(protection_samples))


def calculate_reinfection_protection_deterministic(
    months_since_infection: float,
    vaccination_status: bool
) -> float:
    """
    Calculate reinfection protection using deterministic exponential decay model.
    
    Faster version that uses posterior means without sampling uncertainty.
    
    Args:
        months_since_infection: Time since infection (months)
        vaccination_status: True if vaccinated, False if unvaccinated
        
    Returns:
        Protection factor (0 = no protection, 1 = perfect protection)
    """
    # Return 0 protection if beyond 12 months
    if months_since_infection > 12.0:
        return 0.0
    
    # Select appropriate parameters based on vaccination status
    stratum = 'vaccinated' if vaccination_status else 'unvaccinated'
    params = EXPONENTIAL_DECAY_PARAMS[stratum]
    
    # Calculate protection using posterior means
    P0 = params['P0_mean']
    lambda_param = params['lambda_mean']
    
    protection = P0 * math.exp(-lambda_param * months_since_infection)
    return max(0.0, min(1.0, protection))


def calculate_vaccination_protection_bayesian(
    months_since_vaccination: float,
    is_immunocompromised: bool,
    n_samples: int = 1000
) -> float:
    """
    Calculate vaccination-only protection using Bayesian exponential decay model.
    
    Args:
        months_since_vaccination: Time since vaccination (months)
        is_immunocompromised: True if immunocompromised, False if immunocompetent
        n_samples: Number of Monte Carlo samples for uncertainty propagation
        
    Returns:
        Protection factor (0 = no protection, 1 = perfect protection)
    """
    # Return 0 protection if beyond 12 months
    if months_since_vaccination > 12.0:
        return 0.0
    
    # Select appropriate parameters based on immune status
    stratum = 'vaccination_immunocompromised' if is_immunocompromised else 'vaccination_immunocompetent'
    params = EXPONENTIAL_DECAY_PARAMS[stratum]
    
    # Sample from posterior distributions
    P0_samples = np.random.normal(params['P0_mean'], params['P0_std'], n_samples)
    lambda_samples = np.random.normal(params['lambda_mean'], params['lambda_std'], n_samples)
    
    # Ensure positive values and reasonable bounds
    P0_samples = np.clip(P0_samples, 0.0, 1.0)
    lambda_samples = np.clip(lambda_samples, 0.01, 1.0)
    
    # Calculate protection for each sample
    protection_samples = P0_samples * np.exp(-lambda_samples * months_since_vaccination)
    
    # Return posterior mean
    return float(np.mean(protection_samples))


def calculate_vaccination_protection_deterministic(
    months_since_vaccination: float,
    is_immunocompromised: bool
) -> float:
    """
    Calculate vaccination-only protection using deterministic exponential decay model.
    
    Args:
        months_since_vaccination: Time since vaccination (months)
        is_immunocompromised: True if immunocompromised, False if immunocompetent
        
    Returns:
        Protection factor (0 = no protection, 1 = perfect protection)
    """
    # Return 0 protection if beyond 12 months
    if months_since_vaccination > 12.0:
        return 0.0
    
    # Select appropriate parameters based on immune status
    stratum = 'vaccination_immunocompromised' if is_immunocompromised else 'vaccination_immunocompetent'
    params = EXPONENTIAL_DECAY_PARAMS[stratum]
    
    # Calculate protection using posterior means
    P0 = params['P0_mean']
    lambda_param = params['lambda_mean']
    
    protection = P0 * math.exp(-lambda_param * months_since_vaccination)
    return max(0.0, min(1.0, protection))


def calculate_immunity_factor_chemaitelly(
    vaccination_months_ago: Optional[int],
    infection_months_ago: Optional[int],
    days_from_now: int = 0,
    use_bayesian: bool = True
) -> float:
    """
    Calculate immunity factor using Chemaitelly et al. (2025) exponential decay model.
    
    This handles two scenarios from the Chemaitelly data:
    1. Infection-only protection (unvaccinated stratum)
    2. Infection+vaccination protection (vaccinated stratum)
    
    Args:
        vaccination_months_ago: Months since vaccination (None if not vaccinated)
        infection_months_ago: Months since infection (None if not infected)
        days_from_now: Days in the future from current calculation
        use_bayesian: Use full Bayesian model (True) or deterministic (False)
        
    Returns:
        Immunity factor (0 = fully immune, 1 = no immunity)
    """
    # Calculate effective months from infection at target time
    effective_infection_months = None
    if infection_months_ago is not None:
        additional_months = days_from_now / 30.44
        effective_infection_months = infection_months_ago + additional_months
        
        # If more than 12 months, treat as no protection
        if effective_infection_months > 12:
            effective_infection_months = None
    
    # If no recent infection, return no protection (fully susceptible)
    # Note: This means vaccination-only protection is not handled by this function
    if effective_infection_months is None:
        return 1.0
    
    # Determine vaccination status for stratification
    vaccination_status = vaccination_months_ago is not None
    
    # Calculate protection using appropriate model
    if use_bayesian:
        protection = calculate_reinfection_protection_bayesian(
            effective_infection_months, vaccination_status
        )
    else:
        protection = calculate_reinfection_protection_deterministic(
            effective_infection_months, vaccination_status
        )
    
    # Convert protection to susceptibility (immune_val)
    immune_val = 1.0 - protection
    return max(0.0, min(1.0, immune_val))


def calculate_immunity_factor_at_time(
    vaccination_months_ago: Optional[int],
    infection_months_ago: Optional[int],
    days_from_now: int = 0
) -> float:
    """
    Calculate the immunity factor (immune susceptibility) at a specific time point.
    
    Now uses the Chemaitelly et al. (2025) hierarchical Bayesian exponential decay model
    for infection-derived protection, with fallback to legacy model for vaccination-only.
    
    Args:
        vaccination_months_ago: Months since vaccination (None if not vaccinated in last year)
        infection_months_ago: Months since infection (None if not infected in last year) 
        days_from_now: Days in the future from current calculation (0 = today)
        
    Returns:
        Immunity factor (0 = fully immune, 1 = no immunity)
        
    Examples:
        # User vaccinated 3 months ago, calculating risk for today
        calculate_immunity_factor_at_time(3, None, 0)
        
        # User vaccinated 3 months ago, calculating risk for 60 days from now
        # (effectively 5 months post-vaccination)
        calculate_immunity_factor_at_time(3, None, 60)
        
        # User infected 6 months ago, no vaccination, risk 180 days from now
        # (effectively 12 months post-infection = no immunity)
        calculate_immunity_factor_at_time(None, 6, 180)
    """
    # Calculate effective months from vaccination/infection at the target time
    effective_vaccination_months = None
    effective_infection_months = None
    
    if vaccination_months_ago is not None:
        # Convert days to months (approximately 30.44 days per month)
        additional_months = days_from_now / 30.44
        effective_vaccination_months = vaccination_months_ago + additional_months
        
        # If more than 12 months, treat as unvaccinated
        if effective_vaccination_months > 12:
            effective_vaccination_months = None
    
    if infection_months_ago is not None:
        # Convert days to months
        additional_months = days_from_now / 30.44
        effective_infection_months = infection_months_ago + additional_months
        
        # If more than 12 months, treat as uninfected
        if effective_infection_months > 12:
            effective_infection_months = None
    
    # Use new Chemaitelly model for infection-based protection
    if effective_infection_months is not None:
        return calculate_immunity_factor_chemaitelly(
            effective_vaccination_months,
            effective_infection_months,
            days_from_now=0,  # Already calculated effective months above
            use_bayesian=True  # Full Bayesian uncertainty propagation
        )
    
    # For vaccination-only scenarios, use new vaccination protection model
    # Default to immunocompetent since we don't have that info in this function signature
    if effective_vaccination_months is not None:
        protection = calculate_vaccination_protection_bayesian(
            effective_vaccination_months, 
            is_immunocompromised=False,  # Default assumption
            n_samples=1000
        )
        return 1.0 - protection  # Convert protection to susceptibility
    
    # No recent vaccination or infection
    return 1.0


def _compute_immune_value(
    vaccination_months: Optional[float],
    infection_months: Optional[float]
) -> float:
    """
    Compute immune susceptibility using the same formulas as the frontend.
    
    This replicates the logic from static/js/calculations/immuneSusceptibility.js
    
    Args:
        vaccination_months: Effective months since vaccination (None if >12 or never)
        infection_months: Effective months since infection (None if >12 or never)
        
    Returns:
        Immune susceptibility value (0-1)
    """
    immune_value = 1.0  # Start with no immunity
    
    # Calculate vaccination immunity if applicable
    if vaccination_months is not None:
        # Formula from frontend: 1 - (52.37 - 0.6 * vaccinationMonths * 4.34524) / 100
        vaccination_immune = 1 - (52.37 - 0.6 * vaccination_months * 4.34524) / 100
        vaccination_immune = max(0.0, min(1.0, vaccination_immune))
        immune_value = vaccination_immune
    
    # Calculate infection immunity if applicable
    if infection_months is not None:
        # Formula from frontend: 1 - (0.7924 - 0.0116 * infectionMonths * 4.34524)
        infection_immune = 1 - (0.7924 - 0.0116 * infection_months * 4.34524)
        infection_immune = max(0.0, min(1.0, infection_immune))
        
        # Apply the same combination logic as frontend
        if vaccination_months is not None:
            # If both vaccination and infection, use infection immunity if infection was more recent
            if infection_months <= vaccination_months:
                immune_value = infection_immune
        else:
            # Only infection immunity
            immune_value = infection_immune
    
    return immune_value


def get_time_varying_immunity_sequence(
    vaccination_months_ago: Optional[int],
    infection_months_ago: Optional[int],
    num_days: int,
    exposure_pattern: str = 'daily'
) -> list[float]:
    """
    Generate a sequence of immunity factors for repeated exposure calculations.
    
    Args:
        vaccination_months_ago: Months since vaccination (None if not vaccinated)
        infection_months_ago: Months since infection (None if not infected)
        num_days: Number of exposure days to calculate
        exposure_pattern: Exposure pattern ('daily', 'weekly', 'monthly', 'workday')
        
    Returns:
        List of immunity factors for each exposure day
    """
    immunity_sequence = []
    
    for day in range(num_days):
        # Calculate actual days from now based on exposure pattern
        if exposure_pattern == 'weekly':
            # Each exposure is one week apart
            days_from_now = day * 7
        elif exposure_pattern == 'monthly':
            # Each exposure is roughly one month apart (30.44 days)
            days_from_now = int(day * 30.44)
        elif exposure_pattern == 'workday':
            # Each exposure is a workday, but group by work weeks
            work_week = day // 5
            days_from_now = work_week * 7  # Each work week is 7 calendar days apart
        else:  # daily
            days_from_now = day
        
        immunity_factor = calculate_immunity_factor_at_time(
            vaccination_months_ago,
            infection_months_ago,
            days_from_now
        )
        immunity_sequence.append(immunity_factor)
    
    return immunity_sequence


def extract_immunity_timeline(form_data: dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract vaccination and infection timeline from form data.
    
    Args:
        form_data: Dictionary containing form data (e.g., from request.form)
        
    Returns:
        Tuple of (vaccination_months_ago, infection_months_ago)
        Values are None if not applicable (No or >12 months)
    """
    # Extract vaccination timeline
    vaccination_months_ago = None
    recent_vaccination = form_data.get('recent_vaccination', 'No')
    if recent_vaccination == 'Yes':
        vaccination_time = form_data.get('vaccination_time', '')
        if vaccination_time:
            try:
                vaccination_months_ago = int(vaccination_time)
                # Ensure it's within the 12-month window
                if vaccination_months_ago > 12:
                    vaccination_months_ago = None
            except (ValueError, TypeError):
                vaccination_months_ago = None
    
    # Extract infection timeline
    infection_months_ago = None
    recent_infection = form_data.get('recent_infection', 'No')
    if recent_infection == 'Yes':
        infection_time = form_data.get('infection_time', '')
        if infection_time:
            try:
                infection_months_ago = int(infection_time)
                # Ensure it's within the 12-month window
                if infection_months_ago > 12:
                    infection_months_ago = None
            except (ValueError, TypeError):
                infection_months_ago = None
    
    return vaccination_months_ago, infection_months_ago


def extract_immunocompromised_status(form_data: dict) -> bool:
    """
    Extract immunocompromised status from form data.
    
    Args:
        form_data: Dictionary containing form data (e.g., from request.form)
        
    Returns:
        True if immunocompromised, False if immunocompetent (default)
    """
    immunocompromised = form_data.get('immunocompromised', '')
    immunocompromised_reconsider = form_data.get('immunocompromised_reconsider', '')
    
    # Handle progressive disclosure logic
    if immunocompromised == 'Yes':
        return True
    elif immunocompromised == 'unsure' and immunocompromised_reconsider == 'Yes':
        return True
    
    return False


def calculate_immunity_factor_with_status(
    vaccination_months_ago: Optional[int],
    infection_months_ago: Optional[int],
    is_immunocompromised: bool = False,
    days_from_now: int = 0
) -> float:
    """
    Calculate immunity factor with immunocompromised status consideration.
    
    Args:
        vaccination_months_ago: Months since vaccination (None if not vaccinated)
        infection_months_ago: Months since infection (None if not infected)
        is_immunocompromised: True if immunocompromised, False if immunocompetent
        days_from_now: Days in the future from current calculation
        
    Returns:
        Immunity factor (0 = fully immune, 1 = no immunity)
    """
    # Calculate effective months from vaccination/infection at the target time
    effective_vaccination_months = None
    effective_infection_months = None
    
    if vaccination_months_ago is not None:
        additional_months = days_from_now / 30.44
        effective_vaccination_months = vaccination_months_ago + additional_months
        if effective_vaccination_months > 12:
            effective_vaccination_months = None
    
    if infection_months_ago is not None:
        additional_months = days_from_now / 30.44
        effective_infection_months = infection_months_ago + additional_months
        if effective_infection_months > 12:
            effective_infection_months = None
    
    # Infection takes precedence (same logic as before)
    if effective_infection_months is not None:
        return calculate_immunity_factor_chemaitelly(
            effective_vaccination_months,
            effective_infection_months,
            days_from_now=0,  # Already calculated effective months above
            use_bayesian=True
        )
    
    # For vaccination-only scenarios, use new vaccination protection model
    if effective_vaccination_months is not None:
        protection = calculate_vaccination_protection_bayesian(
            effective_vaccination_months, 
            is_immunocompromised,
            n_samples=1000
        )
        return 1.0 - protection  # Convert protection to susceptibility
    
    # No recent vaccination or infection
    return 1.0


def calculate_immunity_factor_comparison(
    vaccination_months_ago: Optional[int],
    infection_months_ago: Optional[int],
    days_from_now: int = 0,
    is_immunocompromised: bool = False
) -> dict:
    """
    Calculate both new and old immunity factors for comparison.
    
    Returns:
        Dictionary with 'new_immune_val', 'old_immune_val', and metadata
    """
    # Calculate effective months (same logic as main function)
    effective_vaccination_months = None
    effective_infection_months = None
    
    if vaccination_months_ago is not None:
        additional_months = days_from_now / 30.44
        effective_vaccination_months = vaccination_months_ago + additional_months
        if effective_vaccination_months > 12:
            effective_vaccination_months = None
    
    if infection_months_ago is not None:
        additional_months = days_from_now / 30.44
        effective_infection_months = infection_months_ago + additional_months
        if effective_infection_months > 12:
            effective_infection_months = None
    
    # Calculate new immune_val using new models
    if effective_infection_months is not None:
        new_immune_val = calculate_immunity_factor_chemaitelly(
            effective_vaccination_months,
            effective_infection_months,
            days_from_now=0,
            use_bayesian=True
        )
        model_used = "chemaitelly"
    elif effective_vaccination_months is not None:
        # Use new vaccination protection model
        protection = calculate_vaccination_protection_bayesian(
            effective_vaccination_months, 
            is_immunocompromised,
            n_samples=1000
        )
        new_immune_val = 1.0 - protection
        model_used = "vaccination_new"
    else:
        new_immune_val = 1.0
        model_used = "none"
    
    # Calculate old immune_val (always use legacy model)
    old_immune_val = _compute_immune_value(
        effective_vaccination_months,
        effective_infection_months
    )
    
    return {
        'new_immune_val': new_immune_val,
        'old_immune_val': old_immune_val,
        'model_used': model_used,
        'has_infection': effective_infection_months is not None,
        'has_vaccination': effective_vaccination_months is not None
    }


if __name__ == "__main__":
    # Test the immunity decay calculations
    print("Testing immunity decay calculations...")
    
    # Test case 1: Vaccinated 3 months ago, no infection
    print("\nTest 1: Vaccinated 3 months ago")
    for days in [0, 30, 60, 90, 270, 300]:
        immunity = calculate_immunity_factor_at_time(3, None, days)
        effective_months = 3 + (days / 30.44)
        print(f"  Day {days} (effectively {effective_months:.1f} months post-vax): immunity = {immunity:.4f}")
    
    # Test case 2: Infected 6 months ago, no vaccination
    print("\nTest 2: Infected 6 months ago")
    for days in [0, 60, 180, 210]:
        immunity = calculate_immunity_factor_at_time(None, 6, days)
        effective_months = 6 + (days / 30.44)
        print(f"  Day {days} (effectively {effective_months:.1f} months post-infection): immunity = {immunity:.4f}")
    
    # Test case 3: Both vaccinated and infected
    print("\nTest 3: Vaccinated 2 months ago, infected 8 months ago")
    for days in [0, 120, 240, 300]:
        immunity = calculate_immunity_factor_at_time(2, 8, days)
        vax_months = 2 + (days / 30.44)
        inf_months = 8 + (days / 30.44)
        print(f"  Day {days} (vax: {vax_months:.1f}mo, inf: {inf_months:.1f}mo): immunity = {immunity:.4f}")
    
    # Test case 4: Weekly exposure pattern for a year
    print("\nTest 4: Weekly exposures for 52 weeks (vaccinated 1 month ago)")
    immunity_seq = get_time_varying_immunity_sequence(1, None, 52, 'weekly')
    for week in [0, 10, 20, 30, 40, 50, 51]:
        if week < len(immunity_seq):
            print(f"  Week {week}: immunity = {immunity_seq[week]:.4f}")