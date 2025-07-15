// exposure-utils.js
// Extracted inline helpers for fit factor, AJAX submit, and time-label updaters

// Update fit factor hidden field and calculate f_i
function updateFitFactorValue() {
  const input = document.getElementById('fit_factor_input');
  const hidden = document.getElementById('fit_factor_hidden');
  const fiField = document.getElementById('f_i');
  if (input && hidden) {
    hidden.value = input.value;
    const fitFactor = parseFloat(input.value);
    if (!isNaN(fitFactor) && fitFactor > 0 && fiField) {
      const fiValue = Math.max(0, Math.min(1, 1 / fitFactor));
      fiField.value = fiValue.toString();
    } else if (input.value.trim() === '' && fiField) {
      if (typeof updateFi === 'function') updateFi();
    }
  }
}

// Track first calculation for smooth scroll
let isFirstCalculation = true;

// Helper function to display calculation errors
function displayCalculationError(message, type = 'error') {
  // Get the existing error container
  const errorContainer = document.getElementById('calculationErrorMessage');
  if (!errorContainer) {
    console.warn('Error container not found');
    return;
  }
  
  // Set message and styling based on type
  errorContainer.innerHTML = message;
  errorContainer.style.display = 'block';
  errorContainer.style.padding = '1rem';
  errorContainer.style.borderRadius = '0.5rem';
  errorContainer.style.marginBottom = '1rem';
  
  if (type === 'warning') {
    // Rate limit styling (yellow/orange)
    errorContainer.style.color = '#856404';
    errorContainer.style.backgroundColor = '#fff3cd';
    errorContainer.style.border = '1px solid #ffeaa7';
  } else {
    // Error styling (red)
    errorContainer.style.color = '#ef4444';
    errorContainer.style.backgroundColor = '#fef2f2';
    errorContainer.style.border = '1px solid #fecaca';
  }
}

// Advanced field validation helper - simplified
function validateAdvancedFields() {
  const advancedEnabled = document.getElementById('advanced').value === 'true';
  if (!advancedEnabled) return true;
  
  // Only check for incomplete inputs that would cause calculation errors
  const fieldsToCheck = ['relative_humidity', 'temperature', 'co2', 'custom_ACH', 'room_volume', 'covid_prevalence'];
  
  for (const fieldId of fieldsToCheck) {
    const field = document.getElementById(fieldId);
    if (!field) continue;
    
    const value = field.value.trim();
    // Only prevent submission for incomplete decimal inputs
    if (value === '.' || value === '-' || value === '-.') {
      field.focus();
      return false;
    }
  }
  
  return true;
}

