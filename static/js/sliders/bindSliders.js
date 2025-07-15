// bindSliders.js — attach input listeners to sliders for updating display and hidden fields
import { peopleValues, positionPeopleSliderThumb } from './peopleSlider.js';
import { activityValues, physicalIntensityValues, vocalizationValues } from '../data/sliderData.js';

/**
 * Update the activity_choice hidden field based on physical intensity and vocalization sliders.
 * Also update the user's breathing rate (p parameter) based on their activity level.
 * Maps combined activity levels to the 1-5 scale expected by the calculator.
 */
function updateActivityChoice() {
  // Get current slider indices
  const physicalIdx = parseInt(document.getElementById('physical_intensity_index')?.value || '0', 10);
  const vocalizationIdx = parseInt(document.getElementById('vocalization_index')?.value || '0', 10);
  const userActivityIdx = parseInt(document.getElementById('activity_level_index')?.value || '0', 10);
  
  // Map combinations to activity choice (1-5) for others' emission rates
  // Based on emission rate mapping from calculators/exposure_calculator.py:8-14
  let activityChoice;
  
  if (vocalizationIdx === 0) {
    // Just breathing - always sedentary regardless of physical activity
    activityChoice = '1'; // sedentary: ≈6 µL h⁻¹
  } else if (vocalizationIdx === 1) {
    // Speaking
    if (physicalIdx <= 1) {
      activityChoice = '2'; // standard speaking: ≈100 µL h⁻¹
    } else {
      activityChoice = '3'; // light vocalization: ≈200 µL h⁻¹  
    }
  } else {
    // Loudly speaking
    if (physicalIdx <= 1) {
      activityChoice = '4'; // moderate vocalization: ≈400 µL h⁻¹
    } else {
      activityChoice = '5'; // intense vocalization: ≈800 µL h⁻¹
    }
  }
  
  // Update user's breathing rate (p parameter) based on their activity level
  // Based on activity level values from sliderData.js
  const baseBreathingRate = 0.08; // L/s baseline
  const activityMultipliers = [1.0, 1.2, 2.7, 5.8, 11.0]; // from sliderData.js values
  const userBreathingRate = baseBreathingRate * activityMultipliers[userActivityIdx];
  
  // Update the hidden fields
  const activityChoiceField = document.getElementById('activity_choice');
  const pField = document.getElementById('p');
  
  if (activityChoiceField) {
    activityChoiceField.value = activityChoice;
  }
  
  if (pField) {
    pField.value = userBreathingRate.toFixed(3);
  }
  
  console.log(`Activity updated - choice: ${activityChoice} (others: physical=${physicalIdx}, vocal=${vocalizationIdx}), user breathing: ${userBreathingRate.toFixed(3)} L/s (activity=${userActivityIdx})`);
}

/**
 * Bind all sliders (<input class="slider">) to their update functions.
 */
export function bindSliders() {
  document.querySelectorAll('input.slider').forEach(function(slider) {
    const updateSliderValue = function() {
      const id = slider.id;
      const valueLabel = slider.closest('.slider-container')?.querySelector('.slider-value');
      switch (id) {
        case 'N_slider': {
          const idx = parseInt(slider.value, 10);
          const count = peopleValues[idx];
          if (valueLabel) {
            const disp = count === 1 ? '1 person'
              : count >= 1000 ? `${count.toLocaleString()} people`
              : `${count} people`;
            valueLabel.textContent = disp;
          }
          document.getElementById('people_index')?.value = idx;
          document.getElementById('N')?.value = count;
          positionPeopleSliderThumb(slider, idx);
          break;
        }
        case 'activity_level_slider': {
          const idx = parseInt(slider.value, 10);
          const act = activityValues[idx];
          if (valueLabel) valueLabel.textContent = act.display;
          document.getElementById('activity_level_index')?.value = idx;
          document.getElementById('activity_level')?.value = act.value;
          document.getElementById('activity_level_display')?.value = act.display;
          updateActivityChoice();
          break;
        }
        case 'physical_intensity_slider': {
          const idx = parseInt(slider.value, 10);
          const pi = physicalIntensityValues[idx];
          if (valueLabel) valueLabel.textContent = pi.display;
          document.getElementById('physical_intensity_index')?.value = idx;
          document.getElementById('physical_intensity')?.value = pi.value;
          document.getElementById('physical_intensity_display')?.value = pi.display;
          updateActivityChoice();
          break;
        }
        case 'vocalization_slider': {
          const idx = parseInt(slider.value, 10);
          const voc = vocalizationValues[idx];
          if (valueLabel) valueLabel.textContent = voc.display;
          document.getElementById('vocalization_index')?.value = idx;
          document.getElementById('vocalization')?.value = voc.value;
          document.getElementById('vocalization_display')?.value = voc.display;
          updateActivityChoice();
          break;
        }
        default: {
          // other sliders handled via their own handlers (range pickers, custom scripts)
        }
      }
    };
    slider.addEventListener('input', updateSliderValue);
    // Initialize on load
    updateSliderValue();
  });
  
  // Initialize activity choice on page load
  updateActivityChoice();
}