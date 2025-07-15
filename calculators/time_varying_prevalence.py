"""
Time-varying prevalence calculations for repeated exposure risk assessment.
"""
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from calculators.immunity_decay import calculate_immunity_factor_at_time, extract_immunity_timeline


def get_current_iso_week() -> int:
    """Get the current ISO week number (1-52)."""
    return datetime.now().isocalendar()[1]


def load_cdc_prevalence_data() -> Dict[int, Dict[str, float]]:
    """
    Load CDC weekly prevalence data from CSV file.
    
    Returns:
        Dictionary mapping week number to region prevalence values
        Format: {week_num: {'National': prevalence, 'Midwest': prevalence, ...}}
    """
    # Get the path to the CSV file
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.dirname(current_dir)
    csv_path = os.path.join(root_dir, 'wastewater', 'data', 'cdc_weekly_prevalence_2023_2025.csv')
    
    prevalence_data = {}
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                week_num = int(row['ISO_Week'])
                prevalence_data[week_num] = {
                    'National': float(row['National_Prevalence']),
                    'Midwest': float(row['Midwest_Prevalence']),
                    'Northeast': float(row['Northeast_Prevalence']),
                    'South': float(row['South_Prevalence']),
                    'West': float(row['West_Prevalence'])
                }
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"Warning: Could not load CDC prevalence data: {e}")
        # Return default fallback data
        return {week: {'National': 0.01} for week in range(1, 53)}
    
    return prevalence_data


def get_weekly_prevalence_sequence(
    start_week: int, 
    num_weeks: int, 
    region: str = 'National'
) -> List[float]:
    """
    Get a sequence of weekly prevalence values starting from a given week.
    
    Args:
        start_week: Starting ISO week number (1-52)
        num_weeks: Number of weeks to project forward
        region: Region to get prevalence for ('National', 'Midwest', etc.)
        
    Returns:
        List of prevalence values (as proportions, not percentages)
    """
    prevalence_data = load_cdc_prevalence_data()
    
    # Default fallback if region not found
    if not prevalence_data or region not in next(iter(prevalence_data.values()), {}):
        print(f"Warning: Region '{region}' not found, using National data")
        region = 'National'
    
    # If National also not found, use default
    if not prevalence_data or 'National' not in next(iter(prevalence_data.values()), {}):
        return [0.01] * num_weeks  # 1% default
    
    prevalence_sequence = []
    
    for i in range(num_weeks):
        # Calculate the week number, cycling through 1-52
        week_num = ((start_week - 1 + i) % 52) + 1
        
        if week_num in prevalence_data and region in prevalence_data[week_num]:
            prevalence_sequence.append(prevalence_data[week_num][region])
        else:
            # Fallback to national average if specific week/region missing
            if week_num in prevalence_data and 'National' in prevalence_data[week_num]:
                prevalence_sequence.append(prevalence_data[week_num]['National'])
            else:
                prevalence_sequence.append(0.01)  # 1% fallback
    
    return prevalence_sequence


def calculate_time_varying_cumulative_risk(
    base_single_exposure_risk: float,
    base_prevalence: float,
    num_exposures: int,
    region: str = 'National',
    start_week: Optional[int] = None
) -> float:
    """
    Calculate cumulative risk over multiple exposures with time-varying prevalence.
    
    Args:
        base_single_exposure_risk: Single exposure risk at base prevalence
        base_prevalence: The baseline prevalence used in the original calculation (as proportion)
        num_exposures: Number of exposures to calculate cumulative risk for
        region: Geographic region for prevalence data
        start_week: Starting week (defaults to current week)
        
    Returns:
        Cumulative risk as a proportion (0-1)
    """
    if start_week is None:
        start_week = 22
    
    # Get the time-varying prevalence sequence
    prevalence_sequence = get_weekly_prevalence_sequence(start_week, num_exposures, region)
    
    # Calculate weekly risks by scaling the base risk by prevalence ratios
    cumulative_safe_prob = 1.0  # Probability of staying safe
    
    for week_prevalence in prevalence_sequence:
        # Scale the base risk by the ratio of week prevalence to base prevalence
        if base_prevalence > 0:
            prevalence_ratio = week_prevalence / base_prevalence
            weekly_risk = base_single_exposure_risk * prevalence_ratio
            # Clamp to [0, 1] range
            weekly_risk = max(0.0, min(1.0, weekly_risk))
        else:
            weekly_risk = 0.0
        
        # Update cumulative probability
        cumulative_safe_prob *= (1.0 - weekly_risk)
    
    # Convert to cumulative risk
    cumulative_risk = 1.0 - cumulative_safe_prob
    return cumulative_risk


