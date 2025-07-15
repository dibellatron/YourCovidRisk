/**
 * Risk color scale utility
 * Provides consistent color coding for risk values across the application
 */

/**
 * Get the appropriate color for a risk value
 * 
 * @param {number} riskValue - Risk value between 0-1 (0-100%)
 * @return {string} Hex color code for the risk level
 */
function getRiskColor(riskValue) {
  if (typeof riskValue !== 'number' || isNaN(riskValue)) {
    return '#334155'; // default slate color for invalid values
  }
  
  // Always use color scale even for extreme values
  // First clamp to 0-1 range for calculations
  const risk = Math.max(0, Math.min(1, riskValue));
  
  // Gradual color scale
  if (risk < 0.05) {
    return '#10b981'; // deep green
  } else if (risk < 0.1) {
    return '#34d399'; // medium green
  } else if (risk < 0.2) {
    return '#6ee7b7'; // light green
  } else if (risk < 0.3) {
    return '#fb923c'; // light orange
  } else if (risk < 0.4) {
    return '#f97316'; // medium orange
  } else if (risk < 0.5) {
    return '#ea580c'; // darker orange
  } else if (risk < 0.6) {
    return '#f87171'; // light red
  } else if (risk < 0.7) {
    return '#ef4444'; // medium red
  } else if (risk < 0.8) {
    return '#dc2626'; // darker red
  } else if (risk < 0.9) {
    return '#b91c1c'; // deep red
  } else {
    return '#991b1b'; // very deep red
  }
}

// Export the function if using modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { getRiskColor };
}