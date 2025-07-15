// maskFilter.js — computes inhalation & exhalation filter factors
/**
 * Compute inhalation filter factor (f_i) for the user.
 * @param {Object} params
 * @param {"Yes"|"No"} params.masked
 * @param {string} params.maskType
 * @param {string|number|null} params.fitFactor - custom fit factor (ratio), overrides lookup when provided
 * @param {Object} params.fiLookupTable - lookup table mapping maskType -> fit -> f_i
 * @returns {number} f_i in [0,1]
 */
export function computeInhalationFilter({ masked, maskType, fitFactor, fiLookupTable }) {
  let f_i = 1;
  if (masked === "Yes" && maskType) {
    // First attempt to use the lookup table based on mask type and fit
    const maskFit = document.getElementById('mask_fit').value;
    
    if (
      fiLookupTable &&
      fiLookupTable[maskType] != null &&
      maskFit != null &&
      fiLookupTable[maskType][maskFit] != null
    ) {
      f_i = fiLookupTable[maskType][maskFit];
      console.log(`Using lookup table for ${maskType} with ${maskFit} fit: f_i = ${f_i}`);
    }
    
    // Then override with custom fit factor if provided (>0)
    const ff = parseFloat(fitFactor);
    if (!isNaN(ff) && ff > 0) {
      f_i = 1 / ff;
      console.log(`Overriding with custom fit factor ${ff}: f_i = ${f_i}`);
    }
  } else {
    console.log(`Not masked or no mask type selected: f_i = ${f_i}`);
  }
  
  // Clamp between 0 and 1
  return Math.max(0, Math.min(1, f_i));
}

/**
 * Compute exhalation filter factor (f_e) and masked fraction for others.
 * @param {Object} params
 * @param {number} params.sliderValue - slider value (0-100)
 * @param {string} params.othersMaskType
 * @param {Array} params.maskTypesData - array of mask type objects with {value, f_value}
 * @returns {{ fraction: number, feValue: number }}
 */
export function computeExhalationFilter({ sliderValue, othersMaskType, maskTypesData }) {
  // Convert slider (0-100) to fraction
  let fraction = sliderValue / 100;
  fraction = Math.max(0, Math.min(1, fraction));
  
  console.log(`computeExhalationFilter: sliderValue=${sliderValue}, fraction=${fraction}`);
  console.log(`computeExhalationFilter: othersMaskType=${othersMaskType}`);

  let feValue = 1;
  if (fraction > 0 && othersMaskType) {
    const maskData = maskTypesData.find(m => m.value === othersMaskType);
    if (maskData && maskData.f_value != null) {
      feValue = maskData.f_value;
      console.log(`Found mask data for ${othersMaskType}: f_e=${feValue}`);
    } else {
      console.log(`No mask data found for ${othersMaskType}, using default f_e=1`);
    }
  } else {
    console.log(`No masks or no mask type, using default f_e=1`);
  }
  
  console.log(`Returning: fraction=${fraction}, feValue=${feValue}`);
  return { fraction, feValue };
}