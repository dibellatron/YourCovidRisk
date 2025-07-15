/**
 * Simple direct script to make slider labels clickable
 * This approaches the problem by directly targeting the labels with inline event handlers
 */

// When DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Wait a moment for all event handlers to attach
  setTimeout(addClickableLabels, 500);
});

// Also try when window is fully loaded
window.addEventListener('load', function() {
  // Try both immediately and after a delay (helps with dynamic content)
  addClickableLabels();
  setTimeout(addClickableLabels, 1000);
  
  // Ensures month sliders work correctly
  ensureMonthSlidersFunctionality();
});

// Helper function to ensure month sliders have data-month-value attributes
function ensureMonthSlidersFunctionality() {
  // Check vaccination time slider
  const vaccinationContainer = document.getElementById('vaccination_time_container');
  if (vaccinationContainer) {
    const labels = vaccinationContainer.querySelectorAll('.slider-labels span');
    const monthValues = [1, 3, 6, 9, 12]; // Expected month values
    
    labels.forEach((label, index) => {
      if (!label.hasAttribute('data-month-value') && index < monthValues.length) {
        label.setAttribute('data-month-value', monthValues[index]);
        console.log('Added data-month-value to vaccination label:', monthValues[index]);
      }
    });
  }
  
  // Check infection time slider
  const infectionContainer = document.getElementById('infection_time_container');
  if (infectionContainer) {
    const labels = infectionContainer.querySelectorAll('.slider-labels span');
    const monthValues = [1, 3, 6, 9, 12]; // Expected month values
    
    labels.forEach((label, index) => {
      if (!label.hasAttribute('data-month-value') && index < monthValues.length) {
        label.setAttribute('data-month-value', monthValues[index]);
        console.log('Added data-month-value to infection label:', monthValues[index]);
      }
    });
  }
}

function addClickableLabels() {
  console.log('Setting up clickable slider labels');
  // Collect all label spans inside slider containers, tick labels, and distance labels
  var sliderLabels = Array.from(document.querySelectorAll('.slider-labels span'));
  var tickLabels = Array.from(document.querySelectorAll('.slider-ticks .tick'));
  var distanceLabels = Array.from(document.querySelectorAll('.distance-labels .distance-label'));
  var allLabels = sliderLabels.concat(tickLabels).concat(distanceLabels);
  console.log('Found ' + allLabels.length + ' clickable labels');
  
  // We no longer need to handle time-label elements separately
  // since we've converted them to standard slider-labels format
  
  // Process each label
  allLabels.forEach(function(label) {
    // Make it visually clickable
    label.style.cursor = 'pointer';
    
    // Replace the element with a clone to remove any existing handlers
    var clone = label.cloneNode(true);
    if (label.parentNode) {
      label.parentNode.replaceChild(clone, label);
    }
    
    // Add three different event types for maximum compatibility
    // We'll use direct property assignment for maximum browser compatibility
    clone.onmousedown = handleLabelClick;
    clone.onclick = handleLabelClick;
    clone.ontouchstart = handleLabelClick;
  });
}