// AJAX form submission handler
function submitFormAsync(event) {
  event.preventDefault();
  // Ensure dependent sections are visible for validation
  // User mask type question
  const maskSel = document.getElementById('masked');
  if (maskSel && maskSel.value === 'Yes') {
    const mtc = document.getElementById('mask_type_container');
    if (mtc) mtc.style.display = 'block';
  }
  // Other people mask type question
  const maskedPercentSel = document.getElementById('masked_percentage');
  if (maskedPercentSel && parseInt(maskedPercentSel.value, 10) > 0) {
    const omtc = document.getElementById('others_mask_type_container');
    if (omtc) omtc.style.display = 'block';
  }
  // Environment section
  const ioSel = document.getElementById('indoor_outdoor');
  if (ioSel && ioSel.value === 'Indoors') {
    const envc = document.getElementById('environment_container');
    if (envc) envc.style.display = 'block';
  }
  // Sync fit factor
  updateFitFactorValue();
  // Force f_i and f_e updates
  if (typeof updateFi === 'function') updateFi();
  if (typeof updateFe === 'function') updateFe();
  
  // Validate advanced fields first
  if (!validateAdvancedFields()) {
    return; // Stop submission if advanced fields are invalid
  }
  
  // Unified validation for required fields
  let valid = true;
  const validators = [
    { id: 'masked', condition: () => true },
    { id: 'recent_vaccination', condition: () => true },
    { id: 'recent_infection', condition: () => true },
    { id: 'indoor_outdoor', condition: () => true },
    // User mask type
    { id: 'mask_type', condition: () => document.getElementById('masked').value === 'Yes' },
    // Other people mask type: required if some others were masked
    { id: 'others_mask_type', condition: () => {
        const slider = document.getElementById('masked_percentage');
        return slider && parseInt(slider.value, 10) > 0;
      }
    },
    { id: 'ACH', condition: () => document.getElementById('indoor_outdoor').value === 'Indoors' },
    // Immunocompromised severity: required if immunocompromised = 'Yes'
    { id: 'immunocompromised_severity', condition: () => document.getElementById('immunocompromised').value === 'Yes' },
    // Progressive disclosure reconsider: required if immunocompromised = 'unsure'
    { id: 'immunocompromised_reconsider', condition: () => document.getElementById('immunocompromised').value === 'unsure' }
  ];
  validators.forEach(({ id, condition }) => {
    if (!condition()) return;
    const el = document.getElementById(id);
    if (!el) return;
    const wrapper = el.closest('.select-wrapper');
    const msg = wrapper?.querySelector('.validation-message');
    if (!el.value) {
      el.classList.add('validation-error');
      if (msg) msg.style.display = 'block';
      if (valid) el.focus();
      valid = false;
    } else {
      el.classList.remove('validation-error');
      if (msg) msg.style.display = 'none';
    }
  });
  // Duration >0 check
  const dt = parseInt(document.getElementById('delta_t').value, 10) || 0;
  if (dt <= 0) {
    ['exposure_hours', 'exposure_minutes', 'exposure_seconds'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) sel.classList.add('validation-error');
    });
    const mSel = document.getElementById('exposure_minutes');
    const msg = mSel?.closest('.select-wrapper')?.querySelector('.validation-message');
    if (msg) msg.style.display = 'block';
    if (valid && mSel) mSel.focus();
    valid = false;
  }
  if (!valid) return;
  
  // Show loading spinner on submit button
  const submitBtn = document.querySelector('button[type="submit"]');
  let originalBtnText = '';
  if (submitBtn) {
    originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = 'Calculating... <i class="fas fa-spinner fa-spin"></i>';
    submitBtn.disabled = true;
  }
  
  // AJAX send
  const form = document.getElementById('exposureForm');
  const formData = new FormData(form);
  fetch(form.action, { method: 'POST', body: formData, headers: { 'Accept': 'text/html' } })
    .then(r => {
      // Check for rate limiting first
      if (r.status === 429) {
        // Display rate limit message to user
        displayCalculationError('<strong>Please slow down!</strong> You\'ve made too many requests. Please wait a minute and try again.', 'warning');
        // Restore button and stop processing
        if (submitBtn) {
          submitBtn.innerHTML = originalBtnText;
          submitBtn.disabled = false;
        }
        return Promise.reject('Rate limited');
      }
      return r.text();
    })
    .then(html => {
      // Clear any error messages on successful calculation
      const errorContainer = document.getElementById('calculationErrorMessage');
      if (errorContainer) {
        errorContainer.style.display = 'none';
        errorContainer.innerHTML = '';
      }
      
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const resultContainer = doc.getElementById('result');
      const currentResult = document.getElementById('result');
      if (resultContainer && currentResult) {
        currentResult.innerHTML = resultContainer.innerHTML;
        currentResult.style.display = 'block';
        if (isFirstCalculation) {
          currentResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
          isFirstCalculation = false;
        }
        
        // TODO: Uncertainty component AJAX handling - disabled until architectural issues resolved
        
        // Handle repeated exposure calculation for AJAX responses
        const repeatedExposureMsgElement = currentResult.querySelector('#repeatedExposureMessage');
        const interactiveContainerElement = currentResult.querySelector('#interactiveCalculatorContainer');
        const riskElement = currentResult.querySelector('#riskMessage span');
        
        // Extract the actual prevalence and calculation parameters
        let actualPrevalence = null;
        let calculationParams = null;
        const interactiveContainer = currentResult.querySelector('#interactiveCalculatorContainer');
        if (interactiveContainer) {
          const prevalenceAttr = interactiveContainer.getAttribute('data-prevalence');
          if (prevalenceAttr) {
            actualPrevalence = parseFloat(prevalenceAttr);
            if (window.IS_DEVELOPMENT) console.log('Extracted actual prevalence from AJAX response:', actualPrevalence);
          }
        }
        
        // Try to get calculation parameters from script tag
        const paramsScript = currentResult.querySelector('#calculationParams');
        if (paramsScript) {
          try {
            calculationParams = JSON.parse(paramsScript.textContent);
            console.log('Extracted calculation parameters from AJAX response:', calculationParams);
          } catch (e) {
            console.warn('Could not parse calculation parameters from script tag:', e);
          }
        }
        
        if (riskElement) {
          // Extract risk percentage from text content
          const riskText = riskElement.textContent.trim();
          const riskValue = parseFloat(riskText) / 100;
          
          if (!isNaN(riskValue)) {
            // Apply color with shared utility
            riskElement.style.color = getRiskColor(riskValue);
            
            // Show distance warning if distance is very close (0.5 ft or 1 ft)
            const distanceSlider = document.getElementById('x');
            const distanceWarning = currentResult.querySelector('#distanceWarning');
            if (distanceSlider && distanceWarning) {
              const distanceInFeet = parseFloat(distanceSlider.value) || 0;
              if (distanceInFeet <= 1) {
                distanceWarning.style.display = 'block';
              } else {
                distanceWarning.style.display = 'none';
              }
            }
            
            // Apply risk colors to Monte Carlo bounds in AJAX responses
            setTimeout(() => {
              const mcBounds = currentResult.querySelectorAll('.mc-bound');
              mcBounds.forEach(bound => {
                const percentText = bound.textContent.trim();
                const percentValue = parseFloat(percentText) / 100;
                if (!isNaN(percentValue)) {
                  bound.style.color = getRiskColor(percentValue);
                }
              });
            }, 100);
            
            // Update the static message about >50% risk
        // Only show static repeated-exposure message for risks ≥0.01% (0.0001) and <50%
        if (riskValue >= 0.0001 && riskValue < 0.5 && repeatedExposureMsgElement) {
              const repeats = calculateRepeatedExposureRisk(riskValue);
              if (repeats) {
                const repeatNumberElement = repeatedExposureMsgElement.querySelector('#repeatNumber');
                if (repeatNumberElement) {
                  // Format with commas if number is 1000 or greater
                  const formattedRepeats = repeats >= 1000 ? 
                    repeats.toLocaleString('en-US') : repeats.toString();
                  repeatNumberElement.textContent = formattedRepeats;
                }
              } else {
                repeatedExposureMsgElement.style.display = 'none';
              }
              
              // Set up modal interactions for AJAX responses
              setTimeout(() => {
                const infoBtn = document.getElementById('repeatExposureInfoBtn');
                const infoModal = document.getElementById('repeatExposureInfoModal');
                const closeBtn = document.getElementById('closeModalBtn');
                
                if (infoBtn && infoModal && closeBtn) {
                  // Open modal when info button is clicked
                  infoBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    infoModal.style.display = 'flex';
                  });
                  
                  // Close modal when close button is clicked
                  closeBtn.addEventListener('click', function() {
                    infoModal.style.display = 'none';
                  });
                  
                  // Close modal when clicking outside the modal content
                  infoModal.addEventListener('click', function(e) {
                    if (e.target === infoModal) {
                      infoModal.style.display = 'none';
                    }
                  });
                }
              }, 100);
            }
            
            // Update threshold message with time-varying calculation
            const repeatNumberElement = currentResult.querySelector('#repeatNumber');
            if (repeatNumberElement) {
              console.log('=== UPDATING THRESHOLD WITH TIME-VARYING METHOD ===');
              console.log('Risk value for threshold:', riskValue);
              
              // Extract the actual prevalence used in the backend calculation
              let prevalence = 0.01; // fallback default
              
              // Try to get it from the AJAX response data attribute first
              if (actualPrevalence !== null) {
                prevalence = actualPrevalence;
                console.log('Using actual prevalence from AJAX response:', prevalence);
              } else {
                // Fallback: try to get from form data
                const formElement = document.getElementById('exposureForm');
                if (formElement) {
                  const formData = new FormData(formElement);
                  const prevInput = formData.get('covid_prevalence');
                  if (prevInput && !isNaN(parseFloat(prevInput))) {
                    prevalence = parseFloat(prevInput) / 100;
                    console.log('Using prevalence from form data:', prevalence);
                  } else {
                    console.log('Using fallback prevalence (no form data found):', prevalence);
                  }
                }
              }
              
              // Determine region based on selected location (same logic as interactive calculator)
              let region = 'National';
              const locationSelect = document.getElementById('exposure_location');
              if (locationSelect && locationSelect.value) {
                const stateCode = locationSelect.value.toUpperCase();
                const regionMap = {
                  // Northeast
                  'MD': 'Northeast', 'PA': 'Northeast', 'DE': 'Northeast', 'NY': 'Northeast',
                  'MA': 'Northeast', 'VT': 'Northeast', 'CT': 'Northeast', 'NJ': 'Northeast', 
                  'ME': 'Northeast', 'NH': 'Northeast', 'RI': 'Northeast',
                  // South
                  'AL': 'South', 'AR': 'South', 'TX': 'South', 'KY': 'South', 'GA': 'South',
                  'VA': 'South', 'TN': 'South', 'LA': 'South', 'FL': 'South', 'DC': 'South',
                  'NC': 'South', 'SC': 'South', 'MS': 'South', 'OK': 'South', 'WV': 'South',
                  // Midwest
                  'NE': 'Midwest', 'OH': 'Midwest', 'IA': 'Midwest', 'WI': 'Midwest',
                  'MO': 'Midwest', 'MI': 'Midwest', 'IL': 'Midwest', 'MN': 'Midwest',
                  'IN': 'Midwest', 'KS': 'Midwest', 'ND': 'Midwest', 'SD': 'Midwest',
                  // West
                  'AK': 'West', 'WA': 'West', 'NM': 'West', 'CA': 'West', 'OR': 'West',
                  'ID': 'West', 'MT': 'West', 'NV': 'West', 'UT': 'West', 'CO': 'West',
                  'WY': 'West', 'HI': 'West', 'AZ': 'West'
                };
                region = regionMap[stateCode] || 'National';
              }
              
              console.log('Threshold parameters (matching interactive calculator):');
              console.log('  riskValue:', riskValue);
              console.log('  prevalence:', prevalence);
              console.log('  region:', region);
              
              // Call time-varying API for threshold  
              console.log('Making threshold API call with current week...');
              
              // Use the actual calculation parameters from the server-side calculation
              // This avoids race conditions with form DOM updates
              let completeCalculationParams = {};
              
              try {
                // First try to get parameters from the JSON script tag (most reliable)
                const paramsScript = document.getElementById('calculationParams');
                if (paramsScript && paramsScript.textContent) {
                  completeCalculationParams = JSON.parse(paramsScript.textContent);
                  console.log('Using server-side calculation parameters for threshold');
                } else {
                  // Fallback to reading from form (less reliable due to timing)
                  completeCalculationParams = (typeof collectAllCalculationParams === 'function') 
                    ? collectAllCalculationParams() 
                    : calculationParams || {};
                  console.log('Fallback to form-based parameters for threshold');
                }
              } catch (e) {
                console.warn('Error parsing calculation parameters, using fallback:', e);
                completeCalculationParams = calculationParams || {};
              }
              
              const thresholdPayload = {
                base_risk: riskValue,
                base_prevalence: prevalence,
                num_exposures: 1,
                region: region,
                calculation_params: completeCalculationParams
                // start_week will default to current week in backend
              };
              
              console.log('Including complete calculation parameters in threshold API call:', completeCalculationParams);
              console.log('Threshold call - base_risk:', riskValue, 'base_prevalence:', prevalence, 'region:', region);
              
              fetch('/api/time-varying-risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(thresholdPayload)
              })
              .then(response => response.json())
              .then(data => {
                console.log('Time-varying threshold API returned:', data.threshold);
                if (data.threshold) {
                  const formattedDays = data.threshold >= 1000 ? 
                    data.threshold.toLocaleString('en-US') : data.threshold.toString();
                  repeatNumberElement.textContent = formattedDays;
                  console.log('Updated threshold message to:', formattedDays);
                }
              })
              .catch(error => {
                console.warn('Threshold API error:', error);
                repeatNumberElement.textContent = 'Error';
              });
            }
            
            // Initialize the interactive calculator
            if (interactiveContainerElement && typeof initRepeatedExposureCalculator === 'function') {
              // Clear previous calculator (if any)
              interactiveContainerElement.innerHTML = '';
              
              // Extract the actual prevalence used in the backend calculation
              let calculatorPrevalence = 0.01; // fallback default
              
              // Try to get it from the AJAX response data attribute first
              if (actualPrevalence !== null) {
                calculatorPrevalence = actualPrevalence;
                console.log('Interactive calculator using actual prevalence from AJAX response:', calculatorPrevalence);
              } else {
                // Fallback: try to get from form data
                const formElement = document.getElementById('exposureForm');
                if (formElement) {
                  const formData = new FormData(formElement);
                  const prevInput = formData.get('covid_prevalence');
                  if (prevInput && !isNaN(parseFloat(prevInput))) {
                    calculatorPrevalence = parseFloat(prevInput) / 100;
                    console.log('Interactive calculator using prevalence from form data:', calculatorPrevalence);
                  } else {
                    console.log('Interactive calculator using fallback prevalence:', calculatorPrevalence);
                  }
                }
              }
              
              // Determine region based on selected location
              let region = 'National';
              const locationSelect = document.getElementById('exposure_location');
              if (locationSelect && locationSelect.value) {
                // Map state code to region using the same logic as the backend
                const stateCode = locationSelect.value.toUpperCase();
                const regionMap = {
                  // Northeast
                  'MD': 'Northeast', 'PA': 'Northeast', 'DE': 'Northeast', 'NY': 'Northeast',
                  'MA': 'Northeast', 'VT': 'Northeast', 'CT': 'Northeast', 'NJ': 'Northeast', 
                  'ME': 'Northeast', 'NH': 'Northeast', 'RI': 'Northeast',
                  // South
                  'AL': 'South', 'AR': 'South', 'TX': 'South', 'KY': 'South', 'GA': 'South',
                  'VA': 'South', 'TN': 'South', 'LA': 'South', 'FL': 'South', 'DC': 'South',
                  'NC': 'South', 'SC': 'South', 'MS': 'South', 'OK': 'South', 'WV': 'South',
                  // Midwest
                  'NE': 'Midwest', 'OH': 'Midwest', 'IA': 'Midwest', 'WI': 'Midwest',
                  'MO': 'Midwest', 'MI': 'Midwest', 'IL': 'Midwest', 'MN': 'Midwest',
                  'IN': 'Midwest', 'KS': 'Midwest', 'ND': 'Midwest', 'SD': 'Midwest',
                  // West
                  'AK': 'West', 'WA': 'West', 'NM': 'West', 'CA': 'West', 'OR': 'West',
                  'ID': 'West', 'MT': 'West', 'NV': 'West', 'UT': 'West', 'CO': 'West',
                  'WY': 'West', 'HI': 'West', 'AZ': 'West'
                };
                region = regionMap[stateCode] || 'National';
              }
              
              console.log('Parameters for interactive calculator:');
              console.log('  riskValue:', riskValue);
              console.log('  calculatorPrevalence:', calculatorPrevalence);
              console.log('  region:', region);
              
              // Use the same reliable parameter source for interactive calculator
              let completeParams = {};
              
              try {
                // Use the same JSON script tag approach for consistency
                const paramsScript = document.getElementById('calculationParams');
                if (paramsScript && paramsScript.textContent) {
                  completeParams = JSON.parse(paramsScript.textContent);
                  console.log('Using server-side calculation parameters for interactive calculator');
                } else {
                  // Fallback to reading from form
                  completeParams = (typeof collectAllCalculationParams === 'function') 
                    ? collectAllCalculationParams() 
                    : calculationParams || {};
                  console.log('Fallback to form-based parameters for interactive calculator');
                }
              } catch (e) {
                console.warn('Error parsing calculation parameters for interactive calculator, using fallback:', e);
                completeParams = calculationParams || {};
              }
              
              // Initialize new calculator
              initRepeatedExposureCalculator(riskValue, 'interactiveCalculatorContainer', calculatorPrevalence, region, completeParams);
              
              // Extra check to ensure all preset buttons are styled consistently
              setTimeout(() => {
                document.querySelectorAll('.repeat-preset').forEach(button => {
                  if (!button.style.backgroundColor) {
                    button.style.backgroundColor = '#e5e7eb';
                    button.style.border = 'none';
                    button.style.borderRadius = '4px';
                    button.style.padding = '5px 10px';
                    button.style.cursor = 'pointer';
                    button.style.fontSize = '14px';
                  }
                });
                
                // Double-check slider max value
                const slider = document.getElementById('repeatedSlider');
                if (slider && slider.max < 365) {
                  slider.max = 365;
                }
              }, 100);
            }
          }
        }
      }
      
      // Restore button state on success
      if (submitBtn) {
        submitBtn.innerHTML = originalBtnText;
        submitBtn.disabled = false;
      }
    })
    .catch(err => {
      console.error(err);
      
      // Only show generic error message if this wasn't a rate limit error
      if (err !== 'Rate limited') {
        displayCalculationError('An error occurred while calculating. Please try again.');
      }
      
      // Restore button state on error
      if (submitBtn) {
        submitBtn.innerHTML = originalBtnText;
        submitBtn.disabled = false;
      }
    });
}

