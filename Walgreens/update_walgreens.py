#!/usr/bin/env python3
"""
update_walgreens.py

Orchestrate the full pipeline: fetch raw data, transform to CSV,
and produce dated + current master CSVs for both COVID-19 and Flu.
"""
import os
import sys
import subprocess
import datetime
import shutil
import argparse
import csv

# States that don't have data and should be excluded from current CSV files
EXCLUDED_STATES = [
    'OR', 'ID', 'MT', 'WY', 'ND', 'SD', 'NV', 'UT', 'KS', 
    'IA', 'LA', 'KY', 'WV', 'ME', 'NH', 'VT', 'MA', 
    'RI', 'CT', 'HI', 'AK'
]

"""
Previous helper to filter out excluded states, no longer used.
"""
_ = None  # placeholder to retain import csv

def main():
    parser = argparse.ArgumentParser(
        description='Fetch and update Walgreens Respiratory Index CSVs')
    parser.add_argument('--har-file', default='walgreens.har',
                        help='Path to original walgreens.har (for resource key)')
    # Default template directory is this script's templates subfolder
    default_tpl = os.path.join(os.path.dirname(__file__), 'templates')
    parser.add_argument('--template-dir', default=default_tpl,
                        help='Directory containing covid_template.json & flu_template.json')
    parser.add_argument('--data-dir', default='walgreens_data',
                        help='Directory to store intermediate JSON')
    parser.add_argument('--clean-dir', default='walgreens_clean',
                        help='Directory to store final CSVs')
    args = parser.parse_args()
    # 1. Fetch raw JSON data for all metrics and regions
    cmd_fetch = [
        sys.executable, 'pipeline_walgreens.py', args.har_file,
        '--template-dir', args.template_dir,
        '--out-dir', args.data_dir
    ]
    print('Running fetch pipeline:', ' '.join(cmd_fetch))
    subprocess.run(cmd_fetch, check=True)
    # 2. Transform raw JSON to aggregated CSVs
    cmd_transform = [
        sys.executable, 'transform_walgreens_data.py',
        '--data-dir', args.data_dir,
        '--out-dir', args.clean_dir
    ]
    print('Running transform:', ' '.join(cmd_transform))
    subprocess.run(cmd_transform, check=True)
    # 3. Rename CSVs with date and update 'current'
    today = datetime.date.today().strftime('%Y-%m-%d')
    # Rename each metric.csv -> metric_DATE.csv and update metric_current.csv
    for fname in sorted(os.listdir(args.clean_dir)):
        if not fname.endswith('.csv') or '_' in fname:
            continue
        metric = fname[:-4]
        src = os.path.join(args.clean_dir, fname)
        dated = os.path.join(args.clean_dir, f'{metric}_{today}.csv')
        current = os.path.join(args.clean_dir, f'{metric}_current.csv')
        print(f'Renaming {src} to {dated}')
        shutil.move(src, dated)
        # Read the dated CSV for history purposes
        with open(dated, newline='', encoding='utf-8') as f_in:
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            rows = list(reader)
        # Generate current snapshot
        if metric == 'covid':
            print('Generating current snapshot for covid (latest valid per-state within 14 days of national)')
            # Parse valid entries: positivity_rate >0,<1 and test_count >=8
            parsed = []
            for r in rows:
                region_val = r.get('region', '')
                if region_val in EXCLUDED_STATES:
                    continue
                date_str = r.get('date', '')
                rate_str = r.get('positivity_rate', '')
                count_str = r.get('test_count', '')
                try:
                    date_obj = datetime.date.fromisoformat(date_str)
                    rate = float(rate_str)
                    count = int(count_str) if count_str else 0
                except Exception:
                    continue
                if 0 < rate < 1 and count >= 8:
                    parsed.append({'region': region_val, 'date': date_obj, 'row': r})
            # Determine most recent national entry
            nat_entries = [e for e in parsed if e['region'].lower() == 'national']
            national_latest = None
            if nat_entries:
                national_latest = max(nat_entries, key=lambda e: e['date'])
                national_date = national_latest['date']
                national_row = national_latest['row']
            else:
                national_date = None
                national_row = None
            # Build per-state current rows
            current_rows = []
            regions = {e['region'] for e in parsed if e['region'].lower() != 'national'}
            for region in regions:
                # Filter state entries within 14 days of national date
                candidates = []
                for e in parsed:
                    if e['region'] == region and national_date and (national_date - e['date']).days <= 14 and e['date'] <= national_date:
                        candidates.append(e)
                if candidates:
                    sel = max(candidates, key=lambda e: e['date'])['row']
                else:
                    sel = national_row
                if sel:
                    current_rows.append(sel)
            # Include national itself
            if national_row:
                current_rows.append(national_row)
            # Write current CSV
            with open(current, 'w', newline='', encoding='utf-8') as f_curr:
                curr_writer = csv.DictWriter(f_curr, fieldnames=fieldnames)
                curr_writer.writeheader()
                for row in current_rows:
                    curr_writer.writerow(row)
            # Use today for history threshold
            current_date = today
        else:
            print(f'Generating current snapshot {current}')
            # Use only rows from dated file
            dates = [row['date'] for row in rows if row.get('date')]
            if not dates:
                print(f'No date data found in {dated}, skipping history generation')
                continue
            current_date = max(dates)
            with open(current, 'w', newline='', encoding='utf-8') as f_curr:
                curr_writer = csv.DictWriter(f_curr, fieldnames=fieldnames)
                curr_writer.writeheader()
                for row in rows:
                    if row.get('date') == current_date and row.get('region') not in EXCLUDED_STATES:
                        curr_writer.writerow(row)
        # Write history: separate national and statewide older rates
        hist_nat = os.path.join(args.clean_dir, f'{metric}_history_national.csv')
        print(f'Generating national history {hist_nat}')
        with open(hist_nat, 'w', newline='', encoding='utf-8') as f_nat:
            nat_writer = csv.DictWriter(f_nat, fieldnames=fieldnames)
            nat_writer.writeheader()
            for row in rows:
                if row.get('date') < current_date and row.get('region', '').lower() == 'national':
                    nat_writer.writerow(row)
        hist_states = os.path.join(args.clean_dir, f'{metric}_history_states.csv')
        print(f'Generating states history {hist_states}')
        with open(hist_states, 'w', newline='', encoding='utf-8') as f_st:
            st_writer = csv.DictWriter(f_st, fieldnames=fieldnames)
            st_writer.writeheader()
            for row in rows:
                region = row.get('region', '')
                if (row.get('date') < current_date and
                    region not in EXCLUDED_STATES and region.lower() != 'national'):
                    st_writer.writerow(row)
    print('Update complete for', today)

if __name__ == '__main__':
    main()