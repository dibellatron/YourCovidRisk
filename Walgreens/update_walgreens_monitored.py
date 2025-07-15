#!/usr/bin/env python3
"""
update_walgreens_monitored.py

Enhanced version of update_walgreens.py with:
- Weekly scheduling (Mondays only)
- Email notifications on failure
- Duration monitoring
- Data validation and fallback
- Comprehensive error handling
"""

import os
import sys
import subprocess
import datetime
import shutil
import argparse
import csv
from pathlib import Path

# Add shared utilities to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from job_utils import monitored_job, DataValidator

# States that don't have data and should be excluded from current CSV files
EXCLUDED_STATES = [
    'OR', 'ID', 'MT', 'WY', 'ND', 'SD', 'NV', 'UT', 'KS', 
    'IA', 'LA', 'KY', 'WV', 'ME', 'NH', 'VT', 'MA', 
    'RI', 'CT', 'HI', 'AK'
]

def should_run_today():
    """
    Check if job should run today.
    - Tuesdays (weekday 1)
    - Exception: Sunday June 8, 2025
    """
    today = datetime.date.today()
    
    # Special exception for June 8, 2025 (Sunday)
    if today == datetime.date(2025, 6, 8):
        print("🎯 Special run: Sunday June 8, 2025")
        return True
    
    # Normal schedule: Tuesdays only
    is_tuesday = today.weekday() == 1  # Tuesday = 1
    
    print(f"📅 Schedule check: Today is {today.strftime('%A')} (weekday {today.weekday()})")
    
    if not is_tuesday:
        print("⏭️  Skipping Walgreens update - not scheduled for today (Tuesdays only)")
        return False
    
    return True

@monitored_job(
    job_name="walgreens_update",
    weekly_schedule=False,  # We handle scheduling manually
    max_duration_minutes=15,
    email_recipient=os.getenv('NOTIFICATION_EMAIL')
)
def update_walgreens_data():
    """Main function to update Walgreens data with monitoring and validation."""
    
    # Check if we should run today
    if not should_run_today():
        return {"status": "skipped", "reason": "not_scheduled"}
    
    # Set up paths
    script_dir = Path(__file__).parent
    har_file = script_dir / 'walgreens.har'
    template_dir = script_dir / 'templates'
    data_dir = script_dir / 'walgreens_data'
    clean_dir = script_dir / 'walgreens_clean'
    
    # Ensure directories exist
    data_dir.mkdir(exist_ok=True)
    clean_dir.mkdir(exist_ok=True)
    
    results = {
        'files_updated': [],
        'validation_results': {},
        'errors': []
    }
    
    try:
        # 1. Fetch raw JSON data for all metrics and regions
        cmd_fetch = [
            sys.executable, str(script_dir / 'pipeline_walgreens.py'), str(har_file),
            '--template-dir', str(template_dir),
            '--out-dir', str(data_dir)
        ]
        
        print('Running fetch pipeline:', ' '.join(cmd_fetch))
        fetch_result = subprocess.run(cmd_fetch, check=True, capture_output=True, text=True)
        
        if fetch_result.stderr:
            print(f"Fetch warnings: {fetch_result.stderr}")
        
        # 2. Transform raw JSON to aggregated CSVs
        cmd_transform = [
            sys.executable, str(script_dir / 'transform_walgreens_data.py'),
            '--data-dir', str(data_dir),
            '--out-dir', str(clean_dir)
        ]
        
        print('Running transform:', ' '.join(cmd_transform))
        transform_result = subprocess.run(cmd_transform, check=True, capture_output=True, text=True)
        
        if transform_result.stderr:
            print(f"Transform warnings: {transform_result.stderr}")
        
        # 3. Process and validate each CSV file
        today = datetime.date.today().strftime('%Y-%m-%d')
        
        for fname in sorted(os.listdir(clean_dir)):
            if not fname.endswith('.csv') or '_' in fname:
                continue
                
            metric = fname[:-4]
            src = clean_dir / fname
            dated = clean_dir / f'{metric}_{today}.csv'
            current = clean_dir / f'{metric}_current.csv'
            previous = clean_dir / f'{metric}_previous.csv'
            
            print(f'Processing {metric} data...')
            
            # Backup current file as previous (if exists)
            if current.exists():
                shutil.copy2(current, previous)
            
            # Rename to dated version
            print(f'Creating dated file: {dated}')
            shutil.move(src, dated)
            results['files_updated'].append(str(dated))
            
            # Read the dated CSV
            with open(dated, newline='', encoding='utf-8') as f_in:
                reader = csv.DictReader(f_in)
                fieldnames = reader.fieldnames
                rows = list(reader)
            
            # Generate current snapshot with validation
            current_rows = []
            
            if metric == 'covid':
                print('Generating current snapshot for COVID (latest valid per-state within 14 days of national)')
                current_rows = process_covid_data(rows, fieldnames)
            else:
                print(f'Generating current snapshot for {metric}')
                current_rows = process_other_metrics(rows, fieldnames)
            
            # Write current CSV
            with open(current, 'w', newline='', encoding='utf-8') as f_curr:
                curr_writer = csv.DictWriter(f_curr, fieldnames=fieldnames)
                curr_writer.writeheader()
                for row in current_rows:
                    curr_writer.writerow(row)
            
            results['files_updated'].append(str(current))
            
            # Validate the generated file
            # For flu data (fluA, fluB), be more lenient during off-season
            if metric in ['fluA', 'fluB']:
                min_rows_required = 0  # Allow empty flu data during off-season
            else:
                min_rows_required = 5  # COVID data should always have some data
                
            validation = DataValidator.validate_csv_file(
                str(current),
                required_columns=['date', 'region'],
                min_rows=min_rows_required,
                max_change_percent=100.0  # Allow large changes for Walgreens data
            )
            
            results['validation_results'][metric] = validation
            
            # Special handling for flu data during off-season
            if not validation['valid'] and metric in ['fluA', 'fluB']:
                # Check if the only error is "too few rows" for flu data
                row_errors = [e for e in validation['errors'] if 'too few rows' in e.lower() or 'no valid data' in e.lower()]
                other_errors = [e for e in validation['errors'] if e not in row_errors]
                
                if row_errors and not other_errors:
                    # Treat empty flu data as warning, not error (seasonal variation)
                    print(f"⚠️  {metric} data is empty (likely seasonal) - treating as warning")
                    validation['warnings'].extend(row_errors)
                    validation['errors'] = other_errors
                    validation['valid'] = True
            
            if not validation['valid']:
                error_msg = f"Validation failed for {metric}: {validation['errors']}"
                results['errors'].append(error_msg)
                print(f"⚠️  {error_msg}")
                
                # Attempt fallback to previous version
                if previous.exists():
                    print(f"Attempting fallback to previous version for {metric}")
                    shutil.copy2(previous, current)
                    results['files_updated'].append(f"{current} (fallback)")
            else:
                print(f"✅ Validation passed for {metric}")
                if validation['warnings']:
                    print(f"⚠️  Warnings: {validation['warnings']}")
            
            # Generate history files
            generate_history_files(rows, fieldnames, metric, clean_dir, today)
        
        print(f'✅ Update complete for {today}')
        
        # Check if any critical errors occurred
        if results['errors']:
            raise Exception(f"Data validation errors: {'; '.join(results['errors'])}")
        
        return results
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Subprocess failed: {e.cmd[0]} returned {e.returncode}"
        if e.stderr:
            error_msg += f"\nStderr: {e.stderr}"
        results['errors'].append(error_msg)
        raise Exception(error_msg)
    
    except Exception as e:
        results['errors'].append(str(e))
        raise