// Vaccination time slider label updater
function updateVaccinationTimeLabel(value) {
  const month = parseInt(value, 10);
  const text = month === 1 ? '1 month ago' : `${month} months ago`;
  document.querySelector('label[for="vaccination_time"] .slider-value-label').textContent = text;
  document.getElementById('vaccination_time_display').value = text;
  
  // Highlight the matching vaccination time label
  const vacLabels = document.querySelectorAll('#vaccination_time_container .slider-labels span');
  vacLabels.forEach(lbl => lbl.classList.remove('active'));
  vacLabels.forEach(lbl => {
    const mv = parseInt(lbl.getAttribute('data-month-value'), 10);
    if (mv === month) lbl.classList.add('active');
  });
  
  // Update immune calculation and trigger change event to recalculate risk
  if (typeof calculateImmuneSusceptibility === 'function') {
    calculateImmuneSusceptibility();
  }
  
  // Dispatch change event on the slider to trigger main risk calculation
  const slider = document.getElementById('vaccination_time');
  if (slider) {
    try {
      slider.dispatchEvent(new Event('change', {bubbles: true}));
    } catch (e) {
      // Fallback for older browsers
      const event = document.createEvent('Event');
      event.initEvent('change', true, true);
      slider.dispatchEvent(event);
    }
  }
}