def calculate_time_varying_threshold(
    base_single_exposure_risk: float,
    base_prevalence: float,
    region: str = 'National',
    start_week: Optional[int] = None,
    max_days: int = 730,  # 2 years max
    vaccination_months_ago: Optional[int] = None,
    infection_months_ago: Optional[int] = None,
    advanced_params: Optional[Dict] = None
) -> Optional[int]:
    """
    Calculate how many daily exposures needed to exceed 50% cumulative risk with time-varying prevalence and immunity decay.
    Uses PMC current prevalence for first week, then CDC weekly data for subsequent weeks.
    
    Args:
        base_single_exposure_risk: Single exposure risk at base prevalence
        base_prevalence: The baseline prevalence used in the original calculation
        region: Geographic region for prevalence data
        start_week: Starting week (defaults to current week)
        max_days: Maximum number of days to check
        vaccination_months_ago: Months since vaccination (None if not vaccinated in last year)
        infection_months_ago: Months since infection (None if not infected in last year)
        
    Returns:
        Number of daily exposures needed for >50% risk, or None if not reached within max_days
    """
    if start_week is None:
        start_week = 22
    
    # DEBUG: Log threshold calculation parameters
    print(f"DEBUG THRESHOLD: Calculating threshold with base_risk={base_single_exposure_risk:.6f}, base_prevalence={base_prevalence:.6f}")
    if advanced_params:
        print(f"DEBUG THRESHOLD: Advanced params present - RH={advanced_params.get('RH', 0.40)}, CO2={advanced_params.get('CO2', 800.0)}, custom_prevalence={advanced_params.get('covid_prevalence')}")
    
    # Binary search for efficiency
    low, high = 1, max_days
    result = None
    
    while low <= high:
        mid = (low + high) // 2
        risk = calculate_daily_cumulative_risk(
            base_single_exposure_risk, base_prevalence, mid, region, start_week,
            None, 'daily', vaccination_months_ago, infection_months_ago, advanced_params
        )
        
        if risk > 0.5:
            result = mid
            high = mid - 1
        else:
            low = mid + 1
    
    print(f"DEBUG THRESHOLD: Final threshold result = {result} days")
    return result


def load_pmc_current_prevalence() -> Dict[str, float]:
    """
    Load current prevalence data from PMC CSV file.
    
    Returns:
        Dictionary mapping region to current prevalence values
        Format: {'National': prevalence, 'Midwest': prevalence, ...}
    """
    # Get the path to the PMC CSV file
    current_dir = os.path.dirname(__file__)
    root_dir = os.path.dirname(current_dir)
    csv_path = os.path.join(root_dir, 'PMC', 'Prevalence', 'prevalence_current.csv')
    
    current_prevalence = {}
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader, None)  # Get the first (and only) row
            if row:
                for region, value in row.items():
                    if region != 'Date':  # Skip the date column
                        # Convert percentage string to float (remove % if present)
                        val_str = value.strip()
                        if val_str.endswith('%'):
                            val_str = val_str[:-1]
                        current_prevalence[region] = float(val_str) / 100.0  # Convert to proportion
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"Warning: Could not load PMC current prevalence data: {e}")
        # Return default fallback data
        return {'National': 0.01, 'Northeast': 0.01, 'Midwest': 0.01, 'South': 0.01, 'West': 0.01}
    
    return current_prevalence