def process_covid_data(rows, fieldnames):
    """Process COVID data with special logic for current snapshot."""
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
            if (e['region'] == region and national_date and 
                (national_date - e['date']).days <= 14 and e['date'] <= national_date):
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
    
    return current_rows

def process_other_metrics(rows, fieldnames):
    """Process non-COVID metrics."""
    # Use only rows from most recent date
    dates = [row['date'] for row in rows if row.get('date')]
    if not dates:
        print(f'No date data found, skipping processing')
        return []
    
    current_date = max(dates)
    current_rows = []
    
    for row in rows:
        if (row.get('date') == current_date and 
            row.get('region') not in EXCLUDED_STATES):
            current_rows.append(row)
    
    return current_rows

def generate_history_files(rows, fieldnames, metric, clean_dir, current_date):
    """Generate history files for national and state data."""
    # Write history: separate national and statewide older rates
    hist_nat = clean_dir / f'{metric}_history_national.csv'
    print(f'Generating national history {hist_nat}')
    with open(hist_nat, 'w', newline='', encoding='utf-8') as f_nat:
        nat_writer = csv.DictWriter(f_nat, fieldnames=fieldnames)
        nat_writer.writeheader()
        for row in rows:
            if (row.get('date') < current_date and 
                row.get('region', '').lower() == 'national'):
                nat_writer.writerow(row)
    
    hist_states = clean_dir / f'{metric}_history_states.csv'
    print(f'Generating states history {hist_states}')
    with open(hist_states, 'w', newline='', encoding='utf-8') as f_st:
        st_writer = csv.DictWriter(f_st, fieldnames=fieldnames)
        st_writer.writeheader()
        for row in rows:
            region = row.get('region', '')
            if (row.get('date') < current_date and
                region not in EXCLUDED_STATES and region.lower() != 'national'):
                st_writer.writerow(row)

def main():
    """Entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Fetch and update Walgreens Respiratory Index CSVs (Enhanced with monitoring)')
    parser.add_argument('--force', action='store_true',
                        help='Force run even if not scheduled day')
    
    args = parser.parse_args()
    
    # Override weekly schedule if --force is used
    if args.force:
        print("🔧 Force mode: Running regardless of schedule")
        # Temporarily override the scheduling check
        global should_run_today
        original_should_run = should_run_today
        should_run_today = lambda: True
        
        try:
            result = update_walgreens_data()
            print("✅ Forced update completed successfully")
            return result
        finally:
            # Restore original function
            should_run_today = original_should_run
    else:
        # Normal scheduled run
        return update_walgreens_data()

if __name__ == '__main__':
    main()