// Infection time slider label updater
function updateInfectionTimeLabel(value) {
  const month = parseInt(value, 10);
  const text = month === 1 ? '1 month ago' : `${month} months ago`;
  document.querySelector('label[for="infection_time"] .slider-value-label').textContent = text;
  document.getElementById('infection_time_display').value = text;
  
  // Highlight the matching infection time label
  const infLabels = document.querySelectorAll('#infection_time_container .slider-labels span');
  infLabels.forEach(lbl => lbl.classList.remove('active'));
  infLabels.forEach(lbl => {
    const mv = parseInt(lbl.getAttribute('data-month-value'), 10);
    if (mv === month) lbl.classList.add('active');
  });
  
  // Update immune calculation and trigger change event to recalculate risk
  if (typeof calculateImmuneSusceptibility === 'function') {
    calculateImmuneSusceptibility();
  }
  
  // Dispatch change event on the slider to trigger main risk calculation
  const slider = document.getElementById('infection_time');
  if (slider) {
    try {
      slider.dispatchEvent(new Event('change', {bubbles: true}));
    } catch (e) {
      // Fallback for older browsers
      const event = document.createEvent('Event');
      event.initEvent('change', true, true);
      slider.dispatchEvent(event);
    }
  }
}

// Update masked percentage label and slider display
function updateMaskedPercentageLabel(value) {
  const val = parseInt(value);
  let text;

  if (val === 0) text = 'None';
  else if (val === 25) text = 'Some (25%)';
  else if (val === 50) text = 'Half (50%)';
  else if (val === 75) text = 'Most (75%)';
  else if (val === 100) text = 'All (100%)';
  else text = `${val}%`;
  
  // Update hidden fields
  const percentField = document.getElementById('percentage_masked');
  if (percentField) {
    const fractionValue = val === 0 ? "0" :
                        val === 25 ? "0.25" :
                        val === 50 ? "0.5" :
                        val === 75 ? "0.75" :
                        val === 100 ? "1" : "0";
    percentField.value = fractionValue;
  }

  // Update hidden value field
  const valueField = document.getElementById('masked_percentage_value');
  if (valueField) {
    valueField.value = val.toString();
  }
  
  // Set the active class on the appropriate label
  const sliderContainer = document.getElementById('masked_percentage').closest('.slider-container');
  if (sliderContainer) {
    const labels = sliderContainer.querySelectorAll('.slider-labels span');
    
    // Reset all
    labels.forEach(l => l.classList.remove('active'));
    
    // Set active based on value
    let activeIndex = 0;
    if (val === 0) activeIndex = 0;
    else if (val === 25) activeIndex = 1;
    else if (val === 50) activeIndex = 2;
    else if (val === 75) activeIndex = 3;
    else if (val === 100) activeIndex = 4;
    
    if (labels[activeIndex]) {
      labels[activeIndex].classList.add('active');
    }
  }
  
  // Show/hide mask type question based on selection
  const maskTypeContainer = document.getElementById('others_mask_type_container');
  const maskTypeField = document.getElementById('others_mask_type');

  if (val > 0) {
    // Show mask type selector only if not already visible
    if (maskTypeContainer.style.display !== "block") {
      maskTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      maskTypeContainer.style.display = "block";
    }
    maskTypeField.setAttribute('required', true);
  } else {
    // Hide mask type selector when value returns to zero
    if (maskTypeContainer.style.display === "block") {
      maskTypeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
      setTimeout(() => {
        maskTypeContainer.style.display = "none";
      }, 300);
    } else {
      maskTypeContainer.style.display = "none";
    }
    maskTypeField.removeAttribute('required');
  }
  
  // Update f_e value through main JS function
  if (typeof updateFe === 'function') {
    updateFe();
  }
}

