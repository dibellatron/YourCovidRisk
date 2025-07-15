// environment.js — compute room/car/airplane/outdoors volume and ACH values
/**
 * Compute the effective volume for the event space.
 * @param {Object} params
 * @param {string} params.indoorOutdoor - "Indoors" or "Outdoors" or other
 * @param {string} params.achValue - selected ACH value (string)
 * @param {string} params.carType - selected car type value
 * @param {string} params.airplaneType - selected airplane type value
 * @param {string} params.customVolume - user-entered custom volume (string)
 * @param {Object} params.covidRiskData - data definitions from data.js
 * @param {boolean} params.advancedEnabled - whether advanced settings are enabled
 * @param {string} params.distanceFeet - distance to other people in feet (for outdoor volume calculation)
 * @returns {number} effective volume in cubic meters
 */
export function computeVolume({ indoorOutdoor, achValue, carType, airplaneType, customVolume, covidRiskData, advancedEnabled = false, distanceFeet = "6" }) {
  // 1. Custom room volume override (only if advanced settings enabled)
  if (advancedEnabled) {
    const cv = parseFloat(customVolume);
    if (!isNaN(cv) && cv > 0) {
      return cv;
    }
  }
  // 2. Outdoors: calculate volume based on distance (x² × 2m height)
  if (indoorOutdoor === "Outdoors") {
    const distanceMeters = parseFloat(distanceFeet) * 0.3048; // Convert feet to meters
    const areaSquareMeters = distanceMeters * distanceMeters; // x²
    const volumeCubicMeters = areaSquareMeters * 2; // x² × 2m height
    return volumeCubicMeters;
  }
  // 3. Car-specific
  if (indoorOutdoor === "Indoors" && covidRiskData.carAchValues.includes(achValue)) {
    const car = covidRiskData.carTypes.find(c => c.value === carType);
    if (car && car.volume != null) {
      return car.volume;
    }
  }
  // 4. Airplane-specific
  if (indoorOutdoor === "Indoors" && covidRiskData.airplaneAchValues.includes(achValue)) {
    const plane = covidRiskData.airplaneTypes.find(p => p.value === airplaneType);
    if (plane && plane.volume != null) {
      return plane.volume;
    }
  }
  // 5. Generic indoor environments
  for (const group of covidRiskData.environments || []) {
    for (const opt of group.options || []) {
      if (opt.value === achValue && opt.volume != null) {
        return opt.volume;
      }
    }
  }
  // 6. Fallback
  return 0;
}

/**
 * Compute the effective ACH (air changes per hour) for the event space.
 * @param {Object} params
 * @param {string} params.indoorOutdoor - "Indoors" or "Outdoors"
 * @param {string} params.achValue - selected ACH value (string)
 * @param {string} params.customACH - user-entered custom ACH (string)
 * @returns {number} effective ACH
 */
export function computeACH({ indoorOutdoor, achValue, customACH }) {
  // Custom override
  const ca = parseFloat(customACH);
  if (!isNaN(ca) && ca > 0) {
    return ca;
  }
  // Outdoors: very high ACH
  if (indoorOutdoor === "Outdoors") {
    return 1600;
  }
  // Default: parse selected ACH
  const av = parseFloat(achValue);
  return isNaN(av) ? 0 : av;
}
