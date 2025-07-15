#!/usr/bin/env python3
"""
Generate a Markdown table of daily prevalence and cumulative risk for a repeated-exposure
scenario using the current CDC wastewater prevalence (first week) and weekly CDC data after.

Usage:
  python3 scripts/daily_repeated_exposure.py [--state STATE_CODE]

Options:
  --state STATE   Two-letter US state code for regional prevalence (default: National)
"""
import sys, os, csv

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from calculators.exposure_calculator import calculate_unified_transmission_exposure
from calculators.time_varying_prevalence import (
    load_cdc_prevalence_data,
    get_current_iso_week,
    calculate_daily_cumulative_risk,
    calculate_time_varying_threshold,
)

STATE_REGION_MAP = {
    'IL': 'Midwest','IN': 'Midwest','IA': 'Midwest','KS': 'Midwest','MI': 'Midwest',
    'MN': 'Midwest','MO': 'Midwest','NE': 'Midwest','ND': 'Midwest','OH': 'Midwest','SD': 'Midwest','WI': 'Midwest',
    'CT': 'Northeast','ME': 'Northeast','MA': 'Northeast','NH': 'Northeast','NJ': 'Northeast','NY': 'Northeast','PA': 'Northeast','RI': 'Northeast','VT': 'Northeast',
    'AL': 'South','AR': 'South','DE': 'South','FL': 'South','GA': 'South','KY': 'South','LA': 'South','MD': 'South','MS': 'South','NC': 'South','OK': 'South','SC': 'South','TN': 'South','TX': 'South','VA': 'South','WV': 'South',
    'AK': 'West','AZ': 'West','CA': 'West','CO': 'West','HI': 'West','ID': 'West','MT': 'West','NV': 'West','NM': 'West','OR': 'West','UT': 'West','WA': 'West','WY': 'West'
}

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--state', help='US state code for regional prevalence')
    return p.parse_args()

def load_current_prevalence(region):
    path = os.path.join(os.path.dirname(__file__), '..', 'PMC', 'Prevalence', 'prevalence_current.csv')
    with open(path, newline='', encoding='utf-8') as f:
        row = next(csv.DictReader(f))
    val = row.get(region, row.get('National', '0')).strip().rstrip('%')
    try:
        return float(val) / 100.0
    except ValueError:
        return 0.01

def main():
    args = parse_args()
    region = STATE_REGION_MAP.get((args.state or '').upper(), 'National')

    # First-week prevalence from current data
    base_prev = load_current_prevalence(region)
    start_week = get_current_iso_week()

    # Scenario defaults (UI defaults)
    scenario = {
        'C0':'0.065','Q0':'0.08','p':'0.08','ACH':'4.30','room_volume':'300',
        'delta_t': str(8*3600), 'x':'6','activity_choice':'2','gamma':'0.7',
        'f_e':'1','f_i':'1','omicron':'3.3', 'covid_prevalence':str(base_prev),
        'immune':'1','N':'35','percentage_masked':'0', 'RH':0.40,'CO2':800.0,'inside_temp':293.15
    }

    # Compute base one-off risk
    result = calculate_unified_transmission_exposure(**scenario)
    base_risk = result.get('risk', 0.0)

    # Threshold: days to 50% risk
    threshold = calculate_time_varying_threshold(base_risk, base_prev, region, start_week) or 30

    cdc_weekly = load_cdc_prevalence_data()

    print('| Day | Prevalence (%) | Daily Risk (%) | Cumulative Risk (%) |')
    print('|:---:|:--------------:|:--------------:|:------------------:|')

    cum_safe = 1.0
    for day in range(1, threshold+1):
        wk_off = (day-1)//7
        if wk_off == 0:
            prev = base_prev
        else:
            wk = ((start_week-1 + wk_off) % 52) + 1
            prev = cdc_weekly.get(wk, {}).get(region, base_prev)

        scenario['covid_prevalence'] = str(prev)
        day_risk = calculate_unified_transmission_exposure(**scenario).get('risk', 0.0)

        cum_safe *= (1.0 - day_risk)
        cum_risk = 1.0 - cum_safe

        print(f'| {day:3d} | {prev*100:6.2f}% | {day_risk*100:6.2f}% | {cum_risk*100:7.3f}% |')

    print(f'\nThreshold: {threshold} days to exceed 50% risk (Region: {region})')

if __name__ == '__main__':
    main()