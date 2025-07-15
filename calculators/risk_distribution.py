"""
Risk Distribution Analysis Module

Generates histogram data and statistics for Monte Carlo risk uncertainty visualization.
Used by the exposure calculator to provide users with visual uncertainty analysis.

Scientific basis: Bayesian uncertainty propagation through Monte Carlo simulation
"""

import numpy as np


def calculate_optimal_axes(risk_array):
    """
    Calculate smart axis bounds focusing on the main distribution.
    
    Args:
        risk_array: numpy array of risk values
        
    Returns:
        tuple: (x_min, x_max, tick_interval)
    """
    # Remove extreme outliers for axis calculation
    p95 = np.percentile(risk_array, 95)
    p5 = np.percentile(risk_array, 5)
    
    # Set x-axis to capture 90% of data with padding
    x_max = p95 * 1.2
    x_min = max(0, p5 * 0.8)
    
    # Use meaningful tick intervals
    if x_max < 0.01:      # < 1%
        tick_interval = 0.001  # 0.1% increments
    elif x_max < 0.1:     # < 10%
        tick_interval = 0.01   # 1% increments
    else:                 # ≥ 10%
        tick_interval = 0.05   # 5% increments
    
    return x_min, x_max, tick_interval


def create_smart_bins(risk_array, x_min, x_max):
    """
    Create histogram bins with appropriate resolution and round numbers.
    
    Args:
        risk_array: numpy array of risk values
        x_min: minimum x-axis value
        x_max: maximum x-axis value
        
    Returns:
        numpy array: bin edges for histogram
    """
    # Target 15-25 bins for good visual resolution
    target_bins = 20
    bin_width = (x_max - x_min) / target_bins
    
    # Round to "nice" numbers for clean bin edges
    if bin_width < 0.001:
        bin_width = round(bin_width * 10000) / 10000  # 0.01% precision
    elif bin_width < 0.01:
        bin_width = round(bin_width * 1000) / 1000    # 0.1% precision
    else:
        bin_width = round(bin_width * 100) / 100      # 1% precision
    
    bins = np.arange(x_min, x_max + bin_width, bin_width)
    return bins


def calculate_risk_statistics(risk_array):
    """
    Calculate comprehensive statistics for risk distribution.
    
    Args:
        risk_array: numpy array of risk values
        
    Returns:
        dict: statistical measures and interpretive context
    """
    mean_risk = float(np.mean(risk_array))
    median_risk = float(np.median(risk_array))
    
    # Key percentiles for credible intervals
    p25 = float(np.percentile(risk_array, 25))
    p75 = float(np.percentile(risk_array, 75))
    p5 = float(np.percentile(risk_array, 5))
    p95 = float(np.percentile(risk_array, 95))
    
    # Calculate contextual information
    pct_above_mean = float(np.mean(risk_array > mean_risk) * 100)
    pct_above_p95 = float(np.mean(risk_array > p95) * 100)
    
    # Check for skewness to help with interpretation
    skewness = float(np.mean(((risk_array - mean_risk) / np.std(risk_array)) ** 3))
    
    return {
        'mean': mean_risk,
        'median': median_risk,
        'p5': p5,
        'p25': p25,
        'p75': p75,
        'p95': p95,
        'std': float(np.std(risk_array)),
        'skewness': skewness,
        'pct_above_mean': pct_above_mean,
        'pct_above_p95': pct_above_p95,
        'range_51_ci': (p25, p75),
        'range_90_ci': (p5, p95)
    }


def generate_interpretation_text(statistics):
    """
    Generate human-readable interpretation of the risk distribution.
    
    Args:
        statistics: dict from calculate_risk_statistics()
        
    Returns:
        dict: interpretive text for different aspects
    """
    mean_pct = statistics['mean'] * 100
    p25_pct = statistics['p25'] * 100
    p75_pct = statistics['p75'] * 100
    p95_pct = statistics['p95'] * 100
    
    return {
        'typical_range': f"{p25_pct:.1f}% - {p75_pct:.1f}%",
        'extreme_scenarios': f"{statistics['pct_above_p95']:.0f}% of scenarios above {p95_pct:.1f}%",
        'summary': f"Most scenarios cluster around {mean_pct:.1f}%, with typical variation between {p25_pct:.1f}% and {p75_pct:.1f}%",
        'uncertainty_explanation': "This variation reflects biological differences between people (viral loads, breathing patterns) and epidemiological uncertainty, not model error."
    }


def generate_risk_distribution_data(all_risks_array):
    """
    Main function to generate complete risk distribution data for frontend visualization.
    
    Args:
        all_risks_array: numpy array of risk values from Monte Carlo simulations
    
    Returns:
        dict: Complete dataset for frontend visualization including:
              - histogram data (counts, edges)
              - statistical measures
              - axis configuration
              - interpretive text
    """
    if len(all_risks_array) == 0:
        raise ValueError("Risk array is empty")
    
    if np.any(all_risks_array < 0) or np.any(all_risks_array > 1):
        raise ValueError("Risk values must be between 0 and 1")
    
    # Calculate axis configuration
    x_min, x_max, tick_interval = calculate_optimal_axes(all_risks_array)
    bins = create_smart_bins(all_risks_array, x_min, x_max)
    
    # Generate histogram
    counts, edges = np.histogram(all_risks_array, bins=bins)
    
    # Calculate statistics
    statistics = calculate_risk_statistics(all_risks_array)
    
    # Generate interpretive text
    interpretation = generate_interpretation_text(statistics)
    
    return {
        'histogram': {
            'counts': counts.tolist(),
            'edges': edges.tolist(),
            'total_simulations': len(all_risks_array),
            'max_count': int(np.max(counts)) if len(counts) > 0 else 0
        },
        'statistics': statistics,
        'axis_config': {
            'x_min': x_min,
            'x_max': x_max,
            'tick_interval': tick_interval,
            'x_label': 'Infection Risk (%)',
            'y_label': 'Number of Scenarios'
        },
        'interpretation': interpretation,
        'metadata': {
            'generator': 'risk_distribution.py',
            'method': 'Monte Carlo simulation with Bayesian parameter uncertainty',
            'simulation_count': len(all_risks_array)
        }
    }


def validate_risk_distribution_data(distribution_data):
    """
    Validate the structure and content of risk distribution data.
    
    Args:
        distribution_data: dict from generate_risk_distribution_data()
        
    Returns:
        bool: True if valid, raises ValueError if invalid
    """
    required_keys = ['histogram', 'statistics', 'axis_config', 'interpretation']
    
    for key in required_keys:
        if key not in distribution_data:
            raise ValueError(f"Missing required key: {key}")
    
    # Validate histogram data
    hist = distribution_data['histogram']
    if len(hist['counts']) != len(hist['edges']) - 1:
        raise ValueError("Histogram counts and edges dimensions don't match")
    
    # Validate statistics
    stats = distribution_data['statistics']
    if not (0 <= stats['mean'] <= 1):
        raise ValueError("Mean risk must be between 0 and 1")
    
    return True