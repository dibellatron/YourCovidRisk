"""Blueprint for the airborne exposure risk calculator."""

from flask import Blueprint, jsonify, render_template, request, current_app

from calculators.exposure_calculator import calculate_unified_transmission_exposure
from calculators.immunity_decay import calculate_immunity_factor_comparison, extract_immunity_timeline, extract_immunocompromised_status
from calculators.time_varying_prevalence import (
    calculate_daily_cumulative_risk,
    calculate_time_varying_cumulative_risk,
    calculate_time_varying_threshold,
    get_current_iso_week,
    load_cdc_prevalence_data,
)
from calculators.immunity_decay import extract_immunity_timeline
from covid_app.blueprints.testcalc import REGION_MAP, US_STATES

exposure_bp = Blueprint("exposure", __name__)


def _apply_rate_limit(f):
    """Decorator to apply rate limiting to calculator functions."""
    def wrapper(*args, **kwargs):
        if request.method == 'POST' and hasattr(current_app, 'limiter'):
            # This will raise RateLimitExceeded which gets handled by the error handler
            current_app.limiter.check()
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# Expose legacy endpoint name so templates using url_for('exposure_calculator')
@exposure_bp.route(
    "/exposure",
    methods=["GET", "POST"],
    endpoint="exposure_calculator",  # maintain backward‑compatibility
)
@_apply_rate_limit
def exposure_calculator():
    # Prepare list of (code, name) tuples for location dropdown
    states = sorted(US_STATES.items(), key=lambda x: x[1])
    # Read user-selected exposure location (optional)
    exposure_location = request.form.get("exposure_location", "")
    if request.method == "POST":
        # Extract form data for prior risk calculation
        f_e = request.form.get("f_e", "1")
        f_i = request.form.get("f_i", "1")
        omicron = request.form.get("omicron", "4.20")
        C0 = request.form.get("C0", "")
        Q0 = request.form.get("Q0", "")
        p = request.form.get("p", "")

        # Debug mode flag for development
        debug_mode = request.args.get("debug", "0") == "1"
        if debug_mode:
            print("DEBUG: POST request to exposure calculator")
            print(f"DEBUG: Form data: f_e={f_e}, f_i={f_i}, omicron={omicron}")
            print(f"DEBUG: Form data: C0={C0}, Q0={Q0}, p={p}")
            print(f"DEBUG: exposure_location='{exposure_location}'")

        # Check if advanced settings are visible/enabled
        advanced_enabled = request.form.get("advanced", "") == "true"

        # Only use custom ACH if advanced settings are enabled
        custom_ACH = request.form.get("custom_ACH", "") if advanced_enabled else ""
        ACH = custom_ACH if custom_ACH else request.form.get("ACH", "")

        # Only use custom volume if advanced settings are enabled
        custom_volume = request.form.get("room_volume", "") if advanced_enabled else ""
        environment_volume = request.form.get("environment_volume", "")

        # Volume selection logic kept unchanged
        if custom_volume:
            room_volume = custom_volume
        elif environment_volume:
            room_volume = environment_volume
        else:
            from calculators.environment_data import (
                AIRPLANE_ACH_VALUES,
                AIRPLANE_TYPE_VOLUMES,
                CAR_ACH_VALUES,
                CAR_TYPE_VOLUMES,
                ENV_VOLUMES,
            )

            ach_value = ACH
            if not ach_value:
                room_volume = "1000"
            elif ach_value in CAR_ACH_VALUES:
                room_volume = CAR_TYPE_VOLUMES.get(
                    request.form.get("car_type", ""), "3"
                )
            elif ach_value in AIRPLANE_ACH_VALUES:
                room_volume = AIRPLANE_TYPE_VOLUMES.get(
                    request.form.get("airplane_type", ""), "150"
                )
            else:
                # This fallback should rarely be used now that frontend sends paired values
                room_volume = ENV_VOLUMES.get(ach_value, "1000")
                print(f"WARNING: Using ENV_VOLUMES fallback for ACH {ach_value}, got volume {room_volume}")

        delta_t = request.form.get("delta_t", "")
        x = request.form.get("x", "")
        activity_choice = request.form.get("activity_choice", "")
        gamma = request.form.get("gamma", "")

        # Determine prevalence: advanced override, or lookup by exposure location, or fall back
        # Advanced override wins if enabled and provided
        raw_prev = request.form.get("covid_prevalence", "").strip()
        if advanced_enabled and raw_prev:
            covid_prevalence = raw_prev
        else:
            # Lookup prevalence from PMC CSV
            region = REGION_MAP.get(exposure_location.upper(), "National") if exposure_location else "National"
            if debug_mode:
                print(f"DEBUG: region determined as '{region}'")
            prev_val = None
            try:
                import csv
                import os

                root = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..")
                )
                csv_path = os.path.join(
                    root, "PMC", "Prevalence", "prevalence_current.csv"
                )
                with open(csv_path, newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    row = next(reader, None)
                    if debug_mode:
                        print(f"DEBUG: PMC row data: {row}")
                    if row and region in row:
                        val = row.get(region, "").strip()
                        if val.endswith("%"):
                            val = val[:-1]
                        prev_val = val
                        if debug_mode:
                            print(f"DEBUG: extracted prevalence value: '{val}'")
            except Exception as e:
                if debug_mode:
                    print(f"DEBUG: PMC lookup failed: {e}")
                prev_val = None
            # Fall back to national if region lookup failed
            if not prev_val and region != "National":
                try:
                    import csv
                    import os

                    root = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..", "..")
                    )
                    csv_path = os.path.join(
                        root, "PMC", "Prevalence", "prevalence_current.csv"
                    )
                    with open(csv_path, newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        row = next(reader, None)
                        if row and "National" in row:
                            val = row.get("National", "").strip()
                            if val.endswith("%"):
                                val = val[:-1]
                            prev_val = val
                except Exception:
                    prev_val = None
            # Use lookup or default to 1 if nothing found
            covid_prevalence = prev_val if prev_val else "1"
            if debug_mode:
                print(f"DEBUG: final covid_prevalence = '{covid_prevalence}'")
        
        # Recalculate immune value based on current form data including immunocompromised status
        vaccination_months_ago, infection_months_ago = extract_immunity_timeline(request.form)
        
        # Extract immunocompromised status properly considering progressive disclosure
        immunocompromised = request.form.get("immunocompromised", "")
        immunocompromised_severity = request.form.get("immunocompromised_severity", "")
        immunocompromised_reconsider = request.form.get("immunocompromised_reconsider", "")
        
        # Determine immunocompromised boolean status
        is_immunocompromised = False
        if immunocompromised == "Yes":
            is_immunocompromised = True
        elif immunocompromised == "unsure" and immunocompromised_reconsider == "Yes":
            is_immunocompromised = True
        
        if debug_mode:
            print(f"DEBUG: Immunocompromised extraction - main: {immunocompromised}, severity: {immunocompromised_severity}, reconsider: {immunocompromised_reconsider}, final: {is_immunocompromised}")
        
        # Import the function to calculate immunity with immunocompromised status
        from calculators.immunity_decay import calculate_immunity_factor_with_status
        
        # Calculate the actual immune value considering immunocompromised status
        recalculated_immune_val = calculate_immunity_factor_with_status(
            vaccination_months_ago, 
            infection_months_ago,
            is_immunocompromised=is_immunocompromised,
            days_from_now=0
        )
        
        # Use the recalculated value instead of the form value
        immune = str(recalculated_immune_val)
        
        if debug_mode:
            print(f"DEBUG: Original immune from form: {request.form.get('immune', '1')}")
            print(f"DEBUG: Recalculated immune value: {immune} (immunocompromised: {is_immunocompromised})")
        
        N = request.form.get("N", "1")

        # Masking fraction
        percentage_masked = request.form.get("percentage_masked", "0")
        masked_percentage_value = request.form.get("masked_percentage_value", "0")

        # Relative Humidity (optional, override, percent 0–100)
        raw_rh = request.form.get("relative_humidity", "") if advanced_enabled else ""
        try:
            # convert percent to fraction [0..1]
            rh = float(raw_rh) / 100.0 if raw_rh != "" else 0.40
        except ValueError:
            rh = 0.40
        # CO₂ concentration (ppm) (optional override)
        raw_co2 = request.form.get("co2", "") if advanced_enabled else ""
        try:
            co2 = float(raw_co2) if raw_co2 != "" else 800.0
        except ValueError:
            co2 = 800.0
        # Temperature (optional, °C or °F)
        raw_temp = request.form.get("temperature", "") if advanced_enabled else ""
        unit_temp = (
            request.form.get("temperature_unit", "C") if advanced_enabled else "C"
        )
        try:
            temp_val = float(raw_temp) if raw_temp != "" else 20.0
        except ValueError:
            temp_val = 20.0
        # Convert Fahrenheit to Celsius if needed
        if unit_temp.upper() == "F":
            temp_c = (temp_val - 32.0) * 5.0 / 9.0
        else:
            temp_c = temp_val
        # Convert Celsius to Kelvin for model
        temp_k = temp_c + 273.15

        # Extract separated activities from frontend UI
        # Map frontend slider indices to Henriques activity categories
        activity_level_index = int(request.form.get("activity_level_index", "1"))  # User's physical activity
        physical_intensity_index = int(request.form.get("physical_intensity_index", "1"))  # Others' physical activity
        vocalization_index = int(request.form.get("vocalization_index", "1"))  # Others' vocal activity
        
        # Map indices to Henriques activity names
        user_activity_map = ["sitting", "standing", "light", "moderate", "heavy"]
        others_activity_map = ["sitting", "standing", "light", "moderate", "heavy"]
        vocal_activity_map = ["breathing", "speaking", "loudly_speaking"]
        
        user_physical_activity = user_activity_map[min(activity_level_index, 4)]
        others_physical_activity = others_activity_map[min(physical_intensity_index, 4)]
        others_vocal_activity = vocal_activity_map[min(vocalization_index, 2)]
        
        # Debug the extracted activity values
        if debug_mode:
            print(f"DEBUG: Extracted activities - user_physical: {user_physical_activity}")
            print(f"DEBUG: Extracted activities - others_physical: {others_physical_activity}")
            print(f"DEBUG: Extracted activities - others_vocal: {others_vocal_activity}")

        # Extract immunocompromised status
        immunocompromised = request.form.get("immunocompromised", "")
        immunocompromised_severity = request.form.get("immunocompromised_severity", "")
        immunocompromised_reconsider = request.form.get("immunocompromised_reconsider", "")
        
        if debug_mode:
            print(f"DEBUG: Immunocompromised: {immunocompromised}, Severity: {immunocompromised_severity}, Reconsider: {immunocompromised_reconsider}")

        # Progressive disclosure logic: handle reconsideration first
        if immunocompromised == "unsure" and immunocompromised_reconsider:
            if immunocompromised_reconsider == "Yes":
                # User realized they are immunocompromised after seeing examples
                immunocompromised = "Yes"
                # Set default severity to moderate if not specified
                if not immunocompromised_severity:
                    immunocompromised_severity = "moderate"
                if debug_mode:
                    print(f"DEBUG: Progressive disclosure resolved to Yes, using severity: {immunocompromised_severity}")
            elif immunocompromised_reconsider == "No":
                # User realized they are not immunocompromised after seeing examples
                immunocompromised = "No"
                immunocompromised_severity = ""
                if debug_mode:
                    print("DEBUG: Progressive disclosure resolved to No")
            elif immunocompromised_reconsider == "still_unsure":
                # User is still unsure after seeing examples - proceed with dual calculation
                if debug_mode:
                    print("DEBUG: Progressive disclosure - user still unsure, proceeding with dual calculation")

        # Handle different immunocompromised scenarios
        if immunocompromised == "unsure":
            # Special case: Calculate both normal and moderate in parallel, then average
            if debug_mode:
                print("DEBUG: Calculating weighted average for 'unsure' status (parallel execution)")
            
            import concurrent.futures
            import functools
            import time
            
            start_time = time.time() if debug_mode else None
            
            # Create partial function with common parameters
            calc_func = functools.partial(
                calculate_unified_transmission_exposure,
                C0, Q0, p, ACH, room_volume, delta_t, x, gamma, f_e, f_i, omicron,
                covid_prevalence, immune, N, activity_choice, percentage_masked,
                user_physical_activity, others_physical_activity, others_vocal_activity,
                rh, co2, temp_k
            )
            
            # Run both calculations in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both calculations
                future_normal = executor.submit(calc_func, "normal")
                future_moderate = executor.submit(calc_func, "moderate")
                
                # Wait for both to complete
                result_normal = future_normal.result()
                result_moderate = future_moderate.result()
            
            if debug_mode:
                elapsed_time = time.time() - start_time
                print(f"DEBUG: Parallel calculations completed in {elapsed_time:.3f} seconds")
            
            # Create averaged result
            result = result_normal.copy()  # Start with normal structure
            
            # Average the key risk metrics
            result["risk"] = (result_normal["risk"] + result_moderate["risk"]) / 2
            result["old_risk"] = (result_normal["old_risk"] + result_moderate["old_risk"]) / 2
            result["new_risk"] = (result_normal["new_risk"] + result_moderate["new_risk"]) / 2
            result["mc_mean"] = (result_normal["mc_mean"] + result_moderate["mc_mean"]) / 2
            
            # Average confidence intervals
            result["mc_ci_5"] = (result_normal["mc_ci_5"] + result_moderate["mc_ci_5"]) / 2
            result["mc_ci_95"] = (result_normal["mc_ci_95"] + result_moderate["mc_ci_95"]) / 2
            result["mc_ci_25"] = (result_normal["mc_ci_25"] + result_moderate["mc_ci_25"]) / 2
            result["mc_ci_75"] = (result_normal["mc_ci_75"] + result_moderate["mc_ci_75"]) / 2
            result["mc_ci_0_5"] = (result_normal["mc_ci_0_5"] + result_moderate["mc_ci_0_5"]) / 2
            result["mc_ci_99_5"] = (result_normal["mc_ci_99_5"] + result_moderate["mc_ci_99_5"]) / 2
            result["mc_median"] = (result_normal["mc_median"] + result_moderate["mc_median"]) / 2
            
            if debug_mode:
                print(f"DEBUG: Normal risk: {result_normal['mc_mean']:.6f}, Moderate risk: {result_moderate['mc_mean']:.6f}")
                print(f"DEBUG: Averaged risk: {result['mc_mean']:.6f}")
                
        elif immunocompromised == "Yes" and immunocompromised_severity == "unsure":
            # Special case: Calculate both moderate and severe in parallel, then average
            if debug_mode:
                print("DEBUG: Calculating weighted average for severity 'unsure' status (parallel execution)")
            
            import concurrent.futures
            import functools
            import time
            
            start_time = time.time() if debug_mode else None
            
            # Create partial function with common parameters
            calc_func = functools.partial(
                calculate_unified_transmission_exposure,
                C0, Q0, p, ACH, room_volume, delta_t, x, gamma, f_e, f_i, omicron,
                covid_prevalence, immune, N, activity_choice, percentage_masked,
                user_physical_activity, others_physical_activity, others_vocal_activity,
                rh, co2, temp_k
            )
            
            # Run both calculations in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both calculations
                future_moderate = executor.submit(calc_func, "moderate")
                future_severe = executor.submit(calc_func, "severe")
                
                # Wait for both to complete
                result_moderate = future_moderate.result()
                result_severe = future_severe.result()
            
            if debug_mode:
                elapsed_time = time.time() - start_time
                print(f"DEBUG: Parallel calculations completed in {elapsed_time:.3f} seconds")
            
            # Create averaged result
            result = result_moderate.copy()  # Start with moderate structure
            
            # Average the key risk metrics
            result["risk"] = (result_moderate["risk"] + result_severe["risk"]) / 2
            result["old_risk"] = (result_moderate["old_risk"] + result_severe["old_risk"]) / 2
            result["new_risk"] = (result_moderate["new_risk"] + result_severe["new_risk"]) / 2
            result["mc_mean"] = (result_moderate["mc_mean"] + result_severe["mc_mean"]) / 2
            
            # Average confidence intervals
            result["mc_ci_5"] = (result_moderate["mc_ci_5"] + result_severe["mc_ci_5"]) / 2
            result["mc_ci_95"] = (result_moderate["mc_ci_95"] + result_severe["mc_ci_95"]) / 2
            result["mc_ci_25"] = (result_moderate["mc_ci_25"] + result_severe["mc_ci_25"]) / 2
            result["mc_ci_75"] = (result_moderate["mc_ci_75"] + result_severe["mc_ci_75"]) / 2
            result["mc_ci_0_5"] = (result_moderate["mc_ci_0_5"] + result_severe["mc_ci_0_5"]) / 2
            result["mc_ci_99_5"] = (result_moderate["mc_ci_99_5"] + result_severe["mc_ci_99_5"]) / 2
            result["mc_median"] = (result_moderate["mc_median"] + result_severe["mc_median"]) / 2
            
            if debug_mode:
                print(f"DEBUG: Moderate risk: {result_moderate['mc_mean']:.6f}, Severe risk: {result_severe['mc_mean']:.6f}")
                print(f"DEBUG: Averaged risk: {result['mc_mean']:.6f}")
                
        else:
            # Standard single calculation
            if immunocompromised == "Yes" and immunocompromised_severity in ["moderate", "severe"]:
                immunocompromised_status = immunocompromised_severity
            else:
                immunocompromised_status = "normal"
            
            if debug_mode:
                print(f"DEBUG: Using single calculation with status: {immunocompromised_status}")

            # Compute risk with single status
            result = calculate_unified_transmission_exposure(
                C0, Q0, p, ACH, room_volume, delta_t, x, gamma, f_e, f_i, omicron,
                covid_prevalence, immune, N, activity_choice, percentage_masked,
                user_physical_activity, others_physical_activity, others_vocal_activity,
                rh, co2, temp_k, immunocompromised_status
            )

        # Calculate immunity factor comparison for display
        try:
            vaccination_months_ago, infection_months_ago = extract_immunity_timeline(request.form)
            is_immunocompromised = extract_immunocompromised_status(request.form)
            immunity_comparison = calculate_immunity_factor_comparison(
                vaccination_months_ago, infection_months_ago, days_from_now=0, 
                is_immunocompromised=is_immunocompromised
            )
            
            # Add immunity comparison data to result
            result['immunity_comparison'] = immunity_comparison
            
            # Also add the actual recalculated immune value for display
            result['recalculated_immune_val'] = float(immune)
            
            # Calculate what the risk would be with old immune_val
            if immunity_comparison['old_immune_val'] != immunity_comparison['new_immune_val']:
                # Calculate old risk by scaling
                old_risk_multiplier = immunity_comparison['old_immune_val'] / immunity_comparison['new_immune_val']
                result['risk_with_old_immune_val'] = result['risk'] * old_risk_multiplier
            else:
                result['risk_with_old_immune_val'] = result['risk']
                
        except Exception as e:
            print(f"DEBUG: Error calculating immunity comparison: {e}")
            result['immunity_comparison'] = None
            result['risk_with_old_immune_val'] = result['risk']

        # Uncertainty data debugging (remove after testing)
        # print(f"DEBUG UNCERTAINTY: risk_distribution_data present: {result.get('risk_distribution_data') is not None}")

        # Additional debug output
        if debug_mode:
            print(f"DEBUG: Calculation result: risk={result.get('risk')}")
            print(f"DEBUG: Percent value: {result.get('risk', 0) * 100}%")
            print(f"DEBUG: Full result object: {result}")
            if result.get('immunity_comparison'):
                print(f"DEBUG: Immunity comparison: {result['immunity_comparison']}")

        return render_template(
            "exposure_calculator.html",
            result=result,
            percentage_masked=percentage_masked,
            masked_percentage_value=masked_percentage_value,
            # expose location dropdown data
            states=states,
            exposure_location=exposure_location,
        )

    # GET request – blank form
    return render_template(
        "exposure_calculator.html",
        states=sorted(US_STATES.items(), key=lambda x: x[1]),
        exposure_location="",
    )


@exposure_bp.route("/api/time-varying-risk", methods=["POST"])
@_apply_rate_limit
def calculate_time_varying_risk():
    """API endpoint for time-varying prevalence risk calculations."""
    try:
        data = request.get_json()
        print(f"DEBUG API: Received request data: {data}")

        # Extract parameters
        base_risk = float(data.get("base_risk", 0))
        base_prevalence = float(data.get("base_prevalence", 0.01))
        num_exposures = int(data.get("num_exposures", 1))
        region = data.get("region", "National")
        start_week = data.get("start_week", 22)  # Default to week 22
        
        print(f"DEBUG API: Parsed - base_risk={base_risk}, base_prevalence={base_prevalence}, num_exposures={num_exposures}, region={region}")
        
        # Extract calculation parameters for proper recalculation
        calc_params = data.get("calculation_params")
        
        # Extract immunity timeline parameters from calculation_params
        vaccination_months_ago = None
        infection_months_ago = None
        advanced_params = {}

        if calc_params:
            # Extract immunity timeline
            vaccination_months_ago, infection_months_ago = extract_immunity_timeline(calc_params)

            # Extract advanced environmental parameters
            advanced_params = {
                'RH': calc_params.get('RH', 0.40),
                'CO2': calc_params.get('CO2', 800.0),
                'inside_temp': calc_params.get('inside_temp', 293.15),
                'immunocompromised_status': calc_params.get('immunocompromised_status', 'normal'),
                'ACH': calc_params.get('ACH'),
                'room_volume': calc_params.get('room_volume'),
                'covid_prevalence': calc_params.get('covid_prevalence'),
                'user_physical_activity': calc_params.get('user_physical_activity', 'standing'),
                'others_physical_activity': calc_params.get('others_physical_activity', 'standing'),
                'others_vocal_activity': calc_params.get('others_vocal_activity', 'speaking'),
                'percentage_masked': calc_params.get('percentage_masked', 0.0),
                'f_e': calc_params.get('f_e', 1.0),
                'f_i': calc_params.get('f_i', 1.0),
                'C0': calc_params.get('C0', '0.065'),
                'Q0': calc_params.get('Q0', '0.08'),
                'p': calc_params.get('p', '0.08'),
                'delta_t': calc_params.get('delta_t', '42'),
                'x': calc_params.get('x', '0.7'),
                'gamma': calc_params.get('gamma', '0.7'),
                'omicron': calc_params.get('omicron', '3.3'),
                'immune': calc_params.get('immune', '1'),
                'N': calc_params.get('N', '1')
            }

            # Override base parameters if advanced params provided
            if advanced_params['covid_prevalence']:
                # Override base prevalence if advanced override provided
                try:
                    # Handle prevalence as either percentage string or decimal
                    prev_str = str(advanced_params['covid_prevalence']).strip()
                    if prev_str.endswith('%'):
                        prev_str = prev_str[:-1]
                    base_prevalence = float(prev_str) / 100.0
                except (ValueError, TypeError):
                    pass  # Keep original base_prevalence
        
        # Determine exposure pattern based on number of exposures
        if num_exposures == 12:
            exposure_pattern = 'monthly'
        elif num_exposures == 52:
            exposure_pattern = 'weekly'
        elif num_exposures == 250:
            exposure_pattern = 'workday'
        else:
            exposure_pattern = 'daily'

        # Calculate time-varying cumulative risk (daily exposures if requested)
        if data.get("daily"):
            time_varying_risk = calculate_daily_cumulative_risk(
                base_risk, base_prevalence, num_exposures, region, start_week, calc_params, 
                exposure_pattern, vaccination_months_ago, infection_months_ago, advanced_params
            )
        else:
            time_varying_risk = calculate_time_varying_cumulative_risk(
                base_risk, base_prevalence, num_exposures, region, start_week
            )

        # Also calculate the threshold (now with immunity decay and advanced params)
        threshold = calculate_time_varying_threshold(
            base_risk, base_prevalence, region, start_week, 730,
            vaccination_months_ago, infection_months_ago, advanced_params
        )

        # If daily mode, include per-day prevalence and cumulative risk sequence
        daily_sequence = None
        if data.get("daily"):
            # Load CDC weekly data for subsequent weeks  
            from calculators.time_varying_prevalence import recalculate_risk_with_prevalence
            cdc_weekly = load_cdc_prevalence_data()
            
            # For the first week, use the actual base prevalence from the calculation
            # (this could be PMC data, user-entered, or any other source)
            current_prevalence = base_prevalence
            
            cumulative_safe = 1.0
            seq = []
            for day in range(num_exposures):
                # Calculate which week this exposure uses based on pattern
                if exposure_pattern == 'weekly':
                    # Each exposure uses next week's prevalence
                    week_offset = day
                elif exposure_pattern == 'monthly':
                    # Each exposure uses prevalence ~4.25 weeks apart
                    week_offset = int(day * 4.25)
                elif exposure_pattern == 'workday':
                    # Every 5 days (workdays) uses next work week's prevalence, skipping weeks 51-52
                    work_week = day // 5
                    week_offset = work_week
                    # Add extra offset for each time we skip weeks 51-52
                    if work_week >= 29:  # Week 22 + 29 = 51, so we start skipping here
                        week_offset += 2  # Skip weeks 51 and 52
                else:
                    # Daily pattern: group days into weeks
                    week_offset = day // 7
                
                if day == 0:
                    # First exposure always uses the base prevalence from calculation
                    week_prev = current_prevalence
                else:
                    # Subsequent exposures: use CDC weekly data
                    wk = ((start_week - 1 + week_offset) % 52) + 1
                    week_prev = cdc_weekly.get(wk, {}).get(region,
                              cdc_weekly.get(wk, {}).get('National', base_prevalence))
                
                # Calculate daily risk using scaling (fast)
                if day == 0:
                    # First exposure: use the original calculation
                    d_risk = base_risk
                else:
                    # Subsequent exposures: use scaling for speed
                    if base_prevalence > 0:
                        d_risk = base_risk * week_prev / base_prevalence
                    else:
                        d_risk = base_risk
                
                d_risk = max(0.0, min(1.0, d_risk))
                cumulative_safe *= (1.0 - d_risk)
                seq.append({
                    "day": day + 1,
                    "prevalence": week_prev,
                    "daily_risk": d_risk,
                    "cumulative_risk": 1.0 - cumulative_safe,
                })
            daily_sequence = seq

        print(f"DEBUG API: Returning time_varying_risk={time_varying_risk}, threshold={threshold}")
        
        return jsonify(
            {
                "time_varying_risk": time_varying_risk,
                "threshold": threshold,
                "current_week": 22,
                "daily_sequence": daily_sequence,
            }
        )

    except (ValueError, KeyError, TypeError) as e:
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "request_data": locals().get('data', 'Could not parse request data')
        }
        print(f"API Error: {error_details}")  # Debug logging
        return jsonify({"error": str(e)}), 400