// Update distance value and display
function updateDistanceLabel(value) {
  const v = parseInt(value, 10);
  const text = v === 1 ? '1 foot' : `${v} feet`;
  // Update label next to slider
  const labelSpan = document.querySelector('label[for="x"] .slider-value-label');
  if (labelSpan) {
    labelSpan.textContent = text;
  }
  // Sync hidden display input
  let dispInput = document.getElementById('x_display');
  if (!dispInput) {
    dispInput = document.createElement('input');
    dispInput.type = 'hidden';
    dispInput.id = 'x_display';
    dispInput.name = 'x_display';
    document.getElementById('exposureForm').appendChild(dispInput);
  }
  dispInput.value = text;
}
// Initialize distance label on load
document.addEventListener('DOMContentLoaded', function() {
  const xSlider = document.getElementById('x');
  if (xSlider) updateDistanceLabel(xSlider.value);
});
function updateDistanceDisplay() {
  const slider = document.getElementById('x');
  if (!slider) return;
  
  const sliderValue = parseInt(slider.value);
  // Map slider value to actual distance
  const actualDistance = sliderValue === 0 ? 0.5 : sliderValue;
  
  // For display in the slider labels
  const labelText = actualDistance === 20 ? "20+ ft" :
                    actualDistance === 1 ? "1 foot" :
                    actualDistance === 0.5 ? "0.5 feet" :
                    `${actualDistance} feet`;

  // For display at the top of the form (fuller version)
  const displayText = actualDistance === 20 ? "20+ feet" :
                    actualDistance === 1 ? "1 foot" :
                    actualDistance === 0.5 ? "0.5 feet" :
                    `${actualDistance} feet`;

  // Update hidden fields for form submission
  const displayField = document.getElementById('x_display');
  const actualField = document.getElementById('x_actual');
  const metersField = document.getElementById('x_meters');
  
  if (displayField) displayField.value = displayText;
  if (actualField) actualField.value = actualDistance;
  if (metersField) metersField.value = (actualDistance * 0.3048).toFixed(2);

  // Update label in the heading
  const labelSpan = document.querySelector('label[for="x"] .slider-value-label');
  if (labelSpan) labelSpan.textContent = displayText;
  // Highlight corresponding distance label
  const distanceLabels = document.querySelectorAll('.distance-labels .distance-label');
  distanceLabels.forEach(lbl => lbl.classList.remove('active'));
  const map = {0.5: 0, 3: 1, 6: 2, 10: 3, 15: 4};
  const idx = map[actualDistance];
  if (idx !== undefined && distanceLabels[idx]) {
    distanceLabels[idx].classList.add('active');
  }
}

// Toggle info boxes with exclusive behavior for moderate/severe
function toggleInfoBox(id) {
  const infoBox = document.getElementById(id);
  if (!infoBox) return;
  
  // Special handling for moderate/severe info boxes - only show one at a time
  if (id === 'moderate_info' || id === 'severe_info') {
    const moderateInfo = document.getElementById('moderate_info');
    const severeInfo = document.getElementById('severe_info');
    
    // If the clicked box is already visible, hide it
    if (infoBox.style.display === 'block') {
      infoBox.style.display = 'none';
      return;
    }
    
    // Hide both boxes first
    if (moderateInfo) moderateInfo.style.display = 'none';
    if (severeInfo) severeInfo.style.display = 'none';
    
    // Show the clicked box
    infoBox.style.display = 'block';
  } else {
    // Normal toggle behavior for other info boxes
    infoBox.style.display = infoBox.style.display === 'none' ? 'block' : 'none';
  }
}

// Time input handling
function updateDeltaT() {
  const hSel = document.getElementById('exposure_hours');
  const mSel = document.getElementById('exposure_minutes');
  const sSel = document.getElementById('exposure_seconds');

  if (!(hSel && mSel && sSel)) return;

  const h = parseInt(hSel.value || '0', 10) || 0;
  const m = parseInt(mSel.value || '0', 10) || 0;
  const s = parseInt(sSel.value || '0', 10) || 0;

  const totalSeconds = h * 3600 + m * 60 + s;
  const dtInput = document.getElementById('delta_t');
  if (dtInput) dtInput.value = totalSeconds.toString();
  
  // Clear time validation if user enters any non-zero duration
  if (totalSeconds > 0) {
    [hSel, mSel, sSel].forEach(sel => sel.classList.remove('validation-error'));
    const msg = mSel.closest('.select-wrapper')?.querySelector('.time-validation-message');
    if (msg) msg.style.display = 'none';
  }
}

