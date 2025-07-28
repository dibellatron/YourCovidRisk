import math

oneoverln2 = 1.0 / math.log(2)
import numpy as np

# normalization constant for the D⁻³ shape over [0.5,100]
SHAPE_NORM = (0.5 ** (-2) - 100.0 ** (-2)) / 2.0

from calculators.validators import safe_float, safe_int

# ─────────────────────────────────────────────────────────────────────────────
# Size-resolved Monte Carlo helpers (Henriques et al.)
# ─────────────────────────────────────────────────────────────────────────────
# Particle-size grid [µm]
Ds = np.logspace(np.log10(0.1), np.log10(30.0), 50)
# Bin widths (µm) for numerical integration over the size spectrum
dDs = np.empty_like(Ds)
dDs[1:-1] = (Ds[2:] - Ds[:-2]) / 2  # central differences
dDs[0] = Ds[1] - Ds[0]
dDs[-1] = Ds[-1] - Ds[-2]
Dmax_SR = 100.0  # µm, short-range cutoff (unchanged)
Dmax_LR = 20.0  # µm, long-range cutoff per Henriques (updated from 30µm based on new evidence)

# Henriques jet physics constants (shared across functions)
D_mouth = 0.02  # Mouth opening diameter [m] (20 mm)
beta_r_j = 0.18  # Radial penetration coefficient (jet-like stage)
beta_r_p = 0.20  # Radial penetration coefficient (puff-like stage)
beta_x_j = 2.4   # Streamwise penetration coefficient (jet-like)
                 # NOTE: Corrected value from Henriques (personal communication)
                 # Paper shows 0.20, but this produces unrealistic transition distances (~0.01m)
beta_x_p = 2.2   # Streamwise penetration coefficient (puff-like)
                 # NOTE: Corrected value from Henriques (personal communication)



def emission_spectrum_henriques(D, activity_choice):
    """
    Henriques-style BLO emission spectrum following Eq. S.19-S.20.
    Uses vocalization amplification factors (famp) instead of simple activity mapping.
    
    Args:
        D: particle diameter [μm]
        activity_choice: activity level string ("1"=breathing, "2"=speaking, "4+"=shouting)
    
    Returns: volumetric emission [mL of particles / m³ air / µm]
    """
    # BLO parameters from official CAiMIRA data registry (exact values)
    cn = {"B": 0.06, "L": 0.2, "O": 0.0010008}  # cm^-3
    mu = {"B": 0.989541, "L": 1.38629, "O": 4.97673}  # ln μm  
    sigma = {"B": 0.262364, "L": 0.506818, "O": 0.585005}  # ln μm
    
    # Vocalization amplification factors (famp) from Henriques
    if activity_choice == "1":  # Breathing
        famp = {"B": 1.0, "L": 0.0, "O": 0.0}  # Only bronchiolar mode
    elif activity_choice == "2" or activity_choice == "3":  # Speaking  
        famp = {"B": 1.0, "L": 1.0, "O": 1.0}  # All modes active
    else:  # Shouting/Loud speaking (activity_choice >= 4)
        famp = {"B": 1.0, "L": 5.0, "O": 5.0}  # Amplified laryngeal/oral modes
    
    # Compute BLO tri-modal emission spectrum (Eq. S.20)
    result = 0.0
    modes = ["B", "L", "O"]
    for mode in modes:
        if famp[mode] > 0:  # Only include active modes
            # Number concentration per diameter (following Eq. S.20)
            Np_term = (famp[mode] * cn[mode] / (np.sqrt(2 * np.pi) * sigma[mode]) / D) * np.exp(
                -((np.log(D) - mu[mode]) ** 2) / (2 * sigma[mode] ** 2)
            )
            
            # Particle volume (assuming sphere): V = (4/3) * π * (D/2)^3 in μm³
            Vp = (4.0/3.0) * np.pi * (D/2.0)**3  # μm³
            
            # Convert to mL/m³/μm (Eq. S.19): 10^-6 converts μm³/cm³ to mL/m³
            result += Np_term * Vp * 1e-6
    
    return result


def get_henriques_breathing_rate(physical_activity):
    """Get Henriques breathing rate from Table 1 based on physical activity level."""
    # Henriques Table 1 breathing rates [m³/h]
    rates = {
        "sitting": 0.51,      # seated BRse
        "standing": 0.57,     # standing BRst  
        "light": 1.24,        # light activity BRl
        "moderate": 1.77,     # moderate activity BRm
        "heavy": 3.28,        # heavy exercise BRh
        # Backwards compatibility mappings
        "seated": 0.51,
        "light_exercise": 1.24,
        "moderate_exercise": 1.77,
        "high_intensity": 3.28,
    }
    return rates.get(physical_activity, 0.57)  # Default to standing


