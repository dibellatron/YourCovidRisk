"""Module for calculating Monte Carlo confidence intervals for the test calculator.

This module provides four different methods for uncertainty quantification:

METHOD 1 - Min-Max Range (calculate_min_max_range):
   Shows absolute bounds using extreme test performance values.
   Uses only the sens_low/sens_high and spec_low/spec_high bounds to compute
   the most conservative possible range.

METHOD 2 - Uniform Monte Carlo (calculate_monte_carlo_ci_uniform):
   Original method that samples uniformly between published bounds.
   Uses uniform distributions between sens_low/sens_high and spec_low/spec_high
   from published confidence intervals.

METHOD 3 - Beta Monte Carlo (calculate_monte_carlo_ci_beta):
   Uses proper statistical distributions based on study sample sizes.
   Creates Beta distributions using k/n values from clinical studies, providing
   more realistic uncertainty that reflects actual study data rather than uniform sampling.

METHOD 4 - Full Uncertainty Propagation (calculate_monte_carlo_ci_full_uncertainty):
   Most complete uncertainty analysis that additionally includes uncertainty in
   positivity rates based on testing volume from covid_current.csv.
   Combines Beta distributions for test performance with Beta distributions for
   positivity rates, accounting for the number of tests performed in each region.

METHOD 5 - Enhanced Prevalence Uncertainty (calculate_monte_carlo_ci_prevalence_uncertainty):
   Advanced uncertainty analysis that incorporates full Bayesian prevalence distributions
   from wastewater modeling. Uses the PrevalenceEstimator to generate probability
   distributions based on regional wastewater levels, combining uncertainty from
   test performance, positivity rates, and empirically-calibrated prevalence models.
"""

import random
import numpy as np
from typing import List, Tuple, Dict, Any, Optional


