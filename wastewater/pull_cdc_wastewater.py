#!/usr/bin/env python3
"""
pull_cdc_wastewater.py

Fetch CDC wastewater surveillance data and extract the most recent values
for all states, outputting in a simple state,value CSV format.
"""
import requests
import json
import csv
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

def fetch_wastewater_data():
    """Fetch the complete wastewater data from CDC."""
    url = "https://www.cdc.gov/wcms/vizdata/NCEZID_DIDRI/sc2/nwsssc2stateactivitylevel.json"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Handle UTF-8 BOM by removing it from the text
        text = response.text
        if text.startswith('\ufeff'):
            text = text[1:]
        
        return json.loads(text)
    except requests.RequestException as e:
        print(f"Error fetching wastewater data: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON data: {e}", file=sys.stderr)
        return None

def get_most_recent_data(data):
    """Extract the most recent data for each state individually."""
    
    # Group data by state and find most recent entry for each
    state_data = defaultdict(list)
    for entry in data:
        state = entry.get('State/Territory', '').strip()
        if state:
            state_data[state].append(entry)
    
    # Get most recent entry for each state individually
    most_recent = {}
    global_latest_date = None
    national_value = None
    
    for state, entries in state_data.items():
        # Sort by date to get most recent for this state
        sorted_entries = sorted(entries, key=lambda x: x.get('Week_Ending_Date', ''), reverse=True)
        if sorted_entries:
            most_recent[state] = sorted_entries[0]
            entry_date = sorted_entries[0].get('Week_Ending_Date', '')
            
            # Track the globally most recent date for getting national value
            if not global_latest_date or entry_date > global_latest_date:
                global_latest_date = entry_date
                national_value = sorted_entries[0].get('National_WVAL')
    
    return {
        'global_latest_date': global_latest_date,
        'national_value': national_value,
        'states': most_recent
    }

def write_csv_files(data):
    """Write CSV files with state,value format."""
    
    # Create wastewater folder if it doesn't exist
    os.makedirs('.', exist_ok=True)
    
    global_latest_date = data['global_latest_date']
    national_value = data['national_value']
    states = data['states']
    
    # Format date for filename (convert from YYYY-MM-DD format)
    try:
        date_obj = datetime.strptime(global_latest_date, '%Y-%m-%d')
        filename_date = date_obj.strftime('%Y-%m-%d')
    except:
        filename_date = global_latest_date.replace('/', '-')
    
    # PMC Regional Multiplier for converting WVAL to prevalence (as proportion)
    PMC_MULTIPLIER = 0.00293
    
    # Prepare CSV data
    csv_rows = []
    
    # Add national row first (use global latest date for national)
    national_prevalence = ''
    if national_value:
        try:
            national_prevalence = f"{float(national_value) * PMC_MULTIPLIER:.4f}"
        except (ValueError, TypeError):
            national_prevalence = ''
    csv_rows.append(['National', national_value if national_value else '', national_prevalence, global_latest_date])
    
    # Add all states/territories in alphabetical order, each with their own most recent date
    state_names = sorted(states.keys())
    for state in state_names:
        state_entry = states[state]
        state_val = state_entry.get('State/Territory_WVAL', '')
        state_date = state_entry.get('Week_Ending_Date', '')
        
        # Calculate prevalence using PMC multiplier
        state_prevalence = ''
        if state_val and state_val != 'No Data':
            try:
                state_prevalence = f"{float(state_val) * PMC_MULTIPLIER:.4f}"
            except (ValueError, TypeError):
                state_prevalence = ''
        
        csv_rows.append([state, state_val, state_prevalence, state_date])
    
    headers = ["State", "WVAL", "Prevalence", "Date"]
    
    # Write cdc_wastewater_current.csv (overwrite)
    current_path = "data/cdc_wastewater_current.csv"
    with open(current_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(csv_rows)
    
    # Write cdc_wastewater_<date>.csv
    dated_path = f"data/cdc_wastewater_{filename_date}.csv"
    with open(dated_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(csv_rows)
    
    print(f"✔ Wrote current → {current_path}")
    print(f"✔ Wrote dated   → {dated_path}")
    
    return current_path, dated_path

def main():
    print("Fetching CDC wastewater surveillance data...")
    
    # Fetch data
    raw_data = fetch_wastewater_data()
    if not raw_data:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)
    
    print(f"✔ Fetched {len(raw_data)} wastewater data entries")
    
    # Process data to get most recent values
    processed_data = get_most_recent_data(raw_data)
    
    print(f"\nMost Recent Wastewater Data:")
    print(f"National (from {processed_data['global_latest_date']}): {processed_data['national_value']}")
    print(f"Found data for {len(processed_data['states'])} states/territories")
    print("(Each state uses its own most recent available date)")
    
    # Write CSV files
    current_file, dated_file = write_csv_files(processed_data)
    
    # Show a few example values
    print(f"\nExample state values:")
    examples = ['Colorado', 'California', 'New York', 'Florida', 'Texas']
    for state in examples:
        if state in processed_data['states']:
            state_val = processed_data['states'][state].get('State/Territory_WVAL', 'N/A')
            print(f"  {state}: {state_val}")

if __name__ == "__main__":
    main()