def get_henriques_vocalization_activity(vocal_activity):
    """Map vocal activity to Henriques emission spectrum activity code."""
    mapping = {
        "breathing": "1",        # Just breathing → Activity 1
        "just_breathing": "1",   # Alternative name
        "speaking": "2",         # Speaking → Activity 2  
        "loudly_speaking": "5",  # Loudly speaking → Activity 5 (shouting)
        "loud_speaking": "5",    # Alternative name
        "shouting": "5",         # Shouting → Activity 5
    }
    return mapping.get(vocal_activity, "2")  # Default to speaking


def get_henriques_vocalization(activity_choice):
    """Legacy function for backwards compatibility."""
    mapping = {
        "1": "breathing",     # Sedentary → Breathing only
        "2": "speaking",      # Standard → Speaking  
        "3": "speaking",      # Light → Speaking
        "4": "shouting",      # Moderate → Shouting
        "5": "shouting"       # Intense → Shouting
    }
    return mapping.get(activity_choice, "speaking")




def calculate_henriques_jet_parameters(BR, D_mouth=D_mouth):
    """
    Calculate dynamic jet parameters following Henriques supplement equations S.3-S.8.
    
    Args:
        BR: Breathing rate [m³/h]
        D_mouth: Mouth opening diameter [m] (default: 0.02 m = 20 mm)
    
    Returns:
        dict with x_transition, x0_j, x0_p, t_star, Q_exh, u0
    """
    # Constants from Henriques supplement
    T = 4.0  # Breathing cycle duration [s]
    phi_j = 2.0  # Exhalation coefficient 
    
    # Convert breathing rate from m³/h to m³/s
    BR_s = BR / 3600.0
    
    # Exhalation volumetric flowrate [m³/s] - Eq S.23 context
    Q_exh = phi_j * BR_s  # φj = 2 (ratio of cycle duration to exhalation duration)
    
    # Tidal volume in a single puff [m³]
    V_p = T * BR_s  # Total volume exhaled per cycle
    
    # Initial jet velocity [m/s] 
    A_mouth = math.pi * (D_mouth / 2.0) ** 2  # Cross-sectional area [m²]
    u0 = Q_exh / A_mouth
    
    # Jet-puff transition time [s] - Eq S.4
    t_star = T / 2.0  # Half the breathing cycle
    
    # Virtual origin of jet-like stage [s] - Eq S.3
    t0_j = (math.sqrt(math.pi) * (D_mouth ** 3)) / (8 * (beta_r_j ** 2) * (beta_x_j ** 2) * Q_exh)
    
    # Virtual origin of puff-like stage [s] - Eq S.5
    t0_p = ((beta_r_j ** 4) * (beta_x_j ** 4) / ((beta_r_p ** 4) * (beta_x_p ** 4))) * (Q_exh / V_p) * ((t_star + t0_j) ** 2) - t_star
    
    # Virtual penetration distances [m] - Eq S.6-S.8
    x0_j = D_mouth / (2 * beta_r_j)  # Eq S.6
    
    # Jet-puff transition distance [m] - Eq S.7
    x_transition = beta_x_j * ((Q_exh * u0) ** 0.25) * ((t_star + t0_j) ** 0.5) - x0_j
    
    # Virtual penetration distance for puff-like stage [m] - Eq S.8
    x0_p = (beta_r_j / beta_r_p) * (x_transition + x0_j) - x_transition
    
    return {
        'x_transition': x_transition,
        'x0_j': x0_j, 
        'x0_p': x0_p,
        't_star': t_star,
        'Q_exh': Q_exh,
        'u0': u0,
        't0_j': t0_j,
        't0_p': t0_p
    }


def emission_spectrum_IRP_henriques(D, vocal_activity, viral_load, f_inf):
    """
    Convert emission spectrum to IRP units using pure Henriques et al. methodology.
    Follows Equations S.18-S.20 exactly without external multipliers.
    
    Args:
        D: particle diameter [μm]
        vocal_activity: vocal activity string ("breathing", "speaking", "loudly_speaking")
        viral_load: viral load [RNA copies/mL]
        f_inf: IRP-to-RNA ratio [dimensionless]
    
    Returns: IRP concentration per m³ air per μm diameter [IRP/m³/μm]
    """
    # Map vocal activity to Henriques emission spectrum activity code
    henriques_activity = get_henriques_vocalization_activity(vocal_activity)
    
    # Use Henriques emission spectrum with vocalization effects
    Ec_liquid = emission_spectrum_henriques(D, henriques_activity)
    
    # Convert to IRP concentration following Henriques Eq. S.18
    # C0,SR(D) = Ec,j(D) × vlin × finf
    C0_SR = Ec_liquid * viral_load * f_inf  # IRP/m³/μm
    
    # Pure Henriques implementation - NO calibration factor needed
    # Following Equations S.18-S.20 exactly as published
    # Any calibration would represent deviation from the peer-reviewed methodology
    
    return C0_SR


def emission_spectrum_IRP_henriques_legacy(D, activity_choice, viral_load, f_inf):
    """Legacy function for backwards compatibility with single activity parameter."""
    vocalization = get_henriques_vocalization(activity_choice)
    return emission_spectrum_IRP_henriques(D, vocalization, viral_load, f_inf)


