// exhalation.js — pure computation for exhalation flow rate (Q0)
/**
 * Compute exhalation flow rate Q0 from multiplier.
 * @param {number} multiplier
 * @returns {number}
 */
export function computeExhalationFlowRate(multiplier) {
  return 0.08 * multiplier;
}

/**
 * Safely lookup multiplier from a nested multipliers table.
 * @param {Object} multipliers - nested object multipliers[physical][vocal]
 * @param {string} physical
 * @param {string} vocal
 * @returns {number}
 */
export function getMultiplier(multipliers, physical, vocal) {
  if (
    multipliers &&
    multipliers[physical] != null &&
    multipliers[physical][vocal] != null
  ) {
    return multipliers[physical][vocal];
  }
  return 1;
}