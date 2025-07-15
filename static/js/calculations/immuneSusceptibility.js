// immuneSusceptibility.js — pure computation of immune susceptibility
// Updated to use Chemaitelly et al. (2025) hierarchical Bayesian exponential decay model

// Exponential decay parameters: P(t) = P0 * exp(-λt)
const PROTECTION_PARAMS = {
  // Infection-derived protection (Chemaitelly model)
  infection_unvaccinated: {
    P0: 0.85,      // Initial protection
    lambda: 0.12   // Decay rate (1/months)
  },
  infection_vaccinated: {
    P0: 0.95,      // Initial protection
    lambda: 0.18   // Decay rate (1/months)
  },
  // Vaccination-only protection
  vaccination_immunocompetent: {
    P0: 0.40,      // Initial protection
    lambda: 0.23   // Decay rate (1/months)
  },
  vaccination_immunocompromised: {
    P0: 0.25,      // Initial protection
    lambda: 0.30   // Decay rate (1/months)
  }
};

/**
 * Calculate reinfection protection using Chemaitelly exponential decay model
 * @param {number} monthsSinceInfection - Months since infection
 * @param {boolean} vaccinationStatus - True if vaccinated, false if unvaccinated
 * @returns {number} Protection factor (0 = no protection, 1 = perfect protection)
 */
function calculateReinfectionProtection(monthsSinceInfection, vaccinationStatus) {
  // No protection if beyond 12 months
  if (monthsSinceInfection > 12) {
    return 0.0;
  }
  
  // Select appropriate parameters based on vaccination status
  const params = vaccinationStatus ? PROTECTION_PARAMS.infection_vaccinated : PROTECTION_PARAMS.infection_unvaccinated;
  
  // Calculate protection using exponential decay
  const protection = params.P0 * Math.exp(-params.lambda * monthsSinceInfection);
  return Math.max(0.0, Math.min(1.0, protection));
}

/**
 * Calculate vaccination-only protection using exponential decay model
 * @param {number} monthsSinceVaccination - Months since vaccination
 * @param {boolean} isImmunocompromised - True if immunocompromised, false if immunocompetent
 * @returns {number} Protection factor (0 = no protection, 1 = perfect protection)
 */
function calculateVaccinationProtection(monthsSinceVaccination, isImmunocompromised) {
  // No protection if beyond 12 months
  if (monthsSinceVaccination > 12) {
    return 0.0;
  }
  
  // Select appropriate parameters based on immune status
  const params = isImmunocompromised ? PROTECTION_PARAMS.vaccination_immunocompromised : PROTECTION_PARAMS.vaccination_immunocompetent;
  
  // Calculate protection using exponential decay
  const protection = params.P0 * Math.exp(-params.lambda * monthsSinceVaccination);
  return Math.max(0.0, Math.min(1.0, protection));
}

/**
 * Legacy vaccination-only protection calculation
 * @param {number} vaccinationMonths - Months since vaccination
 * @returns {number} Protection factor (0 = no protection, 1 = perfect protection)
 */
function calculateVaccinationOnlyProtection(vaccinationMonths) {
  // Legacy formula for vaccination-only scenarios
  let vaccinationImmune = 1 - (52.37 - 0.6 * vaccinationMonths * 4.34524) / 100;
  return Math.max(0, Math.min(1, vaccinationImmune));
}

/**
 * Get immunocompromised status from form
 * @returns {boolean} True if immunocompromised (moderate or severe), false if immunocompetent
 */
function getImmunocompromisedStatusBoolean() {
  const immunocompromised = document.getElementById('immunocompromised')?.value;
  const severity = document.getElementById('immunocompromised_severity')?.value;
  const reconsider = document.getElementById('immunocompromised_reconsider')?.value;

  console.log('DEBUG: getImmunocompromisedStatusBoolean called');
  console.log('  immunocompromised field value:', immunocompromised);
  console.log('  severity field value:', severity);
  console.log('  reconsider field value:', reconsider);

  // Handle progressive disclosure logic
  if (immunocompromised === 'unsure' && reconsider === 'Yes') {
    console.log('  returning TRUE (unsure + reconsider Yes)');
    return true;  // Assume immunocompromised if unsure but reconsidering
  } else if (immunocompromised === 'unsure' && reconsider === 'No') {
    console.log('  returning FALSE (unsure + reconsider No)');
    return false;  // Assume immunocompetent if unsure but not reconsidering
  } else if (immunocompromised === 'Yes') {
    console.log('  returning TRUE (immunocompromised = Yes)');
    return true;  // Return true for any "Yes" selection, regardless of severity
  }
  
  console.log('  returning FALSE (default)');
  return false;  // Default to immunocompetent
}

/**
 * Compute immune susceptibility value based on vaccination and infection recency.
 * Now uses Chemaitelly et al. (2025) model for infection-based protection and 
 * new exponential decay model for vaccination-only protection.
 *
 * @param {Object} params
 * @param {"Yes"|"No"} params.recentVaccination
 * @param {number|null} params.vaccinationMonths
 * @param {"Yes"|"No"} params.recentInfection
 * @param {number|null} params.infectionMonths
 * @returns {number} Immune susceptibility in [0,1]
 */
export function computeImmuneValue({ recentVaccination, vaccinationMonths, recentInfection, infectionMonths }) {
  console.log('DEBUG: computeImmuneValue called with:', { recentVaccination, vaccinationMonths, recentInfection, infectionMonths });
  
  // Check if we have recent infection data
  const hasRecentInfection = recentInfection === "Yes" && infectionMonths != null && !isNaN(infectionMonths);
  const hasRecentVaccination = recentVaccination === "Yes" && vaccinationMonths != null && !isNaN(vaccinationMonths);
  
  console.log('DEBUG: hasRecentInfection:', hasRecentInfection, 'hasRecentVaccination:', hasRecentVaccination);
  
  // Use Chemaitelly model for infection-based protection (takes precedence)
  if (hasRecentInfection) {
    console.log('DEBUG: Using Chemaitelly infection model (ignores immunocompromised status)');
    const protection = calculateReinfectionProtection(infectionMonths, hasRecentVaccination);
    const result = 1.0 - protection;
    console.log('DEBUG: Infection model result - protection:', protection, 'immune_val:', result);
    return result;  // Convert protection to susceptibility
  }
  
  // For vaccination-only scenarios, use new vaccination protection model
  if (hasRecentVaccination) {
    console.log('DEBUG: Using vaccination-only model (considers immunocompromised status)');
    const isImmunocompromised = getImmunocompromisedStatusBoolean();
    console.log('DEBUG: isImmunocompromised result:', isImmunocompromised);
    const protection = calculateVaccinationProtection(vaccinationMonths, isImmunocompromised);
    const result = 1.0 - protection;
    console.log('DEBUG: Vaccination model result - protection:', protection, 'immune_val:', result);
    return result;  // Convert protection to susceptibility
  }
  
  console.log('DEBUG: No recent vaccination or infection, returning 1.0');
  // No recent vaccination or infection
  return 1.0;  // Fully susceptible
}