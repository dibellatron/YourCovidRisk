#!/usr/bin/env python3
"""
Manually generate pre-computed prevalence distributions from current prevalence data.
This can be run independently of pull_prevalence.py when needed.
"""

import os
import sys
import json
import csv
import numpy as np
from datetime import datetime
from pathlib import Path

# Add wastewater module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wastewater'))

def load_current_prevalence():
    """Load the most recent prevalence data from prevalence_current.csv."""
    csv_path = Path(__file__).parent / "Prevalence" / "prevalence_current.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"prevalence_current.csv not found at {csv_path}")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)  # Get first (and only) row
        return row

def prevalence_to_wastewater(prevalence_pct):
    """Convert prevalence percentage to approximate wastewater level."""
    # Based on calibrated model: log10(ww) ≈ 4.211 + 0.353 * log(prevalence)
    if prevalence_pct <= 0:
        return 50  # Minimum detectable level
    prevalence_fraction = prevalence_pct / 100.0
    log_prevalence = np.log(prevalence_fraction)
    log10_ww = 4.211 + 0.353 * log_prevalence
    return 10 ** log10_ww

def generate_distributions():
    """Generate and save prevalence distributions for all regions."""
    from estimate_prevalence import PrevalenceEstimator
    
    # Load current prevalence data
    print("Loading current prevalence data...")
    prevalence_data = load_current_prevalence()
    date = prevalence_data.get('Date', 'unknown')
    
    print(f"Prevalence data from: {date}")
    print("-" * 40)
    
    # Directory for storing pre-computed distributions
    dist_dir = Path(__file__).parent / "PrecomputedDistributions"
    dist_dir.mkdir(exist_ok=True)
    
    # Generate distributions for each region
    estimator = PrevalenceEstimator(variant_period="omicron")
    regions = ["National", "Northeast", "Midwest", "South", "West"]
    
    results_summary = {}
    
    for region in regions:
        prevalence_str = prevalence_data.get(region, "")
        if not prevalence_str:
            print(f"⚠️  No data for {region}, skipping...")
            continue
        
        try:
            # Parse prevalence percentage
            prevalence_pct = float(prevalence_str.strip().rstrip('%'))
            
            # Convert to wastewater level
            wastewater_level = prevalence_to_wastewater(prevalence_pct)
            
            print(f"\n{region}:")
            print(f"  Prevalence: {prevalence_pct}%")
            print(f"  Wastewater level: {wastewater_level:.0f}")
            print("  Generating distribution...", end="", flush=True)
            
            # Generate prevalence distribution
            results = estimator.estimate_prevalence(
                wastewater_level=wastewater_level,
                n_samples=20000,  # Generate many samples for better coverage
                seed=42
            )
            
            # Save distribution
            output_path = dist_dir / f"{region.lower()}_distribution.json"
            estimator.save_distribution_only(
                results['samples'], 
                wastewater_level, 
                str(output_path)
            )
            
            print(" ✓")
            
            # Store summary for reporting
            results_summary[region] = {
                'prevalence_input': prevalence_pct,
                'wastewater_level': wastewater_level,
                'median': float(np.median(results['samples']) * 100),
                'std': float(np.std(results['samples']) * 100),
                'p5': float(np.percentile(results['samples'], 5) * 100),
                'p95': float(np.percentile(results['samples'], 95) * 100)
            }
            
        except (ValueError, KeyError) as e:
            print(f"\n❌ Error processing {region}: {e}")
    
    # Save timestamp and summary
    timestamp_path = dist_dir / "generation_timestamp.json"
    with open(timestamp_path, "w") as f:
        json.dump({
            "source_date": date,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "prevalence_data": {k: prevalence_data.get(k) for k in regions if k in prevalence_data},
            "summary": results_summary
        }, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)
    print(f"Source data date: {date}")
    print(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("\nRegion      | Input  | Median | Std   | 90% CI")
    print("-" * 60)
    
    for region, summary in results_summary.items():
        print(f"{region:<11} | {summary['prevalence_input']:5.2f}% | {summary['median']:5.3f}% | {summary['std']:5.3f}% | [{summary['p5']:5.3f}%, {summary['p95']:5.3f}%]")
    
    print("\n✅ Distributions generated successfully!")
    print(f"📁 Saved to: {dist_dir}")

if __name__ == "__main__":
    generate_distributions()