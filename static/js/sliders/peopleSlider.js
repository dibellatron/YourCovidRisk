// peopleSlider.js — draws tick marks and manual entry for the people slider
// Discrete values for the people slider (must match slider max = length - 1)
export const peopleValues = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  15, 20, 25, 30, 35, 40, 45, 50, 75, 100,
  150, 200, 250, 500, 750, 1000
];

// Map slider indices to approximate CSS positions for the people slider ticks
export const peopleTickIndices = {
  0: 0,      // 1 person (index 0)
  9: 25,     // 10 people (index 9)
  17: 50,    // 50 people (index 17)
  19: 62.5,  // 100 people (index 19)
  23: 81.25, // 500 people (index 23)
  25: 100    // 1000 people (index 25)
};

/**
 * Draw dynamic tick marks under the people slider
 */
export function drawPeopleTicks() {
  const peopleSlider = document.getElementById('N_slider');
  if (!peopleSlider) return;
  const sliderContainer = peopleSlider.closest('.slider-container');
  if (!sliderContainer) return;
  const tickContainer = sliderContainer.querySelector('.slider-ticks');
  if (!tickContainer) return;
  tickContainer.innerHTML = '';
  // Choose values that map to slider positions
  const tickValues = [1, 10, 25, 50, 100, 500, 1000];
  const maxIndex = parseInt(peopleSlider.getAttribute('max'), 10);
  // For percentage-based positioning, we don't need these
  const thumbSize = 0;
  const containerWidth = 100; // Using percentages
  const formatNum = n => n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  tickValues.forEach(val => {
    let idx = peopleValues.indexOf(val);
    if (idx === -1) {
      let hi = peopleValues.findIndex(v => v > val);
      if (hi === -1) hi = peopleValues.length - 1;
      let lo = hi > 0 ? hi - 1 : 0;
      const loVal = peopleValues[lo];
      const hiVal = peopleValues[hi];
      const frac = (val - loVal) / (hiVal - loVal);
      idx = lo + frac;
    }
    // This calculation is not used anymore with our new percentage-based approach
const posPx = 0; // Replaced with percentage-based positioning
    const tickEl = document.createElement('span');
    tickEl.className = 'tick';
    tickEl.textContent = val >= 1000 ? formatNum(val) : val;
    tickEl.dataset.index = idx;
    
    // Use the predefined mapping for known index positions
    // This approach gives us precise control over tick positioning
    let percentPos;
    
    // Responsive positioning based on screen width
    const screenWidth = window.innerWidth;
    let positions;
    
    if (screenWidth <= 375) {
      // Extra small phones - very tight positioning
      positions = {
        1: 2,
        10: 23,
        25: 42,
        50: 48,
        100: 60,
        500: 79,
        1000: 98
      };
    } else if (screenWidth <= 480) {
      // Small phones - tight positioning
      positions = {
        1: 1,
        10: 24,
        25: 43,
        50: 49,
        100: 61,
        500: 80,
        1000: 99
      };
    } else if (screenWidth <= 820) {
      // Tablets & large phones - adjusted positioning
      positions = {
        1: 1,
        10: 24,
        25: 44,
        50: 49.5,
        100: 61.5,
        500: 80.5,
        1000: 99
      };
    } else {
      // Desktop - original positioning
      positions = {
        1: 0,
        10: 25,
        25: 45,
        50: 50,
        100: 62.5,
        500: 81.25,
        1000: 100
      };
    }
    
    if (val in positions) {
      percentPos = positions[val];
    } else if (idx in peopleTickIndices) {
      percentPos = peopleTickIndices[idx];
    } else {
      // For any values not in our mapping, use interpolation
      percentPos = (idx / maxIndex) * 100;
    }
    
    tickEl.style.left = percentPos + '%';
    tickEl.style.transform = 'translateX(-50%)';
    
    // Add a custom class for our important tick values to make targeting them in CSS easier
    if ([1, 10, 25, 50, 100, 500, 1000].includes(val)) {
      tickEl.classList.add('important-tick');
      tickEl.dataset.value = val;
    }
    
    tickContainer.appendChild(tickEl);
    // Allow clicking on ticks to move the slider thumb
    tickEl.style.cursor = 'pointer';
    tickEl.addEventListener('click', () => {
      // Round index to nearest integer and update slider
      const targetIndex = Math.round(idx);
      peopleSlider.value = targetIndex;
      peopleSlider.dispatchEvent(new Event('input'));
    });
  });
}

