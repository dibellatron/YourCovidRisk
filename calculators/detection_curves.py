"""
Detection curve calibration for COVID tests.

Calibrates logistic detection curves g_j(v) = logit⁻¹(α_j + β_j × v) for each test
to satisfy two constraints:
1. LoD constraint: g_j(v₉₅) = 0.95 (95% detection at limit of detection)
2. Population sensitivity: ∫ g_j(v) f_V(v) dv = Se_pop (matches published sensitivity)

Uses optimization to solve the constraint system for each test's α_j, β_j parameters.
"""

import numpy as np
from scipy import optimize, integrate
from typing import Tuple, Dict, Any, Callable
import warnings

from calculators.viral_load_distributions import viral_load_pdf, get_omicron_viral_load_distribution
from calculators.viral_load_unit_conversion import standardize_lod_from_test_data


def logistic(x: np.ndarray) -> np.ndarray:
    """Logistic function: 1 / (1 + exp(-x))"""
    # Clip x to prevent overflow
    x_clipped = np.clip(x, -500, 500)
    return 1.0 / (1.0 + np.exp(-x_clipped))


def detection_curve(v: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """
    Detection curve: probability of positive result given viral load.
    
    Args:
        v: Viral load values in log₁₀ RNA copies·mL⁻¹
        alpha: Intercept parameter
        beta: Slope parameter
        
    Returns: Detection probability in [0, 1]
    """
    return logistic(alpha + beta * v)


def population_sensitivity_integrand(v: float, alpha: float, beta: float, symptom_status: str) -> float:
    """
    Integrand for population sensitivity calculation.
    
    Args:
        v: Viral load in log₁₀ RNA copies·mL⁻¹
        alpha: Detection curve intercept
        beta: Detection curve slope
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: g_j(v) × f_V(v)
    """
    detection_prob = detection_curve(np.array([v]), alpha, beta)[0]
    viral_load_density = viral_load_pdf(np.array([v]), symptom_status)[0]
    return detection_prob * viral_load_density


def calculate_population_sensitivity(alpha: float, beta: float, symptom_status: str) -> float:
    """
    Calculate population sensitivity: ∫ g_j(v) f_V(v) dv
    
    Args:
        alpha: Detection curve intercept
        beta: Detection curve slope
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: Population sensitivity [0, 1]
    """
    # Integration bounds: cover 99.9% of viral load distribution
    mu, sigma, _ = get_omicron_viral_load_distribution(symptom_status)
    v_min = mu - 4 * sigma  # ~0.01% tail
    v_max = mu + 4 * sigma  # ~99.99% coverage
    
    result, _ = integrate.quad(
        population_sensitivity_integrand,
        v_min, v_max,
        args=(alpha, beta, symptom_status),
        limit=100
    )
    
    return result


def constraint_equations(params: np.ndarray, lod_95_log: float, se_pop: float, symptom_status: str) -> np.ndarray:
    """
    Constraint equations for detection curve calibration.
    
    Args:
        params: [alpha, beta] parameters to solve for
        lod_95_log: LoD₉₅ in log₁₀ RNA copies·mL⁻¹
        se_pop: Target population sensitivity
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: Array of constraint violations [constraint1, constraint2]
    """
    alpha, beta = params
    
    # Constraint 1: g_j(lod_95) = 0.95
    lod_detection = detection_curve(np.array([lod_95_log]), alpha, beta)[0]
    constraint1 = lod_detection - 0.95
    
    # Constraint 2: ∫ g_j(v) f_V(v) dv = se_pop
    pop_sens = calculate_population_sensitivity(alpha, beta, symptom_status)
    constraint2 = pop_sens - se_pop
    
    return np.array([constraint1, constraint2])


def calibrate_detection_curve(
    lod_95_log: float, 
    se_pop: float, 
    symptom_status: str,
    initial_guess: Tuple[float, float] = None
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Solve for α_j, β_j such that:
    1. g_j(lod_95) = 0.95
    2. ∫ g_j(v) f_V(v) dv = se_pop
    
    Args:
        lod_95_log: LoD₉₅ in log₁₀ RNA copies·mL⁻¹
        se_pop: Target population sensitivity [0, 1]
        symptom_status: "symptomatic" or "asymptomatic"
        initial_guess: Optional (alpha, beta) starting point
        
    Returns: (alpha, beta, diagnostics) where diagnostics contains convergence info
    
    Raises:
        ValueError: If no solution found or constraints cannot be satisfied
    """
    
    # Validate inputs
    if not (0 < se_pop < 1):
        raise ValueError(f"Population sensitivity must be in (0,1), got {se_pop}")
    
    # Initial guess strategy
    if initial_guess is None:
        # Start with reasonable defaults
        # For beta > 0 (steeper is better for detection), alpha such that we're in the right ballpark
        mu, sigma, _ = get_omicron_viral_load_distribution(symptom_status)
        
        # Rough initial guess: place the detection curve so it intersects the LoD correctly
        beta_init = 2.0  # Reasonable slope
        alpha_init = -beta_init * lod_95_log + np.log(0.95 / 0.05)  # logit(0.95) ≈ 2.944
        
        initial_guess = (alpha_init, beta_init)
    
    # Try to solve the constraint system
    try:
        solution = optimize.fsolve(
            constraint_equations,
            initial_guess,
            args=(lod_95_log, se_pop, symptom_status),
            full_output=True,
            xtol=1e-8
        )
        
        params, info_dict, exit_flag, message = solution
        alpha, beta = params
        
        # Check convergence
        if exit_flag != 1:
            warnings.warn(f"Detection curve calibration may not have converged: {message}")
        
        # Validate solution
        residuals = constraint_equations(params, lod_95_log, se_pop, symptom_status)
        max_residual = np.max(np.abs(residuals))
        
        if max_residual > 0.02:  # Tolerance from implementation plan
            warnings.warn(f"Large constraint residual: {max_residual:.4f} > 0.02. "
                         f"This may indicate inconsistent Se/LoD combination.")
        
        # Ensure beta > 0 (monotonic increasing detection curve)
        if beta <= 0:
            # Try with different initial guess
            alt_guess = (alpha + 1, abs(beta) + 1)
            alt_solution = optimize.fsolve(
                constraint_equations,
                alt_guess,
                args=(lod_95_log, se_pop, symptom_status),
                full_output=True,
                xtol=1e-8
            )
            alt_params, _, alt_exit_flag, _ = alt_solution
            alt_alpha, alt_beta = alt_params
            
            if alt_beta > 0 and alt_exit_flag == 1:
                alpha, beta = alt_alpha, alt_beta
                residuals = constraint_equations(alt_params, lod_95_log, se_pop, symptom_status)
                max_residual = np.max(np.abs(residuals))
            else:
                raise ValueError(f"Cannot find solution with β > 0. Got β = {beta}")
        
        diagnostics = {
            'converged': exit_flag == 1,
            'residuals': residuals,
            'max_residual': max_residual,
            'message': message,
            'constraint1_value': 0.95 + residuals[0],  # Actual g(lod_95)
            'constraint2_value': se_pop + residuals[1]  # Actual population sensitivity
        }
        
        return alpha, beta, diagnostics
        
    except Exception as e:
        # Fall back to constrained optimization if root finding fails
        warnings.warn(f"Root finding failed ({e}), trying constrained optimization")
        
        def objective(params):
            residuals = constraint_equations(params, lod_95_log, se_pop, symptom_status)
            return np.sum(residuals**2)  # L₂ norm minimization
        
        # Constraints: beta > 0
        constraints = [{'type': 'ineq', 'fun': lambda params: params[1]}]
        
        bounds = [(-20, 20), (0.1, 10)]  # Reasonable bounds for alpha, beta
        
        opt_result = optimize.minimize(
            objective,
            initial_guess,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-8}
        )
        
        if not opt_result.success:
            raise ValueError(f"No solution found: {opt_result.message}")
        
        alpha, beta = opt_result.x
        residuals = constraint_equations(opt_result.x, lod_95_log, se_pop, symptom_status)
        max_residual = np.max(np.abs(residuals))
        
        if max_residual > 0.05:  # More lenient for backup method
            raise ValueError(f"Cannot satisfy constraints within tolerance. "
                           f"Max residual: {max_residual:.4f}")
        
        diagnostics = {
            'converged': opt_result.success,
            'residuals': residuals,
            'max_residual': max_residual,
            'message': opt_result.message,
            'constraint1_value': 0.95 + residuals[0],
            'constraint2_value': se_pop + residuals[1]
        }
        
        return alpha, beta, diagnostics


def calibrate_test_detection_curve(
    test_name: str, 
    test_data: Dict[str, Any], 
    symptom_status: str
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Calibrate detection curve for a specific test and symptom status.
    
    Args:
        test_name: Name of the test
        test_data: Test performance data from test_performance_data.py
        symptom_status: "symptomatic" or "asymptomatic"
        
    Returns: (alpha, beta, diagnostics) for this test/symptom combination
    """
    # Get standardized LoD in log₁₀ RNA copies·mL⁻¹
    lod_95_log = standardize_lod_from_test_data(test_name, test_data)
    
    # Get population sensitivity for this symptom status
    se_pop = test_data['sens']
    
    # Calibrate detection curve
    return calibrate_detection_curve(lod_95_log, se_pop, symptom_status)


def validate_detection_curves():
    """Run validation tests for detection curve calibration."""
    
    # Test with known values
    lod_95_log = 5.0  # 10^5 RNA copies/mL
    se_pop = 0.8
    symptom_status = "symptomatic"
    
    try:
        alpha, beta, diagnostics = calibrate_detection_curve(lod_95_log, se_pop, symptom_status)
        
        # Validation 1: Check LoD constraint
        lod_detection = detection_curve(np.array([lod_95_log]), alpha, beta)[0]
        assert abs(lod_detection - 0.95) < 0.02, f"LoD constraint violation: {lod_detection}"
        
        # Validation 2: Check population sensitivity constraint
        pop_sens = calculate_population_sensitivity(alpha, beta, symptom_status)
        assert abs(pop_sens - se_pop) < 0.02, f"Pop sens constraint violation: {pop_sens}"
        
        # Validation 3: Beta should be positive
        assert beta > 0, f"Beta should be positive, got {beta}"
        
        # Validation 4: Detection curve should be monotonic
        v_test = np.linspace(2, 8, 100)
        det_probs = detection_curve(v_test, alpha, beta)
        assert np.all(np.diff(det_probs) >= -1e-10), "Detection curve not monotonic"
        
        print("Detection curve calibration validation tests passed!")
        print(f"  Alpha: {alpha:.4f}, Beta: {beta:.4f}")
        print(f"  LoD detection prob: {lod_detection:.4f}")
        print(f"  Population sensitivity: {pop_sens:.4f}")
        print(f"  Max residual: {diagnostics['max_residual']:.6f}")
        
    except Exception as e:
        print(f"Detection curve validation failed: {e}")
        raise


if __name__ == "__main__":
    validate_detection_curves()