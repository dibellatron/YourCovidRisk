// COVID Risk Calculator-specific JavaScript
// refactored to ES module: import pure computation modules
console.log('DEBUG: exposure-calculator.js module loading at', new Date().toISOString());
import { computeImmuneValue } from "./js/calculations/immuneSusceptibility.js";
import { getMultiplier, computeExhalationFlowRate } from "./js/calculations/exhalation.js";
import { computeInhalationFilter, computeExhalationFilter } from "./js/calculations/maskFilter.js";
import { computeVolume, computeACH } from "./js/calculations/environment.js";
import {
  peopleValues,
  peopleTickIndices,
  drawPeopleTicks,
  setupManualPeopleInput,
  positionPeopleSliderThumb
} from "./js/sliders/peopleSlider.js";
import { initializeSlider } from "./js/sliders/genericSlider.js";
import { saveFormState, restoreFormState, TAB_STORAGE_KEY } from "./js/stateManager.js";
import { initFormHandler } from "./js/formHandler.js";
// Alias distance display to our updateDistanceLabel for module event handling
const updateDistanceDisplay = window.updateDistanceLabel;

// DOM Ready wrapper function
// Create a global function that will be available immediately
window.calculateImmuneSusceptibility = function() {
  console.log('DEBUG: Global calculateImmuneSusceptibility wrapper called');
  // This will be populated once DOM loads
  if (window._calculateImmuneSusceptibilityImpl) {
    window._calculateImmuneSusceptibilityImpl();
  } else {
    console.log('DEBUG: Implementation not yet available, DOM may not be loaded');
  }
};

