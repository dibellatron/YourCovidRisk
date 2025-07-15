/**
 * Repeated exposure risk calculation module
 * Handles both threshold calculation and interactive risk estimation
 */

/**
 * Calculate repetitions needed for infection risk to exceed 50%
 * Treating each exposure as an independent trial
 *
 * @param {number} singleExposureRisk - Risk of infection from a single exposure (between 0-1)
 * @return {number} Number of repetitions needed for >50% cumulative risk (integer)
 */
function calculateRepeatedExposureRisk(singleExposureRisk) {
  // Validate input
  if (typeof singleExposureRisk !== 'number' || singleExposureRisk <= 0 || singleExposureRisk >= 1) {
    return null; // Invalid input
  }

  // Formula: Find N where 1 - (1 - p)^N > 0.5
  // Solve for N: N > log(0.5) / log(1 - p)
  const repeats = Math.ceil(Math.log(0.5) / Math.log(1 - singleExposureRisk));

  return repeats;
}

/**
 * Calculate cumulative risk after multiple exposures
 *
 * @param {number} singleExposureRisk - Risk from a single exposure (0-1)
 * @param {number} repetitions - Number of times the exposure is repeated
 * @return {number} Cumulative risk (0-1)
 */
function calculateCumulativeRisk(singleExposureRisk, repetitions) {
  // Validate inputs
  if (typeof singleExposureRisk !== 'number' || singleExposureRisk < 0 || singleExposureRisk > 1) {
    return null;
  }

  if (typeof repetitions !== 'number' || repetitions <= 0) {
    return null;
  }

  // Formula: 1 - (1 - p)^n
  return 1 - Math.pow(1 - singleExposureRisk, repetitions);
}

/**
 * Collect all calculation parameters from the current form state
 * @return {Object} Complete calculation parameters object
 */
function collectAllCalculationParams() {
  const params = {};

  // Basic parameters
  params.C0 = document.getElementById('C0')?.value || '0.065';
  params.Q0 = document.getElementById('Q0')?.value || '0.08';
  params.p = document.getElementById('p')?.value || '0.08';
  params.delta_t = document.getElementById('delta_t')?.value || '42';
  params.x = document.getElementById('x')?.value || '0.7';
  params.gamma = document.getElementById('gamma')?.value || '0.7';
  params.f_e = document.getElementById('f_e')?.value || '1';
  params.f_i = document.getElementById('f_i')?.value || '1';
  params.omicron = document.getElementById('omicron')?.value || '3.3';
  params.immune = document.getElementById('immune')?.value || '1';
  params.N = document.getElementById('N')?.value || '1';
  params.percentage_masked = document.getElementById('percentage_masked')?.value || '0';

  // Activity parameters
  params.user_physical_activity = getUserPhysicalActivity();
  params.others_physical_activity = getOthersPhysicalActivity();
  params.others_vocal_activity = getOthersVocalActivity();

  // Environment parameters
  params.ACH = document.getElementById('ACH')?.value || '1';
  params.room_volume = getRoomVolume();

  // Immunity parameters
  params.recent_vaccination = document.querySelector('select[name="recent_vaccination"]')?.value || 'No';
  params.vaccination_time = document.querySelector('input[name="vaccination_time"]')?.value || '';
  params.recent_infection = document.querySelector('select[name="recent_infection"]')?.value || 'No';
  params.infection_time = document.querySelector('input[name="infection_time"]')?.value || '';

  // Immunocompromised status
  params.immunocompromised_status = getImmunocompromisedStatus();

  // Advanced parameters (only if advanced mode is enabled)
  const advancedEnabled = document.getElementById('advanced')?.value === 'true';
  if (advancedEnabled) {
    // Environmental overrides
    const customACH = document.getElementById('custom_ACH')?.value;
    if (customACH) params.ACH = customACH;

    const customVolume = document.getElementById('room_volume')?.value;
    if (customVolume) params.room_volume = customVolume;

    const customPrevalence = document.getElementById('covid_prevalence')?.value;
    if (customPrevalence) params.covid_prevalence = customPrevalence;

    // Environmental conditions
    const relativeHumidity = document.getElementById('relative_humidity')?.value;
    if (relativeHumidity) params.RH = parseFloat(relativeHumidity) / 100.0; // Convert % to fraction

    const temperature = document.getElementById('temperature')?.value;
    const tempUnit = document.getElementById('temperature_unit')?.value || 'C';
    if (temperature) {
      let tempC = parseFloat(temperature);
      if (tempUnit === 'F') {
        tempC = (tempC - 32.0) * 5.0 / 9.0; // Convert F to C
      }
      params.inside_temp = tempC + 273.15; // Convert C to Kelvin
    }

    const co2 = document.getElementById('co2')?.value;
    if (co2) params.CO2 = parseFloat(co2);
  }

  return params;
}

