"""
Bayesian viral load model with explicit error state modeling.

Key innovation: Models an underlying "error state" (good vs error-prone) that 
persists across tests and is updated based on observed results.

Theoretical framework:
- Each test occurs in either "good" state (high spec) or "error-prone" state (low spec)
- Error state has persistence (correlation) between tests
- Positive results → increase belief in error-prone state → lower effective specificity
- Negative results → increase belief in good state → higher effective specificity  
- Alternating results → specificity swings based on state transitions
"""

import numpy as np
from scipy import integrate, stats, optimize
from typing import List, Tuple, Dict, Any, Optional
from functools import lru_cache
import warnings

try:
    from .viral_load_distributions import (
        viral_load_pdf, 
        get_omicron_viral_load_distribution,
        viral_load_cdf
    )
    from .viral_load_unit_conversion import standardize_lod_from_test_data
    from .test_performance_data import get_performance
except ImportError:
    # Handle imports when running as a script
    from viral_load_distributions import (
        viral_load_pdf, 
        get_omicron_viral_load_distribution,
        viral_load_cdf
    )
    from viral_load_unit_conversion import standardize_lod_from_test_data
    from test_performance_data import get_performance


class ErrorStateBayesianModel:
    """
    Bayesian viral load model with explicit error state modeling.
    
    Models an underlying binary error state:
    - State 0: "Good" - high specificity, low false positive rate
    - State 1: "Error-prone" - low specificity, high false positive rate
    
    Error state persists across tests with correlation parameter.
    Each test result updates our belief about current error state.
    """
    
    def __init__(self, symptom_status: str, error_correlation: float = 0.3):
        self.symptom_status = symptom_status
        self.error_correlation = error_correlation  # Persistence of error state
        self.detection_curves_cache = {}
        self.calibration_diagnostics = {}
        
        # Get initial viral load distribution parameters
        self.initial_mu, self.initial_sigma, _ = get_omicron_viral_load_distribution(symptom_status)
        
        # Initialize error state beliefs
        self.initial_error_state_prob = 0.1  # 10% chance of starting in error-prone state
        
    def get_error_state_specificities(self, test_name: str) -> Tuple[float, float]:
        """
        Get specificities for good vs error-prone states.
        
        Returns:
            (spec_good, spec_error_prone)
        """
        # Get baseline population specificity
        test_data = get_performance(test_name, self.symptom_status == "symptomatic")
        baseline_spec = test_data['spec']
        
        # Model specificity in different error states
        # Good state: higher than baseline (population includes some error-prone cases)
        spec_good = min(0.999, baseline_spec + 0.01)
        
        # Error-prone state: significantly lower
        # The difference depends on test type
        if test_name in ["BinaxNOW", "Flowflex (Covid-only)"]:
            # Antigen tests: more susceptible to cross-reactivity
            spec_error_prone = max(0.8, baseline_spec - 0.1)
        else:
            # Molecular tests: more robust
            spec_error_prone = max(0.95, baseline_spec - 0.05)
        
        return spec_good, spec_error_prone
    
    @lru_cache(maxsize=128)
    def get_detection_curve_parameters(self, test_name: str) -> Tuple[float, float]:
        """Get calibrated detection curve parameters for test."""
        
        if test_name not in self.detection_curves_cache:
            alpha, beta, diagnostics = self._calibrate_detection_curve(test_name)
            self.detection_curves_cache[test_name] = (alpha, beta)
            self.calibration_diagnostics[test_name] = diagnostics
        
        return self.detection_curves_cache[test_name]
    
    def _calibrate_detection_curve(self, test_name: str) -> Tuple[float, float, Dict[str, Any]]:
        """Calibrate detection curve to LoD_95 constraint only."""
        
        # Get test data and LoD
        test_data = get_performance(test_name, self.symptom_status == "symptomatic")
        lod_log = standardize_lod_from_test_data(test_name, test_data)
        
        def detection_curve(v: float, alpha: float, beta: float) -> float:
            """Logistic detection curve."""
            return 1.0 / (1.0 + np.exp(-(alpha + beta * v)))
        
        def objective(params: np.ndarray) -> float:
            """Minimize |g(LoD_95) - 0.95|."""
            alpha, beta = params
            
            # Constraint: beta must be positive
            if beta <= 0:
                return 1e6
            
            # Calculate detection at LoD_95
            det_at_lod = detection_curve(lod_log, alpha, beta)
            
            # Objective: squared error from 95%
            error = (det_at_lod - 0.95) ** 2
            return error
        
        # Optimization
        try:
            result = optimize.minimize(
                objective,
                x0=[-10.0, 3.0],
                method='Nelder-Mead',
                options={'xatol': 1e-8, 'fatol': 1e-12, 'maxiter': 1000}
            )
            
            alpha_opt, beta_opt = result.x
            
            # Validate result
            det_at_lod = detection_curve(lod_log, alpha_opt, beta_opt)
            residual = abs(det_at_lod - 0.95)
            
            diagnostics = {
                'test_name': test_name,
                'lod_log': lod_log,
                'lod_ge_ml': 10**lod_log,
                'target_detection': 0.95,
                'achieved_detection': det_at_lod,
                'residual': residual,
                'optimization_success': result.success,
                'alpha': alpha_opt,
                'beta': beta_opt
            }
            
            if residual > 0.05:
                warnings.warn(f"Large LoD calibration residual for {test_name}: {residual:.4f}")
            
            return alpha_opt, beta_opt, diagnostics
            
        except Exception as e:
            warnings.warn(f"Detection curve calibration failed for {test_name}: {e}")
            return -10.0, 3.0, {
                'test_name': test_name,
                'optimization_success': False,
                'error': str(e)
            }
    
    def detection_probability(self, v: np.ndarray, test_name: str) -> np.ndarray:
        """Calculate detection probability g(v) for given viral loads."""
        alpha, beta = self.get_detection_curve_parameters(test_name)
        return 1.0 / (1.0 + np.exp(-(alpha + beta * v)))
    
    def update_viral_load_distribution(
        self, 
        current_mu: float, 
        current_sigma: float,
        test_name: str, 
        test_result: str
    ) -> Tuple[float, float]:
        """Update viral load distribution using Bayesian updating."""
        
        def log_likelihood(v: float) -> float:
            """Log-likelihood of test result given viral load v."""
            det_prob = self.detection_probability(np.array([v]), test_name)[0]
            
            # Clip to prevent numerical issues
            det_prob = np.clip(det_prob, 1e-12, 1 - 1e-12)
            
            if test_result.lower() == "positive":
                return np.log(det_prob)
            elif test_result.lower() == "negative":
                return np.log(1 - det_prob)
            else:
                raise ValueError(f"Unknown test result: {test_result}")
        
        def log_prior(v: float) -> float:
            """Log-prior viral load density."""
            return stats.norm.logpdf(v, loc=current_mu, scale=current_sigma)
        
        def log_posterior(v: float) -> float:
            """Log-posterior (unnormalized)."""
            return log_likelihood(v) + log_prior(v)
        
        # Find the mode of the posterior (MAP estimate)
        v_range = np.linspace(current_mu - 4*current_sigma, current_mu + 4*current_sigma, 1000)
        log_post_values = [log_posterior(v) for v in v_range]
        
        # Find maximum
        max_idx = np.argmax(log_post_values)
        new_mu = v_range[max_idx]
        
        # Update sigma based on test result
        if test_result.lower() == "negative":
            # Negative test provides information → reduce uncertainty
            new_sigma = current_sigma * 0.9
        else:
            # Positive test → viral load could be anywhere above detection threshold
            new_sigma = current_sigma * 1.1
        
        # Ensure sigma doesn't get too small or too large
        new_sigma = np.clip(new_sigma, 0.3, 2.0)
        
        return new_mu, new_sigma
    
    def update_error_state_belief(
        self,
        current_error_prob: float,
        test_name: str,
        test_result: str
    ) -> float:
        """
        Update belief about error state using Bayesian updating.
        
        Args:
            current_error_prob: Current P(error_state = 1)
            test_name: Name of test
            test_result: "positive" or "negative"
            
        Returns:
            new_error_prob: Updated P(error_state = 1)
        """
        
        # Get specificities for good vs error-prone states
        spec_good, spec_error_prone = self.get_error_state_specificities(test_name)
        
        # Current belief about error state
        p_error = current_error_prob
        p_good = 1 - current_error_prob
        
        if test_result.lower() == "positive":
            # Positive result: more likely in error-prone state
            # P(positive | error_state) = false positive rate
            likelihood_error = 1 - spec_error_prone
            likelihood_good = 1 - spec_good
            
        elif test_result.lower() == "negative":
            # Negative result: more likely in good state  
            # P(negative | error_state) = specificity
            likelihood_error = spec_error_prone
            likelihood_good = spec_good
            
        else:
            raise ValueError(f"Unknown test result: {test_result}")
        
        # Bayes update for error state
        numerator_error = likelihood_error * p_error
        numerator_good = likelihood_good * p_good
        denominator = numerator_error + numerator_good
        
        if denominator > 0:
            new_error_prob = numerator_error / denominator
        else:
            new_error_prob = current_error_prob
        
        return np.clip(new_error_prob, 0.001, 0.999)
    
    def calculate_effective_sensitivity(
        self, 
        test_name: str, 
        current_mu: float, 
        current_sigma: float
    ) -> float:
        """Calculate effective sensitivity for test given current VL distribution."""
        
        def integrand(v: float) -> float:
            det_prob = self.detection_probability(np.array([v]), test_name)[0]
            vl_density = stats.norm.pdf(v, loc=current_mu, scale=current_sigma)
            return det_prob * vl_density
        
        # Integration bounds
        v_min = current_mu - 5 * current_sigma
        v_max = current_mu + 5 * current_sigma
        
        try:
            effective_sens, _ = integrate.quad(
                integrand, v_min, v_max,
                limit=200, epsabs=1e-12, epsrel=1e-10
            )
            return np.clip(effective_sens, 1e-6, 1 - 1e-6)
            
        except Exception as e:
            warnings.warn(f"Integration failed for effective sensitivity: {e}")
            # Fallback to population sensitivity
            test_data = get_performance(test_name, self.symptom_status == "symptomatic")
            return test_data['sens']
    
    def calculate_effective_specificity(
        self,
        test_name: str,
        current_error_prob: float
    ) -> float:
        """
        Calculate effective specificity based on current error state belief.
        
        Args:
            test_name: Name of test
            current_error_prob: Current P(error_state = 1)
            
        Returns:
            effective_specificity: Weighted average of good/error-prone specificities
        """
        
        # Get specificities for good vs error-prone states
        spec_good, spec_error_prone = self.get_error_state_specificities(test_name)
        
        # Weighted average based on error state belief
        effective_spec = (
            (1 - current_error_prob) * spec_good +
            current_error_prob * spec_error_prone
        )
        
        return effective_spec
    
    def calculate_sequential_posterior(
        self, 
        prior_prob: float, 
        test_results: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Calculate posterior probability using error state Bayesian updating."""
        
        if not (0 <= prior_prob <= 1):
            raise ValueError(f"Prior probability must be in [0,1], got {prior_prob}")
        
        if not test_results:
            return {
                'posterior_prob': prior_prob,
                'vl_mu': self.initial_mu,
                'vl_sigma': self.initial_sigma,
                'error_state_prob': self.initial_error_state_prob,
                'error_correlation': self.error_correlation,
                'test_sequence': []
            }
        
        # Initialize
        current_prob = prior_prob
        current_mu = self.initial_mu
        current_sigma = self.initial_sigma
        current_error_prob = self.initial_error_state_prob
        
        sequence_info = []
        
        # Process each test
        for i, (test_name, result) in enumerate(test_results, 1):
            
            if i == 1:
                # First test: use population sensitivity/specificity
                test_data = get_performance(test_name, self.symptom_status == "symptomatic")
                sens = test_data['sens']
                spec = test_data['spec']
                
            else:
                # Subsequent tests: use effective sensitivity/specificity
                
                # Apply error state persistence (correlation)
                # With probability = correlation, stay in same state
                # With probability = (1-correlation), reset to baseline
                persistent_error_prob = (
                    self.error_correlation * current_error_prob +
                    (1 - self.error_correlation) * self.initial_error_state_prob
                )
                
                # Update error state belief based on current test result
                # But use the persistent probability as the prior
                current_error_prob = self.update_error_state_belief(
                    persistent_error_prob, test_name, result
                )
                
                # Calculate effective sensitivity and specificity
                sens = self.calculate_effective_sensitivity(test_name, current_mu, current_sigma)
                spec = self.calculate_effective_specificity(test_name, current_error_prob)
            
            # Apply Bayes theorem for infection probability
            if result.lower() == "positive":
                likelihood_infected = sens
                likelihood_uninfected = 1 - spec
            elif result.lower() == "negative":
                likelihood_infected = 1 - sens
                likelihood_uninfected = spec
            else:
                raise ValueError(f"Unknown test result: {result}")
            
            # Update infection probability
            numerator = likelihood_infected * current_prob
            denominator = numerator + likelihood_uninfected * (1 - current_prob)
            
            if denominator > 0:
                current_prob = numerator / denominator
            
            # Update viral load distribution (if infected)
            current_mu, current_sigma = self.update_viral_load_distribution(
                current_mu, current_sigma, test_name, result
            )
            
            # For first test, update error state belief
            if i == 1:
                current_error_prob = self.update_error_state_belief(
                    self.initial_error_state_prob, test_name, result
                )
            
            # Determine state transition description
            if i == 1:
                state_transition = "initial"
            elif result.lower() == "positive":
                state_transition = "→ error-prone"
            else:
                state_transition = "→ good"
            
            sequence_info.append({
                'test_number': i,
                'test_name': test_name,
                'result': result,
                'sensitivity_used': sens,
                'specificity_used': spec,
                'posterior_prob': current_prob,
                'vl_mu': current_mu,
                'vl_sigma': current_sigma,
                'error_state_prob': current_error_prob,
                'state_transition': state_transition
            })
        
        return {
            'posterior_prob': current_prob,
            'vl_mu': current_mu,
            'vl_sigma': current_sigma,
            'error_state_prob': current_error_prob,
            'error_correlation': self.error_correlation,
            'test_sequence': sequence_info
        }
    
    def get_calibration_diagnostics(self, test_name: str) -> Dict[str, Any]:
        """Get calibration diagnostics for a test."""
        # Trigger calibration if not done
        self.get_detection_curve_parameters(test_name)
        return self.calibration_diagnostics.get(test_name, {})


def demonstrate_error_state_effects():
    """Demonstrate error state model with different test patterns."""
    
    print("ERROR STATE MODEL DEMONSTRATION")
    print("=" * 80)
    
    model = ErrorStateBayesianModel("symptomatic", error_correlation=0.4)
    prior = 0.05
    
    # Test different patterns
    test_patterns = [
        ("All Positives", [("BinaxNOW", "positive")] * 5),
        ("All Negatives", [("BinaxNOW", "negative")] * 5), 
        ("Alternating", [("BinaxNOW", "positive"), ("BinaxNOW", "negative"), 
                         ("BinaxNOW", "positive"), ("BinaxNOW", "negative"),
                         ("BinaxNOW", "positive")]),
        ("Pos→Neg Switch", [("BinaxNOW", "positive"), ("BinaxNOW", "positive"),
                            ("BinaxNOW", "negative"), ("BinaxNOW", "negative")])
    ]
    
    for pattern_name, test_sequence in test_patterns:
        print(f"\n{pattern_name.upper()}:")
        print("-" * 40)
        
        result = model.calculate_sequential_posterior(prior, test_sequence)
        
        print(f"{'Test #':<8} {'Result':<10} {'Specificity':<12} {'Error State':<12} {'Infection %':<12}")
        print("-" * 65)
        
        for step in result['test_sequence']:
            print(f"{step['test_number']:<8} {step['result']:<10} {step['specificity_used']*100:<11.1f}% {step['error_state_prob']*100:<11.1f}% {step['posterior_prob']*100:<11.3f}%")
    
    print(f"\n" + "=" * 80)
    print("KEY PATTERNS:")
    print("- All positives: Specificity steadily decreases (increasing error state belief)")
    print("- All negatives: Specificity steadily increases (decreasing error state belief)")
    print("- Alternating: Specificity swings up/down with each state transition")
    print("- Pos→Neg switch: Sharp specificity jump when pattern changes")
    print("=" * 80)


if __name__ == "__main__":
    demonstrate_error_state_effects()