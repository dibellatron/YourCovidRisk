"""
Bayesian test integration module for the test calculator.
This module provides a clean interface between the test calculator and the Error State Bayesian Model.
"""

from typing import List, Tuple, Dict, Any, Optional
try:
    from .error_state_bayesian_model import ErrorStateBayesianModel
    from .test_performance_data import get_performance
except ImportError:
    # Handle imports when running as a script
    from error_state_bayesian_model import ErrorStateBayesianModel
    from test_performance_data import get_performance


class BayesianTestCalculator:
    """
    Handles both single and multiple test calculations with appropriate model selection.
    
    For single tests: Uses naive Bayes (maintains backward compatibility)
    For multiple tests: Uses Error State Bayesian Model with dynamic sensitivity/specificity
    """
    
    def __init__(self, error_correlation: float = 0.3):
        """
        Initialize the Bayesian test calculator.
        
        Args:
            error_correlation: Error correlation parameter (0.0-1.0).
                              0.3 recommended for production (moderate shared error sources)
        """
        self.error_correlation = error_correlation
    
    def calculate_test_impacts(
        self,
        prior_probability: float,
        test_types: List[str],
        test_results: List[str],
        symptomatic: bool
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Calculate test impacts using appropriate model (naive vs Bayesian).
        
        Args:
            prior_probability: Prior infection probability (0.0-1.0)
            test_types: List of test names (e.g., ["BinaxNOW", "Pluslife"])
            test_results: List of test results (e.g., ["negative", "positive"])
            symptomatic: Whether person is symptomatic
            
        Returns:
            Tuple of (final_probability, test_impacts_list)
            
        test_impacts_list contains dictionaries with:
            - testType: Test name
            - testResult: Test result
            - sensitivity: Effective sensitivity used
            - specificity: Effective specificity used  
            - priorRisk: Risk before this test
            - updatedRisk: Risk after this test
            - errorState: Error state probability (if multiple tests)
            - isEffective: Whether using effective (vs population) sens/spec
        """
        
        if len(test_types) != len(test_results):
            raise ValueError("test_types and test_results must have same length")
        
        if len(test_types) == 0:
            return prior_probability, []
        
        if len(test_types) == 1:
            # Single test: Use naive Bayes for backward compatibility
            return self._calculate_single_test_naive(
                prior_probability, test_types[0], test_results[0], symptomatic
            )
        else:
            # Multiple tests: Use Error State Bayesian Model
            return self._calculate_multiple_tests_bayesian(
                prior_probability, test_types, test_results, symptomatic
            )
    
    def _calculate_single_test_naive(
        self,
        prior_probability: float,
        test_type: str,
        test_result: str,
        symptomatic: bool
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Calculate single test using naive Bayes (maintains exact backward compatibility)."""
        
        # Get population-level test performance
        perf = get_performance(test_type, symptomatic)
        sensitivity = perf["sens"]
        specificity = perf["spec"]
        
        # Apply naive Bayes
        if test_result.lower() == "positive":
            numerator = sensitivity * prior_probability
            denominator = numerator + (1 - specificity) * (1 - prior_probability)
            final_probability = numerator / denominator if denominator != 0 else 1.0
        elif test_result.lower() == "negative":
            numerator = (1 - sensitivity) * prior_probability
            denominator = numerator + specificity * (1 - prior_probability)
            final_probability = numerator / denominator if denominator != 0 else 0.0
        else:
            raise ValueError(f"Unknown test result: {test_result}")
        
        # Create test impact data (compatible with existing interface)
        test_impact = {
            "testType": test_type,
            "testResult": test_result,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "priorRisk": prior_probability,
            "updatedRisk": final_probability,
            "isEffective": False  # Using population-level performance
        }
        
        return final_probability, [test_impact]
    
    def _calculate_multiple_tests_bayesian(
        self,
        prior_probability: float,
        test_types: List[str],
        test_results: List[str],
        symptomatic: bool
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Calculate multiple tests using Error State Bayesian Model."""
        
        # Create Error State Bayesian Model
        symptom_status = "symptomatic" if symptomatic else "asymptomatic"
        model = ErrorStateBayesianModel(symptom_status, self.error_correlation)
        
        # Prepare test sequence for model
        test_sequence = list(zip(test_types, test_results))
        
        # Calculate sequential posterior
        result = model.calculate_sequential_posterior(prior_probability, test_sequence)
        
        # Convert model output to test_impacts format
        test_impacts = []
        for step in result['test_sequence']:
            
            # Determine if using effective vs population performance
            is_effective = step['test_number'] > 1  # First test uses population, rest use effective
            
            test_impact = {
                "testType": step['test_name'],
                "testResult": step['result'],
                "sensitivity": step['sensitivity_used'],
                "specificity": step['specificity_used'],
                "priorRisk": step.get('prior_prob', prior_probability),  # TODO: Add to model output
                "updatedRisk": step['posterior_prob'],
                "errorState": step['error_state_prob'],
                "isEffective": is_effective
            }
            test_impacts.append(test_impact)
        
        # Add prior risk information (need to reconstruct)
        self._add_prior_risk_info(test_impacts, prior_probability)
        
        return result['posterior_prob'], test_impacts
    
    def _add_prior_risk_info(self, test_impacts: List[Dict[str, Any]], initial_prior: float):
        """Add priorRisk information to test impacts (since model doesn't track this)."""
        
        if not test_impacts:
            return
        
        # First test has the initial prior
        test_impacts[0]['priorRisk'] = initial_prior
        
        # Subsequent tests have the previous test's updatedRisk as their prior
        for i in range(1, len(test_impacts)):
            test_impacts[i]['priorRisk'] = test_impacts[i-1]['updatedRisk']
    
    def get_model_info(self, num_tests: int) -> Dict[str, Any]:
        """
        Get information about which model is being used and why.
        
        Args:
            num_tests: Number of tests being processed
            
        Returns:
            Dictionary with model information for user education
        """
        
        if num_tests <= 1:
            return {
                "model_type": "naive_bayes",
                "model_name": "Standard Bayes",
                "description": "Uses population-level test sensitivity and specificity",
                "explanation": "For single tests, we use the standard approach with fixed test performance characteristics.",
                "sensitivity_type": "population",
                "specificity_type": "population",
                "error_correlation": None
            }
        else:
            return {
                "model_type": "error_state_bayesian",
                "model_name": "Error State Bayesian Model",
                "description": "Uses dynamic sensitivity and specificity with error correlation modeling",
                "explanation": "For multiple tests, we account for how test performance changes based on previous results and potential shared error sources.",
                "sensitivity_type": "dynamic",
                "specificity_type": "dynamic", 
                "error_correlation": self.error_correlation
            }
    
    def get_explanation_text(self, test_impacts: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate explanation text for the calculation approach used.
        
        Args:
            test_impacts: List of test impact dictionaries
            
        Returns:
            Dictionary with explanation text for different UI sections
        """
        
        num_tests = len(test_impacts)
        model_info = self.get_model_info(num_tests)
        
        if num_tests <= 1:
            return {
                "method_explanation": (
                    f"This calculation uses the standard Bayesian approach with "
                    f"population-level test sensitivity and specificity."
                ),
                "performance_note": (
                    f"The test sensitivity and specificity values are based on "
                    f"published clinical studies and represent typical performance."
                ),
                "additional_info": ""
            }
        else:
            return {
                "method_explanation": (
                    f"This calculation uses an advanced <strong>Error State Bayesian Model</strong> "
                    f"that accounts for how test performance changes with multiple tests. "
                    f"Both sensitivity and specificity are updated based on previous test results."
                ),
                "performance_note": (
                    f"<strong>Dynamic Performance:</strong> Test sensitivity changes based on "
                    f"viral load beliefs, while specificity changes based on error state beliefs. "
                    f"This accounts for shared error sources between tests."
                ),
                "correlation_info": (
                    f"<strong>Error Correlation:</strong> Using correlation parameter of "
                    f"{self.error_correlation} to model systematic error sources like "
                    f"sample contamination, cross-reactivity, or operator effects."
                ),
                "additional_info": (
                    f"Tests showing high error state probability may indicate potential "
                    f"systematic issues. Consider confirmatory testing with different "
                    f"test types or different operators/labs."
                )
            }


def create_bayesian_calculator(error_correlation: Optional[float] = None) -> BayesianTestCalculator:
    """
    Factory function to create a BayesianTestCalculator with appropriate settings.
    
    Args:
        error_correlation: Override default error correlation (0.3).
                          None uses default production setting.
                          
    Returns:
        Configured BayesianTestCalculator instance
    """
    
    if error_correlation is None:
        error_correlation = 0.3  # Production default (moderate shared error sources)
    
    return BayesianTestCalculator(error_correlation)