def safe_float_param(params, key, default):
    """Safely extract float parameter with fallback."""
    try:
        value = params.get(key, default)
        return float(value) if value != '' else default
    except (ValueError, TypeError):
        return default

def safe_str_param(params, key, default):
    """Safely extract string parameter with fallback."""
    value = params.get(key, default)
    return str(value) if value is not None else str(default)


def calculate_daily_cumulative_risk(
    base_single_exposure_risk: float,
    base_prevalence: float,
    num_days: int,
    region: str = 'National',
    start_week: Optional[int] = None,
    calculation_params: Optional[Dict] = None,
    exposure_pattern: str = 'daily',
    vaccination_months_ago: Optional[int] = None,
    infection_months_ago: Optional[int] = None,
    advanced_params: Optional[Dict] = None
) -> float:
    """
    Calculate cumulative risk after daily exposures with time-varying prevalence and immunity decay.
    Uses PMC current prevalence for first week, then CDC weekly data for subsequent weeks.
    Accounts for waning vaccine and infection-acquired immunity over time.
    
    Args:
        advanced_params: Advanced environmental and calculation parameters from frontend
    
    Args:
        base_single_exposure_risk: Single exposure risk at base prevalence (for fallback)
        base_prevalence: The baseline prevalence used in the original calculation (as proportion)
        num_days: Number of daily exposures to calculate cumulative risk for
        region: Geographic region for prevalence data
        start_week: Starting week (defaults to current week)
        calculation_params: Parameters from original calculation to recalculate risk
        exposure_pattern: Pattern of exposures ('daily', 'weekly', 'monthly', 'workday')
        vaccination_months_ago: Months since vaccination (None if not vaccinated in last year)
        infection_months_ago: Months since infection (None if not infected in last year)
        
    Returns:
        Cumulative risk as a proportion (0-1)
    """
    if start_week is None:
        start_week = 22
    
    # DEBUG: Log advanced params received
    print(f"DEBUG TIME_VARYING: Advanced params received: {advanced_params}")
    if advanced_params:
        print(f"DEBUG TIME_VARYING: Environmental conditions - RH: {advanced_params.get('RH', 0.40)}, CO2: {advanced_params.get('CO2', 800.0)}, Temp: {advanced_params.get('inside_temp', 293.15)}")
        print(f"DEBUG TIME_VARYING: Custom prevalence: {advanced_params.get('covid_prevalence')}")
    
    # Load CDC weekly prevalence data for subsequent weeks
    cdc_weekly = load_cdc_prevalence_data()
    
    # For the first week, use the actual base prevalence from the calculation
    # (this could be PMC data, user-entered, or any other source)
    current_prevalence = base_prevalence
    
    # Calculate daily risks using proper recalculation when params available
    cumulative_safe_prob = 1.0  # Probability of staying safe
    
    print(f"DEBUG: Starting daily cumulative risk calculation for {num_days} exposures")
    print(f"DEBUG: Base risk: {base_single_exposure_risk}, Base prevalence: {base_prevalence}")
    
    for day in range(num_days):
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
            # Start from current week and add work weeks, but skip weeks 51-52
            week_offset = work_week
            # Add extra offset for each time we skip weeks 51-52
            if work_week >= 29:  # Week 22 + 29 = 51, so we start skipping here
                week_offset += 2  # Skip weeks 51 and 52
        else:
            # Daily pattern: group days into weeks
            week_offset = day // 7
        
        if day == 0:
            # First exposure always uses the base prevalence from calculation
            week_prevalence = current_prevalence
        else:
            # Subsequent exposures: use CDC weekly data
            exposure_week = ((start_week - 1 + week_offset) % 52) + 1
            
            if exposure_week in cdc_weekly and region in cdc_weekly[exposure_week]:
                week_prevalence = cdc_weekly[exposure_week][region]
            else:
                # Fallback to national average if specific week/region missing
                if exposure_week in cdc_weekly and 'National' in cdc_weekly[exposure_week]:
                    week_prevalence = cdc_weekly[exposure_week]['National']
                else:
                    week_prevalence = base_prevalence  # Ultimate fallback
        
        # Calculate immunity factor for this time point (accounts for waning immunity)
        if vaccination_months_ago is not None or infection_months_ago is not None:
            # Calculate days from now based on exposure pattern
            if exposure_pattern == 'weekly':
                days_from_now = day * 7
            elif exposure_pattern == 'monthly':
                days_from_now = int(day * 30.44)  # Average days per month
            elif exposure_pattern == 'workday':
                work_week = day // 5
                days_from_now = work_week * 7  # Each work week is 7 calendar days apart
            else:  # daily
                days_from_now = day
            
            immunity_factor = calculate_immunity_factor_at_time(
                vaccination_months_ago, 
                infection_months_ago, 
                days_from_now
            )
        else:
            # No vaccination or infection immunity - use baseline susceptibility
            immunity_factor = 1.0
        
        # Calculate daily risk for this exposure's prevalence and immunity
        if day == 0:
            # First exposure: use the original calculation (already calculated with current immunity)
            daily_risk = base_single_exposure_risk
        else:
            # Check if user manually entered prevalence as advanced input
            prevalence_value = advanced_params.get('covid_prevalence') if advanced_params else None
            use_fixed_prevalence = (prevalence_value is not None and 
                                  str(prevalence_value).strip() != '' and
                                  str(prevalence_value).strip() != '0' and
                                  str(prevalence_value).strip().lower() != 'none')
            
            # Only log for first few days to avoid spam
            if day < 3:
                print(f"DEBUG: Day {day+1}: prevalence_value='{prevalence_value}', use_fixed_prevalence={use_fixed_prevalence}")
            
            if use_fixed_prevalence:
                # User manually entered prevalence - use that for ALL future exposures
                try:
                    fixed_prev_str = str(advanced_params['covid_prevalence']).strip()
                    if fixed_prev_str.endswith('%'):
                        fixed_prev_str = fixed_prev_str[:-1]
                    fixed_prevalence = float(fixed_prev_str) / 100.0
                    
                    # Only adjust for immunity changes, not prevalence
                    if vaccination_months_ago is not None or infection_months_ago is not None:
                        original_immunity = calculate_immunity_factor_at_time(
                            vaccination_months_ago, infection_months_ago, 0
                        )
                        if original_immunity > 0:
                            immunity_ratio = immunity_factor / original_immunity
                            daily_risk = base_single_exposure_risk * immunity_ratio
                        else:
                            daily_risk = base_single_exposure_risk
                    else:
                        daily_risk = base_single_exposure_risk
                        
                    # Override week_prevalence for consistent reporting
                    week_prevalence = fixed_prevalence
                        
                except (ValueError, TypeError):
                    # Fallback to time-varying prevalence if parsing fails
                    use_fixed_prevalence = False
            
            if not use_fixed_prevalence:
                # Use time-varying prevalence (normal behavior)
                # TEMPORARILY DISABLE full recalculation to debug
                # TODO: Re-enable this once we confirm the scaling method works
                # if calculation_params and advanced_params:
                if False:  # Temporarily disabled
                    # Create updated parameters for this day
                    updated_params = calculation_params.copy()
                    updated_params.update(advanced_params)

                    # Update prevalence for this exposure
                    updated_params['covid_prevalence'] = week_prevalence * 100  # Convert to percentage

                    # Update immunity factor for this time point
                    if vaccination_months_ago is not None or infection_months_ago is not None:
                        updated_params['immune'] = immunity_factor

                    # Recalculate with full model
                    daily_risk = recalculate_risk_with_prevalence(updated_params, week_prevalence)
                else:
                    # Use scaling method (proven to work)
                    if base_prevalence > 0:
                        prevalence_ratio = week_prevalence / base_prevalence
                        # Get original immunity factor (what was used in base calculation)
                        original_immunity = calculate_immunity_factor_at_time(
                            vaccination_months_ago, 
                            infection_months_ago, 
                            0  # Current time
                        ) if (vaccination_months_ago is not None or infection_months_ago is not None) else 1.0
                        
                        # Scale risk by both prevalence change and immunity change
                        if original_immunity > 0:
                            immunity_ratio = immunity_factor / original_immunity
                            daily_risk = base_single_exposure_risk * prevalence_ratio * immunity_ratio
                        else:
                            daily_risk = base_single_exposure_risk * prevalence_ratio
                    else:
                        daily_risk = base_single_exposure_risk
                        
                    # Only log for first few days to avoid spam
                    if day < 3:
                        print(f"DEBUG: Day {day+1}: Using scaling method - base_risk={base_single_exposure_risk:.6f}, week_prev={week_prevalence:.6f}, base_prev={base_prevalence:.6f}, daily_risk={daily_risk:.6f}")
        
        # Clamp to [0, 1] range
        daily_risk = max(0.0, min(1.0, daily_risk))
        
        # Update cumulative probability
        cumulative_safe_prob *= (1.0 - daily_risk)
        
        # Debug log key days only  
        if day < 3 or day == num_days - 1:
            print(f"DEBUG: Day {day+1}: daily_risk={daily_risk:.6f}, cumulative_safe={cumulative_safe_prob:.6f}")
    
    # Convert to cumulative risk
    cumulative_risk = 1.0 - cumulative_safe_prob
    print(f"DEBUG: Final cumulative risk: {cumulative_risk:.6f}")
    return cumulative_risk


