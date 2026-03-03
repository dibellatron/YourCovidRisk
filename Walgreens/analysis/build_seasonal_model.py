#!/usr/bin/env python3
"""
build_seasonal_model.py — Seasonal COVID Test Positivity Model

Builds a week-of-year seasonal model from historical Walgreens COVID test
positivity data (May 2021 – July 2025). This model estimates what test
positivity rates tend to be at any given time of year.

BACKGROUND
----------
Walgreens stopped publishing COVID test positivity data in summer 2025.
The test calculator needs current positivity estimates to function as a
Bayesian prior for symptomatic users and as a calibration parameter for
asymptomatic users. This script builds a seasonal model from the historical
record so we can estimate positivity for any week of the year.

METHODOLOGY
-----------
1. We use ONLY 2023–2025 data. Testing behavior in 2021–2022 was
   fundamentally different (mass asymptomatic screening vs. today's
   symptomatic-only testing), making those positivity rates incomparable.

2. For each region (national + 29 states) and ISO week-of-year (1–52),
   we compute a test-count-weighted average positivity rate. Weighting by
   test_count means days with more tests (= more statistical power)
   contribute more to the estimate.

3. Week 53 (which occurs in some years) is merged into week 52.

4. States missing data for a given week get no entry in the model;
   the test calculator already falls back to national when state data
   is unavailable.

OUTPUT
------
- seasonal_positivity_model.csv : Full model (region × week → positivity)
- seasonal_positivity_plot.png  : National seasonal curve visualization

USAGE
-----
    python3 build_seasonal_model.py

Run from the Walgreens/analysis/ directory, or the script will locate
data files relative to its own path.
"""

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for PNG output
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Only use data from these years (post-mass-testing era)
MIN_YEAR = 2023
MAX_YEAR = 2025

# Merge ISO week 53 into week 52
MAX_WEEK = 52


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_iso_week(date_str):
    """Parse a YYYY-MM-DD date string and return (year, iso_week)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso_year, iso_week, _ = dt.isocalendar()
    # Merge week 53 into week 52
    if iso_week > MAX_WEEK:
        iso_week = MAX_WEEK
    return iso_year, iso_week


def locate_data_dir():
    """Return the absolute path to Walgreens/walgreens_clean/."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, "..", "walgreens_clean")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_model():
    data_dir = locate_data_dir()
    national_path = os.path.join(data_dir, "covid_history_national.csv")
    states_path = os.path.join(data_dir, "covid_history_states.csv")

    # Accumulator: {(region, week): {"weighted_pos": float, "total_weight": int}}
    accum = defaultdict(lambda: {"weighted_pos": 0.0, "total_weight": 0})

    files_to_read = []
    if os.path.exists(national_path):
        files_to_read.append(national_path)
    else:
        print(f"WARNING: National history not found at {national_path}", file=sys.stderr)

    if os.path.exists(states_path):
        files_to_read.append(states_path)
    else:
        print(f"WARNING: State history not found at {states_path}", file=sys.stderr)

    rows_read = 0
    rows_used = 0

    for fpath in files_to_read:
        with open(fpath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_read += 1
                date_str = row.get("date", "")
                region = row.get("region", "").strip()
                pos_str = row.get("positivity_rate", "")
                count_str = row.get("test_count", "")

                if not (date_str and region and pos_str and count_str):
                    continue

                try:
                    year, week = get_iso_week(date_str)
                except ValueError:
                    continue

                # Filter to target year range
                if year < MIN_YEAR or year > MAX_YEAR:
                    continue

                try:
                    positivity = float(pos_str)
                    test_count = int(float(count_str))
                except (ValueError, TypeError):
                    continue

                if test_count <= 0:
                    continue

                rows_used += 1
                key = (region.lower(), week)
                accum[key]["weighted_pos"] += positivity * test_count
                accum[key]["total_weight"] += test_count

    print(f"Read {rows_read:,} rows, used {rows_used:,} (from {MIN_YEAR}–{MAX_YEAR})")

    # Compute weighted averages
    model = []
    for (region, week), vals in sorted(accum.items()):
        if vals["total_weight"] > 0:
            avg_pos = vals["weighted_pos"] / vals["total_weight"]
            model.append({
                "region": region,
                "week": week,
                "positivity_rate": round(avg_pos, 6),
                "sample_size": vals["total_weight"],
            })

    # Write model CSV
    output_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(output_dir, "seasonal_positivity_model.csv")
    with open(model_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["region", "week", "positivity_rate", "sample_size"])
        writer.writeheader()
        writer.writerows(model)

    print(f"Wrote seasonal model → {model_path}")
    print(f"  {len(model)} entries across {len(set(r['region'] for r in model))} regions")

    # Generate national seasonal plot
    national_data = [(r["week"], r["positivity_rate"], r["sample_size"])
                     for r in model if r["region"] == "national"]
    national_data.sort(key=lambda x: x[0])

    if national_data:
        weeks = [d[0] for d in national_data]
        rates = [d[1] * 100 for d in national_data]  # Convert to percentage
        sizes = [d[2] for d in national_data]

        fig, ax = plt.subplots(figsize=(12, 5))

        # Scatter with size proportional to sample size (capped for readability)
        max_size = max(sizes)
        scaled_sizes = [max(20, (s / max_size) * 200) for s in sizes]
        ax.scatter(weeks, rates, s=scaled_sizes, alpha=0.4, color="#3b82f6",
                   label="Weekly estimate (size = sample count)", zorder=2)

        # Smoothed line (simple moving average with wrap-around for continuity)
        extended_rates = rates[-3:] + rates + rates[:3]
        kernel = np.ones(7) / 7
        smoothed = np.convolve(extended_rates, kernel, mode="same")[3:-3]
        ax.plot(weeks, smoothed, color="#1e40af", linewidth=2.5,
                label="7-week smoothed average", zorder=3)

        ax.set_xlabel("ISO Week of Year", fontsize=12)
        ax.set_ylabel("Test Positivity Rate (%)", fontsize=12)
        ax.set_title(
            f"Seasonal COVID Test Positivity (National, {MIN_YEAR}–{MAX_YEAR})\n"
            "Based on historical Walgreens testing data, weighted by test count",
            fontsize=13
        )
        ax.set_xlim(0.5, 52.5)
        ax.set_ylim(0, max(rates) * 1.15)
        ax.legend(loc="upper left", fontsize=10)
        ax.grid(True, alpha=0.3)

        # Add month labels on x-axis
        month_starts = {1: "Jan", 5: "Feb", 9: "Mar", 14: "Apr", 18: "May",
                        22: "Jun", 27: "Jul", 31: "Aug", 36: "Sep", 40: "Oct",
                        44: "Nov", 48: "Dec"}
        ax.set_xticks(list(month_starts.keys()))
        ax.set_xticklabels(list(month_starts.values()))

        plot_path = os.path.join(output_dir, "seasonal_positivity_plot.png")
        fig.tight_layout()
        fig.savefig(plot_path, dpi=150)
        plt.close(fig)
        print(f"Wrote plot → {plot_path}")
    else:
        print("WARNING: No national data found for plot", file=sys.stderr)

    return model_path


if __name__ == "__main__":
    build_model()
