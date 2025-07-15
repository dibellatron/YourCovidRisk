#!/usr/bin/env python3
"""
pull_prevalence_monitored.py

Enhanced version of pull_prevalence.py with:
- Tesseract OCR for image analysis
- Weekly scheduling (Tuesdays only, plus exception for Sunday June 8, 2025)
- Email notifications on failure
- Duration monitoring
- Data validation and fallback
- Comprehensive error handling
"""

import sys
import datetime
import os
import re
import csv
import glob
import json
import requests
import numpy as np
from datetime import datetime as _dt, timezone
from urllib.parse import urljoin
import pytesseract
from PIL import Image
from pathlib import Path

# Add shared utilities to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from job_utils import monitored_job, DataValidator

# --- Config ---
BASE_PAGE   = "https://pmc19.com/data/"
IMAGES_DIR  = "Images"
PREV_DIR    = "Prevalence"
HEADERS     = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.2 Safari/605.1.15"
    ),
    "Referer": BASE_PAGE
}

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
        print("⏭️  Skipping PMC update - not scheduled for today (Tuesdays only)")
        return False
    
    return True

@monitored_job(
    job_name="pmc_prevalence_update",
    weekly_schedule=False,  # We handle scheduling manually
    max_duration_minutes=10,
    email_recipient=os.getenv('NOTIFICATION_EMAIL')
)
def pull_prevalence_data():
    """Main function to pull PMC prevalence data with monitoring and validation."""
    
    # Check if we should run today
    if not should_run_today():
        return {"status": "skipped", "reason": "not_scheduled"}
    
    # Set up paths
    script_dir = Path(__file__).parent
    images_dir = script_dir / IMAGES_DIR
    prev_dir = script_dir / PREV_DIR
    
    # Ensure directories exist
    images_dir.mkdir(exist_ok=True)
    prev_dir.mkdir(exist_ok=True)
    
    results = {
        'images_downloaded': [],
        'prevalence_data': {},
        'files_created': [],
        'validation_results': {},
        'errors': []
    }
    
    try:
        # 1) Scrape & download images
        print("🔍 Fetching PNG links from PMC website...")
        links = fetch_png_links(BASE_PAGE)
        
        print(f"📥 Downloading _06.png images...")
        downloaded = download_06_images(links, images_dir)
        results['images_downloaded'] = downloaded
        
        if not downloaded:
            raise Exception("No `_06.png` images found on PMC website")
        
        # 2) Pick latest & parse date
        latest = most_recent_image(images_dir)
        date_label = parse_date_from_filename(latest)
        print(f"📊 Analyzing {os.path.basename(latest)} (date={date_label})")
        
        # 3) Use Tesseract OCR for image analysis
        print("🔍 Analyzing image with Tesseract OCR...")
        prevalence_data = analyze_with_tesseract(latest)
        results['prevalence_data'] = prevalence_data
        
        # Validate prevalence data
        validation = validate_prevalence_data(prevalence_data)
        results['validation_results']['prevalence'] = validation
        
        if not validation['valid']:
            error_msg = f"Prevalence data validation failed: {validation['errors']}"
            results['errors'].append(error_msg)
            
            # Attempt fallback to previous data
            prev_current = prev_dir / "prevalence_current.csv"
            if prev_current.exists():
                print("⚠️  Using fallback to previous prevalence data")
                # Don't overwrite current file, just log the issue
                raise Exception(error_msg + " (fallback preserved previous data)")
            else:
                raise Exception(error_msg + " (no fallback available)")
        
        # 4) Write out CSVs
        print("💾 Writing CSV files...")
        csv_files = write_csv(date_label, prevalence_data, prev_dir)
        results['files_created'].extend(csv_files)
        
        # Validate written CSV files
        for csv_file in csv_files:
            csv_validation = DataValidator.validate_csv_file(
                str(csv_file),
                required_columns=['Date', 'National'],
                min_rows=1,
                max_change_percent=200.0  # Allow large changes for prevalence data
            )
            results['validation_results'][csv_file.name] = csv_validation
            
            if not csv_validation['valid']:
                error_msg = f"CSV validation failed for {csv_file}: {csv_validation['errors']}"
                results['errors'].append(error_msg)
        
        # 5) Generate prevalence distributions
        print("📈 Generating prevalence distributions...")
        try:
            generate_prevalence_distributions(prevalence_data, date_label, script_dir)
            results['files_created'].append("PrecomputedDistributions/*.json")
        except Exception as e:
            # Distribution generation is optional, don't fail the whole job
            warning_msg = f"Distribution generation failed: {e}"
            results['errors'].append(warning_msg)
            print(f"⚠️  {warning_msg}")
        
        print("✅ PMC prevalence update completed successfully")
        
        # Check if any critical errors occurred
        critical_errors = [e for e in results['errors'] if 'validation failed' in e.lower()]
        if critical_errors:
            raise Exception(f"Critical validation errors: {'; '.join(critical_errors)}")
        
        return results
        
    except Exception as e:
        results['errors'].append(str(e))
        raise