def deposition_fraction(D, evaporation_factor=0.3):
    """
    f_dep(D): fraction of inhaled particles of diameter D that deposit.
    From W. C. Hinds, "Aerosol Technology", New York, Wiley, 1999 (pp. 233-259).
    Implementation matches official CAiMIRA/Henriques methodology.
    
    Args:
        D: particle diameter [μm]
        evaporation_factor: factor applied to diameter due to evaporation (0.3 for long-range, 1.0 for short-range)
    """
    d = D * evaporation_factor
    IFrac = 1 - 0.5 * (1 - (1 / (1 + (0.00076*(d**2.8)))))
    fdep = IFrac * (0.0587
            + (0.911/(1 + np.exp(4.77 + 1.485 * np.log(d))))
            + (0.943/(1 + np.exp(0.508 - 2.58 * np.log(d)))))
    return fdep


def sedimentation_rate(D, evaporation_factor=0.3):
    """
    Calculate gravitational settling removal rate [h⁻¹].

    Parameters:
    - D: particle diameter [µm]
    - evaporation_factor: factor accounting for droplet shrinkage (default 0.3)

    Returns:
    - Removal rate constant [h⁻¹]
    """
    # Calculate settling velocity [m/s] using CAiMIRA's formula
    vg = 1.88e-4 * ((D * evaporation_factor) / 2.5) ** 2

    # Emission source height [m]
    h = 1.5

    # Convert to hourly removal rate [h⁻¹]
    return (vg * 3600) / h


def viral_inactivation_rate_long(D, T=293.15, RH=0.4):
    """
    Biological (viability) decay rate [h⁻¹] in long-range, temperature- and humidity-dependent.
    T: inside temperature [K]
    RH: relative humidity [0..1]
    """
    # Convert Kelvin to Celsius
    Tc = T - 273.15
    # Normalize temperature and humidity
    t_norm = (Tc - 20.615) / 10.585
    h_norm = (RH * 100 - 45.235) / 28.665
    # Empirical half-life calculation (hours) from Dabisch et al.
    hl = np.log(2) / (
        0.16030 + 0.04018 * t_norm + 0.02176 * h_norm - 0.14369 - 0.02636 * t_norm
    )
    # Cap to [0, 6.43] hours
    hl = np.where(hl <= 0, 6.43, np.minimum(6.43, hl))
    # Convert half-life to decay constant [h^-1]
    return np.log(2) / hl


def short_range_viability_decay(x, u0, RH):
    """
    Short-range viability decay factor per Henriques et al. Equation 2.4.
    Based on Haddrell et al. triphasic viral aerosol decay (TVAD).
    
    Args:
        x: Distance from source [m]
        u0: Initial jet velocity [m/s]
        RH: Relative humidity [0-1]
    
    Returns:
        lambda_SR: Viability decay factor [dimensionless, 0-1]
    """
    if RH <= 0.40:  # 40% RH threshold from Henriques et al.
        tx = x / u0  # Time for jet to travel distance x (seconds)
        lambda_SR = 1.0 - 0.016 * tx  # Linear decay: -1.6% per second
        return max(0.0, lambda_SR)  # Ensure non-negative
    else:
        return 1.0  # No short-range decay above 40% RH


def calculate_jet_velocity(Q0_exhaled, D_mouth=0.02):
    """
    Calculate initial jet velocity from volumetric exhalation flow rate.
    
    Args:
        Q0_exhaled: Volumetric exhalation flow rate [m³/s]
        D_mouth: Mouth opening diameter [m] (default: 0.02 m = 20 mm)
    
    Returns:
        u0: Initial jet velocity [m/s]
    """
    A_mouth = math.pi * (D_mouth / 2.0) ** 2  # Cross-sectional area [m²]
    u0 = Q0_exhaled / A_mouth  # Initial velocity [m/s]
    return u0


# ─────────────────────────────────────────────────────────────────────────────
# Omicron TVAD helper (triphasic survival fraction)
# ─────────────────────────────────────────────────────────────────────────────
CO2_REF = 500.0  # ppm reference
LAG_HIGHRH = 15.0  # s, for RH > 50%
LAG_LOWRH = 0.0  # efflorescence instant
T1_2_DYN = 32.0  # s dynamic half-life at CO2_REF
T1_2_SLOW = 4800.0  # s slow half-life at CO2_REF