function handleLabelClick(event) {
  // Stop event propagation and prevent default behavior
  event.stopPropagation();
  event.preventDefault();
  
  console.log('Label clicked:', this.textContent);
  
  // Find the slider container
  var container = this.closest('.slider-container');
  if (!container) {
    console.error('Could not find slider container');
    return false;
  }
  
  // Find the slider input
  var slider = container.querySelector('input[type="range"]');
  if (!slider) {
    console.error('Could not find slider input');
    return false;
  }
  
  // Get the siblings to determine index
  var parent = this.parentNode;
  var siblings = Array.from(parent.children);
  var index = siblings.indexOf(this);
  console.log('Index:', index, 'of', siblings.length);

  // Handle distance slider label clicks
  if (parent.classList.contains('distance-labels')) {
    // Map click index to slider value (in feet) for distance slider
    var distanceMap = [0, 3, 6, 10, 15, 20];
    var sliderValue = distanceMap[index];
    console.log('Distance label clicked, setting slider', slider.id, 'to', sliderValue);
    slider.value = sliderValue;
    // Dispatch events
    try {
      slider.dispatchEvent(new MouseEvent('input', {bubbles: true}));
      slider.dispatchEvent(new MouseEvent('change', {bubbles: true}));
    } catch (e) {
      slider.dispatchEvent(new Event('input', {bubbles: true}));
      slider.dispatchEvent(new Event('change', {bubbles: true}));
    }
    // Update active class
    siblings.forEach(function(sibling) { sibling.classList.remove('active'); });
    this.classList.add('active');
    return false;
  }
  
  // Special handling for month sliders (vaccination and infection time)
  if ((slider.id === 'vaccination_time' || slider.id === 'infection_time') && 
      parent.classList.contains('slider-labels')) {
    // Check if we have a month value attribute
    var monthValue = this.getAttribute('data-month-value');
    if (monthValue) {
      monthValue = parseInt(monthValue);
      console.log('Month label clicked, setting slider', slider.id, 'to month value', monthValue);
      
      // Set slider directly to the month value
      slider.value = monthValue;
      
      // Call the appropriate update function
      if (slider.id === 'vaccination_time' && typeof updateVaccinationTimeLabel === 'function') {
        // Use setTimeout to ensure the value is fully updated in the DOM first
        setTimeout(function() {
          updateVaccinationTimeLabel(monthValue);
        }, 0);
      } else if (slider.id === 'infection_time' && typeof updateInfectionTimeLabel === 'function') {
        // Use setTimeout to ensure the value is fully updated in the DOM first
        setTimeout(function() {
          updateInfectionTimeLabel(monthValue);
        }, 0);
      } else {
        // Fallback: dispatch events to trigger oninput handlers
        try {
          slider.dispatchEvent(new MouseEvent('input', {bubbles: true}));
          slider.dispatchEvent(new MouseEvent('change', {bubbles: true}));
        } catch (e) {
          slider.dispatchEvent(new Event('input', {bubbles: true}));
          slider.dispatchEvent(new Event('change', {bubbles: true}));
        }
      }
      
      // Update active class
      siblings.forEach(function(sibling) { sibling.classList.remove('active'); });
      this.classList.add('active');
      return false;
    }
  }

  // Handle people slider tick label clicks
  if (parent.classList.contains('slider-ticks')) {
    // Use data-index attribute from drawPeopleTicks
    var dataIdx = parseFloat(this.getAttribute('data-index'));
    var sliderValue = Math.round(dataIdx);
    console.log('Tick label clicked, setting slider', slider.id, 'to index', sliderValue);
    slider.value = sliderValue;
    // Dispatch events
    try {
      slider.dispatchEvent(new MouseEvent('input', {bubbles: true}));
      slider.dispatchEvent(new MouseEvent('change', {bubbles: true}));
    } catch (e) {
      slider.dispatchEvent(new Event('input', {bubbles: true}));
      slider.dispatchEvent(new Event('change', {bubbles: true}));
    }
    return false;
  }

  // Determine slider value based on index and step for other sliders
  var min = parseFloat(slider.min) || 0;
  var max = parseFloat(slider.max);
  var step = parseFloat(slider.step);
  if (isNaN(step) || step === 0) {
    var count = siblings.length - 1;
    step = count > 0 ? (max - min) / count : 0;
  }
  var value = min + index * step;
  
  console.log('Setting slider', slider.id, 'to value', value);
  
  // Set the value directly
  slider.value = value;
  
  // Dispatch events to trigger any other handlers
  try {
    // Try MouseEvent first (more compatible with form handlers)
    slider.dispatchEvent(new MouseEvent('input', {bubbles: true}));
    slider.dispatchEvent(new MouseEvent('change', {bubbles: true}));
  } catch (e) {
    console.log('Using fallback Event dispatching');
    // Fallback to regular Event if MouseEvent not supported
    slider.dispatchEvent(new Event('input', {bubbles: true}));
    slider.dispatchEvent(new Event('change', {bubbles: true}));
  }
  
  // Update activity choice if this is an activity-related slider
  if (slider.id === 'activity_level_slider' || 
      slider.id === 'physical_intensity_slider' || 
      slider.id === 'vocalization_slider') {
    console.log('Activity slider changed, updating index fields and calling updateActivityChoice()');
    
    // Update the corresponding index field that updateActivityChoice() reads from
    let indexFieldId;
    if (slider.id === 'activity_level_slider') {
      indexFieldId = 'activity_level_index';
    } else if (slider.id === 'physical_intensity_slider') {
      indexFieldId = 'physical_intensity_index';
    } else if (slider.id === 'vocalization_slider') {
      indexFieldId = 'vocalization_index';
    }
    
    if (indexFieldId) {
      const indexField = document.getElementById(indexFieldId);
      if (indexField) {
        console.log(`Updating ${indexFieldId} from ${indexField.value} to ${value}`);
        indexField.value = value;
      } else {
        console.error(`Could not find index field: ${indexFieldId}`);
      }
    }
    
    if (typeof window.updateActivityChoice === 'function') {
      window.updateActivityChoice();
    } else {
      console.error('updateActivityChoice function not found on window object');
    }
  }
  
  // Update active class
  siblings.forEach(function(sibling) {
    sibling.classList.remove('active');
  });
  this.classList.add('active');
  
  return false;
}