// Setup real-time validation for advanced fields
function setupAdvancedFieldValidation() {
  const advancedFields = [
    'relative_humidity', 'temperature', 'co2', 'custom_ACH', 'room_volume', 'covid_prevalence'
  ];
  
  advancedFields.forEach(fieldId => {
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    // Add keydown event to prevent invalid characters
    field.addEventListener('keydown', function(e) {
      // Allow: backspace, delete, tab, escape, enter, home, end, left, right
      if ([8, 9, 27, 13, 46, 35, 36, 37, 39].indexOf(e.keyCode) !== -1 ||
          // Allow Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X
          (e.keyCode === 65 && e.ctrlKey === true) ||
          (e.keyCode === 67 && e.ctrlKey === true) ||
          (e.keyCode === 86 && e.ctrlKey === true) ||
          (e.keyCode === 88 && e.ctrlKey === true)) {
        return;
      }
      
      // Allow digits
      if ((e.keyCode >= 48 && e.keyCode <= 57) || (e.keyCode >= 96 && e.keyCode <= 105)) {
        return;
      }
      
      // Allow decimal point only if not already present
      if ((e.keyCode === 190 || e.keyCode === 110) && this.value.indexOf('.') === -1) {
        return;
      }
      
      // Allow minus sign only for temperature field and only at the beginning
      if (fieldId === 'temperature' && (e.keyCode === 189 || e.keyCode === 109) && 
          (this.value === '' || this.selectionStart === 0)) {
        return;
      }
      
      // Prevent all other keys
      e.preventDefault();
    });
    
    // Add input event listener for auto-capping values
    field.addEventListener('input', function() {
      // Auto-cap relative humidity and covid prevalence at 100
      if ((fieldId === 'relative_humidity' || fieldId === 'covid_prevalence') && this.value !== '') {
        const num = parseFloat(this.value);
        if (!isNaN(num) && num > 100) {
          this.value = '100';
        }
      }
    });
    
    // Add blur event listener for final value cleanup
    field.addEventListener('blur', function() {
      // Auto-cap values on blur as well
      if ((fieldId === 'relative_humidity' || fieldId === 'covid_prevalence') && this.value !== '') {
        const num = parseFloat(this.value);
        if (!isNaN(num) && num > 100) {
          this.value = '100';
        }
      }
    });
    
    // Add paste event listener to validate pasted content
    field.addEventListener('paste', function(e) {
      e.preventDefault();
      const paste = (e.clipboardData || window.clipboardData).getData('text');
      
      // Validate pasted content
      let validPaste = paste;
      if (fieldId === 'temperature') {
        // Allow negative numbers for temperature
        validPaste = paste.replace(/[^-0-9.]/g, '');
      } else {
        // Only allow positive numbers
        validPaste = paste.replace(/[^0-9.]/g, '');
      }
      
      // Ensure only one decimal point
      const parts = validPaste.split('.');
      if (parts.length > 2) {
        validPaste = parts[0] + '.' + parts.slice(1).join('');
      }
      
      // For temperature, ensure only one minus sign at the beginning
      if (fieldId === 'temperature' && validPaste.includes('-')) {
        const minusIndex = validPaste.indexOf('-');
        if (minusIndex > 0) {
          validPaste = validPaste.replace('-', '');
        }
        // Remove additional minus signs
        validPaste = validPaste.replace(/-/g, function(match, offset) {
          return offset === 0 ? match : '';
        });
      }
      
      // Apply auto-capping for relative humidity and covid prevalence
      if ((fieldId === 'relative_humidity' || fieldId === 'covid_prevalence') && validPaste !== '') {
        const num = parseFloat(validPaste);
        if (!isNaN(num) && num > 100) {
          validPaste = '100';
        }
      }
      
      this.value = validPaste;
    });
  });
}