def calculate_monte_carlo_ci_uniform(
    symptoms: str,
    test_types: list,
    test_results: list,
    initial_risk: float,
    num_simulations: int = 10000,
    confidence_levels: List[float] = [0.51, 0.95, 0.99, 0.999]
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate confidence intervals for test risk using Monte Carlo simulation with uniform sampling.
    This is the original method that samples uniformly between sens_low/sens_high bounds.
    
    Parameters:
        symptoms (str): "yes" if the user is symptomatic, "no" otherwise
        test_types (list): List of test types used
        test_results (list): List of test results ("positive" or "negative")
        initial_risk (float): Starting probability (prior) between 0 and 1
        num_simulations (int): Number of Monte Carlo simulations to run
        confidence_levels (list): List of confidence levels to calculate
        
    Returns:
        Dict[str, Tuple[float, float]]: Dictionary mapping confidence level strings to (lower, upper) bounds
    """
    from calculators.test_performance_data import get_performance

    # Symptomatic flag for passing to get_performance
    symptomatic = symptoms.lower() == "yes"
    
    # List to store all simulation results
    simulation_results = []
    
    # Run Monte Carlo simulations
    for _ in range(num_simulations):
        risk = initial_risk  # Start with the initial risk
        
        # For each test, apply Bayes' rule with randomly sampled sensitivity/specificity
        for test_type, test_result in zip(test_types, test_results):
            # Get test performance metrics
            perf = get_performance(test_type, symptomatic)
            
            # Sample from uniform distribution between low and high values
            sens_low, sens_high = perf["sens_low"], perf["sens_high"]
            spec_low, spec_high = perf["spec_low"], perf["spec_high"]
            
            # Random sample from uniform distributions
            sens = random.uniform(sens_low, sens_high)
            spec = random.uniform(spec_low, spec_high)
            
            # Apply Bayes' rule based on test result
            if test_result == "positive":
                numerator = sens * risk
                denominator = numerator + (1 - spec) * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 1.0
            elif test_result == "negative":
                numerator = (1 - sens) * risk
                denominator = numerator + spec * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 0.0
        
        # Add the final risk to our results
        simulation_results.append(risk)
    
    # Sort results for percentile calculations
    simulation_results.sort()
    
    # Calculate all confidence intervals
    result_intervals = {}
    
    for confidence_level in confidence_levels:
        # Calculate alpha - the percentage in each tail
        alpha = (1 - confidence_level) / 2
        
        # Find indices for the lower and upper bounds
        lower_idx = int(alpha * num_simulations)
        upper_idx = int((1 - alpha) * num_simulations)
        
        # Ensure indices are within bounds
        lower_idx = max(0, lower_idx)
        upper_idx = min(num_simulations - 1, upper_idx)
        
        # Store the interval with a string key (e.g., "0.95" for 95% CI)
        result_intervals[str(confidence_level)] = (
            simulation_results[lower_idx],
            simulation_results[upper_idx]
        )
    
    # Return all confidence intervals
    return result_intervals


def calculate_monte_carlo_ci_beta(
    symptoms: str,
    test_types: list,
    test_results: list,
    initial_risk: float,
    num_simulations: int = 10000,
    confidence_levels: List[float] = [0.51, 0.95, 0.99, 0.999]
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate confidence intervals for test risk using Monte Carlo simulation with Beta distributions.
    This improved method uses the k/n values to create proper Beta distributions for sensitivity and specificity.
    
    Parameters:
        symptoms (str): "yes" if the user is symptomatic, "no" otherwise
        test_types (list): List of test types used
        test_results (list): List of test results ("positive" or "negative")
        initial_risk (float): Starting probability (prior) between 0 and 1
        num_simulations (int): Number of Monte Carlo simulations to run
        confidence_levels (list): List of confidence levels to calculate
        
    Returns:
        Dict[str, Tuple[float, float]]: Dictionary mapping confidence level strings to (lower, upper) bounds
    """
    from calculators.test_performance_data import get_performance

    # Symptomatic flag for passing to get_performance
    symptomatic = symptoms.lower() == "yes"
    
    # List to store all simulation results
    simulation_results = []
    
    # Run Monte Carlo simulations
    for _ in range(num_simulations):
        risk = initial_risk  # Start with the initial risk
        
        # For each test, apply Bayes' rule with Beta-distributed sensitivity/specificity
        for test_type, test_result in zip(test_types, test_results):
            # Get test performance metrics
            perf = get_performance(test_type, symptomatic)
            
            # Get k and n values for Beta distributions
            sens_k = perf.get("sens_k")
            sens_n = perf.get("sens_n")
            spec_k = perf.get("spec_k")
            spec_n = perf.get("spec_n")
            
            # Sample from Beta distributions if k/n data available, otherwise fall back to uniform
            if sens_k is not None and sens_n is not None and sens_k >= 0 and sens_n > 0:
                # Beta distribution: Beta(k+1, n-k+1) with uniform prior
                sens = np.random.beta(sens_k + 1, sens_n - sens_k + 1)
            else:
                # Fallback to uniform sampling between bounds
                sens_low, sens_high = perf["sens_low"], perf["sens_high"]
                sens = random.uniform(sens_low, sens_high)
            
            if spec_k is not None and spec_n is not None and spec_k >= 0 and spec_n > 0:
                # Beta distribution: Beta(k+1, n-k+1) with uniform prior
                spec = np.random.beta(spec_k + 1, spec_n - spec_k + 1)
            else:
                # Fallback to uniform sampling between bounds
                spec_low, spec_high = perf["spec_low"], perf["spec_high"]
                spec = random.uniform(spec_low, spec_high)
            
            # Apply Bayes' rule based on test result
            if test_result == "positive":
                numerator = sens * risk
                denominator = numerator + (1 - spec) * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 1.0
            elif test_result == "negative":
                numerator = (1 - sens) * risk
                denominator = numerator + spec * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 0.0
        
        # Add the final risk to our results
        simulation_results.append(risk)
    
    # Sort results for percentile calculations
    simulation_results.sort()
    
    # Calculate all confidence intervals
    result_intervals = {}
    
    for confidence_level in confidence_levels:
        # Calculate alpha - the percentage in each tail
        alpha = (1 - confidence_level) / 2
        
        # Find indices for the lower and upper bounds
        lower_idx = int(alpha * num_simulations)
        upper_idx = int((1 - alpha) * num_simulations)
        
        # Ensure indices are within bounds
        lower_idx = max(0, lower_idx)
        upper_idx = min(num_simulations - 1, upper_idx)
        
        # Store the interval with a string key (e.g., "0.95" for 95% CI)
        result_intervals[str(confidence_level)] = (
            simulation_results[lower_idx],
            simulation_results[upper_idx]
        )
    
    # Return all confidence intervals
    return result_intervals


def calculate_monte_carlo_ci_full_uncertainty(
    symptoms: str,
    test_types: list,
    test_results: list,
    covid_prevalence_input: str,
    positivity_rate_input: str,
    positivity_uncertainty_params: Optional[Tuple[int, int]] = None,
    covid_exposure: str = "About average",
    manual_prior: Optional[float] = None,
    num_simulations: int = 10000,
    confidence_levels: List[float] = [0.51, 0.95, 0.99, 0.999]
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate confidence intervals using Monte Carlo simulation with full uncertainty propagation.
    This method includes uncertainty in both test performance AND positivity rates.
    
    Parameters:
        symptoms (str): "yes" if the user is symptomatic, "no" otherwise
        test_types (list): List of test types used
        test_results (list): List of test results ("positive" or "negative")
        covid_prevalence_input (str): Covid prevalence as string (for asymptomatic cases)
        positivity_rate_input (str): Base positivity rate as string
        positivity_uncertainty_params (tuple): (positive_count, negative_count) for Beta distribution
        covid_exposure (str): Exposure level for asymptomatic users ("Much more", "Somewhat more", "About average", "Somewhat less", "Much less", "Almost none")
        manual_prior (float, optional): Manual prior probability (0-1). If provided, overrides prevalence/positivity calculations
        num_simulations (int): Number of Monte Carlo simulations to run
        confidence_levels (list): List of confidence levels to calculate
        
    Returns:
        Dict[str, Tuple[float, float]]: Dictionary mapping confidence level strings to (lower, upper) bounds
    """
    from calculators.test_performance_data import get_performance
    from calculators.validators import safe_float

    # Symptomatic flag for passing to get_performance
    symptomatic = symptoms.lower() == "yes"
    
    # Parse base inputs
    covid_prevalence_val, _ = safe_float(covid_prevalence_input, 1.0)
    covid_prevalence_val = covid_prevalence_val / 100.0  # Convert to fraction
    positivity_rate_val, _ = safe_float(positivity_rate_input, 15.0)
    positivity_rate_val = positivity_rate_val / 100.0  # Convert to fraction
    
    # List to store all simulation results
    simulation_results = []
    
    # Run Monte Carlo simulations
    for _ in range(num_simulations):
        # Step 1: Sample positivity rate from Beta distribution if uncertainty data available
        if positivity_uncertainty_params and positivity_uncertainty_params[0] is not None:
            pos_count, neg_count = positivity_uncertainty_params
            if pos_count >= 0 and neg_count >= 0 and (pos_count + neg_count) > 0:
                # Sample from Beta distribution: Beta(positive + 1, negative + 1)
                sampled_positivity = np.random.beta(pos_count + 1, neg_count + 1)
            else:
                # Fallback to fixed rate
                sampled_positivity = positivity_rate_val
        else:
            # No uncertainty data, use fixed rate
            sampled_positivity = positivity_rate_val
        
        # Step 2: Calculate initial risk
        if manual_prior is not None:
            # Use manual prior when provided (overrides all other calculations)
            initial_risk = manual_prior
        elif symptomatic:
            # For symptomatic people, prior probability = sampled positivity rate
            initial_risk = sampled_positivity
        else:
            # For asymptomatic people, apply the complex prevalence adjustment
            # This is the same logic as in test_calculator.py but with sampled positivity
            prob_covid_and_asymp = 0.32 * covid_prevalence_val  # 32% of Covid cases are asymptomatic
            prob_covid_and_symp = 0.68 * covid_prevalence_val   # 68% of Covid cases are symptomatic
            
            # Calculate how many people are symptomatic based on sampled positivity rate
            if sampled_positivity > 0:
                total_symptomatic = prob_covid_and_symp / sampled_positivity
                total_asymptomatic = 1.0 - total_symptomatic
                
                # Prior for asymptomatic = P(covid and asymp) / P(asymp)
                if total_asymptomatic > 0:
                    initial_risk = prob_covid_and_asymp / total_asymptomatic
                else:
                    initial_risk = prob_covid_and_asymp  # Fallback
            else:
                initial_risk = prob_covid_and_asymp  # Fallback when positivity = 0
            
            # Ensure risk is within bounds
            initial_risk = max(0.0, min(1.0, initial_risk))
        
        # Step 2.5: Apply exposure level adjustment for asymptomatic users (but not for manual priors)
        if not symptomatic and manual_prior is None:
            if covid_exposure == "Much more":
                initial_risk *= 5.0
            elif covid_exposure == "Somewhat more":
                initial_risk *= 2.0
            elif covid_exposure == "About average":
                # No adjustment needed (1.0x)
                pass
            elif covid_exposure == "Somewhat less":
                initial_risk *= 0.5
            elif covid_exposure == "Much less":
                initial_risk *= 0.1
            elif covid_exposure == "Almost none":
                initial_risk *= 0.01
        
        # Step 3: Apply test results with sampled test performance
        risk = initial_risk
        for test_type, test_result in zip(test_types, test_results):
            # Get test performance metrics
            perf = get_performance(test_type, symptomatic)
            
            # Get k and n values for Beta distributions
            sens_k = perf.get("sens_k")
            sens_n = perf.get("sens_n")
            spec_k = perf.get("spec_k")
            spec_n = perf.get("spec_n")
            
            # Sample from Beta distributions if k/n data available, otherwise fall back to uniform
            if sens_k is not None and sens_n is not None and sens_k >= 0 and sens_n > 0:
                # Beta distribution: Beta(k+1, n-k+1) with uniform prior
                sens = np.random.beta(sens_k + 1, sens_n - sens_k + 1)
            else:
                # Fallback to uniform sampling between bounds
                sens_low, sens_high = perf["sens_low"], perf["sens_high"]
                sens = random.uniform(sens_low, sens_high)
            
            if spec_k is not None and spec_n is not None and spec_k >= 0 and spec_n > 0:
                # Beta distribution: Beta(k+1, n-k+1) with uniform prior
                spec = np.random.beta(spec_k + 1, spec_n - spec_k + 1)
            else:
                # Fallback to uniform sampling between bounds
                spec_low, spec_high = perf["spec_low"], perf["spec_high"]
                spec = random.uniform(spec_low, spec_high)
            
            # Apply Bayes' rule based on test result
            if test_result == "positive":
                numerator = sens * risk
                denominator = numerator + (1 - spec) * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 1.0
            elif test_result == "negative":
                numerator = (1 - sens) * risk
                denominator = numerator + spec * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 0.0
        
        # Add the final risk to our results
        simulation_results.append(risk)
    
    # Sort results for percentile calculations
    simulation_results.sort()
    
    # Calculate all confidence intervals
    result_intervals = {}
    
    for confidence_level in confidence_levels:
        # Calculate alpha - the percentage in each tail
        alpha = (1 - confidence_level) / 2
        
        # Find indices for the lower and upper bounds
        lower_idx = int(alpha * num_simulations)
        upper_idx = int((1 - alpha) * num_simulations)
        
        # Ensure indices are within bounds
        lower_idx = max(0, lower_idx)
        upper_idx = min(num_simulations - 1, upper_idx)
        
        # Store the interval with a string key (e.g., "0.95" for 95% CI)
        result_intervals[str(confidence_level)] = (
            simulation_results[lower_idx],
            simulation_results[upper_idx]
        )
    
    # Return all confidence intervals
    return result_intervals


def get_positivity_uncertainty_params(state: str, csv_path: str) -> Optional[Tuple[int, int]]:
    """
    Extract positivity rate uncertainty parameters from covid_current.csv.
    
    Parameters:
        state (str): State code (e.g., "CA") or "NATIONAL" for national data
        csv_path (str): Path to covid_current.csv file
    
    Returns:
        Tuple[int, int]: (positive_count, negative_count) for Beta distribution, or None if not found
    """
    import csv
    import os
    
    if not os.path.exists(csv_path):
        return None
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            latest_date = None
            latest_data = None
            
            # Find the most recent data for the specified region
            target_region = state.upper() if state else "NATIONAL"
            
            for row in reader:
                region = row.get("region", "").strip()
                # Handle both state codes and national data
                if (target_region == "NATIONAL" and region.lower() == "national") or \
                   (target_region != "NATIONAL" and region.upper() == target_region):
                    date = row.get("date", "")
                    if latest_date is None or date > latest_date:
                        latest_date = date
                        latest_data = row
            
            if latest_data:
                # Extract test_count and positivity_rate
                test_count = int(float(latest_data.get("test_count", 0)))
                positivity_rate = float(latest_data.get("positivity_rate", 0))
                
                # Calculate positive and negative counts
                positive_count = int(test_count * positivity_rate)
                negative_count = test_count - positive_count
                
                return (positive_count, negative_count)
                
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"Warning: Could not extract positivity uncertainty for {state}: {e}")
        return None
    
    return None


def calculate_min_max_range(
    symptoms: str,
    test_types: list,
    test_results: list,
    initial_risk: float
) -> Tuple[float, float]:
    """
    Calculate min-max range using extreme values of sensitivity and specificity.
    This represents the most conservative uncertainty estimate.
    
    Parameters:
        symptoms (str): "yes" if the user is symptomatic, "no" otherwise
        test_types (list): List of test types used
        test_results (list): List of test results ("positive" or "negative")
        initial_risk (float): Starting probability (prior) between 0 and 1
        
    Returns:
        Tuple[float, float]: The (minimum, maximum) possible risk values
    """
    from calculators.test_performance_data import get_performance

    # Symptomatic flag for passing to get_performance
    symptomatic = symptoms.lower() == "yes"
    
    # Calculate minimum risk (best case scenario)
    risk_min = initial_risk
    for test_type, test_result in zip(test_types, test_results):
        perf = get_performance(test_type, symptomatic)
        
        if test_result == "positive":
            # For positive test, minimum risk uses highest specificity and lowest sensitivity
            sens = perf["sens_low"]
            spec = perf["spec_high"]
        else:
            # For negative test, minimum risk uses highest sensitivity and lowest specificity
            sens = perf["sens_high"]
            spec = perf["spec_low"]
        
        # Apply Bayes' rule
        if test_result == "positive":
            numerator = sens * risk_min
            denominator = numerator + (1 - spec) * (1 - risk_min)
            risk_min = numerator / denominator if denominator != 0 else 1.0
        elif test_result == "negative":
            numerator = (1 - sens) * risk_min
            denominator = numerator + spec * (1 - risk_min)
            risk_min = numerator / denominator if denominator != 0 else 0.0
    
    # Calculate maximum risk (worst case scenario)
    risk_max = initial_risk
    for test_type, test_result in zip(test_types, test_results):
        perf = get_performance(test_type, symptomatic)
        
        if test_result == "positive":
            # For positive test, maximum risk uses lowest specificity and highest sensitivity
            sens = perf["sens_high"]
            spec = perf["spec_low"]
        else:
            # For negative test, maximum risk uses lowest sensitivity and highest specificity
            sens = perf["sens_low"]
            spec = perf["spec_high"]
        
        # Apply Bayes' rule
        if test_result == "positive":
            numerator = sens * risk_max
            denominator = numerator + (1 - spec) * (1 - risk_max)
            risk_max = numerator / denominator if denominator != 0 else 1.0
        elif test_result == "negative":
            numerator = (1 - sens) * risk_max
            denominator = numerator + spec * (1 - risk_max)
            risk_max = numerator / denominator if denominator != 0 else 0.0
    
    return (risk_min, risk_max)


def calculate_monte_carlo_ci_prevalence_uncertainty(
    symptoms: str,
    test_types: list,
    test_results: list,
    covid_prevalence_input: str,
    positivity_rate_input: str,
    positivity_uncertainty_params: Optional[Tuple[int, int]] = None,
    covid_exposure: str = "About average",
    manual_prior: Optional[float] = None,
    region: str = "National",
    num_simulations: int = 10000,
    confidence_levels: List[float] = [0.51, 0.99]
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate confidence intervals using Monte Carlo simulation with enhanced prevalence uncertainty.
    This method incorporates full Bayesian prevalence distributions from wastewater modeling.
    
    Parameters:
        symptoms (str): "yes" if the user is symptomatic, "no" otherwise
        test_types (list): List of test types used
        test_results (list): List of test results ("positive" or "negative")
        covid_prevalence_input (str): Covid prevalence as string (used as fallback)
        positivity_rate_input (str): Base positivity rate as string
        positivity_uncertainty_params (tuple): (positive_count, negative_count) for Beta distribution
        covid_exposure (str): Exposure level for asymptomatic users
        manual_prior (float, optional): Manual prior probability (0-1). If provided, overrides prevalence calculations
        region (str): Geographic region for prevalence estimation ("National", "Northeast", "Midwest", "South", "West")
        num_simulations (int): Number of Monte Carlo simulations to run
        confidence_levels (list): List of confidence levels to calculate
        
    Returns:
        Dict[str, Tuple[float, float]]: Dictionary mapping confidence level strings to (lower, upper) bounds
    """
    from calculators.test_performance_data import get_performance
    from calculators.validators import safe_float
    import sys
    import os
    
    # Add wastewater directory to path to import PrevalenceEstimator
    # Use absolute path to avoid issues with working directory changes
    current_dir = os.path.dirname(os.path.abspath(__file__))
    wastewater_path = os.path.join(current_dir, '..', 'wastewater')
    wastewater_path = os.path.abspath(wastewater_path)
    
    if wastewater_path not in sys.path:
        sys.path.insert(0, wastewater_path)
    
    try:
        from estimate_prevalence import PrevalenceEstimator
    except ImportError as e:
        # Fallback to the existing method if wastewater module is unavailable
        print(f"Warning: PrevalenceEstimator not available ({e}), falling back to fixed prevalence")
        return calculate_monte_carlo_ci_full_uncertainty(
            symptoms, test_types, test_results, covid_prevalence_input, 
            positivity_rate_input, positivity_uncertainty_params, covid_cautious, 
            manual_prior, num_simulations, confidence_levels
        )
    except Exception as e:
        # Catch any other errors during import
        print(f"Warning: Error importing PrevalenceEstimator ({e}), falling back to fixed prevalence")
        return calculate_monte_carlo_ci_full_uncertainty(
            symptoms, test_types, test_results, covid_prevalence_input, 
            positivity_rate_input, positivity_uncertainty_params, covid_cautious, 
            manual_prior, num_simulations, confidence_levels
        )
    
    # Symptomatic flag for passing to get_performance
    symptomatic = symptoms.lower() == "yes"
    
    # Parse base inputs (used as fallbacks)
    covid_prevalence_val, _ = safe_float(covid_prevalence_input, 1.0)
    covid_prevalence_val = covid_prevalence_val / 100.0  # Convert to fraction
    positivity_rate_val, _ = safe_float(positivity_rate_input, 15.0)
    positivity_rate_val = positivity_rate_val / 100.0  # Convert to fraction
    
    # Load pre-computed prevalence distribution for the region
    prevalence_samples = None
    # Only use prevalence uncertainty if not using manual prior AND no manual prevalence provided
    manual_prevalence_provided = covid_prevalence_input and covid_prevalence_input.strip()
    if not manual_prior and not manual_prevalence_provided:
        try:
            # Try to load pre-computed distribution first
            pmc_dir = os.path.join(current_dir, '..', 'PMC', 'PrecomputedDistributions')
            distribution_file = os.path.join(pmc_dir, f"{region.lower()}_distribution.json")
            
            if os.path.exists(distribution_file):
                # Load pre-computed distribution
                distribution_data = PrevalenceEstimator.load_distribution(distribution_file)
                prevalence_samples = distribution_data['samples']
                
                # Resample if we need more samples than were pre-computed
                if len(prevalence_samples) < num_simulations:
                    # Bootstrap resample to get enough samples
                    prevalence_samples = np.random.choice(
                        prevalence_samples, 
                        size=num_simulations, 
                        replace=True
                    )
                else:
                    # Use subset of pre-computed samples
                    prevalence_samples = prevalence_samples[:num_simulations]
                
                print(f"Loaded pre-computed distribution for {region} ({len(prevalence_samples)} samples)")
                print(f"Prevalence distribution: median={np.median(prevalence_samples):.4f}, std={np.std(prevalence_samples):.4f}")
            else:
                # Fallback: generate on-demand if pre-computed distribution not available
                print(f"Pre-computed distribution not found for {region}, generating on-demand...")
                
                # Regional wastewater level mapping (fallback values)
                regional_wastewater_levels = {
                    "National": 180,    # Current moderate level
                    "Northeast": 160,   # Slightly lower
                    "Midwest": 170,     # Moderate
                    "South": 190,       # Slightly higher  
                    "West": 200         # Highest based on current PMC data (0.8%)
                }
                
                wastewater_level = regional_wastewater_levels.get(region, 180)
                estimator = PrevalenceEstimator(variant_period="omicron")
                prevalence_results = estimator.estimate_prevalence(
                    wastewater_level=wastewater_level, 
                    n_samples=num_simulations,
                    seed=42
                )
                prevalence_samples = prevalence_results['samples']
                print(f"Generated {len(prevalence_samples)} prevalence samples for {region} (wastewater={wastewater_level})")
                
        except Exception as e:
            print(f"Warning: Error loading/generating prevalence distribution: {e}")
            prevalence_samples = None
    
    # List to store all simulation results
    simulation_results = []
    
    # Run Monte Carlo simulations
    for i in range(num_simulations):
        # Step 1: Sample positivity rate from Beta distribution if uncertainty data available
        if positivity_uncertainty_params and positivity_uncertainty_params[0] is not None:
            pos_count, neg_count = positivity_uncertainty_params
            if pos_count >= 0 and neg_count >= 0 and (pos_count + neg_count) > 0:
                # Sample from Beta distribution: Beta(positive + 1, negative + 1)
                sampled_positivity = np.random.beta(pos_count + 1, neg_count + 1)
            else:
                # Fallback to fixed rate
                sampled_positivity = positivity_rate_val
        else:
            # No uncertainty data, use fixed rate
            sampled_positivity = positivity_rate_val
        
        # Step 2: Sample prevalence from wastewater-based Bayesian distribution
        if prevalence_samples is not None and len(prevalence_samples) > 0:
            # Use prevalence sample from Bayesian wastewater model
            sampled_prevalence = prevalence_samples[i % len(prevalence_samples)]
        else:
            # Fallback to fixed prevalence
            sampled_prevalence = covid_prevalence_val
        
        # Step 3: Calculate initial risk
        if manual_prior is not None:
            # Use manual prior when provided (overrides all other calculations)
            initial_risk = manual_prior
        elif symptomatic:
            # For symptomatic people, prior probability = sampled positivity rate
            initial_risk = sampled_positivity
        else:
            # For asymptomatic people, apply the complex prevalence adjustment with sampled prevalence
            prob_covid_and_asymp = 0.32 * sampled_prevalence  # 32% of Covid cases are asymptomatic
            prob_covid_and_symp = 0.68 * sampled_prevalence   # 68% of Covid cases are symptomatic
            
            # Calculate how many people are symptomatic based on sampled positivity rate
            if sampled_positivity > 0:
                total_symptomatic = prob_covid_and_symp / sampled_positivity
                total_asymptomatic = 1.0 - total_symptomatic
                
                # Prior for asymptomatic = P(covid and asymp) / P(asymp)
                if total_asymptomatic > 0:
                    initial_risk = prob_covid_and_asymp / total_asymptomatic
                else:
                    initial_risk = prob_covid_and_asymp  # Fallback
            else:
                initial_risk = prob_covid_and_asymp  # Fallback when positivity = 0
            
            # Ensure risk is within bounds
            initial_risk = max(0.0, min(1.0, initial_risk))
        
        # Step 4: Apply exposure level adjustment for asymptomatic users (but not for manual priors)
        if not symptomatic and manual_prior is None:
            if covid_exposure == "Much more":
                initial_risk *= 5.0
            elif covid_exposure == "Somewhat more":
                initial_risk *= 2.0
            elif covid_exposure == "About average":
                # No adjustment needed (1.0x)
                pass
            elif covid_exposure == "Somewhat less":
                initial_risk *= 0.5
            elif covid_exposure == "Much less":
                initial_risk *= 0.1
            elif covid_exposure == "Almost none":
                initial_risk *= 0.01
        
        # Step 5: Apply test results with sampled test performance
        risk = initial_risk
        for test_type, test_result in zip(test_types, test_results):
            # Get test performance metrics
            perf = get_performance(test_type, symptomatic)
            
            # Get k and n values for Beta distributions
            sens_k = perf.get("sens_k")
            sens_n = perf.get("sens_n")
            spec_k = perf.get("spec_k")
            spec_n = perf.get("spec_n")
            
            # Sample from Beta distributions if k/n data available, otherwise fall back to uniform
            if sens_k is not None and sens_n is not None and sens_k >= 0 and sens_n > 0:
                # Beta distribution: Beta(k+1, n-k+1) with uniform prior
                sens = np.random.beta(sens_k + 1, sens_n - sens_k + 1)
            else:
                # Fallback to uniform sampling between bounds
                sens_low, sens_high = perf["sens_low"], perf["sens_high"]
                sens = random.uniform(sens_low, sens_high)
            
            if spec_k is not None and spec_n is not None and spec_k >= 0 and spec_n > 0:
                # Beta distribution: Beta(k+1, n-k+1) with uniform prior
                spec = np.random.beta(spec_k + 1, spec_n - spec_k + 1)
            else:
                # Fallback to uniform sampling between bounds
                spec_low, spec_high = perf["spec_low"], perf["spec_high"]
                spec = random.uniform(spec_low, spec_high)
            
            # Apply Bayes' rule based on test result
            if test_result == "positive":
                numerator = sens * risk
                denominator = numerator + (1 - spec) * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 1.0
            elif test_result == "negative":
                numerator = (1 - sens) * risk
                denominator = numerator + spec * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 0.0
        
        # Add the final risk to our results
        simulation_results.append(risk)
    
    # Sort results for percentile calculations
    simulation_results.sort()
    
    # Calculate all confidence intervals
    result_intervals = {}
    
    for confidence_level in confidence_levels:
        # Calculate alpha - the percentage in each tail
        alpha = (1 - confidence_level) / 2
        
        # Find indices for the lower and upper bounds
        lower_idx = int(alpha * num_simulations)
        upper_idx = int((1 - alpha) * num_simulations)
        
        # Ensure indices are within bounds
        lower_idx = max(0, lower_idx)
        upper_idx = min(num_simulations - 1, upper_idx)
        
        # Store the interval with a string key (e.g., "0.95" for 95% CI)
        result_intervals[str(confidence_level)] = (
            simulation_results[lower_idx],
            simulation_results[upper_idx]
        )
    
    # Return all confidence intervals
    return result_intervals


def calculate_monte_carlo_ci_error_state_bayesian_fast(
    symptoms: str,
    test_types: list,
    test_results: list,
    covid_prevalence_input: str,
    positivity_rate_input: str,
    positivity_uncertainty_params: Optional[Tuple[int, int]] = None,
    covid_exposure: str = "About average",
    manual_prior: Optional[float] = None,
    region: str = "National",
    error_correlation: float = 0.3,
    num_simulations: int = 1000,  # Reduced for speed
    confidence_levels: List[float] = [0.51, 0.99]
) -> Dict[str, Tuple[float, float]]:
    """
    Fast approximation for Error State Bayesian uncertainty intervals for multiple tests.
    Uses simplified error state modeling to maintain performance while capturing key effects.
    
    This method approximates the Error State Bayesian Model effects without the computationally
    expensive viral load integration, making it suitable for real-time web use.
    """
    from calculators.validators import safe_float
    from calculators.test_performance_data import get_performance
    import random
    import numpy as np
    
    # If only one test, fall back to the standard approach for consistency
    if len(test_types) <= 1:
        return calculate_monte_carlo_ci_prevalence_uncertainty(
            symptoms, test_types, test_results, covid_prevalence_input,
            positivity_rate_input, positivity_uncertainty_params, covid_exposure,
            manual_prior, region, num_simulations, confidence_levels
        )
    
    # Parse base inputs
    covid_prevalence_val, _ = safe_float(covid_prevalence_input, 1.0)
    covid_prevalence_val = covid_prevalence_val / 100.0
    positivity_rate_val, _ = safe_float(positivity_rate_input, 15.0)
    positivity_rate_val = positivity_rate_val / 100.0
    
    # Symptomatic flag
    symptomatic = symptoms.lower() == "yes"
    
    # List to store all simulation results
    simulation_results = []
    
    # Pre-calculate error state evolution approximation
    # Based on observed patterns from Error State Bayesian Model
    error_state_evolution = []
    current_error_prob = 0.1  # Initial error state probability
    
    for i, (test_type, result) in enumerate(zip(test_types, test_results)):
        if i > 0:  # Error state persistence for subsequent tests
            # Apply correlation: blend previous state with baseline
            current_error_prob = (
                error_correlation * current_error_prob + 
                (1 - error_correlation) * 0.1
            )
        
        # Update error state based on result (simplified)
        if result.lower() == "positive":
            # Positive results increase error state belief
            current_error_prob = min(0.8, current_error_prob * 1.5)
        else:
            # Negative results decrease error state belief  
            current_error_prob = max(0.05, current_error_prob * 0.7)
            
        error_state_evolution.append(current_error_prob)
    
    # Run fast Monte Carlo simulations
    for i in range(num_simulations):
        # Step 1: Sample positivity rate
        if positivity_uncertainty_params and positivity_uncertainty_params[0] is not None:
            pos_count, neg_count = positivity_uncertainty_params
            if pos_count >= 0 and neg_count >= 0 and (pos_count + neg_count) > 0:
                sampled_positivity = np.random.beta(pos_count + 1, neg_count + 1)
            else:
                sampled_positivity = positivity_rate_val
        else:
            sampled_positivity = positivity_rate_val
        
        # Step 2: Calculate initial risk using sampled parameters
        if manual_prior is not None:
            initial_risk = manual_prior
        elif symptomatic:
            initial_risk = sampled_positivity
        else:
            # Apply prevalence adjustment (simplified for speed)
            prob_covid_and_asymp = 0.32 * covid_prevalence_val
            prob_covid_and_symp = 0.68 * covid_prevalence_val
            
            if sampled_positivity > 0:
                total_symptomatic = prob_covid_and_symp / sampled_positivity
                total_asymptomatic = 1.0 - total_symptomatic
                
                if total_asymptomatic > 0:
                    initial_risk = prob_covid_and_asymp / total_asymptomatic
                else:
                    initial_risk = prob_covid_and_asymp
            else:
                initial_risk = prob_covid_and_asymp
            
            initial_risk = max(0.0, min(1.0, initial_risk))
        
        # Step 3: Apply exposure level adjustment
        if not symptomatic and manual_prior is None:
            if covid_exposure == "Much more":
                initial_risk *= 5.0
            elif covid_exposure == "Somewhat more":
                initial_risk *= 2.0
            elif covid_exposure == "About average":
                # No adjustment needed (1.0x)
                pass
            elif covid_exposure == "Somewhat less":
                initial_risk *= 0.5
            elif covid_exposure == "Much less":
                initial_risk *= 0.1
            elif covid_exposure == "Almost none":
                initial_risk *= 0.01
        
        # Step 4: Apply tests with approximate Error State dynamics
        risk = initial_risk
        
        for j, (test_type, result) in enumerate(zip(test_types, test_results)):
            # Get test performance
            perf = get_performance(test_type, symptomatic)
            
            # Sample sensitivity from Beta distribution with increased uncertainty
            sens_k = perf.get("sens_k")
            sens_n = perf.get("sens_n")
            if sens_k is not None and sens_n is not None and sens_k >= 0 and sens_n > 0:
                # Add some additional uncertainty to account for real-world variability
                uncertainty_factor = 0.8  # Reduces effective sample size to increase uncertainty
                effective_k = max(1, int(sens_k * uncertainty_factor))
                effective_n = max(2, int(sens_n * uncertainty_factor))
                base_sens = np.random.beta(effective_k + 1, effective_n - effective_k + 1)
            else:
                base_sens = random.uniform(perf["sens_low"], perf["sens_high"])
            
            # Sample base specificity with increased uncertainty
            spec_k = perf.get("spec_k")
            spec_n = perf.get("spec_n")
            if spec_k is not None and spec_n is not None and spec_k >= 0 and spec_n > 0:
                # Add additional uncertainty for specificity as well
                uncertainty_factor = 0.8  
                effective_k = max(1, int(spec_k * uncertainty_factor))
                effective_n = max(2, int(spec_n * uncertainty_factor))
                base_spec = np.random.beta(effective_k + 1, effective_n - effective_k + 1)
            else:
                base_spec = random.uniform(perf["spec_low"], perf["spec_high"])
            
            # Apply Error State approximation
            if j == 0:
                # First test: use population performance
                sens = base_sens
                spec = base_spec
            else:
                # Subsequent tests: apply dynamic adjustments (simplified)
                error_prob = error_state_evolution[j]
                
                # Sensitivity adjustment based on previous results
                if any(r == "negative" for r in test_results[:j]):
                    sens = base_sens * 0.85  # Reduced sensitivity after negatives
                else:
                    sens = base_sens * 1.1   # Slightly increased after positives
                sens = max(0.1, min(0.99, sens))
                
                # Specificity adjustment based on error state
                spec_good = min(0.999, base_spec + 0.01)
                spec_error = max(0.8, base_spec - 0.1)
                spec = (1 - error_prob) * spec_good + error_prob * spec_error
            
            # Apply Bayes' rule
            if result == "positive":
                numerator = sens * risk
                denominator = numerator + (1 - spec) * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 1.0
            elif result == "negative":
                numerator = (1 - sens) * risk
                denominator = numerator + spec * (1 - risk)
                risk = numerator / denominator if denominator != 0 else 0.0
        
        simulation_results.append(risk)
    
    # Sort and calculate confidence intervals
    simulation_results.sort()
    result_intervals = {}
    
    for confidence_level in confidence_levels:
        alpha = (1 - confidence_level) / 2
        lower_idx = int(alpha * num_simulations)
        upper_idx = int((1 - alpha) * num_simulations)
        
        lower_idx = max(0, lower_idx)
        upper_idx = min(num_simulations - 1, upper_idx)
        
        lower_bound = simulation_results[lower_idx] 
        upper_bound = simulation_results[upper_idx]
        
        # Safety check: ensure intervals make sense
        if lower_bound > upper_bound:
            lower_bound, upper_bound = upper_bound, lower_bound
            
        result_intervals[str(confidence_level)] = (lower_bound, upper_bound)
    
    # Final validation: ensure 99% interval is wider than 51% interval
    if '0.51' in result_intervals and '0.99' in result_intervals:
        ci_51_width = result_intervals['0.51'][1] - result_intervals['0.51'][0]
        ci_99_width = result_intervals['0.99'][1] - result_intervals['0.99'][0]
        
        if ci_99_width < ci_51_width:
            # This shouldn't happen with proper Monte Carlo, but if it does,
            # expand the 99% interval appropriately
            ci_51_center = (result_intervals['0.51'][0] + result_intervals['0.51'][1]) / 2
            expand_factor = 1.5  # Make 99% interval at least 1.5x wider than 51%
            half_width_99 = (ci_51_width * expand_factor) / 2
            
            result_intervals['0.99'] = (
                max(0, ci_51_center - half_width_99),
                min(1, ci_51_center + half_width_99)
            )
    
    return result_intervals


# Backward compatibility alias
calculate_monte_carlo_ci = calculate_monte_carlo_ci_uniform