#!/usr/bin/env python3
"""
generate_current_estimates.py — Generate current positivity estimates

Reads the seasonal positivity model (built by build_seasonal_model.py) and
outputs an estimated covid_current.csv for the current week of the year.

The output file uses the EXACT SAME FORMAT as the original Walgreens
covid_current.csv so the test calculator can read it with zero code changes:

    region,date,positivity_rate,test_count
    national,2026-03-03,0.2145,8523
    CA,2026-03-03,0.1987,412
    ...

- date       = today's date (when the estimate was generated)
- test_count  = historical sample size from the seasonal model
                (preserves the uncertainty signal for Monte Carlo CI)

USAGE
-----
    python3 generate_current_estimates.py

Run after build_seasonal_model.py has produced seasonal_positivity_model.csv.
"""

import csv
import os
import sys
from datetime import date


def locate_paths():
    """Return paths to the model CSV and the output covid_current.csv."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, "seasonal_positivity_model.csv")
    output_path = os.path.join(script_dir, "..", "walgreens_clean", "covid_current.csv")
    return model_path, output_path


def generate_estimates():
    model_path, output_path = locate_paths()

    if not os.path.exists(model_path):
        print(f"ERROR: Seasonal model not found at {model_path}", file=sys.stderr)
        print("Run build_seasonal_model.py first.", file=sys.stderr)
        sys.exit(1)

    # Determine current ISO week (merge week 53 → 52)
    today = date.today()
    _, current_week, _ = today.isocalendar()
    if current_week > 52:
        current_week = 52

    today_str = today.isoformat()

    print(f"Generating estimates for {today_str} (ISO week {current_week})")

    # Read the seasonal model
    model = {}  # {region: {week: (positivity_rate, sample_size)}}
    with open(model_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region = row["region"]
            week = int(row["week"])
            pos = float(row["positivity_rate"])
            size = int(row["sample_size"])
            if region not in model:
                model[region] = {}
            model[region][week] = (pos, size)

    # Look up current week for each region
    rows = []
    national_entry = None

    for region in sorted(model.keys()):
        week_data = model[region]
        if current_week in week_data:
            pos, size = week_data[current_week]
        else:
            # Try adjacent weeks as fallback
            for offset in [1, -1, 2, -2]:
                candidate = current_week + offset
                if candidate in week_data:
                    pos, size = week_data[candidate]
                    print(f"  {region}: no data for week {current_week}, "
                          f"using week {candidate}")
                    break
            else:
                # No nearby week found; skip this region
                print(f"  {region}: no data near week {current_week}, skipping")
                continue

        entry = {
            "region": region,
            "date": today_str,
            "positivity_rate": pos,
            "test_count": size,
        }
        rows.append(entry)
        if region == "national":
            national_entry = entry

    # Write covid_current.csv — national first, then states alphabetically
    rows.sort(key=lambda r: ("" if r["region"] == "national" else r["region"]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["region", "date", "positivity_rate", "test_count"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} entries → {output_path}")

    if national_entry:
        print(f"  National estimate: {national_entry['positivity_rate'] * 100:.1f}% positivity "
              f"(based on {national_entry['test_count']:,} historical tests)")


if __name__ == "__main__":
    generate_estimates()
