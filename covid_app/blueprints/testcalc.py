"""Blueprint housing the rapid‑test probability calculator routes."""

import csv
import os

from flask import Blueprint, render_template, request, current_app, jsonify

# Mapping of US state codes to full names for the 'Where do you live?' dropdown
US_STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
    "GU": "Guam",
}


from calculators.test_calculator import calculate_test_risk, REGION_MAP

test_bp = Blueprint("testcalc", __name__)


def get_national_positivity_rate():
    """Helper function to get the current national positivity rate from Walgreens data"""
    try:
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        csv_pos_path = os.path.join(
            root_dir, "Walgreens", "walgreens_clean", "covid_current.csv"
        )
        
        latest = None
        latest_rate = None
        with open(csv_pos_path, newline="", encoding="utf-8") as fpos:
            reader_pos = csv.DictReader(fpos)
            for prow in reader_pos:
                if prow.get("region", "").lower() == "national":
                    date = prow.get("date")
                    rate = prow.get("positivity_rate")
                    if date and rate is not None:
                        if latest is None or date > latest:
                            latest = date
                            latest_rate = rate
        
        if latest_rate is not None:
            pr_val = float(latest_rate) * 100
            return f"{pr_val:.2f}".rstrip("0").rstrip(".")
        else:
            return "15"  # Fallback to hardcoded default
    except (FileNotFoundError, KeyError, ValueError):
        return "15"  # Fallback to hardcoded default


