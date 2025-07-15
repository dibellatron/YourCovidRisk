// genericSlider.js — initialize any slider with label and hidden inputs
/**
 * Initialize a slider element and its associated hidden form fields and display.
 * @param {string} sliderId - ID of the <input type="range">
 * @param {Array} values - array of values or objects with {value, display}
 * @param {string|null} valueField - ID of hidden value input
 * @param {string|null} indexField - ID of hidden index input
 * @param {string|null} displayField - ID of hidden display text input
 */
export function initializeSlider(sliderId, values, valueField, indexField, displayField) {
  const slider = document.getElementById(sliderId);
  if (!slider) return;

  const valueInput = valueField ? document.getElementById(valueField) : null;
  const currentValue = valueInput && valueInput.value
    ? valueInput.value
    : (values[0].value != null ? values[0].value : values[0]);

  let closestIndex = 0;
  if (typeof values[0] === 'object') {
    for (let i = 0; i < values.length; i++) {
      if (values[i].value === currentValue) {
        closestIndex = i;
        break;
      }
    }
  } else {
    let closestValue = values[0];
    let minDiff = Math.abs(currentValue - closestValue);
    for (let i = 1; i < values.length; i++) {
      const diff = Math.abs(currentValue - values[i]);
      if (diff < minDiff) {
        minDiff = diff;
        closestIndex = i;
        closestValue = values[i];
      }
    }
  }

  slider.value = closestIndex;
  if (indexField) {
    const idxInput = document.getElementById(indexField);
    if (idxInput) idxInput.value = closestIndex;
  }

  const container = slider.closest('.slider-container');
  if (container) {
    const valueLabel = container.querySelector('.slider-value');
    if (valueLabel) {
      let displayValue;
      if (typeof values[0] === 'object') {
        displayValue = values[closestIndex].display;
      } else {
        displayValue = values[closestIndex];
      }
      valueLabel.textContent = displayValue;
    }
  }

  if (displayField) {
    const dispInput = document.getElementById(displayField);
    if (dispInput) {
      if (typeof values[0] === 'object') {
        dispInput.value = values[closestIndex].display;
      } else {
        dispInput.value = values[closestIndex];
      }
    }
  }
}