def fetch_png_links(page_url):
    """Fetch PNG links from PMC website."""
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        html = r.text
        raw = re.findall(r'(?:href|src)="([^"]+?\.png)"', html, flags=re.IGNORECASE)
        return sorted({ urljoin(page_url, link) for link in raw })
    except Exception as e:
        raise Exception(f"Failed to fetch PNG links: {e}")

def download_06_images(links, images_dir):
    """Download images ending with _06.png."""
    downloaded = []
    for url in links:
        if url.lower().endswith("_06.png"):
            fn = os.path.basename(url)
            dest = images_dir / fn
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    f.write(resp.content)
                print(f"✔ Downloaded {fn}")
                downloaded.append(str(dest))
            except Exception as e:
                print(f"✗ Failed to download {fn}: {e}")
    return downloaded

def most_recent_image(folder):
    """Find the most recently created PNG image."""
    pngs = glob.glob(os.path.join(folder, "*.png"))
    if not pngs:
        raise Exception(f"No PNGs found in {folder}")
    return max(pngs, key=os.path.getctime)

def parse_date_from_filename(path):
    """Return YYYY-MM-DD extracted from pmc_MonthDayYear_06.png"""
    fname = os.path.basename(path)
    m = re.match(r"pmc_([A-Za-z]+)(\d{1,2})(\d{4})_06\.png", fname)
    if not m:
        raise ValueError(f"Unrecognized filename format: {fname}")
    month_name, day, year = m.groups()
    dt = _dt.strptime(f"{month_name} {day} {year}", "%B %d %Y")
    return dt.strftime("%Y-%m-%d")

def analyze_with_tesseract(image_path):
    """Extract PMC prevalence data using Tesseract OCR."""
    try:
        # Open and process the image
        img = Image.open(image_path)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(img, config='--psm 6')
        
        print(f"🔍 OCR extracted text preview:")
        print("=" * 50)
        print(text[:500] + "..." if len(text) > 500 else text)
        print("=" * 50)
        
        # Parse the PMC Model data from the table
        results = parse_pmc_data(text)
        
        return results
        
    except Exception as e:
        raise Exception(f"Tesseract analysis failed: {e}")