console.log('DEBUG: About to add DOMContentLoaded listener');
document.addEventListener("DOMContentLoaded", function() {
  console.log('DEBUG: DOMContentLoaded event fired!');
  // Debug code removed

  // People slider: draw ticks and support manual entry (moved to module)
  drawPeopleTicks();
  window.addEventListener('resize', drawPeopleTicks);
  setupManualPeopleInput();

  const activityValues = [
    { value: "1", display: "Sitting" },
    { value: "1.2", display: "Standing" },
    { value: "2.7", display: "Light exercise" },
    { value: "5.8", display: "Moderate exercise" },
    { value: "11", display: "Intense exercise" }
  ];

  const physicalIntensityValues = [
    { value: "Resting", display: "Sitting" },
    { value: "Standing", display: "Standing" },
    { value: "Light exercise", display: "Light exercise" },
    { value: "Moderate exercise", display: "Moderate exercise" },
    { value: "Heavy exercise", display: "Intense exercise" }
  ];

  const vocalizationValues = [
    { value: "Just breathing", display: "Just breathing" },
    { value: "Speaking", display: "Speaking" },
    { value: "Loud speaking", display: "Loud speaking" }
  ];

  /**
   * Update the activity_choice hidden field based on physical intensity and vocalization sliders.
   * Also update the user's breathing rate (p parameter) based on their activity level.
   */
  function updateActivityChoice() {
    console.log('=== updateActivityChoice() called ===');
    
    // Get current slider indices
    const physicalIdxField = document.getElementById('physical_intensity_index');
    const vocalizationIdxField = document.getElementById('vocalization_index');
    const userActivityIdxField = document.getElementById('activity_level_index');
    
    console.log('Field elements found:', {
      physicalIdxField: !!physicalIdxField,
      vocalizationIdxField: !!vocalizationIdxField,
      userActivityIdxField: !!userActivityIdxField
    });
    
    console.log('Raw field values:', {
      physical: physicalIdxField?.value || 'NOT FOUND',
      vocalization: vocalizationIdxField?.value || 'NOT FOUND',
      userActivity: userActivityIdxField?.value || 'NOT FOUND'
    });
    
    const physicalIdx = parseInt(physicalIdxField?.value || '0', 10);
    const vocalizationIdx = parseInt(vocalizationIdxField?.value || '0', 10);
    const userActivityIdx = parseInt(userActivityIdxField?.value || '0', 10);
    
    console.log('Parsed indices:', { physicalIdx, vocalizationIdx, userActivityIdx });
    
    // Map combinations to activity choice (1-5) for others' emission rates
    let activityChoice;
    
    if (vocalizationIdx === 0) {
      activityChoice = '1'; // Just breathing - sedentary
    } else if (vocalizationIdx === 1) {
      activityChoice = physicalIdx <= 1 ? '2' : '3'; // Speaking
    } else {
      activityChoice = physicalIdx <= 1 ? '4' : '5'; // Loud speaking
    }
    
    console.log('Calculated activity choice:', activityChoice);
    
    // Update user's breathing rate (p parameter) based on their activity level
    const baseBreathingRate = 0.08; // L/s baseline
    const activityMultipliers = [1.0, 1.2, 2.7, 5.8, 11.0];
    const userBreathingRate = baseBreathingRate * activityMultipliers[userActivityIdx];
    
    console.log('Calculated breathing rate:', userBreathingRate);
    
    // Calculate Q0 (others' exhalation flow rate) using multipliers table
    const physicalActivities = ['Resting', 'Standing', 'Light exercise', 'Moderate exercise', 'Heavy exercise'];
    const vocalActivities = ['Just breathing', 'Speaking', 'Loud speaking'];
    
    const physicalActivity = physicalActivities[physicalIdx] || 'Resting';
    const vocalActivity = vocalActivities[vocalizationIdx] || 'Just breathing';
    
    // Get multiplier from data table (accessing global covidRiskData)
    let multiplier = 1;
    console.log('Multiplier lookup debug:', {
      'window.covidRiskData exists': !!window.covidRiskData,
      'multipliers exists': !!(window.covidRiskData && window.covidRiskData.multipliers),
      'physicalActivity': physicalActivity,
      'vocalActivity': vocalActivity,
      'multipliers table': window.covidRiskData ? window.covidRiskData.multipliers : 'NO DATA'
    });
    
    if (window.covidRiskData && window.covidRiskData.multipliers && 
        window.covidRiskData.multipliers[physicalActivity] && 
        window.covidRiskData.multipliers[physicalActivity][vocalActivity]) {
      multiplier = window.covidRiskData.multipliers[physicalActivity][vocalActivity];
      console.log('Found multiplier:', multiplier);
    } else {
      console.error('Multiplier lookup failed!', {
        physicalActivity: physicalActivity,
        vocalActivity: vocalActivity,
        availablePhysical: window.covidRiskData ? Object.keys(window.covidRiskData.multipliers || {}) : 'NO DATA',
        availableVocal: window.covidRiskData && window.covidRiskData.multipliers && window.covidRiskData.multipliers[physicalActivity] ? 
                       Object.keys(window.covidRiskData.multipliers[physicalActivity]) : 'NO DATA'
      });
    }
    
    const othersExhalationRate = 0.08 * multiplier; // Base rate * multiplier
    
    console.log('Calculated Q0 parameters:', {
      physicalActivity: physicalActivity,
      vocalActivity: vocalActivity,
      multiplier: multiplier,
      Q0: othersExhalationRate
    });
    
    // Update the hidden fields
    const activityChoiceField = document.getElementById('activity_choice');
    const pField = document.getElementById('p');
    const Q0Field = document.getElementById('Q0');
    
    console.log('Target fields:', {
      activityChoiceField: !!activityChoiceField,
      pField: !!pField,
      Q0Field: !!Q0Field
    });
    
    if (activityChoiceField) {
      console.log('Before update - activity_choice value:', activityChoiceField.value);
      activityChoiceField.value = activityChoice;
      console.log('After update - activity_choice value:', activityChoiceField.value);
    } else {
      console.error('Could not find activity_choice field!');
    }
    
    if (pField) {
      console.log('Before update - p value:', pField.value);
      pField.value = userBreathingRate.toFixed(3);
      console.log('After update - p value:', pField.value);
    } else {
      console.error('Could not find p field!');
    }
    
    if (Q0Field) {
      console.log('Before update - Q0 value:', Q0Field.value);
      Q0Field.value = othersExhalationRate.toFixed(3);
      console.log('After update - Q0 value:', Q0Field.value);
    } else {
      console.error('Could not find Q0 field!');
    }
    
    console.log(`=== Activity updated - choice: ${activityChoice} (others: physical=${physicalIdx}/${physicalActivity}, vocal=${vocalizationIdx}/${vocalActivity}), Q0: ${othersExhalationRate.toFixed(3)} L/s, user breathing: ${userBreathingRate.toFixed(3)} L/s (activity=${userActivityIdx}) ===`);
  }

  // Make updateActivityChoice available globally for slider-labels.js
  window.updateActivityChoice = updateActivityChoice;


  // Initialize all sliders
  initializeSlider('N_slider', peopleValues, 'N', 'people_index', null);
  initializeSlider('activity_level_slider', activityValues, 'activity_level', 'activity_level_index', 'activity_level_display');
  initializeSlider('physical_intensity_slider', physicalIntensityValues, 'physical_intensity', 'physical_intensity_index', 'physical_intensity_display');
  initializeSlider('vocalization_slider', vocalizationValues, 'vocalization', 'vocalization_index', 'vocalization_display');
  
  // Initialize activity choice on page load
  setTimeout(function() {
    console.log('=== MANUAL TEST CALL ===');
    updateActivityChoice();
  }, 2000); // Wait 2 seconds after page load to ensure everything is initialized

  // Track whether this is the first calculation in this session
  let isFirstCalculation = true;

  // AJAX form submission and reset handlers
  initFormHandler();

  // Setup sliders to update their value labels
  document.querySelectorAll('.slider').forEach(function(slider) {
    const updateSliderValue = function() {
      // Find the slider value element
      let valueLabel = slider.closest('.slider-container').querySelector('.slider-value');
      if (valueLabel) {
        // Handle each type of slider
        if (slider.id === 'N_slider' || slider.classList.contains('people-slider')) {
          // Get the current index
          const sliderIndex = parseInt(slider.value);

          // Get the corresponding people value from our predefined array
          const peopleCount = peopleValues[sliderIndex];

          // Format display value grammatically (1 person vs 2 people)
          const displayValue = peopleCount === 1 ? "1 person" :
                            peopleCount >= 1000 ? `${peopleCount.toLocaleString()} people` : `${peopleCount} people`;
          valueLabel.textContent = displayValue;

          // Position thumb at correct point if needed
          positionPeopleSliderThumb(slider, sliderIndex);

          // Update the hidden form elements
          const indexField = document.getElementById('people_index');
          if (indexField) {
            indexField.value = sliderIndex;
          }

          // Set the actual N value to the people count
          const nInput = document.getElementById('N');
          if (nInput) {
            nInput.value = peopleCount;
          }
        } else if (slider.id === 'activity_level_slider') {
          // Get the current index
          const sliderIndex = parseInt(slider.value);

          // Get the corresponding activity value
          const activity = activityValues[sliderIndex];

          // Update the value label
          valueLabel.textContent = activity.display;

          // Update the hidden fields
          const indexField = document.getElementById('activity_level_index');
          if (indexField) {
            indexField.value = sliderIndex;
          }

          const valueField = document.getElementById('activity_level');
          if (valueField) {
            valueField.value = activity.value;
          }

          const displayField = document.getElementById('activity_level_display');
          if (displayField) {
            displayField.value = activity.display;
          }

          // Update the displayed value in the label with proper color styling
          const labelElement = document.querySelector('label[for="activity_level"]');
          if (labelElement) {
            const spanElement = labelElement.querySelector('span');
            if (spanElement) {
              // Update the main span text
              spanElement.innerHTML = `Your level of physical activity: <span class="slider-value-label">${activity.display}</span>`;
            }
          }
          
          // Update activity choice parameters
          updateActivityChoice();
        } else if (slider.id === 'physical_intensity_slider') {
          // Get the current index
          const sliderIndex = parseInt(slider.value);

          // Get the corresponding physical intensity value
          const intensity = physicalIntensityValues[sliderIndex];

          // Update the value label
          valueLabel.textContent = intensity.display;

          // Update the hidden fields
          const indexField = document.getElementById('physical_intensity_index');
          if (indexField) {
            indexField.value = sliderIndex;
          }

          const valueField = document.getElementById('physical_intensity');
          if (valueField) {
            valueField.value = intensity.value;
          }

          const displayField = document.getElementById('physical_intensity_display');
          if (displayField) {
            displayField.value = intensity.display;
          }

          // Update the text that shows the selected value
          const container = slider.closest('div');
          if (container && container.querySelector('label')) {
            const label = container.querySelector('label');
            if (label) {
              const span = label.querySelector('span');
              if (span) {
                // Make sure the label shows the current value
                // Update with proper HTML to get the color styling
                span.innerHTML = `Physical activity of other people: <span class="slider-value-label">${intensity.display}</span>`;
              }
            }
          }
          
          // Update activity choice parameters
          updateActivityChoice();
        } else if (slider.id === 'vocalization_slider') {
          // Get the current index
          const sliderIndex = parseInt(slider.value);

          // Get the corresponding vocalization value
          const vocalization = vocalizationValues[sliderIndex];

          // Update the value label
          valueLabel.textContent = vocalization.display;

          // Update the hidden fields
          const indexField = document.getElementById('vocalization_index');
          if (indexField) {
            indexField.value = sliderIndex;
          }

          const valueField = document.getElementById('vocalization');
          if (valueField) {
            valueField.value = vocalization.value;
          }

          const displayField = document.getElementById('vocalization_display');
          if (displayField) {
            displayField.value = vocalization.display;
          }

          // Update the text that shows the selected value
          const container = slider.closest('div');
          if (container && container.querySelector('label')) {
            const label = container.querySelector('label');
            if (label) {
              const span = label.querySelector('span');
              if (span) {
                // Make sure the label shows the current value
                // Update with proper HTML to get the color styling
                span.innerHTML = `Vocal activity of other people: <span class="slider-value-label">${vocalization.display}</span>`;
              }
            }
          }
          
          // Update activity choice parameters
          updateActivityChoice();
        } else {
          valueLabel.textContent = slider.value;
        }
      }

      // Also update any slider-value-label in the parent element's label
      const parentDiv = slider.closest('div');
      if (parentDiv && parentDiv.previousElementSibling && parentDiv.previousElementSibling.tagName === 'LABEL') {
        const labelValueSpan = parentDiv.previousElementSibling.querySelector('.slider-value-label');
        if (labelValueSpan) {
          // Special case handling for different sliders
          if (slider.id === 'vaccination_time' || slider.id === 'infection_time') {
            const val = parseInt(slider.value);
            labelValueSpan.textContent = val === 1 ? '1 month ago' : `${val} months ago`;
            // Also update the hidden display field
            const displayField = document.getElementById(`${slider.id}_display`);
            if (displayField) {
              displayField.value = val === 1 ? '1 month ago' : `${val} months ago`;
            }
          } else if (slider.id === 'x') {
            // Distance slider is now handled in the HTML template with inline JavaScript
            // This section is kept for backward compatibility but won't be called for the new slider
            return;
          } else if (slider.id === 'masked_percentage') {
            // Convert percentage slider to categorical text
            const value = parseInt(slider.value);
            let text;

            if (value === 0) text = 'None';
            else if (value === 25) text = 'Some (25%)';
            else if (value === 50) text = 'Half\n(50%)';
            else if (value === 75) text = 'Most\n(75%)';
            else if (value === 100) text = 'All\n(100%)';
            else text = `${value}%`;

            labelValueSpan.textContent = text;

            // Update the text that shows the selected value in the label
            const container = slider.closest('div').parentElement;
            if (container && container.querySelector('label')) {
              const label = container.querySelector('label');
              if (label && label.querySelector('span')) {
                const span = label.querySelector('span');
                if (span) {
                  // Update with proper HTML to get the color styling
                  span.innerHTML = `How many of them were masked? <span class="slider-value-label">${text}</span>`;
                }
              }
            }

            // Update the percentage_masked hidden field
            const percentField = document.getElementById('percentage_masked');
            if (percentField) {
              percentField.value = (value / 100).toString();
            }

            // Update hidden value field
            const valueField = document.getElementById('masked_percentage_value');
            if (valueField) {
              valueField.value = value.toString();
            }
          } else if (slider.id === 'covid_cautious_level') {
            // Convert level 1-5 to categorical text
            const level = parseInt(slider.value);
            let text;

            if (level === 1) text = 'Not at all';
            else if (level === 2) text = 'Slightly';
            else if (level === 3) text = 'Moderately';
            else if (level === 4) text = 'Very';
            else if (level === 5) text = 'Extremely';

            labelValueSpan.textContent = text;

            // Update hidden field
            const cautionField = document.getElementById('covid_cautious');
            if (cautionField) {
              cautionField.value = text;
            }
          } else if (slider.id === 'N_slider' || slider.classList.contains('people-slider')) {
            // Get the current index
            const sliderIndex = parseInt(slider.value);

            // Get the corresponding people value from our predefined array
            const peopleCount = peopleValues[sliderIndex];

            // Format display value grammatically (1 person vs 2 people)
            const displayText = peopleCount === 1 ? "1 person" : `${peopleCount} people`;
            labelValueSpan.textContent = displayText;

            // We need to update a hidden field that holds the real value for N
            const nInput = document.getElementById('N');
            if (nInput) {
              nInput.value = peopleCount;
            }
          } else {
            // Default case
            labelValueSpan.textContent = slider.value;
          }
        }
      }
    };

    // Initialize slider values
    updateSliderValue();

    // Update on change
    slider.addEventListener('input', updateSliderValue);


    // Also update when window resizes to ensure alignment
    window.addEventListener('resize', updateSliderValue);
  });
  // Global variables to track form elements
  const formElements = {
    // Mask-related
    masked: document.getElementById('masked'),
    maskType: document.getElementById('mask_type'),
    maskTypeContainer: document.getElementById('mask_type_container'),
    maskFit: document.getElementById('mask_fit'),
    maskFitSlider: document.getElementById('mask_fit_slider'),
    maskFitContainer: document.getElementById('mask_fit_container'),
    fitFactor: document.getElementById('fit_factor_input'),
    fitFactorContainer: document.getElementById('fit_factor_container'),

    // Vaccination-related
    recentVaccination: document.getElementById('recent_vaccination'),
    vaccinationTime: document.getElementById('vaccination_time'),
    vaccinationTimeContainer: document.getElementById('vaccination_time_container'),

    // Infection-related
    recentInfection: document.getElementById('recent_infection'),
    infectionTime: document.getElementById('infection_time'),
    infectionTimeContainer: document.getElementById('infection_time_container'),

    // Environment-related
    indoorOutdoor: document.getElementById('indoor_outdoor'),
    environmentContainer: document.getElementById('environment_container'),
    ach: document.getElementById('ACH'),
    carTypeContainer: document.getElementById('car-type-container'),
    carType: document.getElementById('car_type'),
    airplaneTypeContainer: document.getElementById('airplane-type-container'),
    airplaneSizeSlider: document.getElementById('airplane_size_slider'),
    airplaneType: document.getElementById('airplane_type'),
    activityLevelSlider: document.getElementById('activity_level_slider'),
    physicalIntensitySlider: document.getElementById('physical_intensity_slider'),
    vocalizationSlider: document.getElementById('vocalization_slider'),
    distanceSlider: document.getElementById('x'),


    // Others masked-related
    maskedPercentage: document.getElementById('masked_percentage'),
    maskedPercentageContainer: document.getElementById('masked_percentage_container'),
    othersMaskType: document.getElementById('others_mask_type'),
    othersMaskTypeContainer: document.getElementById('others_mask_type_container'),

    // Hidden fields
    fi: document.getElementById('f_i'),
    fe: document.getElementById('f_e'),
    percentageMasked: document.getElementById('percentage_masked'),
    environmentVolume: document.getElementById('environment_volume'),
    immuneField: document.getElementById('immune'),

    // Advanced fields
    roomVolume: document.getElementById('room_volume'),
    customACH: document.getElementById('custom_ACH'),

    // Form
    priorForm: document.getElementById('priorForm'),

    // Advanced
    advancedFields: document.getElementById('advancedFields'),
    advanced: document.getElementById('advanced')
  };

  // Form data
  initFormData();
  // Restore user form state from prior session
  restoreFormState();

  // ========================
  // Initialization functions
  // ========================

  function initFormData() {
    console.log("Initializing form with direct server-side values");

    // Add mask fit container and fit factor container to animation list
    if (document.getElementById('mask_fit_container')) {
      document.getElementById('mask_fit_container').classList.add('animate-container');
    }
    if (document.getElementById('fit_factor_container')) {
      document.getElementById('fit_factor_container').classList.add('animate-container');
    }

    // Initialize mask fit slider
    initializeMaskFitSlider();

    // Populate all select dropdowns
    populateDropdowns();

    // Setup listeners for dynamic behavior
    setupEventListeners();

    // Initialize visibility based on initial values
    initializeVisibility();

    // Critical - make a second pass to restore the environment value
    // after all dropdowns have been populated
    setTimeout(function() {
      // First handle direct simple cases
      restoreSelectedEnvironment();

      // Show/hide conditional sections based on form values
      initializeVisibility();

      // Make sure no values are cleared during this process
      console.log("Form initialization complete");
    }, 100);
  }

  function populateDropdowns() {
    // Populate mask types for user and others
    populateSelect(formElements.maskType, covidRiskData.maskTypes);
    populateSelect(formElements.othersMaskType, covidRiskData.maskTypes);

    // Populate time periods for vaccination and infection
    populateSelect(formElements.vaccinationTime, covidRiskData.timePeriods);
    populateSelect(formElements.infectionTime, covidRiskData.timePeriods);

    // Populate activity levels
    populateSelect(document.getElementById('activity_level'), covidRiskData.activityLevels);

    // Populate physical intensity
    populateSelect(document.getElementById('physical_intensity'), covidRiskData.physicalIntensityLevels);

    // Populate vocalization options
    populateSelect(document.getElementById('vocalization'), covidRiskData.vocalizationTypes);

    // Populate number of people
    populateNumberSelect(document.getElementById('N'), covidRiskData.peopleNumbers);

    // Populate car types
    populateSelect(formElements.carType, covidRiskData.carTypes);

    // No longer populating the airplane types dropdown as we're using a slider now

    // Populate masked percentages
    populateSelect(formElements.maskedPercentage, covidRiskData.maskedPercentages);

    // Populate distances
    populateSelect(document.getElementById('x'), covidRiskData.distances);

    // Populate environments with ACH values
    populateEnvironments(formElements.ach, covidRiskData.environments);
  }

  function setupEventListeners() {
    // ------------------------------------------------------------
    // Keep the hidden delta_t field in sync with the three
    // <select> pickers (hours / minutes / seconds) at all times so
    // it is already correct when the user presses the *Calculate*
    // button.  Relying on handleFormSubmit to compute delta_t *just
    // before* we package FormData proved brittle – a fast click on
    // the submit button straight after editing Fit Factor sometimes
    // runs before the hidden field has been updated, yielding
    // delta_t = 0 and therefore an unrealistically tiny infection
    // probability.
    // ------------------------------------------------------------
    function updateDeltaTField() {
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

    ['exposure_hours', 'exposure_minutes', 'exposure_seconds']
      .forEach((id) => {
        const sel = document.getElementById(id);
        if (sel) {
          sel.addEventListener('change', updateDeltaTField);
          sel.addEventListener('input', updateDeltaTField);
        }
      });

    // Run once on load so delta_t is correct even before the user
    // changes the pickers.
    updateDeltaTField();
    // Mask-related event listeners
    formElements.masked.addEventListener('change', handleMaskedChange);
    formElements.maskType.addEventListener('change', handleMaskTypeChange);
    formElements.maskFitSlider && formElements.maskFitSlider.addEventListener('input', updateFi);
    if (formElements.fitFactor) {
      const ffInput = formElements.fitFactor;
      // Sanitize input: allow only digits and single decimal point
      ffInput.addEventListener('input', function() {
        let val = ffInput.value;
        // Remove non-digit, non-dot characters
        val = val.replace(/[^0-9.]/g, '');
        // Ensure only one decimal point
        const parts = val.split('.');
        if (parts.length > 2) {
          val = parts[0] + '.' + parts.slice(1).join('');
        }
        if (ffInput.value !== val) {
          ffInput.value = val;
        }
      });
      // Validate on blur and Enter
      ffInput.addEventListener('blur', validateFitFactor);
      ffInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
          validateFitFactor();
        }
      });
    }

    // Function to validate fit factor when user leaves the field
    function validateFitFactor() {
      if (!formElements.fitFactor) return true;
      updateFi();
      return true;
    }

    // Vaccination-related event listeners
    formElements.recentVaccination.addEventListener('change', handleRecentVaccinationChange);
    formElements.vaccinationTime.addEventListener('change', calculateImmuneSusceptibility);

    // Infection-related event listeners
    formElements.recentInfection.addEventListener('change', handleRecentInfectionChange);
    formElements.infectionTime.addEventListener('change', calculateImmuneSusceptibility);

    // Environment-related event listeners
    formElements.indoorOutdoor.addEventListener('change', handleIndoorOutdoorChange);
    // Clear validation error when required dropdowns change
    const clearValidation = e => {
      e.target.classList.remove('validation-error');
      const msg = e.target.closest('.select-wrapper')?.querySelector('.validation-message');
      if (msg) msg.style.display = 'none';
    };
    // Bind clearValidation to all dropdowns, including conditional ones
    ['masked', 'recent_vaccination', 'recent_infection', 'indoor_outdoor', 'mask_type', 'others_mask_type', 'ACH']
      .forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', clearValidation);
      });

    // Add input filtering for all advanced numeric fields
    
    // Add validation clearing for advanced input fields when they change
    ['covid_prevalence', 'relative_humidity', 'temperature', 'co2', 'custom_ACH', 'room_volume'].forEach(id => {
      const field = document.getElementById(id);
      if (field) {
        field.addEventListener('input', function() {
          // Clear validation errors when user starts typing
          this.classList.remove('validation-error');
          this.setCustomValidity('');
        });
      }
    });

    // Setup slider value updating for activity sliders
    formElements.activityLevelSlider && formElements.activityLevelSlider.addEventListener('input', updateActivityLevelDisplay);
    formElements.physicalIntensitySlider && formElements.physicalIntensitySlider.addEventListener('input', updatePhysicalIntensityDisplay);
    formElements.vocalizationSlider && formElements.vocalizationSlider.addEventListener('input', updateVocalizationDisplay);
    formElements.distanceSlider && formElements.distanceSlider.addEventListener('input', updateDistanceDisplay);
    formElements.maskedPercentage && formElements.maskedPercentage.addEventListener('input', updateMaskedPercentageDisplay);

    // Save the exact environment display text when user makes a selection
    formElements.ach.addEventListener('change', function(e) {
      // First handle the normal change event
      handleAchChange();

      // Store the displayed text of the selected option - this is what we want to preserve visually
      if (this.selectedIndex > 0) {
        const selectedOption = this.options[this.selectedIndex];
        const textField = document.getElementById('selected_environment_text');
        if (textField) {
          // Store just the text as-is - no JSON, no parsing
          textField.value = selectedOption.textContent;

            // Also store the option index for unambiguous restoration
            const indexField = document.getElementById('selected_environment_index');
            if (indexField) {
              indexField.value = this.selectedIndex;
            }

          // Also add it to our session storage for backup
          const formState = JSON.parse(sessionStorage.getItem(TAB_STORAGE_KEY) || '{}');
          formState.selected_environment_text = selectedOption.textContent;
          sessionStorage.setItem(TAB_STORAGE_KEY, JSON.stringify(formState));

          console.log("Saved selected environment text:", selectedOption.textContent);
        }
      }
    });

    formElements.carType.addEventListener('change', updateCarVolume);
    formElements.airplaneType.addEventListener('change', updateAirplaneVolume);

    // Masked percentage event listener
    formElements.maskedPercentage.addEventListener('change', handleMaskedPercentageChange);
    formElements.maskedPercentage.addEventListener('input', handleMaskedPercentageChange);
    formElements.othersMaskType.addEventListener('change', updateFe);

    // Physical intensity and vocalization
    document.getElementById('physical_intensity').addEventListener('change', updateExhalationFlowRate);
    document.getElementById('vocalization').addEventListener('change', updateExhalationFlowRate);

    // Custom ACH field
    formElements.customACH.addEventListener('input', handleCustomAchInput);

    // Advanced toggle
    document.getElementById('toggleAdvancedBtn').addEventListener('click', toggleAdvancedFields);

    // Form reset handler (submit is wired further up for the main AJAX call)
    // We only need a dedicated listener for the reset button here.
    document.querySelector('button[type="reset"]').addEventListener('click', handleFormReset);

    // Form state saving
    const container = document.querySelector('.form-container');
    container.addEventListener('change', saveFormState);
    container.addEventListener('input', saveFormState);
  }

  function initializeVisibility() {
    // Run each visibility handler to update UI based on values
    handleMaskedChange();
    handleRecentVaccinationChange();
    handleRecentInfectionChange();
    handleIndoorOutdoorChange();
    handleMaskedPercentageChange();

    // Ensure correct visibility of mask fit fields based on mask type
    if (formElements.masked && formElements.masked.value === "Yes" &&
        formElements.maskType && formElements.maskType.value) {
      handleMaskTypeChange();
    }

    // Update calculated fields
    calculateImmuneSusceptibility();
    updateExhalationFlowRate();

    // Initialize slider labels
    updateActivityLevelDisplay();
    updatePhysicalIntensityDisplay();
    updateVocalizationDisplay();
    updateDistanceDisplay();
    updateMaskedPercentageDisplay();

    // Set up airplane size slider if visible
    const airplaneSizeSlider = document.getElementById('airplane_size_slider');
    if (airplaneSizeSlider) {
      airplaneSizeSlider.addEventListener('input', updateAirplaneSize);
    }

    // Show/hide advanced section based on advanced flag
    if (formElements.advanced.value === 'true') {
      formElements.advancedFields.style.display = 'block';
    }

    // For form submission restore, we need a special force-update
    // for conditional fields that might be hidden/shown based on parent values
    if (document.referrer.includes('/calculate_prior')) {
      console.log("Form restored after submission - forcing update of hidden fields");

      // Force the display of dependent fields if we have data for them
      if (formElements.masked.value === "Yes" && formElements.maskType.getAttribute('data-selected-value')) {
        formElements.maskTypeContainer.style.display = "block";
      }

      if (formElements.recentVaccination.value === "Yes" && formElements.vaccinationTime.getAttribute('data-selected-value')) {
        formElements.vaccinationTimeContainer.style.display = "block";
      }

      if (formElements.recentInfection.value === "Yes" && formElements.infectionTime.getAttribute('data-selected-value')) {
        formElements.infectionTimeContainer.style.display = "block";
      }

      if (formElements.othersMasked.value === "Yes") {
        if (formElements.maskedPercentage.getAttribute('data-selected-value')) {
          formElements.maskedPercentageContainer.style.display = "block";

          if (formElements.othersMaskType.getAttribute('data-selected-value')) {
            formElements.othersMaskTypeContainer.style.display = "block";
          }
        }
      }
    }
  }

  // ========================
  // Helper functions
  // ========================

  function populateSelect(selectElement, options) {
    if (!selectElement) return;

    // Get the current value before we repopulate
    const currentValue = selectElement.value;
    // Also check our data-selected-value attribute for server value
    const serverValue = selectElement.getAttribute('data-selected-value');

    options.forEach(option => {
      const optionElement = document.createElement('option');
      optionElement.value = option.value;
      optionElement.textContent = option.label;

      // Select this option if it matches the current or server value
      if (option.value === currentValue || option.value === serverValue) {
        optionElement.selected = true;
      }

      selectElement.appendChild(optionElement);
    });

    // After populating, try to restore the value
    if (serverValue && serverValue !== '') {
      selectElement.value = serverValue;
    } else if (currentValue) {
      selectElement.value = currentValue;
    }
  }

  function populateNumberSelect(selectElement, numbers) {
    if (!selectElement) return;

    // Get the current value before we repopulate
    const currentValue = selectElement.value;
    // Also check our data-selected-value attribute for server value
    const serverValue = selectElement.getAttribute('data-selected-value');

    numbers.forEach(number => {
      const option = document.createElement('option');
      const numStr = number.toString();
      option.value = numStr;
      option.textContent = number >= 1000 ? number.toLocaleString() : numStr;

      // Select this option if it matches the current or server value
      if (numStr === currentValue || numStr === serverValue) {
        option.selected = true;
      }

      selectElement.appendChild(option);
    });

    // After populating, try to restore the value
    if (serverValue && serverValue !== '') {
      selectElement.value = serverValue;
    } else if (currentValue) {
      selectElement.value = currentValue;
    }
  }

  // Function to initialize the mask fit slider
  function initializeMaskFitSlider() {
    const maskFitSlider = formElements.maskFitSlider;
    const maskFitHidden = formElements.maskFit;
    const maskFitDisplay = document.getElementById('mask_fit_display');
    const maskFitIndex = document.getElementById('mask_fit_index');
    
    if (!maskFitSlider || !maskFitHidden) return;
    
    // Function to update mask fit display and hidden fields
    function updateMaskFitDisplay() {
      const sliderValue = parseInt(maskFitSlider.value);
      let fitValue = "";
      let displayText = "Select fit level";
      
      // Map slider position to fit value
      if (sliderValue === 0) {
        fitValue = "Loose";
        displayText = "Loose fit";
      } else if (sliderValue === 1) {
        fitValue = "Average";
        displayText = "Average fit";
      } else if (sliderValue === 2) {
        fitValue = "Snug";
        displayText = "Feels pretty snug";
      } else if (sliderValue === 3) {
        fitValue = "Qualitative";
        displayText = "Passes fit test";
      }
      
      // Update hidden fields
      maskFitHidden.value = fitValue;
      
      if (maskFitDisplay) {
        maskFitDisplay.value = displayText;
      }
      
      if (maskFitIndex) {
        maskFitIndex.value = sliderValue.toString();
      }
      
      // Update active labels
      const sliderLabels = maskFitSlider.closest('.slider-container').querySelector('.slider-labels');
      if (sliderLabels) {
        const labels = sliderLabels.querySelectorAll('span');
        
        // Remove active class from all labels
        labels.forEach(label => {
          label.classList.remove('active');
        });
        
        // Add active class to selected label
        if (labels[sliderValue]) {
          labels[sliderValue].classList.add('active');
        }
      }
      
      // Update f_i based on new fit value
      updateFi();
    }
    
    // Set initial value from hidden field if available
    const savedValue = maskFitHidden.getAttribute('data-selected-value');
    let initialIndex = 1; // Default to Average (index 1)
    
    if (savedValue) {
      if (savedValue === "Loose") initialIndex = 0;
      else if (savedValue === "Average") initialIndex = 1;
      else if (savedValue === "Snug") initialIndex = 2;
      else if (savedValue === "Qualitative") initialIndex = 3;
    }
    
    if (maskFitIndex && maskFitIndex.value) {
      initialIndex = parseInt(maskFitIndex.value);
    }
    
    maskFitSlider.value = initialIndex;
    
    // Set up event listeners
    maskFitSlider.addEventListener('input', updateMaskFitDisplay);
    
    // Initialize with correct display
    updateMaskFitDisplay();
  }

  function populateEnvironments(selectElement, environments) {
    if (!selectElement) return;
    // BEFORE repopulating remove any existing options to avoid duplicates
    selectElement.innerHTML = '';

    // --- Insert default blank <option> so the user must choose explicitly ---
    const blankOpt = document.createElement('option');
    blankOpt.value = '';
    selectElement.appendChild(blankOpt);

    // Values coming from server (data attributes) or from earlier JS state
    const serverValue = selectElement.getAttribute('data-selected-value') || '';
    const serverText  = document.getElementById('selected_environment_text')?.value || '';

    // Track whether we already set the correct option
    let optionChosen = false;

    environments.forEach(envGroup => {
      const optgroup = document.createElement('optgroup');
      optgroup.label = envGroup.group;

      envGroup.options.forEach(env => {
        const option = document.createElement('option');
        option.value = env.value;
        option.textContent = env.label;

        // Add data attributes
        option.setAttribute('data-volume', env.volume);
        if (env.range) {
          option.setAttribute('data-range', env.range);
        }

        // Decide if this option should be selected.
        if (!optionChosen) {
          const valueMatches = env.value === serverValue;
          const textMatches  = serverText && env.label === serverText;

          // If we have both value and text, require both to match. If we only
          // have value (no serverText), fall back to first value match.
          if (valueMatches && (serverText ? textMatches : true)) {
            option.selected = true;
            optionChosen = true;
          }
        }

        optgroup.appendChild(option);
      });

      selectElement.appendChild(optgroup);
    });

    // Fire change event so dependent UI updates.
    if (optionChosen) {
      const evt = new Event('change', { bubbles: true });
      selectElement.dispatchEvent(evt);
    }
  }

  // ========================
  // Event handlers
  // ========================

  function handleMaskedChange() {
    console.log("handleMaskedChange called, masked =", formElements.masked.value);
    
    if (formElements.masked.value === "Yes") {
      // First set to initial state and trigger reflow
      formElements.maskTypeContainer.style.animation = 'none';
      formElements.maskTypeContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.maskTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.maskTypeContainer.style.display = "block";
      formElements.maskType.setAttribute('required', true);

      // If we have a data-selected-value, use it
      const savedValue = formElements.maskType.getAttribute('data-selected-value');
      if (savedValue && savedValue !== '') {
        formElements.maskType.value = savedValue;
        console.log("Restored saved mask type:", savedValue);

        // If there's a selected mask type, also show the fit options
        handleMaskTypeChange();
      }
    } else {
      console.log("User is not masked, hiding mask-related fields");
      
      // Only animate if the element is currently visible
      if (formElements.maskTypeContainer.style.display === "block") {
        // Apply fade-out animation
        formElements.maskTypeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

        // Wait for animation to complete, then hide the element
        setTimeout(() => {
          formElements.maskTypeContainer.style.display = "none";
        }, 300);
      } else {
        formElements.maskTypeContainer.style.display = "none";
      }

      formElements.maskType.removeAttribute('required');

      // Hide mask fit container and fit factor container as well
      const maskFitContainer = document.getElementById('mask_fit_container');
      const fitFactorContainer = document.getElementById('fit_factor_container');

      if (maskFitContainer) {
        if (maskFitContainer.style.display === "block") {
          maskFitContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => {
            maskFitContainer.style.display = "none";
          }, 300);
        } else {
          maskFitContainer.style.display = "none";
        }
      }

      if (fitFactorContainer) {
        if (fitFactorContainer.style.display === "block") {
          fitFactorContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => {
            fitFactorContainer.style.display = "none";
          }, 300);
        } else {
          fitFactorContainer.style.display = "none";
        }
      }

      // Don't clear the values - just make them not required
    }
    
    // IMPORTANT: Update f_i anytime masked status changes
    updateFi();
    console.log("handleMaskedChange complete, f_i =", formElements.fi.value);
  }

  // New function to handle mask type changes
  function handleMaskTypeChange() {
    // Only proceed if user is masked
    if (formElements.masked.value !== "Yes") return;

    // Check if mask type is selected
    if (formElements.maskType.value) {
      const maskType = formElements.maskType.value;
      
      // Show the mask fit container
      const maskFitContainer = document.getElementById('mask_fit_container');
      const maskFitSlider = formElements.maskFitSlider;
      
      if (maskFitContainer && maskFitSlider) {
        // First set to initial state and trigger reflow
        maskFitContainer.style.animation = 'none';
        maskFitContainer.offsetHeight; // Force reflow

        // Apply the animation and show the container
        maskFitContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
        maskFitContainer.style.display = "block";
        
        // Update slider options based on mask type
        const sliderLabels = maskFitSlider.closest('.slider-container').querySelector('.slider-labels');
        
        if (sliderLabels) {
          const qualitativeFitLabel = sliderLabels.querySelector('span:nth-child(4)');
          
          // Show/hide qualitative fit option based on mask type
          if (maskType === "Cloth" || maskType === "Surgical") {
            // Cloth and surgical masks don't have qualitative fit test option
            sliderLabels.classList.remove('four-options');
            sliderLabels.classList.add('three-options');
            if (qualitativeFitLabel) {
              qualitativeFitLabel.style.display = 'none';
            }
            maskFitSlider.max = "2";
            
            // If currently on option 3, reset to option 1
            if (parseInt(maskFitSlider.value) > 2) {
              maskFitSlider.value = "1";
              // Trigger input event to update display
              maskFitSlider.dispatchEvent(new Event('input'));
            }
            
            console.log(`'Passes qualitative fit test' option not available for ${maskType}`);
          } else {
            // Other mask types have qualitative fit test option
            sliderLabels.classList.remove('three-options');
            sliderLabels.classList.add('four-options');
            if (qualitativeFitLabel) {
              qualitativeFitLabel.style.display = 'block';
            }
            maskFitSlider.max = "3";
            
            console.log(`'Passes qualitative fit test' option available for ${maskType}`);
          }
        }

        // Only show fit factor container for masks that support quantitative fit testing
        const fitFactorContainer = document.getElementById('fit_factor_container');
        if (fitFactorContainer) {
          const masksSupportingFitFactor = ['KN94/95', 'N95', 'N99', 'Elastomeric with P100/N100 filters'];
          if (masksSupportingFitFactor.includes(maskType)) {
            fitFactorContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
            fitFactorContainer.style.display = "block";
          } else {
            // Hide for cloth/surgical masks
            fitFactorContainer.style.display = "none";
          }
        }
      }
    } else {
      // Hide the mask fit container if no mask type is selected
      const maskFitContainer = document.getElementById('mask_fit_container');
      const fitFactorContainer = document.getElementById('fit_factor_container');

      if (maskFitContainer) {
        if (maskFitContainer.style.display === "block") {
          maskFitContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => {
            maskFitContainer.style.display = "none";
          }, 300);
        } else {
          maskFitContainer.style.display = "none";
        }
      }

      if (fitFactorContainer) {
        if (fitFactorContainer.style.display === "block") {
          fitFactorContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
          setTimeout(() => {
            fitFactorContainer.style.display = "none";
          }, 300);
        } else {
          fitFactorContainer.style.display = "none";
        }
      }
    }

    updateFi();
  }

  function handleRecentVaccinationChange() {
    if (formElements.recentVaccination.value === "Yes") {
      // First set to initial state and trigger reflow
      formElements.vaccinationTimeContainer.style.animation = 'none';
      formElements.vaccinationTimeContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.vaccinationTimeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.vaccinationTimeContainer.style.display = "block";
      formElements.vaccinationTime.setAttribute('required', true);

      // If we have a data-selected-value, use it
      const savedValue = formElements.vaccinationTime.getAttribute('data-selected-value');
      if (savedValue && savedValue !== '') {
        formElements.vaccinationTime.value = savedValue;
      }
    } else {
      // Only animate if the element is currently visible
      if (formElements.vaccinationTimeContainer.style.display === "block") {
        // Apply fade-out animation
        formElements.vaccinationTimeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

        // Wait for animation to complete, then hide the element
        setTimeout(() => {
          formElements.vaccinationTimeContainer.style.display = "none";
        }, 300);
      } else {
        formElements.vaccinationTimeContainer.style.display = "none";
      }

      formElements.vaccinationTime.removeAttribute('required');
      // Don't clear the value - just make it not required
    }
    calculateImmuneSusceptibility();
  }

  function handleRecentInfectionChange() {
    if (formElements.recentInfection.value === "Yes") {
      // First set to initial state and trigger reflow
      formElements.infectionTimeContainer.style.animation = 'none';
      formElements.infectionTimeContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.infectionTimeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.infectionTimeContainer.style.display = "block";
      formElements.infectionTime.setAttribute('required', true);

      // If we have a data-selected-value, use it
      const savedValue = formElements.infectionTime.getAttribute('data-selected-value');
      if (savedValue && savedValue !== '') {
        formElements.infectionTime.value = savedValue;
      }
    } else {
      // Only animate if the element is currently visible
      if (formElements.infectionTimeContainer.style.display === "block") {
        // Apply fade-out animation
        formElements.infectionTimeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

        // Wait for animation to complete, then hide the element
        setTimeout(() => {
          formElements.infectionTimeContainer.style.display = "none";
        }, 300);
      } else {
        formElements.infectionTimeContainer.style.display = "none";
      }

      formElements.infectionTime.removeAttribute('required');
      // Don't clear the value - just make it not required
    }
    calculateImmuneSusceptibility();
  }

  function handleIndoorOutdoorChange() {
    if (formElements.indoorOutdoor.value === "Indoors") {
      // If indoors, show environment container and enable ACH field
      // First set to initial state and trigger reflow
      formElements.environmentContainer.style.animation = 'none';
      formElements.environmentContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.environmentContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.environmentContainer.style.display = "block";
      formElements.ach.disabled = false;

      // Remove hidden ACH field if exists
      var hiddenField = document.getElementById('ACH_hidden');
      if (hiddenField) {
        hiddenField.parentNode.removeChild(hiddenField);
      }
    } else if (formElements.indoorOutdoor.value === "Outdoors") {
      // If outdoors, compute and hide environment fields, disable ACH select
      const outVolume = computeVolume({
        indoorOutdoor: formElements.indoorOutdoor.value,
        achValue: formElements.ach.value,
        carType: formElements.carType.value,
        airplaneType: formElements.airplaneType.value,
        customVolume: formElements.roomVolume.value,
        covidRiskData,
        advancedEnabled: formElements.advanced.value === 'true',
        distanceFeet: formElements.distanceSlider.value
      });
      formElements.environmentVolume.value = outVolume.toString();
      formElements.environmentContainer.style.display = "none";
      formElements.ach.disabled = true;

      // Create or update hidden ACH field for outdoors
      const achVal = computeACH({
        indoorOutdoor: formElements.indoorOutdoor.value,
        achValue: formElements.ach.value,
        customACH: formElements.customACH.value
      });
      let hiddenACH = document.getElementById('ACH_hidden');
      if (!hiddenACH) {
        hiddenACH = document.createElement('input');
        hiddenACH.type = "hidden";
        hiddenACH.name = "ACH";
        hiddenACH.id = "ACH_hidden";
        formElements.environmentContainer.appendChild(hiddenACH);
      }
      hiddenACH.value = achVal.toString();

      // Also hide car and airplane containers for outdoors
      formElements.carTypeContainer.style.display = "none";
      formElements.airplaneTypeContainer.style.display = "none";
    } else {
      // If no selection, hide the environment container and ensure ACH field is enabled
      formElements.environmentContainer.style.display = "none";
      formElements.ach.disabled = false;
      var hiddenField = document.getElementById('ACH_hidden');
      if (hiddenField) {
        hiddenField.parentNode.removeChild(hiddenField);
      }
    }

    // Call ACH change handler to update car and airplane visibility
    handleAchChange();
  }

  function handleAchChange() {
    const selectedValue = formElements.ach.value;
    const selectedOption = formElements.ach.options[formElements.ach.selectedIndex];
    const indoorOutdoorValue = formElements.indoorOutdoor.value;
    
    // Find the actual environment details from the data structure
    let selectedEnvironment = null;
    let environmentGroup = null;
    
    if (selectedOption && selectedOption.parentElement && selectedOption.parentElement.tagName === 'OPTGROUP') {
      const groupLabel = selectedOption.parentElement.label;
      environmentGroup = covidRiskData.environments.find(env => env.group === groupLabel);
      if (environmentGroup) {
        selectedEnvironment = environmentGroup.options.find(opt => opt.value === selectedValue && opt.label === selectedOption.textContent);
      }
    }
    
    // Determine environment type based on actual selection, not just ACH value
    const isCarValue = environmentGroup && environmentGroup.group === "Car";
    const isAirplaneValue = environmentGroup && environmentGroup.group === "Public transit" && 
                           selectedEnvironment && selectedEnvironment.label.includes("Airplane");

    // Store the selected ACH value and volume in hidden fields
    // Skip volume setting for outdoors - handleIndoorOutdoorChange will handle it
    if (selectedValue && indoorOutdoorValue !== "Outdoors") {
      console.log("Selected environment:", selectedOption.textContent, "Value:", selectedValue);

      // Use the paired volume from the selected environment data, or fall back to computeVolume for special cases
      let volume;
      if (selectedEnvironment && !isCarValue && !isAirplaneValue) {
        // For regular environments, use the paired volume directly
        volume = selectedEnvironment.volume;
        console.log("Using paired volume from environment data:", volume);
      } else {
        // For cars, airplanes, and custom volumes, use the existing computeVolume logic
        volume = computeVolume({
          indoorOutdoor: formElements.indoorOutdoor.value,
          achValue: selectedValue,
          carType: formElements.carType.value,
          airplaneType: formElements.airplaneType.value,
          customVolume: formElements.roomVolume.value,
          covidRiskData,
          advancedEnabled: formElements.advanced.value === 'true',
          distanceFeet: formElements.distanceSlider.value
        });
        console.log("Using computeVolume for special case:", volume);
      }
      
      formElements.environmentVolume.value = volume.toString();
    }

    // Handle car type visibility
    if (indoorOutdoorValue === "Indoors" && isCarValue) {
      // First set to initial state and trigger reflow
      formElements.carTypeContainer.style.animation = 'none';
      formElements.carTypeContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.carTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.carTypeContainer.style.display = 'block';
      formElements.carType.setAttribute('required', true);
      updateCarVolume();
    } else {
      formElements.carTypeContainer.style.display = 'none';
      formElements.carType.removeAttribute('required');
    }

    // Handle airplane type visibility
    if (indoorOutdoorValue === "Indoors" && isAirplaneValue) {
      // First set to initial state and trigger reflow
      formElements.airplaneTypeContainer.style.animation = 'none';
      formElements.airplaneTypeContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.airplaneTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.airplaneTypeContainer.style.display = 'block';
      // Setup the airplane size slider
      const airplaneSizeSlider = document.getElementById('airplane_size_slider');
      if (airplaneSizeSlider) {
        airplaneSizeSlider.addEventListener('input', updateAirplaneSize);
        airplaneSizeSlider.value = 0; // Reset to small
        updateAirplaneSize(); // Initialize with default size
      }
    } else {
      formElements.airplaneTypeContainer.style.display = 'none';
    }
  }

  function updateAirplaneSize() {
    const sizeSlider = document.getElementById('airplane_size_slider');
    const airplaneTypeField = document.getElementById('airplane_type');
    if (!sizeSlider || !airplaneTypeField) return;

    const sizeIndex = parseInt(sizeSlider.value);
    let airplaneType;
    let label;

    // Map slider position to airplane type
    switch(sizeIndex) {
      case 0:
        airplaneType = "small";
        label = "Small";
        break;
      case 1:
        airplaneType = "medium";
        label = "Medium (Boeing 737)";
        break;
      case 2:
        airplaneType = "large";
        label = "Large (A330)";
        break;
      case 3:
        airplaneType = "very_large";
        label = "Very Large (Boeing 777)";
        break;
      default:
        airplaneType = "medium";
        label = "Medium (Boeing 737)";
    }

    // Update the hidden field with the selected airplane type
    airplaneTypeField.value = airplaneType;

    // Update the label to show current selection
    const container = sizeSlider.closest('div').parentElement;
    if (container) {
      const labelElement = container.querySelector('label');
      if (labelElement) {
        labelElement.textContent = `How big was the plane? ${label}`;
      }
    }

    // Call the volume update function
    updateAirplaneVolume();
  }

  function handleOthersMaskedChange() {
    if (formElements.othersMasked.value === "Yes") {
      // First set to initial state and trigger reflow
      formElements.maskedPercentageContainer.style.animation = 'none';
      formElements.maskedPercentageContainer.offsetHeight; // Force reflow

      // Apply the animation and show the container
      formElements.maskedPercentageContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      formElements.maskedPercentageContainer.style.display = "block";
      formElements.maskedPercentage.setAttribute('required', true);

      // If we have a data-selected-value for masked percentage, use it
      const savedPercentage = formElements.maskedPercentage.getAttribute('data-selected-value');
      if (savedPercentage && savedPercentage !== '') {
        formElements.maskedPercentage.value = savedPercentage;
      }

      // Check if we need to also show the mask type question
      handleMaskedPercentageChange();
    } else {
      // Hide the containers
      // Only animate if the element is currently visible
      if (formElements.maskedPercentageContainer.style.display === "block") {
        // Apply fade-out animation
        formElements.maskedPercentageContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

        // Wait for animation to complete, then hide the element
        setTimeout(() => {
          formElements.maskedPercentageContainer.style.display = "none";
        }, 300);
      } else {
        formElements.maskedPercentageContainer.style.display = "none";
      }

      // Also hide the secondary container with animation if visible
      if (formElements.othersMaskTypeContainer.style.display === "block") {
        // Apply fade-out animation
        formElements.othersMaskTypeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

        // Wait for animation to complete, then hide the element
        setTimeout(() => {
          formElements.othersMaskTypeContainer.style.display = "none";
        }, 300);
      } else {
        formElements.othersMaskTypeContainer.style.display = "none";
      }

      // Remove required attributes
      formElements.maskedPercentage.removeAttribute('required');
      formElements.othersMaskType.removeAttribute('required');

      // Don't clear the field values - preserve them for when the form is submitted
      // so they'll still be available in request.form data

      // Set hidden field values used in calculation
      formElements.percentageMasked.value = "0";
      formElements.fe.value = "1";
    }
  }

  function handleMaskedPercentageChange() {
    // Read slider and compute fraction
    const sliderValue = parseInt(formElements.maskedPercentage.value, 10) || 0;
    let fraction = 0;
    if (sliderValue === 25) fraction = 0.25;
    else if (sliderValue === 50) fraction = 0.5;
    else if (sliderValue === 75) fraction = 0.75;
    else if (sliderValue === 100) fraction = 1.0;
    
    console.log(`handleMaskedPercentageChange: sliderValue=${sliderValue}, computing fraction=${fraction}`);
    
    // Update hidden percent
    formElements.percentageMasked.value = fraction.toString();
    console.log(`Updated percentage_masked field to: ${formElements.percentageMasked.value}`);

    if (sliderValue > 0) {
      console.log("Some people are masked");
      // Only animate and restore on first reveal
      if (formElements.othersMaskTypeContainer.style.display !== 'block') {
        console.log("Showing mask type selector");
        formElements.othersMaskTypeContainer.style.animation = 'none';
        // Force reflow
        void formElements.othersMaskTypeContainer.offsetHeight;
        formElements.othersMaskTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
        formElements.othersMaskTypeContainer.style.display = 'block';
        // Restore selected if present
        const saved = formElements.othersMaskType.getAttribute('data-selected-value');
        if (saved) {
          formElements.othersMaskType.value = saved;
          console.log(`Restored saved others mask type: ${saved}`);
        }
      }
      // Always require mask type when shown
      formElements.othersMaskType.setAttribute('required', true);
    } else {
      console.log("No people are masked, hiding mask type selector");
      // Hide others-mask-type dropdown
      if (formElements.othersMaskTypeContainer.style.display === 'block') {
        formElements.othersMaskTypeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
        setTimeout(() => { formElements.othersMaskTypeContainer.style.display = 'none'; }, 300);
      } else {
        formElements.othersMaskTypeContainer.style.display = 'none';
      }
      formElements.othersMaskType.removeAttribute('required');
    }
    
    // Sync exhalation filter - IMPORTANT: This affects f_e calculation!
    console.log("Updating f_e value based on new mask percentage");
    updateFe();
    console.log(`After updateFe: f_e=${formElements.fe.value}, percentage_masked=${formElements.percentageMasked.value}`);
  }

  function handleCustomAchInput() {
    // No longer need to disable the environment dropdown
    // User can now select environment settings and override with custom ACH values
    // This is more flexible and avoids confusing UI where fields are unexpectedly disabled

    // Just log that we have a custom ACH value for debugging
    if (formElements.customACH.value.trim() !== '') {
      console.log("Custom ACH entered:", formElements.customACH.value);
    }
  }

  function handleFormSubmit(e) {
    // CRITICAL: We're simplifying the form submission to just do validation
    // and compute a few derived fields without changing any user selections

    let isValid = true;

    // Validation: Check that visible required fields have values
    const selects = document.querySelectorAll('.form-container select');
    selects.forEach(function(selectElem) {
      // Only validate visible required fields
      if (selectElem.offsetParent !== null && selectElem.hasAttribute('required') && selectElem.value === '') {
        selectElem.setCustomValidity("Select an item from the list");
        isValid = false;
      } else {
        selectElem.setCustomValidity("");
      }
    });

    // Validate fit factor if it's visible and has a value
    if (formElements.fitFactor &&
        formElements.fitFactor.offsetParent !== null &&
        formElements.fitFactor.value.trim() !== '') {

      // Use the same validation function we use for real-time validation
      if (!validateFitFactor()) {
        isValid = false;
      }
    }


    // Validation: Check advanced numeric fields are valid
    const advancedFields = [
      { id: 'covid_prevalence', name: 'Covid prevalence', min: 0, max: 100 },
      { id: 'relative_humidity', name: 'Relative humidity', min: 0, max: 100 },
      { id: 'temperature', name: 'Temperature', min: null, max: null },
      { id: 'co2', name: 'CO₂', min: 0, max: null },
      { id: 'custom_ACH', name: 'ACH', min: 0, max: null },
      { id: 'room_volume', name: 'Room volume', min: 0, max: null }
    ];
    
    advancedFields.forEach(fieldInfo => {
      const field = document.getElementById(fieldInfo.id);
      if (field && field.offsetParent !== null && field.value.trim() !== '') {
        const value = parseFloat(field.value);
        let errorMessage = '';
        
        if (isNaN(value)) {
          errorMessage = `${fieldInfo.name} must be a valid number`;
        } else if (fieldInfo.min !== null && value < fieldInfo.min) {
          errorMessage = `${fieldInfo.name} must be at least ${fieldInfo.min}`;
        } else if (fieldInfo.max !== null && value > fieldInfo.max) {
          errorMessage = `${fieldInfo.name} must be no more than ${fieldInfo.max}`;
        }
        
        if (errorMessage) {
          field.classList.add('validation-error');
          field.setCustomValidity(errorMessage);
          isValid = false;
        } else {
          field.classList.remove('validation-error');
          field.setCustomValidity('');
        }
      }
    });

    // Validation: Check exposure duration has at least one value
    const exposureHours = document.getElementById('exposure_hours');
    const exposureMinutes = document.getElementById('exposure_minutes');
    const exposureSeconds = document.getElementById('exposure_seconds');

    if (exposureHours.value === '' && exposureMinutes.value === '' && exposureSeconds.value === '') {
      // Apply validation error styling to all three dropdowns
      [exposureHours, exposureMinutes, exposureSeconds].forEach(select => {
        select.classList.add('validation-error');
      });

      // Display the validation message under the Minutes dropdown
      const minutesValidationMessage = exposureMinutes.closest('.select-wrapper')?.querySelector('.validation-message');
      if (minutesValidationMessage) {
        minutesValidationMessage.style.display = 'block';
      }

      // Remove validation error on change of any time field
      const clearTimeValidation = function() {
        [exposureHours, exposureMinutes, exposureSeconds].forEach(s => {
          s.classList.remove('validation-error');
        });
        const validationMessage = exposureMinutes.closest('.select-wrapper')?.querySelector('.validation-message');
        if (validationMessage) {
          validationMessage.style.display = 'none';
        }
      };

      exposureHours.addEventListener('change', clearTimeValidation, { once: true });
      exposureMinutes.addEventListener('change', clearTimeValidation, { once: true });
      exposureSeconds.addEventListener('change', clearTimeValidation, { once: true });

      isValid = false;
    }

    // Compute derived values without altering form selections

    // 1. Compute total exposure duration in seconds
    let hours = parseInt(exposureHours.value) || 0;
    let minutes = parseInt(exposureMinutes.value) || 0;
    let seconds = parseInt(exposureSeconds.value) || 0;
    let totalSeconds = hours * 3600 + minutes * 60 + seconds;
    document.getElementById('delta_t').value = totalSeconds;

    // 2. Convert the distance from feet to meters
    let distanceFeet = document.getElementById('x').value;
    if (distanceFeet !== "") {
      let distanceMeters = parseFloat(distanceFeet) * 0.3048;
      document.getElementById('x_meters').value = distanceMeters.toFixed(2);
    }

    // 3. Set advanced flag based on visibility
    formElements.advanced.value = (formElements.advancedFields.style.display === 'block') ? 'true' : '';

    // 4. Special case handling for outdoors: recompute volume & ACH via environment module
    if (formElements.indoorOutdoor.value === "Outdoors") {
      // Update hidden environment volume
      const vol = computeVolume({
        indoorOutdoor: formElements.indoorOutdoor.value,
        achValue: formElements.ach.value,
        carType: formElements.carType.value,
        airplaneType: formElements.airplaneType.value,
        customVolume: formElements.roomVolume.value,
        covidRiskData,
        advancedEnabled: formElements.advanced.value === 'true',
        distanceFeet: formElements.distanceSlider.value
      });
      document.getElementById('environment_volume').value = vol.toString();

      // Update or create hidden ACH field for outdoors
      const achVal = computeACH({
        indoorOutdoor: formElements.indoorOutdoor.value,
        achValue: formElements.ach.value,
        customACH: formElements.customACH.value
      });
      let outdoorAchField = document.getElementById('outdoor_ACH');
      if (!outdoorAchField) {
        outdoorAchField = document.createElement('input');
        outdoorAchField.type = 'hidden';
        outdoorAchField.id = 'outdoor_ACH';
        outdoorAchField.name = 'ACH';
        formElements.priorForm.appendChild(outdoorAchField);
      }
      outdoorAchField.value = achVal.toString();
    }

    // BUGFIX: Directly set mask-related hidden fields using current UI values
    console.log("BEFORE UPDATE - User mask:", formElements.masked.value, "Type:", formElements.maskType.value, "f_i:", formElements.fi.value);
    console.log("BEFORE UPDATE - Others masked %:", formElements.maskedPercentage.value, "Type:", formElements.othersMaskType.value, "f_e:", formElements.fe.value, "percentage_masked:", formElements.percentageMasked.value);

    // 1. Compute user's inhalation filter factor (f_i)
    let f_i_val = 1;
    if (formElements.masked && formElements.masked.value === "Yes" && formElements.maskType && formElements.maskType.value) {
      const maskType = formElements.maskType.value;
      const maskData = covidRiskData.maskTypes.find(mask => mask.value === maskType);
      if (maskData && maskData.f_value !== undefined) {
        f_i_val = maskData.f_value;
      }
      console.log("Base mask f_i for mask type:", maskType, "=", f_i_val);
    }
    // Override with custom fit factor if provided (>0)
    if (formElements.fitFactor && formElements.fitFactor.value.trim() !== "") {
      const ff = parseFloat(formElements.fitFactor.value);
      if (!isNaN(ff) && ff > 0) {
        f_i_val = 1 / ff;
        console.log("Applied fit factor override, fitFactor=", ff, "=> f_i=", f_i_val);
      }
    }
    // Clamp to [0,1]
    f_i_val = Math.max(0, Math.min(1, f_i_val));
    formElements.fi.value = f_i_val.toString();

    // 2. Handle others' masks (exhalation filter)
    // First, ensure percentage_masked is correctly set from the slider
    if (formElements.maskedPercentage) {
      const sliderValue = parseInt(formElements.maskedPercentage.value) || 0;
      let fraction = 0;

      if (sliderValue === 25) fraction = 0.25;
      else if (sliderValue === 50) fraction = 0.5;
      else if (sliderValue === 75) fraction = 0.75;
      else if (sliderValue === 100) fraction = 1.0;

      formElements.percentageMasked.value = fraction.toString();

      // Also make sure masked_percentage_value is set to the slider value
      const valueField = document.getElementById('masked_percentage_value');
      if (valueField) {
        valueField.value = sliderValue.toString();
      }

      console.log("Set percentage_masked to:", fraction, "from slider value:", sliderValue);

      // Only set f_e if there are masked people AND a mask type is selected
      if (fraction > 0 && formElements.othersMaskType && formElements.othersMaskType.value) {
        const othersMaskType = formElements.othersMaskType.value;
        const othersMaskData = covidRiskData.maskTypes.find(mask => mask.value === othersMaskType);

        if (othersMaskData && othersMaskData.f_value !== undefined) {
          formElements.fe.value = othersMaskData.f_value.toString();
          console.log("Set others' masks f_e to:", othersMaskData.f_value, "for mask type:", othersMaskType);
        } else {
          formElements.fe.value = "1";
          console.log("Set others' masks f_e to default: 1 (no matching mask type found)");
        }
      } else {
        formElements.fe.value = "1";
        console.log("Set others' masks f_e to default: 1 (no masked people or mask type not selected)");
      }
    }

    console.log("AFTER UPDATE - User mask:", formElements.masked.value, "Type:", formElements.maskType.value, "f_i:", formElements.fi.value);
    console.log("AFTER UPDATE - Others masked %:", formElements.maskedPercentage.value, "Type:", formElements.othersMaskType.value, "f_e:", formElements.fe.value, "percentage_masked:", formElements.percentageMasked.value);

    if (!isValid) {
      e.preventDefault();
      return;
    }
  }

  // Function to handle manual people input
  function setupManualPeopleInput() {
    const editButton = document.getElementById('edit-people-btn');
    const manualInput = document.getElementById('people-manual-input');
    const inputField = document.getElementById('manual-people-input');
    // No longer using applyButton
    const slider = document.getElementById('N_slider');

    if (!editButton || !manualInput || !inputField || !slider) return; // removed applyButton check

    // Helper function to hide input and restore edit button
    function hideManualInput() {
      manualInput.style.display = 'none';
      editButton.style.display = 'flex';
      document.removeEventListener('click', handleClickOutside);

      // Clear any validation errors
      const validationMessage = document.getElementById('people-validation-message');
      if (validationMessage) {
        validationMessage.style.display = 'none';
      }
      inputField.classList.remove('validation-error');
    }

    // Handle click outside to close the input and apply value
    function handleClickOutside(event) {
      if (manualInput.style.display !== 'none' &&
          !manualInput.contains(event.target) &&
          event.target !== editButton) {
        // Apply the value when clicking outside
        applyManualValue();
      }
    }

    // Add input event listener to filter non-digit input and enforce maximum
    inputField.addEventListener('input', function(e) {
      // Remove any non-digit characters except the first digit can't be 0
      let value = this.value;

      // Remove all non-digit characters
      value = value.replace(/\D/g, '');

      // If the first character is 0, remove it
      if (value.startsWith('0')) {
        value = value.substring(1);
      }

      // Enforce maximum value by truncating if needed
      if (value !== '' && parseInt(value) > 1000000) {
        value = '1000000';
      }

      // Update the input value only if it's different to avoid cursor jumps
      if (this.value !== value) {
        this.value = value;
      }
    });

    // Toggle visibility of manual input when edit button is clicked
    editButton.addEventListener('click', function(e) {
      e.stopPropagation(); // Prevent immediate triggering of outside click

      if (manualInput.style.display === 'none') {
        // Show input field and hide edit button
        manualInput.style.display = 'flex';
        editButton.style.display = 'none';

        // Start with an empty input field
        inputField.value = "";
        inputField.focus();

        // Add click outside listener (setTimeout to avoid immediate trigger)
        setTimeout(() => {
          document.addEventListener('click', handleClickOutside);
        }, 10);
      } else {
        // Hide input field and show edit button
        manualInput.style.display = 'none';
        editButton.style.display = 'flex';
        document.removeEventListener('click', handleClickOutside);
      }
    });

    // Handle applying the manual value
    function applyManualValue() {
      // Get the value and ensure it's a positive integer
      const rawValue = inputField.value.trim();

      // If the input is empty or invalid, just keep the slider value and close
      if (rawValue === "" || !/^[1-9]\d*$/.test(rawValue)) {
        hideManualInput();
        return;
      }

      const manualValue = parseInt(rawValue);
      const validationMessage = document.getElementById('people-validation-message');

      // Validate number is within acceptable range
      if (manualValue > 1000000) {
        // Show validation error
        inputField.classList.add('validation-error');
        if (validationMessage) {
          validationMessage.style.display = 'block';
        }
        inputField.focus();
        // Return to prevent applying values over 1,000,000
        return;
      }

      // Clear validation message
      if (validationMessage) {
        validationMessage.style.display = 'none';
      }
      inputField.classList.remove('validation-error');

      // Find closest index in peopleValues array or add custom value
      let closestIndex = 0;
      let minDiff = Math.abs(manualValue - peopleValues[0]);

      for (let i = 1; i < peopleValues.length; i++) {
        const diff = Math.abs(manualValue - peopleValues[i]);
        if (diff < minDiff) {
          minDiff = diff;
          closestIndex = i;
        }
      }

      // If we found an exact match, use that index
      if (peopleValues[closestIndex] === manualValue) {
        slider.value = closestIndex;
        slider.dispatchEvent(new Event('input'));
      } else {
        // Otherwise, set the value directly
        const nInput = document.getElementById('N');
        if (nInput) {
          nInput.value = manualValue;
        }

        // Update the display value
        const valueLabel = slider.closest('.slider-container').querySelector('.slider-value');
        if (valueLabel) {
          const displayValue = manualValue === 1 ? "1 person" :
                             manualValue >= 1000 ? `${manualValue.toLocaleString()} people` : `${manualValue} people`;
          valueLabel.textContent = displayValue;
        }

        // Try to find a close position on the slider for visual feedback
        slider.value = closestIndex;
      }

      // Use function to hide input
      hideManualInput();
    }

    // Apply when Enter key is pressed
    inputField.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        applyManualValue();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        hideManualInput();
      }
    });

    // Make sure click events on the input don't bubble up
    inputField.addEventListener('click', function(e) {
      e.stopPropagation();
    });
  }

  function handleFormReset(e) {
    e.preventDefault();

    // Reset input fields with fixed default values
    document.getElementById('C0').value = "0.08";
    document.getElementById('p').value = "0.08";
    formElements.fi.value = "1";
    document.getElementById('delta_t').value = "0";
    document.getElementById('x').value = "0.7";
    document.getElementById('gamma').value = "0.5";
    document.getElementById('activity_choice').value = "2";
    formElements.environmentVolume.value = "";
    formElements.advanced.value = "";
    formElements.customACH.value = "";
    formElements.roomVolume.value = "";
    document.getElementById('covid_prevalence').value = "1";
    formElements.immuneField.value = "1";

    // Remove any custom hidden fields created for form submission
    const customACHHidden = document.getElementById('custom_ACH_hidden');
    if (customACHHidden) {
      customACHHidden.parentNode.removeChild(customACHHidden);
    }

    const customVolumeHidden = document.getElementById('custom_volume_hidden');
    if (customVolumeHidden) {
      customVolumeHidden.parentNode.removeChild(customVolumeHidden);
    }

    // Hide advanced fields
    formElements.advancedFields.style.display = 'none';

    // Reset all dropdown menus to the empty string
    document.querySelectorAll('.form-container select').forEach(function(selectElem) {
      selectElem.value = '';
      // Trigger change event
      selectElem.dispatchEvent(new Event('change'));
    });

    // Reset exposure time fields
    document.getElementById('exposure_hours').value = '';
    document.getElementById('exposure_minutes').value = '';
    document.getElementById('exposure_seconds').value = '';

    // Reset all sliders to their initial values
    document.getElementById('N_slider').value = 0; // Reset people slider
    document.getElementById('N').value = 1; // Reset hidden N value
    document.getElementById('activity_level_slider').value = 0;
    document.getElementById('physical_intensity_slider').value = 0;
    document.getElementById('vocalization_slider').value = 0;
    document.getElementById('masked_percentage').value = 0;
    document.getElementById('x').value = 6; // Reset distance to 6 feet

    // Trigger input events to update displays
    document.querySelectorAll('.slider').forEach(slider => {
      slider.dispatchEvent(new Event('input'));
    });

    // Hide the result container when clearing the form
    const resultContainer = document.getElementById('result');
    if (resultContainer) {
      resultContainer.style.display = 'none';
      resultContainer.innerHTML = ''; // Clear the content
    }

    // Notify our AJAX handler that form has been reset
    // This will ensure the next calculation is treated as the "first"
    console.log("Dispatching formReset event");
    document.dispatchEvent(new CustomEvent('formReset'));

    // Update related UI dynamic elements
    handleIndoorOutdoorChange();
  }

  // ========================
  // Calculation functions
  // ========================

  function updateFi() {
    // Compute inhalation filter factor
    const masked = formElements.masked.value;
    const maskType = formElements.maskType.value;
    const fitFactor = formElements.fitFactor ? formElements.fitFactor.value : null;
    
    // Add clear debugging
    console.log("updateFi called with:");
    console.log("  masked:", masked);
    console.log("  maskType:", maskType);
    console.log("  fitFactor:", fitFactor);
    console.log("  mask_fit:", document.getElementById('mask_fit')?.value);
    
    const f_i = computeInhalationFilter({
      masked,
      maskType,
      fitFactor,
      fiLookupTable: covidRiskData.fiLookupTable
    });
    
    console.log("Computed f_i:", f_i);
    formElements.fi.value = f_i.toString();
    console.log("Set f_i input field to:", formElements.fi.value);
    
    // Also update exhalation filter to stay in sync
    updateFe();
  }
  
  // Function to handle form submission - ensures that all values are updated before submission
  function handleFormSubmit(event) {
    // Make sure fit factor value is up to date
    if (typeof updateFitFactorValue === 'function') {
      updateFitFactorValue();
    }
    
    console.log("***** FORM SUBMISSION STARTED *****");
    console.log("Before updates - masked:", formElements.masked.value);
    console.log("Before updates - f_i:", formElements.fi.value);
    console.log("Before updates - f_e:", formElements.fe.value);
    console.log("Before updates - percentage_masked:", formElements.percentageMasked.value);
    
    // Force update of user mask settings
    // Update f_i based on mask type and fit
    updateFi();
    
    // For people not wearing a mask, ensure f_i is 1.0
    if (formElements.masked.value !== "Yes") {
      console.log("Setting f_i to 1.0 because user is not masked");
      formElements.fi.value = "1";
    }
    
    // Force update of others' mask settings
    updateFe();
    
    console.log("***** FORM SUBMISSION FINALIZED *****");
    console.log("FINAL FORM VALUES:");
    console.log("  masked:", formElements.masked.value);
    console.log("  mask_type:", formElements.maskType ? formElements.maskType.value : "none");
    console.log("  f_i:", formElements.fi.value); 
    console.log("  others_mask_percentage:", formElements.maskedPercentage.value);
    console.log("  others_mask_type:", formElements.othersMaskType ? formElements.othersMaskType.value : "none");
    console.log("  f_e:", formElements.fe.value);
    console.log("  percentage_masked:", formElements.percentageMasked.value);
    
    // Continue with normal form handling
    return true;
  }

  function updateFe() {
    // Compute exhalation filter and masked fraction for others
    const sliderValue = parseInt(formElements.maskedPercentage.value, 10) || 0;
    const othersMaskType = formElements.othersMaskType ? formElements.othersMaskType.value : '';
    
    console.log("updateFe called with:");
    console.log("  sliderValue:", sliderValue);
    console.log("  othersMaskType:", othersMaskType);
    
    const { fraction, feValue } = computeExhalationFilter({
      sliderValue,
      othersMaskType,
      maskTypesData: covidRiskData.maskTypes
    });
    
    console.log("Result from computeExhalationFilter:");
    console.log("  fraction:", fraction);
    console.log("  feValue:", feValue);
    
    formElements.percentageMasked.value = fraction.toString();
    formElements.fe.value = feValue.toString();
    
    console.log("Updated form elements:");
    console.log("  percentageMasked:", formElements.percentageMasked.value);
    console.log("  fe:", formElements.fe.value);
  }

  function updateCarVolume() {
    const volume = computeVolume({
      indoorOutdoor: formElements.indoorOutdoor.value,
      achValue: formElements.ach.value,
      carType: formElements.carType.value,
      airplaneType: formElements.airplaneType.value,
      customVolume: formElements.roomVolume.value,
      covidRiskData,
      advancedEnabled: formElements.advanced.value === 'true',
      distanceFeet: formElements.distanceSlider.value
    });
    formElements.environmentVolume.value = volume.toString();
    console.log("updateCarVolume → environmentVolume set to:", volume);
  }

  function updateAirplaneVolume() {
    const volume = computeVolume({
      indoorOutdoor: formElements.indoorOutdoor.value,
      achValue: formElements.ach.value,
      carType: formElements.carType.value,
      airplaneType: document.getElementById('airplane_type').value,
      customVolume: formElements.roomVolume.value,
      covidRiskData,
      advancedEnabled: formElements.advanced.value === 'true',
      distanceFeet: formElements.distanceSlider.value
    });
    formElements.environmentVolume.value = volume.toString();
    console.log("updateAirplaneVolume → environmentVolume set to:", volume);
  }

  function updateExhalationFlowRate() {
    const physical = document.getElementById('physical_intensity').value;
    const vocal = document.getElementById('vocalization').value;
    if (!physical || !vocal) return;

    const multiplier = getMultiplier(covidRiskData.multipliers, physical, vocal);
    const Q0 = computeExhalationFlowRate(multiplier);
    document.getElementById('Q0').value = Q0.toFixed(2);
  }

  function calculateImmuneSusceptibility() {
    console.log('DEBUG: calculateImmuneSusceptibility function called');
    
    // Delegate to pure computation module
    const recentVaccination = formElements.recentVaccination.value;
    const vaccinationMonths = (recentVaccination === "Yes" && formElements.vaccinationTime.value)
      ? parseInt(formElements.vaccinationTime.value, 10)
      : null;
    const recentInfection = formElements.recentInfection.value;
    const infectionMonths = (recentInfection === "Yes" && formElements.infectionTime.value)
      ? parseInt(formElements.infectionTime.value, 10)
      : null;

    console.log('DEBUG: calculateImmuneSusceptibility extracted values:', {
      recentVaccination,
      vaccinationMonths,
      recentInfection,
      infectionMonths
    });

    const immuneValue = computeImmuneValue({
      recentVaccination,
      vaccinationMonths,
      recentInfection,
      infectionMonths
    });
    
    console.log('DEBUG: Final immune_val calculated:', immuneValue);
    console.log('DEBUG: Setting immuneField.value to:', immuneValue.toFixed(4));
    
    formElements.immuneField.value = immuneValue.toFixed(4);
  }
  
  // Set the implementation for the global wrapper
  console.log('DEBUG: Setting calculateImmuneSusceptibility implementation');
  window._calculateImmuneSusceptibilityImpl = calculateImmuneSusceptibility;
  console.log('DEBUG: Implementation set, global function ready');

  // ========================
  // State functions
  // ========================

  function toggleAdvancedFields() {
    if (formElements.advancedFields.style.display === 'none' || formElements.advancedFields.style.display === '') {
      // Show advanced fields
      formElements.advancedFields.style.display = 'block';
      formElements.advanced.value = 'true';
    } else {
      // Hide advanced fields AND clear their values
      formElements.advancedFields.style.display = 'none';
      formElements.advanced.value = '';

      // Clear all advanced fields so their values aren't used in calculation
      formElements.customACH.value = '';
      formElements.roomVolume.value = '';
      document.getElementById('covid_prevalence').value = '';

      // Remove any custom hidden fields that might have been created
      const customACHHidden = document.getElementById('custom_ACH_hidden');
      if (customACHHidden) {
        customACHHidden.parentNode.removeChild(customACHHidden);
      }

      const customVolumeHidden = document.getElementById('custom_volume_hidden');
      if (customVolumeHidden) {
        customVolumeHidden.parentNode.removeChild(customVolumeHidden);
      }

      console.log("Advanced fields hidden and values cleared");
    }
  }


  // Simple direct function to select environment by exact value
  function restoreSelectedEnvironment() {
    const select = document.getElementById('ACH');
    if (!select) return;

    // Saved by server – the *value* the user previously chose
    const savedValue = select.getAttribute('data-selected-value');

    // Saved locally – the *label* the user previously saw (important when
    // multiple options share the same value, e.g. Small Congregational Hall
    // and Large home family dinner both have ACH 2.00).
    const savedTextInput  = document.getElementById('selected_environment_text');
    const savedIndexInput = document.getElementById('selected_environment_index');
    const savedText  = savedTextInput  ? savedTextInput.value  : '';
    const savedIndex = savedIndexInput ? parseInt(savedIndexInput.value, 10) : NaN;

    if (!savedValue) return;

    // Iterate through <option>s to find the *exact* one we want.
    let optionToSelect = null;

    // 1. Try index restoration if we have it and the option exists
    if (!Number.isNaN(savedIndex) && select.options.length > savedIndex) {
      optionToSelect = select.options[savedIndex];
      if (optionToSelect && optionToSelect.value !== savedValue) {
        // Index refers to a different value (data order changed) – ignore
        optionToSelect = null;
      }
    }

    // 2. Fallback: iterate to match value & (if available) text
    if (!optionToSelect) {
      for (const opt of select.options) {
        if (opt.value === savedValue) {
          if (savedText && opt.textContent === savedText) {
            optionToSelect = opt;
            break; // Perfect match
          }
          if (!optionToSelect) optionToSelect = opt; // first value match
        }
      }
    }

    if (optionToSelect) {
      optionToSelect.selected = true;

      // Keep hidden fields in sync
      if (savedTextInput)   savedTextInput.value   = optionToSelect.textContent;
      if (savedIndexInput)  savedIndexInput.value  = optionToSelect.index;

      // Keep hidden text field in sync in case the restored option differs
      if (savedTextInput) {
        savedTextInput.value = optionToSelect.textContent;
      }

      // Manually fire change event so dependent UI updates run.
      const evt = new Event('change', { bubbles: true });
      select.dispatchEvent(evt);
      console.log('Environment restored to:', optionToSelect.textContent);
    } else {
      console.log('Could not restore environment selection');
    }
  }

  // Add new functions to update the display of slider values
  function updateActivityLevelDisplay() {
    if (!formElements.activityLevelSlider) return;

    const sliderIndex = parseInt(formElements.activityLevelSlider.value || 0);
    const activity = activityValues[sliderIndex];

    // Update hidden field value
    const displayField = document.getElementById('activity_level_display');
    if (displayField) {
      displayField.value = activity.display;
    }

    // Update the label indicators by adding active class to selected one
    const sliderContainer = formElements.activityLevelSlider.closest('.slider-container');
    if (sliderContainer) {
      // Remove active class from all labels
      const labels = sliderContainer.querySelectorAll('.slider-labels span');
      labels.forEach(label => {
        label.classList.remove('active');
      });

      // Add active class to the selected label
      if (labels[sliderIndex]) {
        labels[sliderIndex].classList.add('active');
      }
    }
  }

  function updatePhysicalIntensityDisplay() {
    if (!formElements.physicalIntensitySlider) return;

    const sliderIndex = parseInt(formElements.physicalIntensitySlider.value || 0);
    const intensity = physicalIntensityValues[sliderIndex];

    // Update hidden field value
    const displayField = document.getElementById('physical_intensity_display');
    if (displayField) {
      displayField.value = intensity.display;
    }

    // Update the label indicators by adding active class to selected one
    const sliderContainer = formElements.physicalIntensitySlider.closest('.slider-container');
    if (sliderContainer) {
      // Remove active class from all labels
      const labels = sliderContainer.querySelectorAll('.slider-labels span');
      labels.forEach(label => {
        label.classList.remove('active');
      });

      // Add active class to the selected label
      if (labels[sliderIndex]) {
        labels[sliderIndex].classList.add('active');
      }
    }
  }

  function updateVocalizationDisplay() {
    if (!formElements.vocalizationSlider) return;

    const sliderIndex = parseInt(formElements.vocalizationSlider.value || 0);
    const vocalization = vocalizationValues[sliderIndex];

    // Update hidden field value
    const displayField = document.getElementById('vocalization_display');
    if (displayField) {
      displayField.value = vocalization.display;
    }

    // Update the label indicators by adding active class to selected one
    const sliderContainer = formElements.vocalizationSlider.closest('.slider-container');
    if (sliderContainer) {
      // Remove active class from all labels
      const labels = sliderContainer.querySelectorAll('.slider-labels span');
      labels.forEach(label => {
        label.classList.remove('active');
      });

      // Add active class to the selected label
      if (labels[sliderIndex]) {
        labels[sliderIndex].classList.add('active');
      }
    }
  }

  function updateDistanceDisplay() {
    // Distance slider is now handled with inline JavaScript in the HTML template
    // This function is kept for backward compatibility
    return;
  }

  // Static variable to track the previous state of masked percentage value
  let prevMaskedPercentDisplayValue = -1;

  function updateMaskedPercentageDisplay() {
    const maskedPercentage = document.getElementById('masked_percentage');
    if (!maskedPercentage) return;

    const value = parseInt(maskedPercentage.value);
    let text;

    if (value === 0) text = 'None';
    else if (value === 25) text = 'Some (25%)';
    else if (value === 50) text = 'Half\n(50%)';
    else if (value === 75) text = 'Most\n(75%)';
    else if (value === 100) text = 'All\n(100%)';
    else text = `${value}%`;

    // Find the slider value index (0-4 for the five options)
    let sliderIndex = 0;
    if (value === 0) sliderIndex = 0;
    else if (value === 25) sliderIndex = 1;
    else if (value === 50) sliderIndex = 2;
    else if (value === 75) sliderIndex = 3;
    else if (value === 100) sliderIndex = 4;

    // Update the label indicators by adding active class to selected one
    const sliderContainer = maskedPercentage.closest('.slider-container');
    if (sliderContainer) {
      // Remove active class from all labels
      const labels = sliderContainer.querySelectorAll('.slider-labels span');
      labels.forEach(label => {
        label.classList.remove('active');
      });

      // Add active class to the selected label
      if (labels[sliderIndex]) {
        labels[sliderIndex].classList.add('active');
      }
    }

    // Show/hide mask type question based on state changes
    const maskTypeContainer = document.getElementById('others_mask_type_container');
    const othersMaskType = document.getElementById('others_mask_type');

    // Check for state transitions
    const wasZero = prevMaskedPercentDisplayValue === 0;
    const wasPositive = prevMaskedPercentDisplayValue > 0;
    const isZero = value === 0;
    const isPositive = value > 0;
    const isInitialRun = prevMaskedPercentDisplayValue === -1;

    // Update for next time
    prevMaskedPercentDisplayValue = value;

    // Only apply animations when transitioning between zero and positive states
    if (isPositive) {
      if (wasZero || isInitialRun) {
        // Transitioning from zero (or first run) - animate the appearance
        maskTypeContainer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
      } else {
        // Already visible and staying visible - explicitly remove animation
        maskTypeContainer.style.animation = 'none';
      }
      maskTypeContainer.style.display = "block";
      othersMaskType.setAttribute('required', true);
    } else {
      if (wasPositive) {
        // Transitioning from positive to zero - animate the disappearance
        maskTypeContainer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';
        setTimeout(() => {
          maskTypeContainer.style.display = "none";
        }, 300);
      } else {
        // Already hidden and staying hidden - no animation needed
        maskTypeContainer.style.animation = 'none';
        maskTypeContainer.style.display = "none";
      }
      othersMaskType.removeAttribute('required');
    }

    // Hidden percentage_masked is handled by inline updateMaskedPercentageLabel
  }

  // This function updates the airplane size slider label and value
  function updateAirplaneSize() {
    const sizeSlider = document.getElementById('airplane_size_slider');
    const airplaneTypeField = document.getElementById('airplane_type');
    if (!sizeSlider || !airplaneTypeField) return;

    const sizeIndex = parseInt(sizeSlider.value);
    let airplaneType;
    let label;

    // Map slider position to airplane type
    switch(sizeIndex) {
      case 0:
        airplaneType = "small";
        label = "Small";
        break;
      case 1:
        airplaneType = "medium";
        label = "Medium (Boeing 737)";
        break;
      case 2:
        airplaneType = "large";
        label = "Large (A330)";
        break;
      case 3:
        airplaneType = "very_large";
        label = "Very Large (Boeing 777)";
        break;
      default:
        airplaneType = "medium";
        label = "Medium (Boeing 737)";
    }

    // Update the hidden field with the selected airplane type
    airplaneTypeField.value = airplaneType;

    // Update the label to show current selection
    const container = sizeSlider.closest('div').parentElement;
    if (container) {
      const labelElement = container.querySelector('label');
      if (labelElement) {
        labelElement.textContent = `How big was the plane? ${label}`;
      }
    }

    // Call the volume update function
    updateAirplaneVolume();
  }

  // Scrolling behavior now handled in the template directly
});
