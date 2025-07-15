#!/usr/bin/env python3
"""
pull_prevalence_tesseract.py

Weekly fetch of PMC prevalence data via Tesseract OCR.
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

# Only execute every 7 days (based on day-of-year parity matching start date)
# START_DAY_PARITY = day-of-year parity (0 or 1) of first run date (today)
START_DAY_PARITY = _dt.now(timezone.utc).timetuple().tm_yday % 2
# Determine UTC today and check parity
today = _dt.now(timezone.utc).date()
if today.timetuple().tm_yday % 2 != START_DAY_PARITY:
    sys.exit(0)

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

def fetch_png_links(page_url):
    r = requests.get(page_url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    html = r.text
    raw = re.findall(r'(?:href|src)="([^"]+?\.png)"', html, flags=re.IGNORECASE)
    return sorted({ urljoin(page_url, link) for link in raw })

def download_06_images(links):
    os.makedirs(IMAGES_DIR, exist_ok=True)
    downloaded = []
    for url in links:
        if url.lower().endswith("_06.png"):
            fn   = os.path.basename(url)
            dest = os.path.join(IMAGES_DIR, fn)
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                f.write(resp.content)
            print(f"✔ Downloaded {fn}")
            downloaded.append(dest)
    return downloaded

def most_recent_image(folder):
    pngs = glob.glob(os.path.join(folder, "*.png"))
    if not pngs:
        print(f"ERROR: No PNGs found in {folder}", file=sys.stderr)
        sys.exit(1)
    return max(pngs, key=os.path.getctime)

def parse_date_from_filename(path):
    """Return YYYY-MM-DD extracted from pmc_MonthDayYear_06.png"""
    fname = os.path.basename(path)
    m = re.match(r"pmc_([A-Za-z]+)(\d{1,2})(\d{4})_06\.png", fname)
    if not m:
        raise ValueError(f"Unrecognized filename: {fname}")
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
        print(f"ERROR: Tesseract analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

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
        print("ERROR: Could not extract sufficient data from OCR", file=sys.stderr)
        print(f"Found only: {results}")
        sys.exit(1)
    
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

def write_csv(date_label, data):
    os.makedirs(PREV_DIR, exist_ok=True)
    headers = ["Date","National","Northeast","Midwest","South","West"]
    row = [date_label] + [data.get(region, "") for region in headers[1:]]

    # 1) prevalence_current.csv (overwrite)
    curr_path = os.path.join(PREV_DIR, "prevalence_current.csv")
    with open(curr_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)

    # 2) prevalence_<date>.csv
    dated_path = os.path.join(PREV_DIR, f"prevalence_{date_label}.csv")
    with open(dated_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(row)

    print(f"✔ Wrote current → {curr_path}")
    print(f"✔ Wrote dated   → {dated_path}")

def generate_prevalence_distributions(data, date_label):
    """Generate and save prevalence distributions for each region."""
    # Add wastewater module to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'wastewater'))
    
    try:
        from estimate_prevalence import PrevalenceEstimator
    except ImportError as e:
        print(f"WARNING: Could not import PrevalenceEstimator: {e}")
        return
    
    # Directory for storing pre-computed distributions
    DIST_DIR = "PrecomputedDistributions"
    os.makedirs(DIST_DIR, exist_ok=True)
    
    # Mapping from prevalence to approximate wastewater levels
    # This is a simplified approximation - in production this would use actual wastewater data
    def prevalence_to_wastewater(prevalence_pct):
        """Convert prevalence percentage to approximate wastewater level."""
        # Based on calibrated model: log10(ww) ≈ 4.211 + 0.353 * log(prevalence)
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
                n_samples=20000,  # Generate more samples for better coverage
                seed=42
            )
            
            # Save distribution
            output_path = os.path.join(DIST_DIR, f"{region.lower()}_distribution.json")
            estimator.save_distribution_only(
                results['samples'], 
                wastewater_level, 
                output_path
            )
            
            print(f"  ✔ Saved distribution → {output_path}")
            
        except (ValueError, KeyError) as e:
            print(f"  ✗ Error processing {region}: {e}")
    
    # Also save a timestamp file to track when distributions were generated
    timestamp_path = os.path.join(DIST_DIR, "generation_timestamp.json")
    with open(timestamp_path, "w") as f:
        json.dump({
            "date": date_label,
            "generated_at": _dt.now(timezone.utc).isoformat(),
            "prevalence_data": data
        }, f, indent=2)

def main():
    # 1) scrape & download
    links      = fetch_png_links(BASE_PAGE)
    downloaded = download_06_images(links)
    if not downloaded:
        print("ERROR: No `_06.png` images found.", file=sys.stderr)
        sys.exit(1)

    # 2) pick latest & parse date
    latest     = most_recent_image(IMAGES_DIR)
    date_label = parse_date_from_filename(latest)
    print(f"→ Analyzing {os.path.basename(latest)} (date={date_label})")

    # 3) use Tesseract OCR for image analysis
    results = analyze_with_tesseract(latest)

    # 4) write out CSVs
    write_csv(date_label, results)
    
    # 5) generate prevalence distributions
    print("\n→ Generating prevalence distributions...")
    generate_prevalence_distributions(results, date_label)

if __name__ == "__main__":
    main()