def omicron_tvad_survival(t: float, RH: float, CO2: float) -> float:
    """
    Triphasic survival fraction for Omicron (BA.2).
    t  : time [s]
    RH : relative humidity [0..1]
    CO2: ambient CO2 [ppm]
    """
    # 1) pick lag based on humidity
    t_lag = LAG_HIGHRH if RH > 0.50 else LAG_LOWRH

    # 2) scale half-lives by CO2/CO2_REF
    dyn_h = T1_2_DYN * (CO2 / CO2_REF)
    slow_h = T1_2_SLOW * (CO2 / CO2_REF)
    k2 = math.log(2) / dyn_h
    k3 = math.log(2) / slow_h

    # define end of dynamic decay (~87%)
    t_dyn_end = t_lag + 3 * dyn_h

    if t <= t_lag:
        return 1.0
    if t <= t_dyn_end:
        return math.exp(-k2 * (t - t_lag))
    # else: slow phase after dynamic
    s2_end = math.exp(-k2 * (t_dyn_end - t_lag))
    return s2_end * math.exp(-k3 * (t - t_dyn_end))


def get_immune_emission_multiplier(immunocompromised_status: str) -> float:
    """
    Get emission rate multiplier based on immunocompromised status.
    
    Args:
        immunocompromised_status: Immune status ("normal", "moderate", "severe")
    
    Returns:
        Multiplier for quanta emission rates (1.0, 8.0, or 20.0)
    """
    multipliers = {
        "normal": 1.0,
        "moderate": 8.0,
        "severe": 20.0
    }
    return multipliers.get(immunocompromised_status, 1.0)


# Import the risk distribution module
from calculators.risk_distribution import generate_risk_distribution_data


def sample_omicron_transmissibility_bayesian():
    """
    Sample Omicron transmissibility factor from Bayesian posterior distribution.
    
    Based on meta-analysis by Du et al. (2022):
    "Reproduction Number of the Omicron Variant Triples That of the Delta Variant"
    Viruses 14(4):821. https://doi.org/10.3390/v14040821
    
    Uses pooled estimate of effective reproduction number:
    Re = 4.20 (95% CI: 2.05, 6.35) from 6 studies across multiple countries.
    
    Returns:
        float: Omicron transmissibility factor sampled from posterior distribution
    """
    # Meta-analysis posterior parameters from Du et al. (2022)
    pooled_mean = 4.20  # Pooled effective reproduction number
    ci_lower = 2.05     # 95% CI lower bound
    ci_upper = 6.35     # 95% CI upper bound
    
    # Convert to log-normal posterior distribution
    log_mean = np.log(pooled_mean)
    log_se = (np.log(ci_upper) - np.log(ci_lower)) / (2 * 1.96)
    
    # Sample from the meta-analysis posterior
    log_omicron = np.random.normal(loc=log_mean, scale=log_se)
    omicron_factor = np.exp(log_omicron)
    
    # Apply conservative bounds based on observed data range (1.5-8.0)
    return np.clip(omicron_factor, 1.5, 8.0)