// Setup visibility toggles for conditional sections
function setupConditionalSections() {
  // Masked status toggle
  const maskedField = document.getElementById('masked');
  if (maskedField) {
    maskedField.addEventListener('change', function() {
      const maskTypeContainer = document.getElementById('mask_type_container');
      const maskFitContainer = document.getElementById('mask_fit_container');
      const fitFactorContainer = document.getElementById('fit_factor_container');
      
      if (this.value === 'Yes') {
        // Show mask type container
        if (maskTypeContainer) {
          maskTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
          maskTypeContainer.style.display = 'block';
        }
        
        // Make sure fit factor container starts hidden (will only show for compatible mask types)
        const maskFitContainer = document.getElementById('mask_fit_container');
        const fitFactorContainer = document.getElementById('fit_factor_container');
        if (maskFitContainer) maskFitContainer.style.display = 'none';
        if (fitFactorContainer) fitFactorContainer.style.display = 'none';
      } else {
        // Hide mask-related containers
        [maskTypeContainer, maskFitContainer, fitFactorContainer].forEach(container => {
          if (container && container.style.display === 'block') {
            container.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
            setTimeout(() => { container.style.display = 'none'; }, 300);
          } else if (container) {
            container.style.display = 'none';
          }
        });
        
        // Reset mask type dropdown so user has to re-select when switching back to "Yes"
        const maskTypeField = document.getElementById('mask_type');
        if (maskTypeField) maskTypeField.value = "";
        
        // Reset mask fit slider to default
        const maskFitField = document.getElementById('mask_fit');
        if (maskFitField) maskFitField.value = "Average";
        
        const maskFitSlider = document.getElementById('mask_fit_slider');
        if (maskFitSlider) maskFitSlider.value = "1"; // Average = index 1
        
        // For people not wearing a mask, ensure f_i is 1.0 and clear fit factor
        const fiInput = document.getElementById('f_i');
        if (fiInput) fiInput.value = "1";
        
        // Clear fit factor input when switching to not masked
        const fitFactorInput = document.getElementById('fit_factor_input');
        if (fitFactorInput) fitFactorInput.value = "";
        
        // Also clear the hidden fit factor field if it exists
        const fitFactorHidden = document.getElementById('fit_factor_hidden');
        if (fitFactorHidden) fitFactorHidden.value = "";
      }
      
      // Update f_i based on new masked status
      if (typeof updateFi === 'function') {
        updateFi();
      }
    });
  }
  
  // Mask type change handler
  const maskTypeField = document.getElementById('mask_type');
  if (maskTypeField) {
    maskTypeField.addEventListener('change', function() {
      const maskFitContainer = document.getElementById('mask_fit_container');
      const fitFactorContainer = document.getElementById('fit_factor_container');
      
      if (this.value) {
        console.log(`Mask type selected: "${this.value}"`);
        
        // Show mask fit container if mask type is selected
        if (maskFitContainer) {
          maskFitContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
          maskFitContainer.style.display = 'block';
        }
        
        // Check if this mask type supports fit factor
        const masksSupportingFitFactor = ['KN94/95', 'N95', 'N99', 'Elastomeric with P100/N100 filters'];
        console.log('Current fit factor container display:', fitFactorContainer ? fitFactorContainer.style.display : 'not found');
        
        if (masksSupportingFitFactor.includes(this.value)) {
          console.log('This mask supports fit factor - showing container');
          if (fitFactorContainer) {
            fitFactorContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
            fitFactorContainer.style.display = 'block';
          }
        } else {
          console.log('This mask does NOT support fit factor - hiding container');
          if (fitFactorContainer) {
            // Force hide without animation for immediate effect
            fitFactorContainer.style.animation = '';
            fitFactorContainer.style.display = 'none';
            
            // Clear fit factor input when not applicable
            const fitFactorInput = document.getElementById('fit_factor_input');
            if (fitFactorInput) fitFactorInput.value = "";
            
            const fitFactorHidden = document.getElementById('fit_factor_hidden');
            if (fitFactorHidden) fitFactorHidden.value = "";
          }
        }
      } else {
        // Hide containers if no mask type selected
        [maskFitContainer, fitFactorContainer].forEach(container => {
          if (container && container.style.display === 'block') {
            container.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
            setTimeout(() => { container.style.display = 'none'; }, 300);
          } else if (container) {
            container.style.display = 'none';
          }
        });
        
        // Clear fit factor when no mask type selected
        const fitFactorInput = document.getElementById('fit_factor_input');
        if (fitFactorInput) fitFactorInput.value = "";
        
        const fitFactorHidden = document.getElementById('fit_factor_hidden');
        if (fitFactorHidden) fitFactorHidden.value = "";
      }
      
      // Update f_i based on new mask type
      if (typeof updateFi === 'function') {
        updateFi();
      }
    });
  }
  
  // Vaccination status toggle
  const vaccinationField = document.getElementById('recent_vaccination');
  if (vaccinationField) {
    vaccinationField.addEventListener('change', function() {
      const container = document.getElementById('vaccination_time_container');
      
      if (this.value === 'Yes' && container) {
        container.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
        container.style.display = 'block';
      } else if (container) {
        container.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
        setTimeout(() => { container.style.display = 'none'; }, 300);
      }
      
      // Update immune calculation
      if (typeof calculateImmuneSusceptibility === 'function') {
        calculateImmuneSusceptibility();
      }
    });
  }
  
  // Infection status toggle
  const infectionField = document.getElementById('recent_infection');
  if (infectionField) {
    infectionField.addEventListener('change', function() {
      const container = document.getElementById('infection_time_container');
      
      if (this.value === 'Yes' && container) {
        container.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
        container.style.display = 'block';
      } else if (container) {
        container.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
        setTimeout(() => { container.style.display = 'none'; }, 300);
      }
      
      // Update immune calculation
      if (typeof calculateImmuneSusceptibility === 'function') {
        calculateImmuneSusceptibility();
      }
    });
  }
  
  // Indoor/outdoor toggle
  const indoorOutdoorField = document.getElementById('indoor_outdoor');
  if (indoorOutdoorField) {
    indoorOutdoorField.addEventListener('change', function() {
      const environmentContainer = document.getElementById('environment_container');
      
      if (this.value === 'Indoors' && environmentContainer) {
        environmentContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
        environmentContainer.style.display = 'block';
      } else if (environmentContainer) {
        environmentContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
        setTimeout(() => { environmentContainer.style.display = 'none'; }, 300);
      }
      
      // Update ACH and volume if needed
      if (typeof handleIndoorOutdoorChange === 'function') {
        handleIndoorOutdoorChange();
      }
    });
  }
  
  // Immunocompromised status toggle
  console.log('DEBUG: Setting up immunocompromised event listener');
  console.log('DEBUG: calculateImmuneSusceptibility available?', typeof window.calculateImmuneSusceptibility);
  const immunocompromisedField = document.getElementById('immunocompromised');
  if (immunocompromisedField) {
    immunocompromisedField.addEventListener('change', function() {
      const severityContainer = document.getElementById('immunocompromised_severity_container');
      const progressiveDisclosure = document.getElementById('immunocompromised_progressive_disclosure');
      const reconsiderField = document.getElementById('immunocompromised_reconsider');
      
      if (this.value === 'Yes') {
        // Show severity container
        if (severityContainer) {
          severityContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
          severityContainer.style.display = 'block';
        }
        // Hide progressive disclosure
        if (progressiveDisclosure) {
          progressiveDisclosure.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { progressiveDisclosure.style.display = 'none'; }, 300);
        }
        // Clear reconsider field
        if (reconsiderField) {
          reconsiderField.value = '';
        }
      } else if (this.value === 'unsure') {
        // Show progressive disclosure
        if (progressiveDisclosure) {
          progressiveDisclosure.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
          progressiveDisclosure.style.display = 'block';
        }
        // Hide severity container
        if (severityContainer) {
          severityContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { severityContainer.style.display = 'none'; }, 300);
          
          // Clear severity selection when hiding
          const severityField = document.getElementById('immunocompromised_severity');
          if (severityField) {
            severityField.value = '';
          }
        }
      } else {
        // Hide both containers for 'No' or empty selection
        if (severityContainer) {
          severityContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { severityContainer.style.display = 'none'; }, 300);
          
          // Clear severity selection when hiding
          const severityField = document.getElementById('immunocompromised_severity');
          if (severityField) {
            severityField.value = '';
          }
        }
        if (progressiveDisclosure) {
          progressiveDisclosure.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { progressiveDisclosure.style.display = 'none'; }, 300);
        }
        // Clear reconsider field
        if (reconsiderField) {
          reconsiderField.value = '';
        }
      }
      
      // Update immune calculation when immunocompromised status changes
      console.log('DEBUG: immunocompromised field changed to:', this.value);
      
      // Handle timing issues - retry if function not available yet
      const tryCalculateImmune = () => {
        if (typeof window.calculateImmuneSusceptibility === 'function') {
          console.log('DEBUG: calling calculateImmuneSusceptibility from immunocompromised change event');
          window.calculateImmuneSusceptibility();
        } else {
          console.log('DEBUG: calculateImmuneSusceptibility function not available, retrying in 100ms');
          setTimeout(tryCalculateImmune, 100);
        }
      };
      tryCalculateImmune();
    });
  }
  
  // Progressive disclosure reconsider handler
  const reconsiderField = document.getElementById('immunocompromised_reconsider');
  if (reconsiderField) {
    reconsiderField.addEventListener('change', function() {
      const severityContainer = document.getElementById('immunocompromised_severity_container');
      const progressiveDisclosure = document.getElementById('immunocompromised_progressive_disclosure');
      const immunocompromisedField = document.getElementById('immunocompromised');
      
      if (this.value === 'Yes') {
        // User realized they are immunocompromised - show severity container
        if (severityContainer) {
          severityContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
          severityContainer.style.display = 'block';
        }
        // Hide progressive disclosure
        if (progressiveDisclosure) {
          progressiveDisclosure.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { progressiveDisclosure.style.display = 'none'; }, 300);
        }
        // Update main dropdown to reflect choice
        if (immunocompromisedField) {
          immunocompromisedField.value = 'Yes';
        }
      } else if (this.value === 'No') {
        // User realized they are not immunocompromised - hide everything
        if (severityContainer) {
          severityContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { severityContainer.style.display = 'none'; }, 300);
          
          // Clear severity selection
          const severityField = document.getElementById('immunocompromised_severity');
          if (severityField) {
            severityField.value = '';
          }
        }
        if (progressiveDisclosure) {
          progressiveDisclosure.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => { progressiveDisclosure.style.display = 'none'; }, 300);
        }
        // Update main dropdown to reflect choice
        if (immunocompromisedField) {
          immunocompromisedField.value = 'No';
        }
      }
      // For 'still_unsure', keep progressive disclosure visible and main dropdown as 'unsure'
      
      // Update immune calculation when reconsider status changes
      const tryCalculateImmune2 = () => {
        if (typeof window.calculateImmuneSusceptibility === 'function') {
          window.calculateImmuneSusceptibility();
        } else {
          setTimeout(tryCalculateImmune2, 100);
        }
      };
      tryCalculateImmune2();
    });
  }
  
  // Immunocompromised severity change handler
  const severityField = document.getElementById('immunocompromised_severity');
  if (severityField) {
    severityField.addEventListener('change', function() {
      // Update immune calculation when severity changes
      const tryCalculateImmune3 = () => {
        if (typeof window.calculateImmuneSusceptibility === 'function') {
          window.calculateImmuneSusceptibility();
        } else {
          setTimeout(tryCalculateImmune3, 100);
        }
      };
      tryCalculateImmune3();
    });
  }
  
  // Initialize time inputs
  ['exposure_hours', 'exposure_minutes', 'exposure_seconds'].forEach(id => {
    const elem = document.getElementById(id);
    if (elem) {
      elem.addEventListener('change', updateDeltaT);
      elem.addEventListener('input', updateDeltaT);
    }
  });
  
  // Run once to set initial values
  updateDeltaT();
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
  updateFitFactorValue();
  setupConditionalSections();
  setupAdvancedFieldValidation();
  
  // Set up slider labels and fix display issues
  document.querySelectorAll('.slider').forEach(slider => {
    // Handle slider label display
    const labelElement = document.querySelector(`label[for="${slider.id}"]`);
    if (labelElement) {
      const valueDisplay = labelElement.querySelector('.slider-value-label');
      if (valueDisplay) {
        valueDisplay.style.display = 'none';
      }
    }
    
    // Fix active class on labels
    const sliderContainer = slider.closest('.slider-container');
    if (sliderContainer) {
      const labels = sliderContainer.querySelectorAll('.slider-labels span');
      const sliderValue = parseInt(slider.value) || 0;
      
      // Update all labels - remove active class
      labels.forEach((label, index) => {
        label.classList.remove('active');
        if (index === sliderValue) {
          label.classList.add('active');
        }
      });
    }
    
    // Add change handler to keep labels in sync when slider changes
    slider.addEventListener('input', function() {
      const container = this.closest('.slider-container');
      if (container) {
        const allLabels = container.querySelectorAll('.slider-labels span');
        const currentValue = parseInt(this.value) || 0;
        
        allLabels.forEach((label, index) => {
          if (index === currentValue) {
            label.classList.add('active');
          } else {
            label.classList.remove('active');
          }
        });
      }
    });
  });
  // Re-show the live value labels for distance and time sliders
  ['x', 'vaccination_time', 'infection_time'].forEach(id => {
    const lbl = document.querySelector(`label[for="${id}"] .slider-value-label`);
    if (lbl) lbl.style.display = 'inline-block';
  });
  
  // Initialize time sliders if they exist
  const vaccinationTime = document.getElementById('vaccination_time');
  const infectionTime = document.getElementById('infection_time');
  
  if (vaccinationTime) {
    // Initial display and label highlight
    updateVaccinationTimeLabel(vaccinationTime.value);
    // Update display on slider move
    vaccinationTime.addEventListener('input', e => updateVaccinationTimeLabel(e.target.value));
  }
  
  if (infectionTime) {
    // Initial display and label highlight
    updateInfectionTimeLabel(infectionTime.value);
    // Update display on slider move
    infectionTime.addEventListener('input', e => updateInfectionTimeLabel(e.target.value));
  }
  
  // Initialize masked percentage slider
  const maskedPercentage = document.getElementById('masked_percentage');
  if (maskedPercentage) {
    updateMaskedPercentageLabel(maskedPercentage.value);
  }
  
  // Initialize mask fit slider
  const maskFitSlider = document.getElementById('mask_fit_slider');
  if (maskFitSlider) {
    // Set active state on the appropriate label
    const fitContainer = maskFitSlider.closest('.slider-container');
    if (fitContainer) {
      const fitLabels = fitContainer.querySelectorAll('.slider-labels span');
      const fitValue = parseInt(maskFitSlider.value) || 0;
      
      fitLabels.forEach((label, idx) => {
        if (idx === fitValue) {
          label.classList.add('active');
        } else {
          label.classList.remove('active');
        }
      });
      
      // Add change handler
      maskFitSlider.addEventListener('input', function() {
        const val = parseInt(this.value) || 0;
        fitLabels.forEach((label, idx) => {
          if (idx === val) {
            label.classList.add('active');
          } else {
            label.classList.remove('active');
          }
        });
      });
    }
  }
  
  // Initialize distance slider
  const distanceSlider = document.getElementById('x');
  if (distanceSlider) {
    distanceSlider.addEventListener('input', updateDistanceDisplay);
    // Initial update
    updateDistanceDisplay();
  }
  
  // Initialize masked percentage slider
  const maskedPercentageSlider = document.getElementById('masked_percentage');
  if (maskedPercentageSlider) {
    maskedPercentageSlider.addEventListener('input', function() {
      updateMaskedPercentageLabel(this.value);
    });
    // Initial update
    updateMaskedPercentageLabel(maskedPercentageSlider.value);
  }
  
  // Set up info box toggles
  const toggleFuncs = {
    togglePeopleInfo: () => toggleInfoBox('peopleInfo'),
    toggleVaccinationInfo: () => toggleInfoBox('vaccinationInfo'),
    toggleInfectionInfo: () => toggleInfoBox('infectionInfo'),
    toggleActivityInfo: () => toggleInfoBox('activityInfo'),
    toggleOthersActivityInfo: () => toggleInfoBox('othersActivityInfo'),
    toggleVocalizationInfo: () => toggleInfoBox('vocalizationInfo'),
    toggleMaskedPercentInfo: () => toggleInfoBox('maskedPercentInfo'),
    toggleDistanceInfo: () => toggleInfoBox('distanceInfo')
  };
  
  // Expose toggle functions to global scope
  Object.entries(toggleFuncs).forEach(([name, func]) => {
    window[name] = func;
  });
  
});

// Expose to global for inline attributes
window.updateFitFactorValue = updateFitFactorValue;
window.submitFormAsync = submitFormAsync;
window.updateVaccinationTimeLabel = updateVaccinationTimeLabel;
window.updateInfectionTimeLabel = updateInfectionTimeLabel;
window.updateMaskedPercentageLabel = updateMaskedPercentageLabel;
window.updateDeltaT = updateDeltaT;
window.toggleInfoBox = toggleInfoBox;
// Expose distance label updater for inline oninput
window.updateDistanceLabel = updateDistanceLabel;