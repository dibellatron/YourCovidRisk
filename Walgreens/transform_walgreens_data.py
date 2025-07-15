#!/usr/bin/env python3
"""
transform_walgreens_data.py

Convert raw Power BI JSON outputs in walgreens_data/ into clean CSV time-series.
Produces two CSVs: covid.csv and flu.csv with columns: region, date, positivity_rate, test_count.
"""
import os
import sys
import json
import csv
import datetime
import argparse

# Mapping of raw JSON column names to clean field names
FIELD_RENAMES = {
    'Positivity_National': 'positivity_rate',
    'Positivity_test_National': 'test_count',
    'Positivity Confirmed4': 'positivity_rate',
    'Positivity Presumed5': 'positivity_rate',
    # For older combined templates
    'Positivity2 view': 'positivity_rate',
    'Positivity2 Total': 'test_count'
}

def parse_file(filepath):
    """
    Parse a single JSON file from Power BI and return list of dicts:
      [{ 'date': 'YYYY-MM-DD', 'positivity_rate': float, 'test_count': int }, ...]
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        j = json.load(f)
    # Navigate to dsr
    data = j['results'][0]['result']['data']
    dsr = data['dsr']
    ds0 = dsr['DS'][0]
    # Page header with rows
    ph0 = ds0['PH'][0]
    # The row list key usually starts with 'DM'
    row_key = next(k for k in ph0 if isinstance(ph0[k], list))
    rows = ph0[row_key]
    if not rows:
        return []
    # Derive schema from first row's 'S' if present, else fall back to ds0['S']
    first_row = rows[0]
    schema = first_row.get('S') or ds0.get('S', [])
    # Descriptor to map codes to names
    selects = data['descriptor']['Select']
    mapping = { entry['Value']: entry['Name'].split('.')[-1] for entry in selects }
    result = []
    for row in rows:
        cells = row.get('C', [])
        rec = {}
        # Use schema derived above to map columns to cell values
        for col, cell in zip(schema, cells):
            col_code = col.get('N')
            col_name = mapping.get(col_code, col_code)
            # Map Date field
            if col_name == 'Date':
                try:
                    dt = datetime.datetime.utcfromtimestamp(cell/1000)
                    rec['date'] = dt.strftime('%Y-%m-%d')
                except Exception:
                    rec['date'] = cell
            else:
                # numeric positivity or count
                key = FIELD_RENAMES.get(col_name, col_name)
                val = cell
                if isinstance(cell, str):
                    # strip trailing 'D' markers
                    if cell.endswith('D'):
                        cell = cell[:-1]
                    try:
                        val = float(cell)
                    except Exception:
                        val = cell
                rec[key] = val
        result.append(rec)
    return result

def main():
    parser = argparse.ArgumentParser(description='Transform raw walgreens_data JSON to CSV')
    parser.add_argument('--data-dir', default='walgreens_data', help='Input directory from pipeline')
    parser.add_argument('--out-dir', default='walgreens_clean', help='Output directory for CSVs')
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    # Discover metrics directories (e.g. covid, fluA, fluB)
    for metric in sorted(os.listdir(args.data_dir)):
        in_dir = os.path.join(args.data_dir, metric)
        if not os.path.isdir(in_dir):
            continue
        out_csv = os.path.join(args.out_dir, f'{metric}.csv')
        with open(out_csv, 'w', newline='', encoding='utf-8') as f:
            writer = None
            for fname in sorted(os.listdir(in_dir)):
                if not fname.endswith('.json'):
                    continue
                region = fname[:-5]
                filepath = os.path.join(in_dir, fname)
                try:
                    data = parse_file(filepath)
                except Exception as e:
                    print(f'Error parsing {filepath}: {e}', file=sys.stderr)
                    continue
                for rec in data:
                    rec['region'] = region
                    # Initialize writer on first record
                    if writer is None:
                        # Determine field order: region, date, positivity_rate, test_count
                        fieldnames = ['region', 'date', 'positivity_rate', 'test_count']
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                    # Fill missing keys with empty
                    for key in ['positivity_rate', 'test_count']:
                        if key not in rec:
                            rec[key] = ''
                    writer.writerow(rec)
        print(f'Wrote cleaned CSV: {out_csv}')

if __name__ == '__main__':
    main()