def calculate_unified_transmission_exposure(
    C0: str,
    Q0: str,
    p: str,
    ACH: str,
    room_volume: str,
    delta_t: str,
    x: str,
    gamma: str,
    f_e: str,
    f_i: str,
    omicron: str,
    covid_prevalence: str,
    immune: str,
    N: str,
    # Parameters with defaults
    activity_choice: str = "2",  # Keep for backwards compatibility
    percentage_masked: str = "0",
    # Henriques separated activity parameters
    user_physical_activity: str = "standing",
    others_physical_activity: str = "standing", 
    others_vocal_activity: str = "speaking",
    # TVAD testing parameters (RH: relative humidity [0..1], CO2: ppm)
    RH: float = 0.40,
    CO2: float = 800.0,
    inside_temp: float = 293.15,
    # Immunocompromised status for quanta emission rate adjustment
    immunocompromised_status: str = "normal",
) -> dict:
    """
    Calculate the unified (short-range and long-range) airborne transmission infection risk using a modified Wells–Riley equation.

    Parameters:
      C0: Infectious quantum concentration (quanta/L) as a string [default "0.1"].
      Q0: Exhalation flow rate (L/s) as a string [default "0.1"].
      p: Inhalation rate (L/s) as a string [default "0.1"].
      ACH: Air changes per hour as a string [default "20"].
      room_volume: Room volume in m³ as a string [default "1000"].
      delta_t: Exposure duration in seconds as a string [default "42"].
      x: Distance from the source (m) as a string [default "0.7"].
      activity_choice: Legacy activity intensity (1-5) for display label only [default "2" for Standard].
      gamma: Gamma factor as a string [default "0.5"].
      f_e: Exhalation multiplier factor as a string [default "1"].
      f_i: Inhalation multiplier factor as a string [default "1"].
      omicron: Omicron multiplier for Q0 as a string [default "4.20"].
      covid_prevalence: Percentage of people currently infected with Covid as a string [default "0.01"].
      immune: Immune susceptibility of the user as a string [default "1"].
      N: The number of other people present as a string [default "1"].
      RH: Ambient relative humidity [0..1] as a float [default 0.40].
      CO2: Ambient CO2 concentration (ppm) as a float [default 800.0].
      immunocompromised_status: Immune status affecting quanta emission rates ("normal", "moderate", "severe") [default "normal"].

    Returns:
      A dictionary containing:
        - risk: The predicted infection risk (a float between 0 and 1).
        - q_e: Effective ventilation rate (L/s).
        - ACH: The air changes per hour used.
        - room_volume: The room volume (m³).
        - activity_label: Display label for legacy activity_choice parameter (not used in calculations).
        - x_transition: The transition distance (m) for the exhalation profile.
        - stage: Indicates whether the model used the 'jet-like' or 'puff-like' stage.
        - Sx: The computed dilution factor.
        - inputs: A dictionary with the converted input values.
    """
    # Debug input values at the start
    print(f"DEBUG START: f_i={f_i}, percentage_masked={percentage_masked}")
    print(f"DEBUG START: activity_choice={activity_choice}")

    # Calculate immune emission multiplier for quanta emission rates
    immune_emission_multiplier = get_immune_emission_multiplier(immunocompromised_status)
    print(f"DEBUG IMMUNE: immunocompromised_status={immunocompromised_status}, multiplier={immune_emission_multiplier}")

    # Use validation helpers – collect any errors and bail out if present.
    errors = []

    C0_val, err = safe_float(C0, 0.1)
    errors.append(err)
    Q0_val, err = safe_float(Q0, 0.1)
    errors.append(err)
    p_val, err = safe_float(p, 0.1)
    errors.append(err)
    ACH_val, err = safe_float(ACH, 1.0)
    errors.append(err)
    room_volume_val, err = safe_float(room_volume, 1000.0)
    errors.append(err)
    delta_t_val, err = safe_float(delta_t, 42.0)
    errors.append(err)
    x_val, err = safe_float(x, 0.7)
    errors.append(err)
    gamma_val, err = safe_float(gamma, 0.5)
    errors.append(err)
    f_e_val, err = safe_float(f_e, 1.0)
    errors.append(err)
    f_i_val, err = safe_float(f_i, 1.0)
    errors.append(err)
    omicron_val, err = safe_float(omicron, 4.20)
    errors.append(err)

    # Debug converted values
    print(
        f"DEBUG AFTER CONVERSION: f_i_val={f_i_val}, percentage_masked={percentage_masked}"
    )

    # Store the original percentage_masked for debugging
    original_percentage_masked = percentage_masked

    # ------------------------------------------------------------------
    # Covid‑19 prevalence handling
    # ------------------------------------------------------------------
    covid_prev_pct, err = safe_float(covid_prevalence, 1.0)
    errors.append(err)
    # Treat all prevalence inputs as percentages; convert to fraction 0..1
    covid_prevalence_val = covid_prev_pct / 100.0

    immune_val, err = safe_float(immune, 1.0)
    errors.append(err)
    N_val, err_int = safe_int(N, 1)
    errors.append(err_int)
    percentage_masked_val, err = safe_float(percentage_masked, 0.0)
    errors.append(err)

    # If any non‑empty error strings were captured, return generic message to
    # preserve previous behaviour.
    if any(errors):
        return {"error": "Invalid input; please enter numeric values."}

    Q0_val = Q0_val * f_e_val * omicron_val
    p_val = p_val * f_i_val

    # Calculate total ventilation rate (L/s) and effective ventilation rate per person.
    q_total = (ACH_val * room_volume_val * 1000) / 3600
    q_e = q_total  # Assuming one occupant

    # Calculate others' breathing rate for Monte Carlo
    others_BR = get_henriques_breathing_rate(others_physical_activity)
    
    # Map activity choice to display label only (not used in calculations)
    # Actual calculations use user_physical_activity, others_physical_activity, and others_vocal_activity
    activity_map = {
        "1": "Sedentary/Passive",
        "2": "Standard", 
        "3": "Light",
        "4": "Moderate",
        "5": "Intense",
    }
    if activity_choice not in activity_map:
        activity_choice = "2"
    activity_label = activity_map[activity_choice]

    # Original Wells-Riley calculation removed - see auxiliary scripts/historical_risk_methods_documentation.py
    # Now using only Monte Carlo Protection Factor method
    
    # Calculate number of masked and unmasked individuals for Monte Carlo
    N_masked = math.floor(N_val * percentage_masked_val)
    N_unmasked = N_val - N_masked

    # Initialize result dictionary - risk will be set from Monte Carlo results
    result = {
        "risk": 0,  # Placeholder - will be overwritten by MC PF result
        "q_e": q_e,
        "ACH": ACH_val,
        "room_volume": room_volume_val,
        "activity_label": activity_label,
        "inputs": {
            "C0": C0_val,
            "Q0": Q0_val,
            "p": p_val,
            "delta_t": delta_t_val,
            "x": x_val,
            "gamma": gamma_val,
            "activity_choice": activity_choice,
            "f_e": f_e_val,
            "f_i": f_i_val,
            "omicron": omicron_val,
            "covid_prevalence": covid_prevalence_val,
            "immune": immune_val,
            "N": N_val,
            "percentage_masked": percentage_masked_val,
        },
    }

    # Always add the masked/unmasked split to the results for consistency
    result["N_masked"] = N_masked
    result["N_unmasked"] = N_unmasked

    # TVAD-adjusted calculation removed - see auxiliary scripts/historical_risk_methods_documentation.py
    # Now using only Monte Carlo Protection Factor method

    # ─────────────────────────────────────────────────────────────────────────
    # Size‑resolved Monte Carlo per Henriques et al. (width‑weighted & prevalence‑adjusted)
    # ─────────────────────────────────────────────────────────────────────────
    # Adaptive simulation count based on expected number of infectious people
    # Computation time scales with: N_people × prevalence × n_simulations
    expected_infectious = N_val * covid_prevalence_val

    if expected_infectious < 0.5:  # < 0.5 expected infectious people
        n_sims = 25000  # High precision for low infectious load (acceptable timing)
    elif expected_infectious < 2.0:  # 0.5-2 expected infectious people
        n_sims = 8000
    elif expected_infectious < 5.0:
        n_sims = 2000
    elif expected_infectious < 10.0:
        n_sims = 1000
    else:
        n_sims = 300

    # Store results for Monte Carlo Protection Factor method
    all_risks_pf = np.zeros(n_sims)   # protection-factor method

    # Precompute normalization for emission spectrum
    # D1, D2 = 0.5, 100.0
    # norm = (D1 ** -2 - D2 ** -2) / 2  # ∫ D^-3 dD over [0.5,100]

    # No calibration factor needed - using proper IRP units throughout

    # Individual-level sampling: each person is sampled separately for infection status
    
    for i in range(n_sims):
        # Sample Omicron transmissibility factor from Bayesian posterior (Du et al. 2022)
        # This is a population-level parameter, sampled once per simulation
        omicron_val_sim = sample_omicron_transmissibility_bayesian()
        
        # Sample user characteristics (same for all people in this simulation)
        ID50 = np.random.uniform(10, 100)  # infectious dose [IRP]
        
        # Sample user's breathing rate for inhalation dose
        user_BR_base = get_henriques_breathing_rate(user_physical_activity)
        if user_physical_activity in ["sitting", "seated"]:
            BR = np.random.lognormal(np.log(user_BR_base), 0.053)
        elif user_physical_activity == "standing":
            BR = np.random.lognormal(np.log(user_BR_base), 0.053)
        elif user_physical_activity in ["light", "light_exercise"]:
            BR = np.random.lognormal(np.log(user_BR_base), 0.12)
        elif user_physical_activity in ["moderate", "moderate_exercise"]:
            BR = np.random.lognormal(np.log(user_BR_base), 0.34)
        else:  # heavy/high_intensity
            BR = np.random.lognormal(np.log(user_BR_base), 0.72)

        # Debug the values before Monte Carlo calculation
        if i == 0:
            print(
                f"DEBUG MONTE CARLO: f_i_val={f_i_val}, percentage_masked_val={percentage_masked_val}"
            )
            print(
                f"DEBUG MONTE CARLO: User physical: {user_physical_activity}, Others physical: {others_physical_activity}"
            )
            print(
                f"DEBUG MONTE CARLO: Others vocal: {others_vocal_activity}"
            )
            print(
                f"DEBUG MONTE CARLO: Using individual-level sampling - each person sampled separately"
            )

        # User's inhalation filter (eta_in = filter efficiency)
        eta_in = 1.0 - f_i_val
        if i == 0:
            print(
                f"DEBUG MONTE CARLO: User inhalation efficiency eta_in={eta_in:.4f}"
            )

        # Use the user‑specified distance for MC
        x_eff = x_val
        include_SR = True  # Always include short-range - let dilution handle distance

        # Convert breathing rate and times
        BR_s = BR / 3600.0  # m³/s
        dt_s = delta_t_val  # s
        dt_h = delta_t_val / 3600.0  # h

        # Initialize dose accumulator
        total_dose = 0.0
        infectious_count = 0

        # Sample each person individually
        for person in range(N_val):
            # Step 1: Determine if this person is infectious
            is_infectious = np.random.random() < covid_prevalence_val
            
            if is_infectious:
                infectious_count += 1
                
                # Step 2: Sample this person's viral characteristics
                # Log₁₀ viral load (copies mL⁻¹) distribution from Chen et al. (2021)
                # SARS-CoV-2 rVL follows Weibull distribution with mean=6.2, std=1.8 log10 copies/ml
                # Weibull parameters fitted to individual sample data (N=3834 samples from 26 studies)
                # Truncated between 10² and 10¹⁰ RNA copies/ml as per Chen et al. methods
                
                # Weibull parameters fitted to match Henriques Table 1: mean=6.2, std=1.8 log10 copies/ml
                # Using method of moments optimization to match target statistics exactly
                weibull_shape = 3.900  # Shape parameter (k) to match Henriques Table 1
                weibull_scale = 6.850  # Scale parameter (λ) to match Henriques Table 1 
                vlin_log10 = np.random.weibull(weibull_shape) * weibull_scale
                vlin_log10 = np.clip(vlin_log10, 2.0, 10.0)  # Truncate between 10² and 10¹⁰
                vlin = 10 ** vlin_log10
                f_inf = np.random.uniform(0.01, 0.60)  # IRP-to-RNA viability ratio
                
                # Step 3: Sample this person's emission characteristics
                # Use Henriques breathing rate based on physical activity level
                # Sample from lognormal distributions per Henriques Table 1 (σ values from Table 1)
                others_BR_base = get_henriques_breathing_rate(others_physical_activity)
                if others_physical_activity in ["sitting", "seated"]:
                    others_BR = np.random.lognormal(np.log(others_BR_base), 0.053)
                elif others_physical_activity == "standing":
                    others_BR = np.random.lognormal(np.log(others_BR_base), 0.053)
                elif others_physical_activity in ["light", "light_exercise"]:
                    others_BR = np.random.lognormal(np.log(others_BR_base), 0.12)
                elif others_physical_activity in ["moderate", "moderate_exercise"]:
                    others_BR = np.random.lognormal(np.log(others_BR_base), 0.34)
                else:  # heavy/high_intensity
                    others_BR = np.random.lognormal(np.log(others_BR_base), 0.72)
                
                # Determine if this person is masked
                is_masked = np.random.random() < percentage_masked_val
                exhalation_filter = f_e_val if is_masked else 1.0
                
                # Step 4: Calculate jet/dilution parameters for this person
                # Calculate dynamic jet parameters following Henriques supplement equations S.3-S.8
                mc_jet_params = calculate_henriques_jet_parameters(others_BR)
                mc_x_transition = mc_jet_params['x_transition'] 
                mc_x0_j = mc_jet_params['x0_j']
                mc_x0_p = mc_jet_params['x0_p']
                mc_u0 = mc_jet_params['u0']
                
                # Compute dilution using exact Henriques Eq. 2.1 with this person's breathing rate
                if x_eff < mc_x_transition:
                    # Jet-like stage: S(x) = 2 * βr,j * (x + x0,j) / Dm
                    Sx_sim = 2 * beta_r_j * (x_eff + mc_x0_j) / D_mouth
                else:
                    # Puff-like stage: S(x) = S(x*) * [1 + βr,p(x-x*) / (βr,j(x*+x0,j))]³
                    Sx_star_mc = 2 * beta_r_j * (mc_x_transition + mc_x0_j) / D_mouth
                    Sx_sim = Sx_star_mc * (
                        1 + beta_r_p * (x_eff - mc_x_transition) / (beta_r_j * (mc_x_transition + mc_x0_j))
                    ) ** 3
                
                # Short-range viability decay factor using this person's jet velocity
                lambda_SR = short_range_viability_decay(x_eff, mc_u0, RH)
                
                # Step 5: Calculate dose contribution from this person
                person_dose = 0.0
                for idx, Dv in enumerate(Ds):
                    width = dDs[idx]  # µm
                    
                    # Emission concentration from this specific person
                    # Get IRP emission concentration using pure Henriques et al. methodology
                    C0_SR = emission_spectrum_IRP_henriques(Dv, others_vocal_activity, vlin, f_inf)  # IRP/m³/μm
                    # Apply Omicron transmissibility factor (sampled from Bayesian posterior)
                    C0_SR_omicron = C0_SR * omicron_val_sim  # IRP/m³/μm
                    # Apply immunocompromised emission multiplier
                    C0_SR_immune_adjusted = C0_SR_omicron * immune_emission_multiplier  # IRP/m³/μm
                    # Apply this person's exhalation filter
                    C0_SR_filtered = C0_SR_immune_adjusted * exhalation_filter  # IRP/m³/μm

                    # Long-range concentration from this person
                    # Note: For long-range, particles have time to evaporate during transport
                    # Dmax_LR=20µm corresponds to particles that evaporate to ~6µm desiccated diameter per Henriques
                    if Dv <= Dmax_LR:
                        emission_rate = C0_SR_filtered * others_BR  # IRP/h per μm
                        lam = (
                            ACH_val
                            + sedimentation_rate(Dv)
                            + viral_inactivation_rate_long(Dv, inside_temp, RH)
                        )
                        CLR = emission_rate / (lam * room_volume_val)  # Background concentration [IRP/m³/μm]
                    else:
                        CLR = 0.0

                    # Short-range concentration from this person per Henriques Eq. 2.5
                    if include_SR and Dv <= Dmax_SR:
                        CSR = CLR + (1/Sx_sim) * lambda_SR * (C0_SR_filtered - CLR)
                    else:
                        CSR = CLR  # Only background concentration if no short-range

                    # Dose from this person for this particle size
                    dose_increment = CSR * BR * dt_h * deposition_fraction(Dv) * (1 - eta_in)
                    person_dose += dose_increment * width
                
                # Add this person's dose contribution to total
                total_dose += person_dose
            
            # If not infectious: contributes 0 dose (no action needed)

        # Debug output for first simulation to check dose components
        if i == 0:
            print(f"DEBUG MC: Distance = {x_eff:.1f}m")
            print(f"DEBUG MC: Omicron transmissibility factor = {omicron_val_sim:.3f} (Bayesian sample from Du et al. 2022)")
            print(f"DEBUG MC: Individual-level sampling - {infectious_count}/{N_val} people infectious")
            print(f"DEBUG MC: First simulation total_dose = {total_dose:.6f} IRP")
            print(f"DEBUG MC: ID50 = {ID50:.1f} IRP, User BR = {BR:.3f} m³/h")
            print(f"DEBUG MC: User: {user_physical_activity}, Others: {others_physical_activity}/{others_vocal_activity}, dt_h = {dt_h:.3f}h")

        # ---- Dose-response using Protection Factor method ----
        ID63 = oneoverln2 * ID50  # baseline threshold

        # Protection Factor method – raise ID50 by Protection Factor
        # Sample protection factor from log-normal posterior
        PF_MAX = 50.0
        if immune_val <= 0:  # perfect immunity edge-case
            PF = PF_MAX
        else:
            SIGMA_PF = 0.2  # posterior σ on ln PF (20% GCV default)
            mu_ln = math.log(1.0 / immune_val)  # centre at deterministic PF
            PF = np.random.lognormal(mean=mu_ln, sigma=SIGMA_PF)
            if PF > PF_MAX:
                PF = PF_MAX
        ID63_pf = ID63 * PF
        risk_pf = 1.0 - math.exp(-total_dose / ID63_pf)

        # Store result
        all_risks_pf[i] = risk_pf
    # Summarize Monte Carlo Protection Factor method
    result["mc_mean_pf"] = float(all_risks_pf.mean())
    result["mc_pf_ci_5"] = float(np.percentile(all_risks_pf, 5))
    result["mc_pf_ci_95"] = float(np.percentile(all_risks_pf, 95))
    result["mc_pf_ci_25"] = float(np.percentile(all_risks_pf, 25))
    result["mc_pf_ci_75"] = float(np.percentile(all_risks_pf, 75))
    result["mc_pf_ci_0_5"] = float(np.percentile(all_risks_pf, 0.5))
    result["mc_pf_ci_99_5"] = float(np.percentile(all_risks_pf, 99.5))
    result["mc_pf_median"] = float(np.percentile(all_risks_pf, 50))

    print(f"DEBUG PF PERCENTILES: mean={result['mc_mean_pf']:.6f}, median={result['mc_pf_median']:.6f}")

    # --------------------------------------------------------------
    # Set risk as Monte Carlo PF result
    # --------------------------------------------------------------
    result["risk"] = result["mc_mean_pf"]  # main value consumed by UI

    # ------------------------------------------------------------------
    # Back-compat keys expected by Jinja templates
    # ------------------------------------------------------------------
    result["mc_mean"] = result["mc_mean_pf"]
    result["mc_median"] = result["mc_pf_median"]

    # Back-compat for confidence interval keys expected by templates
    result["mc_ci_5"] = result["mc_pf_ci_5"]
    result["mc_ci_95"] = result["mc_pf_ci_95"]
    result["mc_ci_25"] = result["mc_pf_ci_25"]
    result["mc_ci_75"] = result["mc_pf_ci_75"]
    result["mc_ci_0_5"] = result["mc_pf_ci_0_5"]
    result["mc_ci_99_5"] = result["mc_pf_ci_99_5"]

    # ------------------------------------------------------------------
    # Generate risk distribution data for uncertainty visualization
    # ------------------------------------------------------------------
    try:
        risk_distribution_data = generate_risk_distribution_data(all_risks_pf)
        result["risk_distribution_data"] = risk_distribution_data
        print(f"DEBUG UNCERTAINTY: Generated risk distribution data with {len(all_risks_pf)} simulations")
    except Exception as e:
        print(f"DEBUG UNCERTAINTY: Failed to generate risk distribution data: {e}")
        result["risk_distribution_data"] = None

    # Debug final values
    print(f"DEBUG RESULT: mc_pf={result['mc_mean_pf']:.6f}")
    print(
        f"DEBUG FINAL: Using f_i_val={f_i_val}, percentage_masked_val={percentage_masked_val}"
    )

    return result


if __name__ == "__main__":
    # Test the unified transmission risk calculation with default values.
    result = calculate_unified_transmission_exposure(
        "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""
    )
    if "error" in result:
        print(result["error"])
    else:
        print("Unified Airborne Transmission Risk Model Results:")
        print(f"Risk: {result['risk']*100:.2f}%")
        print(f"Effective ventilation rate (qₑ): {result['q_e']:.2f} L/s")
        print(f"Stage: {result['stage']} (Dilution factor, Sₓ: {result['Sx']:.2f})")
        print(
            f"Activity: {result['activity_label']} (Transition distance: {result['x_transition']} m)"
        )
