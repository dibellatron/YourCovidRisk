"""
Estimate COVID-19 prevalence from wastewater levels using calibrated hierarchical Bayesian model.

This script provides point estimates, credible intervals, and probability distributions
for prevalence given a wastewater level input.

Usage:
    python estimate_prevalence.py --wastewater 180
    python estimate_prevalence.py --wastewater 500 --samples 20000 --plot
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import json
from pathlib import Path
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# Set style
plt.style.use('default')
sns.set_palette("husl")


class PrevalenceEstimator:
    """Calibrated hierarchical Bayesian prevalence estimator."""
    
    def __init__(self, population=332_000_000, variant_period="omicron"):
        """Initialize with US population and variant period."""
        self.population = population
        self.variant_period = variant_period
        
        # Wastewater-prevalence relationship parameters (from empirical analysis)
        self.alpha_mean = 4.211
        self.alpha_sd = 0.05
        self.beta_mean = 0.353
        self.beta_sd = 0.02
        self.sigma_mean = 0.230
        self.sigma_sd = 0.02
        
        # Variant-specific infectiousness duration parameters (empirically fitted)
        if variant_period == "omicron":
            # Omicron (Keske et al.): Gamma distribution (empirically longer duration)
            self.duration_distribution = "gamma"
            self.duration_shape_mean = 8.25
            self.duration_shape_sd = 1.00
            self.duration_scale_mean = 0.90
            self.duration_scale_sd = 0.20
        elif variant_period == "pre_omicron":
            # Pre-Omicron (Hakki et al.): Weibull distribution (empirically shorter duration)
            self.duration_distribution = "weibull" 
            self.duration_shape_mean = 3.20
            self.duration_shape_sd = 0.50
            self.duration_scale_mean = 6.80
            self.duration_scale_sd = 1.00
        else:
            raise ValueError("variant_period must be 'omicron' or 'pre_omicron'")
        
    def estimate_prevalence(self, wastewater_level, n_samples=10000, seed=42):
        """
        Estimate prevalence from wastewater level.
        
        Parameters:
        -----------
        wastewater_level : float
            Wastewater level measurement
        n_samples : int
            Number of posterior samples to generate
        seed : int
            Random seed for reproducibility
            
        Returns:
        --------
        dict : Dictionary containing estimates and samples
        """
        
        np.random.seed(seed)
        
        # Sample model parameters
        alpha_samples = np.random.normal(self.alpha_mean, self.alpha_sd, n_samples)
        beta_samples = np.random.normal(self.beta_mean, self.beta_sd, n_samples)
        sigma_samples = np.abs(np.random.normal(self.sigma_mean, self.sigma_sd, n_samples))
        
        # Sample variant-specific infectiousness duration parameters
        if self.duration_distribution == "weibull":
            # Pre-Omicron (Hakki): Weibull distribution
            shape_samples = np.random.normal(self.duration_shape_mean, self.duration_shape_sd, n_samples)
            scale_samples = np.random.normal(self.duration_scale_mean, self.duration_scale_sd, n_samples)
            # Ensure positive values
            shape_samples = np.maximum(shape_samples, 0.5)
            scale_samples = np.maximum(scale_samples, 1.0)
        elif self.duration_distribution == "gamma":
            # Omicron (Keske): Gamma distribution  
            shape_samples = np.random.normal(self.duration_shape_mean, self.duration_shape_sd, n_samples)
            scale_samples = np.random.normal(self.duration_scale_mean, self.duration_scale_sd, n_samples)
            # Ensure positive values
            shape_samples = np.maximum(shape_samples, 1.0)
            scale_samples = np.maximum(scale_samples, 0.1)
        
        # Ensure positive beta values
        beta_samples = np.maximum(beta_samples, 0.01)
        
        # Calculate log10 of wastewater level
        log10_ww = np.log10(wastewater_level)
        
        # Generate prevalence samples
        prevalence_samples = []
        
        for i in range(n_samples):
            # Add observation noise
            log10_ww_noisy = np.random.normal(log10_ww, sigma_samples[i])
            
            # Inverse prediction: log_prevalence = (log10_ww - alpha) / beta
            log_prevalence = (log10_ww_noisy - alpha_samples[i]) / beta_samples[i]
            base_prevalence = np.exp(log_prevalence)
            
            # Apply variant-specific infectiousness duration adjustment (empirically fitted)
            if self.duration_distribution == "weibull":
                # Pre-Omicron (Hakki): empirically shorter duration
                # Mean Weibull duration ≈ scale * Γ(1 + 1/shape)
                from scipy.special import gamma as gamma_func
                mean_duration = scale_samples[i] * gamma_func(1 + 1/shape_samples[i])
                duration_factor = mean_duration / 7.0  # Relative to 7-day baseline
            elif self.duration_distribution == "gamma":
                # Omicron (Keske): empirically longer duration (contrary to expectations)
                # Mean Gamma duration = shape * scale
                mean_duration = shape_samples[i] * scale_samples[i]
                duration_factor = mean_duration / 7.0  # Relative to 7-day baseline
            
            prevalence = base_prevalence * duration_factor
            
            # Apply reasonable bounds
            if 0.00001 < prevalence < 0.5:  # 0.001% to 50%
                prevalence_samples.append(prevalence)
        
        prevalence_samples = np.array(prevalence_samples)
        
        if len(prevalence_samples) == 0:
            raise ValueError("No valid prevalence samples generated. Check wastewater level.")
        
        # Calculate summary statistics
        results = self._calculate_statistics(prevalence_samples, wastewater_level)
        results['samples'] = prevalence_samples
        results['n_valid_samples'] = len(prevalence_samples)
        results['n_requested_samples'] = n_samples
        
        return results
    
    def _calculate_statistics(self, samples, wastewater_level):
        """Calculate summary statistics from samples."""
        
        # Basic statistics
        median = np.median(samples)
        mean = np.mean(samples)
        std = np.std(samples)
        
        # Credible intervals
        ci_51 = [np.percentile(samples, (100-51)/2), 
                   np.percentile(samples, 51 + (100-51)/2)]
        ci_95 = [np.percentile(samples, 2.5), np.percentile(samples, 97.5)]
        ci_99 = [np.percentile(samples, 0.5), np.percentile(samples, 99.5)]
        
        # Infectious population estimates
        infectious_median = median * self.population
        infectious_ci_51 = [ci_51[0] * self.population, ci_51[1] * self.population]
        infectious_ci_95 = [ci_95[0] * self.population, ci_95[1] * self.population]
        infectious_ci_99 = [ci_99[0] * self.population, ci_99[1] * self.population]
        
        # Probability distribution summary
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        distribution_summary = {f'p{p}': np.percentile(samples, p) for p in percentiles}
        
        return {
            'wastewater_level': wastewater_level,
            'prevalence': {
                'median': median,
                'mean': mean,
                'std': std,
                'ci_51': ci_51,
                'ci_95': ci_95,
                'ci_99': ci_99
            },
            'infectious_population': {
                'median': infectious_median,
                'ci_51': infectious_ci_51,
                'ci_95': infectious_ci_95,
                'ci_99': infectious_ci_99
            },
            'distribution_summary': distribution_summary
        }
    
    def print_results(self, results):
        """Print formatted results."""
        
        ww = results['wastewater_level']
        prev = results['prevalence']
        inf_pop = results['infectious_population']
        dist = results['distribution_summary']
        
        print("="*70)
        print(f"PREVALENCE ESTIMATE FOR WASTEWATER LEVEL {ww}")
        print("="*70)
        print(f"Model: Calibrated Hierarchical Bayesian ({self.variant_period.replace('_', '-').title()})")
        print(f"Duration model: {self.duration_distribution.title()} distribution")
        print(f"Valid samples: {results['n_valid_samples']:,} / {results['n_requested_samples']:,}")
        print()
        
        print("PREVALENCE ESTIMATES:")
        print(f"Mean:           {prev['mean']*100:.3f}%")
        print(f"Median:         {prev['median']*100:.3f}%")
        print(f"Std Dev:        {prev['std']*100:.3f}%")
        print()
        
        print("CREDIBLE INTERVALS:")
        print(f"51% CI:         [{prev['ci_51'][0]*100:.3f}%, {prev['ci_51'][1]*100:.3f}%]")
        print(f"95.0% CI:       [{prev['ci_95'][0]*100:.3f}%, {prev['ci_95'][1]*100:.3f}%]")
        print(f"99.0% CI:       [{prev['ci_99'][0]*100:.3f}%, {prev['ci_99'][1]*100:.3f}%]")
        print()
        
        print("INFECTIOUS POPULATION:")
        print(f"Median:         {inf_pop['median']:,.0f} people")
        print(f"51% CI:         [{inf_pop['ci_51'][0]:,.0f}, {inf_pop['ci_51'][1]:,.0f}] people")
        print(f"95.0% CI:       [{inf_pop['ci_95'][0]:,.0f}, {inf_pop['ci_95'][1]:,.0f}] people")
        print(f"99.0% CI:       [{inf_pop['ci_99'][0]:,.0f}, {inf_pop['ci_99'][1]:,.0f}] people")
        print()
        
        print("PROBABILITY DISTRIBUTION SUMMARY:")
        print("Percentile    Prevalence")
        print("-" * 25)
        for p in [5, 10, 25, 50, 75, 90, 95]:
            print(f"    {p:2d}%        {dist[f'p{p}']*100:.3f}%")
        
        print()
        print("INTERPRETATION:")
        print(f"• There is a 51% probability that prevalence is between")
        print(f"  {prev['ci_51'][0]*100:.3f}% and {prev['ci_51'][1]*100:.3f}%")
        print(f"• There is a 95% probability that prevalence is between")
        print(f"  {prev['ci_95'][0]*100:.3f}% and {prev['ci_95'][1]*100:.3f}%")
        print("="*70)
    
    def plot_distribution(self, results, save_path=None, show_plot=True):
        """Create visualization of prevalence distribution."""
        
        samples = results['samples']
        prev = results['prevalence']
        ww = results['wastewater_level']
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Histogram with credible intervals
        ax1 = axes[0, 0]
        ax1.hist(samples*100, bins=50, density=True, alpha=0.7, color='skyblue', 
                edgecolor='navy', linewidth=0.5)
        
        # Add credible interval lines
        ax1.axvline(prev['median']*100, color='red', linestyle='-', linewidth=2, 
                   label=f"Median: {prev['median']*100:.3f}%")
        ax1.axvline(prev['ci_51'][0]*100, color='orange', linestyle='--', linewidth=2)
        ax1.axvline(prev['ci_51'][1]*100, color='orange', linestyle='--', linewidth=2, 
                   label=f"51% CI")
        ax1.axvline(prev['ci_95'][0]*100, color='green', linestyle=':', linewidth=2)
        ax1.axvline(prev['ci_95'][1]*100, color='green', linestyle=':', linewidth=2, 
                   label=f"95% CI")
        
        ax1.set_xlabel('Prevalence (%)')
        ax1.set_ylabel('Density')
        ax1.set_title(f'Prevalence Distribution (Wastewater = {ww})')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot
        ax2 = axes[0, 1]
        bp = ax2.boxplot([samples*100], patch_artist=True, labels=['Prevalence'])
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][0].set_alpha(0.7)
        
        ax2.set_ylabel('Prevalence (%)')
        ax2.set_title('Distribution Summary')
        ax2.grid(True, alpha=0.3)
        
        # Cumulative distribution
        ax3 = axes[1, 0]
        sorted_samples = np.sort(samples*100)
        y = np.linspace(0, 1, len(sorted_samples))
        ax3.plot(sorted_samples, y, 'b-', linewidth=2)
        
        # Add credible interval markers
        for ci_level, color, style in [(51, 'orange', '--'), (95, 'green', ':')]:
            lower = np.percentile(samples*100, (100-ci_level)/2)
            upper = np.percentile(samples*100, ci_level + (100-ci_level)/2)
            lower_y = (100-ci_level)/200
            upper_y = ci_level/100 + (100-ci_level)/200
            ax3.plot([lower, upper], [lower_y, upper_y], color=color, 
                    linestyle=style, linewidth=3, alpha=0.8,
                    label=f'{ci_level}% CI')
        
        ax3.set_xlabel('Prevalence (%)')
        ax3.set_ylabel('Cumulative Probability')
        ax3.set_title('Cumulative Distribution Function')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Log scale histogram for better visualization of tails
        ax4 = axes[1, 1]
        ax4.hist(samples*100, bins=50, density=True, alpha=0.7, color='lightcoral')
        ax4.set_xlabel('Prevalence (%)')
        ax4.set_ylabel('Density')
        ax4.set_title('Distribution (Log Scale)')
        ax4.set_yscale('log')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        
        if show_plot:
            plt.show()
        else:
            plt.close()
    
    def save_results(self, results, output_path):
        """Save results to JSON file."""
        
        # Convert numpy arrays to lists for JSON serialization
        results_json = {}
        for key, value in results.items():
            if key == 'samples':
                results_json[key] = value.tolist()
            elif isinstance(value, dict):
                results_json[key] = {}
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, (list, tuple)):
                        results_json[key][subkey] = [float(x) for x in subvalue]
                    else:
                        results_json[key][subkey] = float(subvalue)
            else:
                results_json[key] = value
        
        with open(output_path, 'w') as f:
            json.dump(results_json, f, indent=2)
        
        print(f"Results saved to: {output_path}")
    
    def save_distribution_only(self, samples, wastewater_level, output_path):
        """Save only the distribution samples in a compact format."""
        
        distribution_data = {
            'wastewater_level': wastewater_level,
            'variant_period': self.variant_period,
            'n_samples': len(samples),
            'samples': samples.tolist(),
            # Include summary statistics for quick reference
            'summary': {
                'median': float(np.median(samples)),
                'mean': float(np.mean(samples)),
                'std': float(np.std(samples)),
                'p5': float(np.percentile(samples, 5)),
                'p25': float(np.percentile(samples, 25)),
                'p75': float(np.percentile(samples, 75)),
                'p95': float(np.percentile(samples, 95))
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(distribution_data, f, separators=(',', ':'))  # Compact JSON
            
    @staticmethod
    def load_distribution(filepath):
        """Load pre-computed distribution from file."""
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return {
            'samples': np.array(data['samples']),
            'wastewater_level': data['wastewater_level'],
            'variant_period': data.get('variant_period', 'omicron'),
            'summary': data.get('summary', {})
        }


def main():
    """Main estimation pipeline."""
    
    parser = argparse.ArgumentParser(description="Estimate COVID-19 prevalence from wastewater level")
    parser.add_argument("--wastewater", type=float, required=True, 
                       help="Wastewater level measurement")
    parser.add_argument("--samples", type=int, default=10000,
                       help="Number of posterior samples (default: 10000)")
    parser.add_argument("--plot", action="store_true",
                       help="Generate and display plots")
    parser.add_argument("--save-plot", type=str,
                       help="Save plot to specified path")
    parser.add_argument("--save-results", type=str,
                       help="Save results to JSON file")
    parser.add_argument("--population", type=float, default=332_000_000,
                       help="Population size (default: 332M)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility")
    parser.add_argument("--variant", choices=["omicron", "pre_omicron"], default="omicron",
                       help="Variant period for infectiousness duration (default: omicron)")
    
    args = parser.parse_args()
    
    # Validate input
    if args.wastewater <= 0:
        raise ValueError("Wastewater level must be positive")
    
    # Initialize estimator
    estimator = PrevalenceEstimator(population=args.population, variant_period=args.variant)
    
    # Generate estimates
    print(f"Generating prevalence estimates for wastewater level {args.wastewater}...")
    results = estimator.estimate_prevalence(
        wastewater_level=args.wastewater,
        n_samples=args.samples,
        seed=args.seed
    )
    
    # Print results
    estimator.print_results(results)
    
    # Generate plots if requested
    if args.plot or args.save_plot:
        estimator.plot_distribution(
            results, 
            save_path=args.save_plot,
            show_plot=args.plot
        )
    
    # Save results if requested
    if args.save_results:
        estimator.save_results(results, args.save_results)


if __name__ == "__main__":
    main()