/**
 * Helper functions to extract activity parameters
 */
function getUserPhysicalActivity() {
  const activityIndex = parseInt(document.getElementById('activity_level_index')?.value || '1');
  const activityMap = ["sitting", "standing", "light", "moderate", "heavy"];
  return activityMap[Math.min(activityIndex, 4)];
}

function getOthersPhysicalActivity() {
  const activityIndex = parseInt(document.getElementById('physical_intensity_index')?.value || '1');
  const activityMap = ["sitting", "standing", "light", "moderate", "heavy"];
  return activityMap[Math.min(activityIndex, 4)];
}

function getOthersVocalActivity() {
  const vocalizationIndex = parseInt(document.getElementById('vocalization_index')?.value || '1');
  const vocalMap = ["breathing", "speaking", "loudly_speaking"];
  return vocalMap[Math.min(vocalizationIndex, 2)];
}

function getRoomVolume() {
  // Check for environment-specific volume first
  const environmentVolume = document.getElementById('environment_volume')?.value;
  if (environmentVolume) return environmentVolume;

  // Check for custom volume
  const customVolume = document.getElementById('room_volume')?.value;
  if (customVolume) return customVolume;

  // Fallback to default
  return '1000';
}

function getImmunocompromisedStatus() {
  const immunocompromised = document.getElementById('immunocompromised')?.value;
  const severity = document.getElementById('immunocompromised_severity')?.value;
  const reconsider = document.getElementById('immunocompromised_reconsider')?.value;

  // Handle progressive disclosure logic
  if (immunocompromised === 'unsure' && reconsider === 'Yes') {
    return severity || 'moderate';
  } else if (immunocompromised === 'unsure' && reconsider === 'No') {
    return 'normal';
  } else if (immunocompromised === 'Yes' && severity) {
    return severity;
  } else if (immunocompromised === 'unsure') {
    return 'unsure'; // Will trigger dual calculation
  }

  return 'normal';
}

/**
 * Calculate time-varying cumulative risk using backend API
 *
 * @param {number} baseRisk - Base single exposure risk
 * @param {number} basePrevalence - Base prevalence used in calculation
 * @param {number} repetitions - Number of exposures (daily if daily=true)
 * @param {string} region - Geographic region
 * @param {Object} [calculationParams=null] - Parameters from original calculation for proper recalculation
 * @return {Promise<Object>} Promise resolving to risk calculation result
 */