def parse_pmc_data(text):
    """Parse PMC prevalence data from OCR text."""
    results = {}
    
    # Define the regions we're looking for
    regions = ["National", "Northeast", "Midwest", "South", "West"]
    
    # Split text into lines for easier processing
    lines = text.split('\n')
    
    # Look for patterns like:
    # "National 0.5% (1 in 197)"
    # "Northeast 0.4% (1 in 271)"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try multiple regex patterns to catch variations in OCR output
        patterns = [
            # Standard format: "National 0.5% (1 in 197)"
            r'(National|Northeast|Midwest|South|West)\s+(\d+\.\d+)%',
            # With extra spaces: "National  0.5 %"
            r'(National|Northeast|Midwest|South|West)\s+(\d+\.\d+)\s*%',
            # OCR might misread characters: "Nationa| 0.5%"
            r'(Nationa[l|]|Northeast|Midwest|South|West)\s+(\d+\.\d+)%',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                region_raw = match.group(1)
                percentage = match.group(2)
                
                # Normalize region name (handle OCR errors)
                region = normalize_region_name(region_raw)
                
                if region in regions:
                    results[region] = f"{percentage}%"
                    print(f"✔ Found {region}: {percentage}%")
                    break
    
    # Validate we found all required regions
    missing = set(regions) - set(results.keys())
    if missing:
        print(f"WARNING: Missing regions from OCR: {missing}")
        
        # Try alternative parsing approaches
        results.update(fallback_parsing(text, missing))
    
    # Final validation
    if len(results) < 3:  # We need at least 3 regions to be useful
        raise Exception(f"Could not extract sufficient data from OCR. Found only: {results}")
    
    return results

def normalize_region_name(raw_name):
    """Normalize region names that might have OCR errors."""
    raw_lower = raw_name.lower()
    
    if 'nation' in raw_lower:
        return 'National'
    elif 'northeast' in raw_lower or 'north' in raw_lower:
        return 'Northeast'
    elif 'midwest' in raw_lower or 'mid' in raw_lower:
        return 'Midwest'
    elif 'south' in raw_lower:
        return 'South'
    elif 'west' in raw_lower:
        return 'West'
    else:
        return raw_name  # Return as-is if no match

def fallback_parsing(text, missing_regions):
    """Fallback parsing for regions not found in standard parsing."""
    results = {}
    
    # More aggressive pattern matching for missing regions
    for region in missing_regions:
        # Look for the region name and any nearby percentage
        region_pattern = re.compile(rf'{region[:4]}.*?(\d+\.\d+)%', re.IGNORECASE | re.DOTALL)
        match = region_pattern.search(text)
        
        if match:
            percentage = match.group(1)
            results[region] = f"{percentage}%"
            print(f"✔ Fallback found {region}: {percentage}%")
    
    return results

def validate_prevalence_data(data):
    """Validate the prevalence data extracted from the image."""
    validation = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    required_regions = ['National', 'Northeast', 'Midwest', 'South', 'West']
    
    if not isinstance(data, dict):
        validation['valid'] = False
        validation['errors'].append("Data is not a dictionary")
        return validation
    
    # Check required regions
    missing_regions = set(required_regions) - set(data.keys())
    if missing_regions:
        validation['valid'] = False
        validation['errors'].append(f"Missing regions: {missing_regions}")
    
    # Validate percentage format and ranges
    for region, value in data.items():
        if not isinstance(value, str):
            validation['errors'].append(f"{region}: value is not a string")
            continue
        
        # Check percentage format
        if not value.endswith('%'):
            validation['errors'].append(f"{region}: value '{value}' doesn't end with %")
            continue
        
        try:
            # Extract numeric value
            numeric_value = float(value.rstrip('%'))
            
            # Check reasonable range (0-10% prevalence)
            if numeric_value < 0:
                validation['errors'].append(f"{region}: negative prevalence {numeric_value}%")
            elif numeric_value > 10:
                validation['warnings'].append(f"{region}: unusually high prevalence {numeric_value}%")
            elif numeric_value > 5:
                validation['warnings'].append(f"{region}: high prevalence {numeric_value}%")
                
        except ValueError:
            validation['errors'].append(f"{region}: cannot parse numeric value from '{value}'")
    
    if validation['errors']:
        validation['valid'] = False
    
    return validation

def write_csv(date_label, data, prev_dir):
    """Write prevalence data to CSV files."""
    headers = ["Date","National","Northeast","Midwest","South","West"]
    row = [date_label] + [data.get(region, "") for region in headers[1:]]
    
    created_files = []

    # 1) prevalence_current.csv (overwrite)
    curr_path = prev_dir / "prevalence_current.csv"
    with open(curr_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)
    created_files.append(curr_path)

    # 2) prevalence_<date>.csv
    dated_path = prev_dir / f"prevalence_{date_label}.csv"
    with open(dated_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)
    created_files.append(dated_path)

    print(f"✔ Wrote current → {curr_path}")
    print(f"✔ Wrote dated   → {dated_path}")
    
    return created_files

def generate_prevalence_distributions(data, date_label, script_dir):
    """Generate and save prevalence distributions for each region."""
    # Add wastewater module to path
    wastewater_path = script_dir.parent / 'wastewater'
    sys.path.insert(0, str(wastewater_path))
    
    try:
        from estimate_prevalence import PrevalenceEstimator
    except ImportError as e:
        raise Exception(f"Could not import PrevalenceEstimator: {e}")
    
    # Directory for storing pre-computed distributions
    dist_dir = script_dir / "PrecomputedDistributions"
    dist_dir.mkdir(exist_ok=True)
    
    # Mapping from prevalence to approximate wastewater levels
    def prevalence_to_wastewater(prevalence_pct):
        """Convert prevalence percentage to approximate wastewater level."""
        if prevalence_pct <= 0:
            return 50  # Minimum detectable level
        prevalence_fraction = prevalence_pct / 100.0
        log_prevalence = np.log(prevalence_fraction)
        log10_ww = 4.211 + 0.353 * log_prevalence
        return 10 ** log10_ww
    
    # Generate distributions for each region
    estimator = PrevalenceEstimator(variant_period="omicron")
    regions = ["National", "Northeast", "Midwest", "South", "West"]
    
    for region in regions:
        prevalence_str = data.get(region, "")
        if not prevalence_str:
            continue
            
        try:
            # Parse prevalence percentage
            prevalence_pct = float(prevalence_str.strip().rstrip('%'))
            
            # Convert to wastewater level
            wastewater_level = prevalence_to_wastewater(prevalence_pct)
            
            print(f"→ Generating distribution for {region}: {prevalence_pct}% prevalence, wastewater≈{wastewater_level:.0f}")
            
            # Generate prevalence distribution
            results = estimator.estimate_prevalence(
                wastewater_level=wastewater_level,
                n_samples=20000,
                seed=42
            )
            
            # Save distribution
            output_path = dist_dir / f"{region.lower()}_distribution.json"
            estimator.save_distribution_only(
                results['samples'], 
                wastewater_level, 
                output_path
            )
            
            print(f"  ✔ Saved distribution → {output_path}")
            
        except (ValueError, KeyError) as e:
            print(f"  ✗ Error processing {region}: {e}")
    
    # Save timestamp file
    timestamp_path = dist_dir / "generation_timestamp.json"
    with open(timestamp_path, "w") as f:
        json.dump({
            "date": date_label,
            "generated_at": _dt.now(timezone.utc).isoformat(),
            "prevalence_data": data
        }, f, indent=2)

def main():
    """Entry point with argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Pull PMC prevalence data (Enhanced with monitoring)')
    parser.add_argument('--force', action='store_true',
                        help='Force run even if not scheduled day')
    
    args = parser.parse_args()
    
    if args.force:
        print("🔧 Force mode: Running regardless of schedule")
        # Temporarily override the scheduling check
        global should_run_today
        original_should_run = should_run_today
        should_run_today = lambda: True
        
        try:
            result = pull_prevalence_data()
            print("✅ Forced update completed successfully")
            return result
        finally:
            # Restore original function
            should_run_today = original_should_run
    else:
        # Normal scheduled run
        return pull_prevalence_data()

if __name__ == "__main__":
    main()