def _apply_rate_limit(f):
    """Decorator to apply rate limiting to calculator functions."""
    def wrapper(*args, **kwargs):
        if request.method == 'POST' and hasattr(current_app, 'limiter'):
            # This will raise RateLimitExceeded which gets handled by the error handler
            current_app.limiter.check()
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@test_bp.route("/test", methods=["GET", "POST"], endpoint="test_calculator")
@_apply_rate_limit
def test_calculator():
    """Handle the test‑calculator form; logic copied unchanged from legacy app.py."""

    risk: float | None = None
    symptoms_value = ""
    tests = []
    covid_cautious = ""
    advanced_risk: tuple | None = None

    # Prepare list of (code, name) tuples for template
    states = sorted(US_STATES.items(), key=lambda x: x[1])  # sort by state name
    if request.method == "POST":
        action = request.form.get("action", "Calculate")
        _advanced_requested = action == "More info"  # kept for future use

        # Get user inputs
        symptoms_value = request.form.get("symptoms", "")
        state = request.form.get("state", "")
        # Initialize tracking variables
        used_national_positivity_fallback = False
        # Advanced form inputs
        manual_prior_input = request.form.get("priorProbability", "") or ""
        covid_prevalence_input = request.form.get("covidPrevalence", "") or ""
        positivity_rate_input = request.form.get("positivityRate", "") or ""
        # Determine prior probability input according to priority:
        # 1) Manual prior overrides everything
        # 2) If symptomatic: use positivity (advanced or lookup)
        # 3) If asymptomatic: advanced prevalence or lookup
        if manual_prior_input:
            prior_probability_input = manual_prior_input
        else:
            if symptoms_value.lower() == "yes":
                # Symptomatic branch: use advanced positivity rate or lookup
                if positivity_rate_input:
                    prior_probability_input = positivity_rate_input
                else:
                    # Lookup state/national positivity
                    root_dir = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "..")
                    )
                    csv_pos_path = os.path.join(
                        root_dir, "Walgreens", "walgreens_clean", "covid_current.csv"
                    )
                    prior_probability_input = ""
                    try:
                        latest = None
                        latest_rate = None
                        with open(csv_pos_path, newline="", encoding="utf-8") as fpos:
                            reader_pos = csv.DictReader(fpos)
                            for prow in reader_pos:
                                if prow.get("region", "").upper() == state.upper():
                                    date = prow.get("date")
                                    rate = prow.get("positivity_rate")
                                    if date and rate is not None:
                                        if latest is None or date > latest:
                                            latest = date
                                            latest_rate = rate
                        if latest_rate is None:
                            # Use national rate as fallback
                            latest_rate = float(get_national_positivity_rate()) / 100
                            used_national_positivity_fallback = True
                        
                        if latest_rate is not None:
                            pr_val = float(latest_rate) * 100
                            rate_str = f"{pr_val:.2f}".rstrip("0").rstrip(".")
                            prior_probability_input = rate_str
                            positivity_rate_input = rate_str  # Also set this for explanation text
                    except (FileNotFoundError, KeyError, ValueError):
                        # Use national rate as final fallback
                        national_rate = get_national_positivity_rate()
                        prior_probability_input = national_rate
                        positivity_rate_input = national_rate  # Also set this for explanation text
                        used_national_positivity_fallback = True
            else:
                # Asymptomatic branch: need both prevalence and positivity rate
                if not covid_prevalence_input:
                    # Look up prevalence from PMC CSV if not provided
                    root_dir = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "..")
                    )
                    csv_path = os.path.join(
                        root_dir, "PMC", "Prevalence", "prevalence_current.csv"
                    )
                    try:
                        with open(csv_path, newline="", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            row = next(reader, None)
                            region = REGION_MAP.get(state.upper(), "National")
                            if row and region in row:
                                val = row[region]
                                if val.endswith("%"):
                                    val = val[:-1]
                                rate_val = float(val)
                                covid_prevalence_input = f"{rate_val:.2f}".rstrip(
                                    "0"
                                ).rstrip(".")
                    except (FileNotFoundError, KeyError, ValueError):
                        covid_prevalence_input = ""
                
                # Also look up positivity rate for asymptomatic users (needed for corrected calculation)
                if not positivity_rate_input:
                    root_dir = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "..")
                    )
                    csv_pos_path = os.path.join(
                        root_dir, "Walgreens", "walgreens_clean", "covid_current.csv"
                    )
                    try:
                        latest = None
                        latest_rate = None
                        with open(csv_pos_path, newline="", encoding="utf-8") as fpos:
                            reader_pos = csv.DictReader(fpos)
                            for prow in reader_pos:
                                if prow.get("region", "").upper() == state.upper():
                                    date = prow.get("date")
                                    rate = prow.get("positivity_rate")
                                    if date and rate is not None:
                                        if latest is None or date > latest:
                                            latest = date
                                            latest_rate = rate
                        if latest_rate is None:
                            # Use national rate as fallback
                            latest_rate = float(get_national_positivity_rate()) / 100
                            used_national_positivity_fallback = True
                        
                        if latest_rate is not None:
                            pr_val = float(latest_rate) * 100
                            positivity_rate_input = f"{pr_val:.2f}".rstrip(
                                "0"
                            ).rstrip(".")
                    except (FileNotFoundError, KeyError, ValueError):
                        # Use national rate as final fallback
                        positivity_rate_input = get_national_positivity_rate()
                        used_national_positivity_fallback = True
                
                # Don't set prior_probability_input for asymptomatic case - let it go through normal calculation
                prior_probability_input = ""
        test_types = request.form.getlist("test_type")
        test_results = request.form.getlist("test_result")
        
        # Filter out empty test entries
        valid_tests = [(tt, tr) for tt, tr in zip(test_types, test_results) if tt and tr]
        if valid_tests:
            test_types, test_results = zip(*valid_tests)
            test_types = list(test_types)
            test_results = list(test_results)
        else:
            test_types = []
            test_results = []
        
        tests = [
            {"test_type": tt, "test_result": tr}
            for tt, tr in zip(test_types, test_results)
        ]

        # Advanced parameters
        advanced_flag = request.form.get("advanced", "")
        # Note: prior_probability_input was set based on state selection above

        # Preserve Covid exposure level text
        covid_exposure = request.form.get("covid_cautious", "")  # Keep reading from old form field for now
        covid_cautious_level = request.form.get("covid_cautious_level", "")

        # Delegate to calculation engine (pure python)
        # Check if Monte Carlo calculation was requested
        calculate_monte_carlo = request.form.get('calculate_monte_carlo') == 'true'
        
        # Track whether prevalence/positivity were looked up from data sources vs user-entered
        prevalence_from_pmc = False
        positivity_from_walgreens = False
        # used_national_positivity_fallback is already set above in the lookup logic, don't reset it
        
        # Check if we looked up prevalence from PMC for asymptomatic users
        if symptoms_value.lower() == "no" and not manual_prior_input:
            original_covid_prevalence = request.form.get("covidPrevalence", "") or ""
            if not original_covid_prevalence and covid_prevalence_input:
                prevalence_from_pmc = True
            
            # Also check if we looked up positivity rate for asymptomatic users
            original_positivity_rate = request.form.get("positivityRate", "") or ""
            if not original_positivity_rate and positivity_rate_input:
                positivity_from_walgreens = True
        
        # Check if we looked up positivity from Walgreens for symptomatic users  
        if symptoms_value.lower() == "yes" and not manual_prior_input:
            original_positivity_rate = request.form.get("positivityRate", "") or ""
            if not original_positivity_rate and prior_probability_input:
                positivity_from_walgreens = True
        
        try:
            risk_data = calculate_test_risk(
                symptoms_value,
                test_types,
                test_results,
                covid_exposure,
                covid_prevalence_input,
                positivity_rate_input,
                prior_probability_input,
                advanced_flag,
                bool(manual_prior_input),
                state,
                calculate_monte_carlo,
                prevalence_from_pmc,
                positivity_from_walgreens,
                used_national_positivity_fallback,
            )
        except ValueError as e:
            # Handle validation errors with descriptive messages
            return jsonify({"error": str(e)}), 400

        # Render with all user inputs preserved
        return render_template(
            "test_calculator.html",
            risk=risk_data.get("risk"),
            risk_old=risk_data.get("risk_old"),
            advanced_risk=risk_data.get("advanced_risk"),
            monte_carlo_risk=risk_data.get("monte_carlo_risk"),
            monte_carlo_beta_risk=risk_data.get("monte_carlo_beta_risk"),
            monte_carlo_full_risk=risk_data.get("monte_carlo_full_risk"),
            monte_carlo_prevalence_risk=risk_data.get("monte_carlo_prevalence_risk"),
            min_max_range=risk_data.get("min_max_range"),
            symptoms=risk_data.get("symptoms"),
            tests=risk_data.get("tests"),
            covid_cautious=risk_data.get("covid_exposure"),  # Pass to template with old name for compatibility
            covid_cautious_level=covid_cautious_level,
            covid_prevalence=risk_data.get("covid_prevalence"),
            positivity_rate=risk_data.get("positivity_rate"),
            prior_probability=risk_data.get("prior_probability"),
            has_confidence_intervals=risk_data.get("has_confidence_intervals"),
            calculation_details=risk_data.get(
                "calculation_details"
            ),  # Pass structured detail data
            state=state if "state" in locals() else "",
            states=states,
        )

    # GET request – render blank form (or previously posted values via Jinja)
    # Default to no state selected
    state = ""
    states = sorted(US_STATES.items(), key=lambda x: x[1])
    return render_template(
        "test_calculator.html",
        risk=risk,
        advanced_risk=advanced_risk,
        symptoms=symptoms_value,
        tests=tests,
        covid_cautious="",  # Default for GET request
        covid_prevalence="",
        positivity_rate="",
        prior_probability="",
        state=state,
        states=states,
        calculation_details=[],
    )