async function calculateTimeVaryingCumulativeRisk(baseRisk, basePrevalence, repetitions, region = 'National', calculationParams = null) {
  console.log('Interactive calculator API call:', {
    base_risk: baseRisk,
    base_prevalence: basePrevalence,
    num_exposures: repetitions,
    region: region,
    daily: true
  });

  try {
    const payload = {
      base_risk: baseRisk,
      base_prevalence: basePrevalence,
      num_exposures: repetitions,
      region: region,
      // start_week will default to current week in backend
      daily: true    // use daily exposures rather than weekly
    };
    
    // Collect complete calculation parameters from current form state
    const allCalculationParams = collectAllCalculationParams();
    
    // DEBUG: Log complete parameters
    console.log('=== REPEATED EXPOSURE DEBUG ===');
    console.log('Advanced mode enabled:', document.getElementById('advanced')?.value === 'true');
    console.log('Complete calculation params:', allCalculationParams);
    console.log('Environmental params:', {
      RH: allCalculationParams.RH,
      CO2: allCalculationParams.CO2,
      inside_temp: allCalculationParams.inside_temp
    });
    
    // Use complete calculation parameters
    payload.calculation_params = allCalculationParams;
    
    const response = await fetch('/api/time-varying-risk', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.warn('Failed to calculate time-varying risk:', error);
    // Fallback to constant prevalence calculation
    return {
      time_varying_risk: calculateCumulativeRisk(baseRisk, repetitions),
      threshold: calculateRepeatedExposureRisk(baseRisk),
      current_week: null,
      error: error.message
    };
  }
}
// ------------------------------------------------------------------
// Format a probability (0..1) as a percentage string with variable precision,
// matching the server-side format_percent logic.
// ------------------------------------------------------------------
function formatPercent(p) {
  const percent = p * 100;
  if (percent >= 99.999999) {
    return '> 99.999999%';
  }
  if (percent >= 99.99999) {
    return percent.toFixed(6) + '%';
  }
  if (percent >= 99.9999) {
    return percent.toFixed(5) + '%';
  }
  if (percent >= 99.999) {
    return percent.toFixed(4) + '%';
  }
  if (percent >= 99.99) {
    return percent.toFixed(3) + '%';
  }
  if (percent >= 99.9) {
    return percent.toFixed(2) + '%';
  }
  if (percent >= 0.1) {
    return percent.toFixed(1) + '%';
  }
  if (percent >= 0.01) {
    return percent.toFixed(2) + '%';
  }
  if (percent >= 0.001) {
    return percent.toFixed(3) + '%';
  }
  if (percent >= 0.0001) {
    return percent.toFixed(4) + '%';
  }
  if (percent >= 0.00001) {
    return percent.toFixed(5) + '%';
  }
  if (percent >= 0.000001) {
    return percent.toFixed(6) + '%';
  }
  if (percent >= 0.0000001) {
    return percent.toFixed(7) + '%';
  }
  return '< 0.0000001%';
}

/**
 * Initialize the interactive repeated exposure calculator
 *
 * @param {number} baseRisk - The single exposure risk
 * @param {string} containerId - ID of container to add calculator to
 * @param {number} basePrevalence - The base prevalence used in the original calculation (as proportion)
 * @param {string} region - Geographic region for prevalence data
 * @param {Object} calculationParams - Parameters from original calculation for proper recalculation
 */
function initRepeatedExposureCalculator(baseRisk, containerId, basePrevalence = 0.01, region = 'National', calculationParams = null) {
  const container = document.getElementById(containerId);
  if (!container || typeof baseRisk !== 'number') return;

  // Create calculator toggle button with more prominent styling
  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'exploreRepeatedBtn';
  toggleBtn.className = 'primary-btn';
  toggleBtn.style.fontSize = '16px';
  toggleBtn.style.fontWeight = '600';
  toggleBtn.style.padding = '12px 20px';
  toggleBtn.style.marginTop = '15px';
  toggleBtn.style.borderRadius = '8px';
  toggleBtn.style.cursor = 'pointer';
  toggleBtn.style.backgroundColor = '#3b82f6';
  toggleBtn.style.color = '#ffffff';
  toggleBtn.style.border = 'none';
  toggleBtn.style.boxShadow = '0 2px 4px rgba(59, 130, 246, 0.3)';
  toggleBtn.style.transition = 'all 0.2s ease';
  toggleBtn.innerHTML = '<i class="fas fa-chart-line"></i> Explore repeated exposures';
  
  // Add hover effects
  toggleBtn.addEventListener('mouseenter', function() {
    this.style.backgroundColor = '#2563eb';
    this.style.boxShadow = '0 4px 8px rgba(59, 130, 246, 0.4)';
  });
  
  toggleBtn.addEventListener('mouseleave', function() {
    this.style.backgroundColor = '#3b82f6';
    this.style.boxShadow = '0 2px 4px rgba(59, 130, 246, 0.3)';
  });
  
  container.appendChild(toggleBtn);

  // Create calculator container (hidden initially)
  const calcContainer = document.createElement('div');
  calcContainer.id = 'repeatedCalculator';
  calcContainer.style.display = 'none';
  calcContainer.style.backgroundColor = '#f8f9fa';
  calcContainer.style.borderRadius = '8px';
  calcContainer.style.padding = '15px';
  calcContainer.style.marginTop = '10px';
  calcContainer.style.borderLeft = '3px solid #3b82f6';
  container.appendChild(calcContainer);

  // Build calculator content
  calcContainer.innerHTML = `
    <div style="margin-bottom: 15px;">
      <div style="font-weight: 600; margin-bottom: 5px;">What if you repeat this exposure?</div>
      <div style="font-size: 14px; color: #666; margin-bottom: 10px;">
        Select an exposure pattern to see how cumulative risk changes with repeated exposures over time.
      </div>
    </div>

    <div style="margin-bottom: 15px;">
      <div style="font-weight: 600; margin-bottom: 8px;">Choose exposure pattern:</div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
        <button class="repeat-preset" data-value="12">Monthly for a year (12×)</button>
        <button class="repeat-preset" data-value="52">Weekly for a year (52×)</button>
        <button class="repeat-preset" data-value="250">Every workday for a year (250×)</button>
        <button class="repeat-preset" data-value="365">Daily for a year (365×)</button>
      </div>
      
      <details style="margin-top: 10px;">
        <summary style="cursor: pointer; font-size: 14px; color: #666;">Daily exposures for shorter periods</summary>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; padding: 8px; background-color: #f8f9fa; border-radius: 4px;">
          <button class="repeat-preset" data-value="5">5 days</button>
          <button class="repeat-preset" data-value="10">10 days</button>
          <button class="repeat-preset" data-value="30">30 days</button>
          <button class="repeat-preset" data-value="90">90 days</button>
        </div>
      </details>
    </div>

    <!-- Time-varying risk result -->
    <div style="background-color: white; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
      <div style="font-size: 15px; line-height: 1.4;">
        <span id="repeatedResultText">If you were to repeat this exposure on 5 consecutive days, your risk of getting Covid would be: </span><span id="timeVaryingRisk" style="font-weight: 600; font-size: 16px;">...</span>
        <span id="loadingIndicator" style="color: #666; font-size: 12px; margin-left: 5px;">calculating...</span>
      </div>
    </div>

    <!-- Table container hidden but code preserved for future use -->
    <div id="dailySequenceContainer" style="display: none; margin-top:10px; max-height:200px; overflow:auto;"></div>
  `;

  // Style preset buttons
  document.querySelectorAll('.repeat-preset').forEach(button => {
    button.style.backgroundColor = '#e5e7eb';
    button.style.border = 'none';
    button.style.borderRadius = '4px';
    button.style.padding = '5px 10px';
    button.style.cursor = 'pointer';
    button.style.fontSize = '14px';
    button.style.transition = 'all 0.2s ease';

    // Add hover effect
    button.addEventListener('mouseenter', function() {
      if (this.style.backgroundColor !== 'rgb(79, 70, 229)') { // Not already selected
        this.style.backgroundColor = '#d1d5db';
      } else {
        // Already selected - just add deeper shadow
        this.style.boxShadow = '0 4px 6px rgba(0,0,0,0.25)';
      }
    });

    button.addEventListener('mouseleave', function() {
      if (this.style.backgroundColor !== 'rgb(79, 70, 229)') { // Not selected
        this.style.backgroundColor = '#e5e7eb';
      } else {
        // Return to normal selected shadow
        this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
      }
    });
  });

  // Check for saved preset value within this session only
  const savedPreset = sessionStorage.getItem('repeatedExposurePreset');
  const initialPreset = savedPreset ? parseInt(savedPreset) : 12;
  updateCalculatorDisplay(baseRisk, initialPreset, basePrevalence, region, calculationParams);

  // Set initial button state for the selected value
  document.querySelectorAll('.repeat-preset').forEach(btn => {
    if (parseInt(btn.dataset.value) === initialPreset) {
      btn.style.backgroundColor = '#4f46e5';
      btn.style.color = '#fff';
      btn.style.fontWeight = 'bold';
      btn.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
    }
  });

  // Check for saved visibility state within this session only
  const savedVisibility = sessionStorage.getItem('repeatedExposureVisible');
  if (savedVisibility === 'true') {
    calcContainer.style.display = 'block';
    toggleBtn.innerHTML = '<i class="fas fa-times"></i> Hide repeated exposures';
  }

  // Set up event listeners
  toggleBtn.addEventListener('click', function() {
    if (calcContainer.style.display === 'none') {
      calcContainer.style.display = 'block';
      toggleBtn.innerHTML = '<i class="fas fa-times"></i> Hide repeated exposures';
      sessionStorage.setItem('repeatedExposureVisible', 'true');
    } else {
      calcContainer.style.display = 'none';
      toggleBtn.innerHTML = '<i class="fas fa-chart-line"></i> Explore repeated exposures';
      sessionStorage.setItem('repeatedExposureVisible', 'false');
    }
  });

  // Slider removed - using preset buttons only

  document.querySelectorAll('.repeat-preset').forEach(button => {
    button.addEventListener('click', function() {
      // Clear selected class from all buttons
      document.querySelectorAll('.repeat-preset').forEach(btn => {
        btn.style.backgroundColor = '#e5e7eb';
        btn.style.color = '#000';
        btn.style.fontWeight = 'normal';
        btn.style.boxShadow = 'none';
      });

      // Highlight the selected button
      this.style.backgroundColor = '#4f46e5'; // Using primary color from variables
      this.style.color = '#fff';
      this.style.fontWeight = 'bold';
      this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';

      const value = parseInt(this.dataset.value);
      // Save the selected preset value for this session only
      sessionStorage.setItem('repeatedExposurePreset', value.toString());
      updateCalculatorDisplay(baseRisk, value, basePrevalence, region, calculationParams);
    });
  });
}

/**
 * Update the calculator display with risk values for both methods
 *
 * @param {number} baseRisk - Single exposure risk
 * @param {number} count - Number of exposures
 * @param {number} basePrevalence - Base prevalence used in calculation
 * @param {string} region - Geographic region for time-varying calculation
 * @param {Object} calculationParams - Parameters from original calculation for proper recalculation
 */
async function updateCalculatorDisplay(baseRisk, count, basePrevalence = 0.01, region = 'National', calculationParams = null) {
  const resultText = document.getElementById('repeatedResultText');
  const timeVaryingRiskSpan = document.getElementById('timeVaryingRisk');
  const loadingIndicator = document.getElementById('loadingIndicator');

  if (!resultText || !timeVaryingRiskSpan) return;

  // Update result text based on pattern
  let displayText;
  if (count === 12) {
    displayText = 'If you had this same kind of exposure <strong>once a month for the next year</strong>, your risk of getting Covid would be: ';
  } else if (count === 52) {
    displayText = 'If you had this same kind of exposure <strong>once a week for the next year</strong>, your risk of getting Covid would be: ';
  } else if (count === 250) {
    displayText = 'If you had this same kind of exposure <strong>every workday for the next year</strong>, your risk of getting Covid would be: ';
  } else if (count === 365) {
    displayText = 'If you had this same kind of exposure <strong>every day for the next year</strong>, your risk of getting Covid would be: ';
  } else {
    displayText = `If you had this same kind of exposure <strong>every day for the next ${count} days</strong>, your risk of getting Covid would be: `;
  }
  resultText.innerHTML = displayText;

  // Update button highlights based on slider value
  document.querySelectorAll('.repeat-preset').forEach(btn => {
    const btnValue = parseInt(btn.dataset.value);
    if (btnValue === count) {
      // Highlight the matching button
      btn.style.backgroundColor = '#4f46e5';
      btn.style.color = '#fff';
      btn.style.fontWeight = 'bold';
      btn.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
    } else {
      // Reset other buttons
      btn.style.backgroundColor = '#e5e7eb';
      btn.style.color = '#000';
      btn.style.fontWeight = 'normal';
      btn.style.boxShadow = 'none';
    }
  });

  // Calculate time-varying risk (async)
  if (loadingIndicator) {
    loadingIndicator.style.display = 'inline';
    loadingIndicator.textContent = 'calculating...';
  }

  try {
    const timeVaryingResult = await calculateTimeVaryingCumulativeRisk(
      baseRisk, basePrevalence, count, region, calculationParams
    );

    if (loadingIndicator) {
      loadingIndicator.style.display = 'none';
    }

    if (timeVaryingResult && typeof timeVaryingResult.time_varying_risk === 'number') {
      const timeVaryingRisk = timeVaryingResult.time_varying_risk;
      const formattedTimeVaryingRisk = formatPercent(timeVaryingRisk);
      const timeVaryingRiskColor = getRiskColor(timeVaryingRisk);

      timeVaryingRiskSpan.textContent = formattedTimeVaryingRisk;
      timeVaryingRiskSpan.style.color = timeVaryingRiskColor;
    } else {
      timeVaryingRiskSpan.textContent = 'Error calculating';
      timeVaryingRiskSpan.style.color = '#666';
    }

    // Render exposure prevalence & cumulative risk if available
    const seqContainer = document.getElementById('dailySequenceContainer');
    if (seqContainer) {
      if (Array.isArray(timeVaryingResult.daily_sequence)) {
        const seq = timeVaryingResult.daily_sequence;
        
        // Determine exposure pattern and labels based on count
        let exposureLabel, riskLabel, pattern;
        if (count === 12) {
          pattern = 'monthly';
          exposureLabel = 'Month';
          riskLabel = 'Monthly Risk';
        } else if (count === 52) {
          pattern = 'weekly';
          exposureLabel = 'Week';
          riskLabel = 'Weekly Risk';
        } else if (count === 250) {
          pattern = 'workday';
          exposureLabel = 'Work Week';
          riskLabel = 'Daily Risk';
        } else {
          pattern = 'daily';
          exposureLabel = count > 30 ? 'Week' : 'Day';
          riskLabel = count > 30 ? 'Weekly Risk' : 'Daily Risk';
        }
        
        if (pattern === 'monthly' || pattern === 'weekly') {
          // Show each exposure individually for monthly/weekly patterns
          let html = '<table style="width:100%;border-collapse:collapse;">'
                   + '<thead><tr>'
                   + `<th style="border:1px solid #ddd;padding:4px;">Exposure</th>`
                   + `<th style="border:1px solid #ddd;padding:4px;">Prevalence Week</th>`
                   + '<th style="border:1px solid #ddd;padding:4px;">Prevalence</th>'
                   + `<th style="border:1px solid #ddd;padding:4px;">${riskLabel}</th>`
                   + '<th style="border:1px solid #ddd;padding:4px;">Cumulative Risk</th>'
                   + '</tr></thead><tbody>';
          
          seq.forEach((item, index) => {
            // Calculate which week number this exposure is using
            let weekNum;
            const currentWeek = timeVaryingResult.current_week || 22; // Use actual current week from API
            if (pattern === 'weekly') {
              weekNum = ((currentWeek - 1 + index) % 52) + 1;
            } else { // monthly
              weekNum = ((currentWeek - 1 + Math.floor(index * 4.25)) % 52) + 1;
            }
            
            html += '<tr>'
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${index + 1}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">Week ${weekNum}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${(item.prevalence*100).toFixed(2)}%</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(item.daily_risk)}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(item.cumulative_risk)}</td>`
                 + '</tr>';
          });
          html += '</tbody></table>';
          seqContainer.innerHTML = html;
        } else if (pattern === 'workday') {
          // Show work weeks (every 5 days) for workday pattern
          let html = '<table style="width:100%;border-collapse:collapse;">'
                   + '<thead><tr>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Work Week</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Days</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Prevalence Week</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Prevalence</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Daily Risk</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Cumulative Risk</th>'
                   + '</tr></thead><tbody>';
          
          // Group by work weeks (every 5 days)
          for (let workWeekStart = 0; workWeekStart < seq.length; workWeekStart += 5) {
            const workWeekEnd = Math.min(workWeekStart + 4, seq.length - 1);
            const workWeekNum = Math.floor(workWeekStart / 5) + 1;
            const firstDay = seq[workWeekStart];
            const lastDay = seq[workWeekEnd];
            const dayRange = workWeekStart === workWeekEnd ? `${firstDay.day}` : `${firstDay.day}-${lastDay.day}`;
            
            // Calculate which prevalence week this work week is using
            const workWeek = Math.floor(workWeekStart / 5);
            let weekOffset = workWeek;
            if (workWeek >= 29) weekOffset += 2; // Skip weeks 51-52
            const currentWeek = timeVaryingResult.current_week || 22; // Use actual current week from API
            const prevWeekNum = ((currentWeek - 1 + weekOffset) % 52) + 1;
            
            html += '<tr>'
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${workWeekNum}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${dayRange}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">Week ${prevWeekNum}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${(firstDay.prevalence*100).toFixed(2)}%</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(firstDay.daily_risk)}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(lastDay.cumulative_risk)}</td>`
                 + '</tr>';
          }
          html += '</tbody></table>';
          seqContainer.innerHTML = html;
        } else if (count > 30) {
          // For long daily patterns, group by weeks and show weekly summary
          let html = '<table style="width:100%;border-collapse:collapse;">'
                   + '<thead><tr>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Week</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Days</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Prevalence</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Daily Risk</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Cumulative Risk</th>'
                   + '</tr></thead><tbody>';
          
          // Group by weeks (every 7 days)
          for (let weekStart = 0; weekStart < seq.length; weekStart += 7) {
            const weekEnd = Math.min(weekStart + 6, seq.length - 1);
            const weekNum = Math.floor(weekStart / 7) + 1;
            const firstDay = seq[weekStart];
            const lastDay = seq[weekEnd];
            const dayRange = weekStart === weekEnd ? `${firstDay.day}` : `${firstDay.day}-${lastDay.day}`;
            
            html += '<tr>'
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${weekNum}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${dayRange}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${(firstDay.prevalence*100).toFixed(2)}%</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(firstDay.daily_risk)}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(lastDay.cumulative_risk)}</td>`
                 + '</tr>';
          }
          html += '</tbody></table>';
          seqContainer.innerHTML = html;
        } else {
          // For shorter timeframes, show daily details as before
          let html = '<table style="width:100%;border-collapse:collapse;">'
                   + '<thead><tr>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Day</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Prevalence</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Daily Risk</th>'
                   + '<th style="border:1px solid #ddd;padding:4px;">Cumulative Risk</th>'
                   + '</tr></thead><tbody>';
          seq.forEach(item => {
            html += '<tr>'
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${item.day}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${(item.prevalence*100).toFixed(2)}%</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(item.daily_risk)}</td>`
                 + `<td style="border:1px solid #eee;padding:4px;text-align:center;">${formatPercent(item.cumulative_risk)}</td>`
                 + '</tr>';
          });
          html += '</tbody></table>';
          seqContainer.innerHTML = html;
        }
      } else {
        seqContainer.innerHTML = '';
      }
    }
  } catch (error) {
    console.warn('Error calculating time-varying risk:', error);
    if (loadingIndicator) {
      loadingIndicator.textContent = 'error';
      loadingIndicator.style.color = '#dc2626';
    }
    timeVaryingRiskSpan.textContent = 'Calculation failed';
    timeVaryingRiskSpan.style.color = '#666';
  }
}

// Export the functions if using modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    calculateRepeatedExposureRisk,
    calculateCumulativeRisk,
    initRepeatedExposureCalculator,
    updateCalculatorDisplay
  };
}
