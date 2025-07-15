#!/usr/bin/env python3
"""
pipeline_walgreens.py

Automate fetching of Walgreens Respiratory Index time-series data for COVID-19 and Influenza A/B.
Uses extracted Power BI query templates from har_extracted/requests.
"""
import os
import sys
import json
import copy
import argparse
import requests

# US state codes to state names
US_STATES = {
    'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado',
    'CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho',
    'IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana',
    'ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi',
    'MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey',
    'NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma',
    'OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee',
    'TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia',
    'WI':'Wisconsin','WY':'Wyoming'
}

def get_resource_key(har_file):
    """Extract X-PowerBI-ResourceKey header from HAR."""
    with open(har_file, 'r', encoding='utf-8') as f:
        har = json.load(f)
    for e in har.get('log', {}).get('entries', []):
        url = e.get('request', {}).get('url', '')
        if 'querydata' in url:
            for h in e.get('request', {}).get('headers', []):
                if h.get('name', '').lower() == 'x-powerbi-resourcekey':
                    return h.get('value')
    return None

def load_template(path):
    return json.load(open(path, 'r', encoding='utf-8'))

def build_payload(template, region, alias='t'):
    """
    Return a deep copy of 'template' with an optional state filter inserted.
    'alias' is the SourceRef alias used in the template (e.g. 't' or 'f').
    """
    p = copy.deepcopy(template)
    cmds = p['queries'][0]['Query']['Commands']
    for cmd in cmds:
        sq = cmd.get('SemanticQueryDataShapeCommand')
        if not sq:
            continue
        where = sq['Query']['Where']
        if region and region.lower() != 'national':
            state_name = US_STATES.get(region.upper())
            if not state_name:
                raise ValueError(f'Unknown state code: {region}')
            clause = {
                "Condition": {"In": {
                    "Expressions": [{"Column":{
                        "Expression": {"SourceRef": {"Source": alias}},
                        "Property": "State"
                    }}],
                    "Values": [[{"Literal": {"Value": f"'{state_name}'"}}]]
                }}
            }
            where.append(clause)
        return p
    raise RuntimeError('No SemanticQueryDataShapeCommand found in template')


def post_and_save(payload, url, headers, out_file):
    """POST the payload and save JSON response to file."""
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Fetch Walgreens Respiratory Index time-series')
    parser.add_argument('har_file', help='Path to walgreens.har')
    # Default to the templates folder alongside this script
    default_tpl = os.path.join(os.path.dirname(__file__), 'templates')
    parser.add_argument('--template-dir', default=default_tpl,
                        help='Directory containing JSON templates (covid_template.json, fluA_template.json, fluB_template.json)')
    parser.add_argument('--out-dir', default='walgreens_data',
                        help='Output directory for fetched JSON')
    args = parser.parse_args()
    # Headers setup
    resource_key = get_resource_key(args.har_file)
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://app.powerbi.com',
        'Referer': 'https://app.powerbi.com/',
        'User-Agent': f'python-requests/{requests.__version__}'
    }
    if resource_key:
        headers['X-PowerBI-ResourceKey'] = resource_key
    # Endpoint
    url = 'https://wabi-us-north-central-api.analysis.windows.net/public/reports/querydata?synchronous=true'
    # Prepare regions: national + all US states
    regions = ['national'] + sorted(US_STATES.keys())
    # Fetch all metrics: covid, fluA, fluB
    metrics_templates = {
        'covid': 'covid_template.json',
        'fluA': 'fluA_template.json',
        'fluB': 'fluB_template.json',
    }
    for metric, template_name in metrics_templates.items():
        tpl_path = os.path.join(args.template_dir, template_name)
        tpl = load_template(tpl_path)
        metric_out_dir = os.path.join(args.out_dir, metric)
        os.makedirs(metric_out_dir, exist_ok=True)
        for region in regions:
            payload = build_payload(tpl, region)
            outfile = os.path.join(metric_out_dir, f'{region}.json')
            print(f'Fetching {metric} data for {region} -> {outfile}')
            post_and_save(payload, url, headers, outfile)

if __name__ == '__main__':
    main()