def recalculate_risk_with_prevalence(params: Dict, new_prevalence: float) -> float:
    """
    Recalculate exposure risk using the full model with a new prevalence value.
    
    Args:
        params: Dictionary containing all the original calculation parameters
        new_prevalence: New prevalence value to use (as proportion 0-1)
        
    Returns:
        Recalculated risk as a proportion (0-1)
    """
    from calculators.exposure_calculator import calculate_unified_transmission_exposure
    
    # Convert prevalence back to percentage string for the calculator
    prevalence_pct = str(new_prevalence * 100)
    
    # Call the full exposure calculator with new prevalence
    result = calculate_unified_transmission_exposure(
        safe_str_param(params, 'C0', 0.065),
        safe_str_param(params, 'Q0', 0.08), 
        safe_str_param(params, 'p', 0.08),
        safe_str_param(params, 'ACH', 1.0),
        safe_str_param(params, 'room_volume', 1000.0),
        safe_str_param(params, 'delta_t', 42.0),
        safe_str_param(params, 'x', 0.7),
        safe_str_param(params, 'gamma', 0.7),
        safe_str_param(params, 'f_e', 1.0),
        safe_str_param(params, 'f_i', 1.0),
        safe_str_param(params, 'omicron', 3.3),
        prevalence_pct,  # Use new prevalence
        safe_str_param(params, 'immune', 1.0),
        safe_str_param(params, 'N', 1),
        safe_str_param(params, 'percentage_masked', 0.0),
        params.get('user_physical_activity', 'standing'),
        params.get('others_physical_activity', 'standing'),
        params.get('others_vocal_activity', 'speaking'),
        safe_float_param(params, 'RH', 0.40),
        safe_float_param(params, 'CO2', 800.0),
        safe_float_param(params, 'inside_temp', 293.15),
        params.get('immunocompromised_status', 'normal')
    )
    
    if 'error' in result:
        # Fallback to scaling if recalculation fails
        print(f"Recalculation failed: {result.get('error')}")
        base_risk = params.get('base_risk', 0.0)
        base_prev = params.get('base_prevalence', 0.01)
        return base_risk * (new_prevalence / base_prev) if base_prev > 0 else 0.0
    
    # Use the Monte Carlo mean as the primary risk estimate
    return result.get('mc_mean', result.get('risk', 0.0))