/**
 * Setup manual entry (input box) for the people slider
 */
export function setupManualPeopleInput() {
  const editButton = document.getElementById('edit-people-btn');
  const manualInput = document.getElementById('people-manual-input');
  const inputField = document.getElementById('manual-people-input');
  const slider = document.getElementById('N_slider');
  if (!editButton || !manualInput || !inputField || !slider) return;

  function hideManualInput() {
    manualInput.style.display = 'none';
    editButton.style.display = 'flex';
    document.removeEventListener('click', handleClickOutside);
    const validationMessage = document.getElementById('people-validation-message');
    if (validationMessage) validationMessage.style.display = 'none';
    inputField.classList.remove('validation-error');
  }

  function handleClickOutside(event) {
    if (
      manualInput.style.display !== 'none' &&
      !manualInput.contains(event.target) &&
      event.target !== editButton
    ) {
      applyManualValue();
    }
  }

  inputField.addEventListener('input', function() {
    let value = this.value.replace(/\D/g, '');
    if (value.startsWith('0')) value = value.substring(1);
    if (value && parseInt(value) > 1000) value = '1000';
    if (this.value !== value) this.value = value;
  });

  editButton.addEventListener('click', function(e) {
    e.stopPropagation();
    if (manualInput.style.display === 'none') {
      manualInput.style.display = 'flex';
      editButton.style.display = 'none';
      inputField.value = '';
      inputField.focus();
      setTimeout(() => document.addEventListener('click', handleClickOutside), 10);
    } else {
      manualInput.style.display = 'none';
      editButton.style.display = 'flex';
      document.removeEventListener('click', handleClickOutside);
    }
  });

  function applyManualValue() {
    const raw = inputField.value.trim();
    if (!raw || !/^[1-9]\d*$/.test(raw)) { hideManualInput(); return; }
    const val = parseInt(raw, 10);
    if (val > 1000) {
      inputField.classList.add('validation-error');
      const msg = document.getElementById('people-validation-message');
      if (msg) msg.style.display = 'block';
      inputField.focus();
      return;
    }
    inputField.classList.remove('validation-error');
    const idxArr = peopleValues;
    let closest = 0;
    let minDiff = Math.abs(val - idxArr[0]);
    for (let i = 1; i < idxArr.length; i++) {
      const diff = Math.abs(val - idxArr[i]);
      if (diff < minDiff) { minDiff = diff; closest = i; }
    }
    if (idxArr[closest] === val) {
      slider.value = closest;
      slider.dispatchEvent(new Event('input'));
    } else {
      const hidden = document.getElementById('N');
      if (hidden) hidden.value = val;
      const label = slider.closest('.slider-container').querySelector('.slider-value');
      if (label) {
        const disp = val === 1 ? '1 person' :
          val >= 1000 ? `${val.toLocaleString()} people` : `${val} people`;
        label.textContent = disp;
      }
      slider.value = closest;
    }
    hideManualInput();
  }

  inputField.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); applyManualValue(); }
    else if (e.key === 'Escape') { e.preventDefault(); hideManualInput(); }
  });
  inputField.addEventListener('click', e => e.stopPropagation());
}
/**
 * Position the people slider thumb more accurately between non-exact ticks.
 * Currently logs the computed positions for debugging.
 * @param {HTMLInputElement} slider
 * @param {number} sliderIndex
 */
export function positionPeopleSliderThumb(slider, sliderIndex) {
  // This function just logs position data for debugging
  // We're using CSS to handle thumb alignment and not adjusting the thumb position
  // since browser thumb placement is based on the input's internal value logic
  return; // Skip this functionality as we're using a different approach
}
