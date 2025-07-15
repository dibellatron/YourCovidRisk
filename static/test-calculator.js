// index.js — CovidRisk
// IMPORTANT: All input fields (sliders, dropdowns, etc.) should retain their values across calculations.
// Only clearDashboard() should reset form values; user selections must persist after Calculate.

// Multiple test functionality re-enabled with advanced Bayesian model
function addTestBlock() {
  var testsContainer = document.getElementById('tests_container');
  
  // Create new test block
  var newTestBlock = document.createElement('div');
  newTestBlock.className = 'test-block';
  newTestBlock.innerHTML = `
    <div class="test-header">
      <span class="test-number"></span>
      <label>Test Type:
        <div class="select-wrapper">
          <select name="test_type" required class="dropdown-styled">
            <option value="" selected disabled></option>
            <option value="BinaxNOW">BinaxNOW</option>
            <option value="CorDx (Covid & Flu)">CorDx (Covid & Flu)</option>
            <option value="Flowflex (Covid-only)">Flowflex (Covid-only)</option>
            <option value="Flowflex Plus (Covid & Flu)">Flowflex Plus (Covid & Flu)</option>
            <option value="iHealth (Covid & Flu)">iHealth (Covid & Flu)</option>
            <option value="iHealth (Covid-only)">iHealth (Covid-only)</option>
            <option value="Lucira">Lucira</option>
            <option value="Metrix">Metrix</option>
            <option value="OSOM (Covid & Flu)">OSOM (Covid & Flu)</option>
            <option value="Other RAT (Rapid Antigen Test)">Other RAT (Rapid Antigen Test)</option>
            <option value="Pluslife">Pluslife</option>
            <option value="WELLLife (Covid & Flu)">WELLLife (Covid & Flu)</option>
          </select>
          <span class="validation-message">Please select an option</span>
        </div>
      </label>
    </div>
    <label class="test-result">Test Result:
      <div class="select-wrapper">
        <select name="test_result" required class="dropdown-styled">
          <option value="" selected disabled></option>
          <option value="positive">Positive</option>
          <option value="negative">Negative</option>
        </select>
        <span class="validation-message">Please select an option</span>
      </div>
      <!-- Remove button for additional tests -->
      <button type="button" class="remove-test-btn" onclick="removeTestBlock(this)">×</button>
    </label>
  `;
  
  // Add the new test block
  testsContainer.appendChild(newTestBlock);
  
  // Setup validation for the new test block
  setupTestBlockValidation(newTestBlock);
  
  // Update numbering for all test blocks
  updateTestBlockHeaders();
  
  // Update existing test blocks to show remove buttons
  updateRemoveButtons();
  
  // Update multiple tests timing note visibility
  updateMultipleTestsTimingNote();
}

function clearDashboard() {
  // Reset the form
  document.getElementById('dashboardForm').reset();
  document.getElementById('advanced').value = '';
  document.getElementById('symptoms').value = '';
  document.getElementById('covid_cautious').value = '';
  document.getElementById('cautionInfo').style.display = 'none';

  // Hide the cautiousness section (default state for no symptoms selected)
  const cautiousnessSection = document.getElementById('cautiousnessSection');
  if (cautiousnessSection) {
    cautiousnessSection.style.display = 'none';
  }

  // Hide the advanced fields
  document.getElementById('advancedFields').style.display = 'none';

  // Reset the tests container with one default test block
  var testsContainer = document.getElementById('tests_container');
  testsContainer.innerHTML = `
    <div class="test-block">
      <div class="test-header">
        <span class="test-number"></span>
        <label>Test Type:
          <div class="select-wrapper">
            <select name="test_type" required class="dropdown-styled">
              <option value="" selected disabled></option>
              <option value="BinaxNOW">BinaxNOW</option>
              <option value="CorDx (Covid & Flu)">CorDx (Covid & Flu)</option>
              <option value="Flowflex (Covid-only)">Flowflex (Covid-only)</option>
              <option value="Flowflex Plus (Covid & Flu)">Flowflex Plus (Covid & Flu)</option>
              <option value="iHealth (Covid & Flu)">iHealth (Covid & Flu)</option>
              <option value="iHealth (Covid-only)">iHealth (Covid-only)</option>
              <option value="Lucira">Lucira</option>
              <option value="Metrix">Metrix</option>
              <option value="OSOM (Covid & Flu)">OSOM (Covid & Flu)</option>
              <option value="Other RAT (Rapid Antigen Test)">Other RAT (Rapid Antigen Test)</option>
              <option value="Pluslife">Pluslife</option>
              <option value="WELLLife (Covid & Flu)">WELLLife (Covid & Flu)</option>
            </select>
            <span class="validation-message">Please select an option</span>
          </div>
        </label>
      </div>
      <label class="test-result">Test Result:
        <div class="select-wrapper">
          <select name="test_result" required class="dropdown-styled">
            <option value="" selected disabled></option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
          </select>
          <span class="validation-message">Please select an option</span>
        </div>
      </label>
    </div>
  `;

  // Ensure numbering and remove buttons are updated after reset
  updateTestBlockHeaders();
  updateRemoveButtons();
  updateMultipleTestsTimingNote();

  // Setup validation for the new default test block
  var defaultTestBlock = testsContainer.querySelector('.test-block');
  if (defaultTestBlock) {
    setupTestBlockValidation(defaultTestBlock);
  }

  // Clear risk messages
  var riskContainer = document.getElementById('riskContainer');
  if (riskContainer) {
    // Clear and hide the risk results container
    riskContainer.innerHTML = '';
    riskContainer.style.display = 'none';
  }

  // Clear any error messages
  var errorMsg = document.getElementById('errorMessage');
  if (errorMsg) {
    errorMsg.innerHTML = '';
  }

  // Reset the covid-cautious slider to default (3 - Moderately)
  const covidCautiousSlider = document.getElementById('covid_cautious_level');
  if (covidCautiousSlider) {
    covidCautiousSlider.value = 3;
    updateCautionLevel(3); // Make sure the display updates
  }

  // Reset first calculation state if the function exists
  if (typeof window.resetTestCalculation === 'function') {
    window.resetTestCalculation();
  }
}

function toggleAdvancedFields() {
  var advDiv = document.getElementById('advancedFields');
  var advancedField = document.getElementById('advanced');

  if (advDiv.style.display === 'none' || advDiv.style.display === '') {
    // First set to initial state and trigger reflow
    advDiv.style.animation = 'none';
    advDiv.offsetHeight; // Force reflow

    // Apply the animation and show the container
    advDiv.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
    advDiv.style.display = 'block';
    advancedField.value = 'true';
  } else {
    // Apply fade-out animation
    advDiv.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

    // Wait for animation to complete, then hide the element
    setTimeout(() => {
      advDiv.style.display = 'none';
      advancedField.value = '';
    }, 300);
  }
}

function toggleCautionInfo() {
  var infoDiv = document.getElementById('cautionInfo');
  // Reference to slider container (no longer used to hide overlays).
  var sliderEl = document.getElementById('covid_cautious_level');
  var sliderContainer = sliderEl ? sliderEl.closest('.slider-container') : null;
  if (infoDiv.style.display === 'none' || infoDiv.style.display === '') {
    // First set to initial state and trigger reflow
    infoDiv.style.animation = 'none';
    infoDiv.offsetHeight; // Force reflow

    // Apply the animation and show the container
    infoDiv.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
    infoDiv.style.display = 'block';

    // no hiding of overlays – keep ticks/labels visible
  } else {
    // Apply fade-out animation
    infoDiv.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

    // Wait for animation to complete, then hide the element
    setTimeout(() => {
      infoDiv.style.display = 'none';
    }, 300);

    // nothing to restore
  }
}

function toggleFaqAnswer(button) {
  var answer = button.nextElementSibling;
  if (answer.style.display === "none" || answer.style.display === "") {
    // First set to initial state and trigger reflow
    answer.style.animation = 'none';
    answer.offsetHeight; // Force reflow

    // Apply the animation and show the container
    answer.style.animation = 'fadeInSlideDown 0.4s ease-out forwards';
    answer.style.display = "block";
  } else {
    // Apply fade-out animation
    answer.style.animation = 'fadeOutSlideUp 0.3s ease-out forwards';

    // Wait for animation to complete, then hide the element
    setTimeout(() => {
      answer.style.display = "none";
    }, 300);
  }
}

// Multiple test functionality re-enabled with advanced Bayesian model
function removeTestBlock(button) {
  var testBlock = button.closest('.test-block');
  var testsContainer = document.getElementById('tests_container');
  
  // Don't remove if it's the only test block
  var testBlocks = testsContainer.querySelectorAll('.test-block');
  if (testBlocks.length <= 1) {
    return;
  }
  
  // Remove the test block
  testBlock.remove();
  
  // Update numbering for remaining test blocks
  updateTestBlockHeaders();
  
  // Update remove buttons visibility
  updateRemoveButtons();
  
  // Update multiple tests timing note visibility
  updateMultipleTestsTimingNote();
}

// Function to update test block numbering
function updateTestBlockHeaders() {
  const testBlocks = document.querySelectorAll('.test-block');
  const totalTests = testBlocks.length;

  // If there's only one test, don't number it
  if (totalTests === 1) {
    testBlocks[0].querySelector('.test-number').textContent = '';
  } else {
    // Number all tests when there are multiple
    testBlocks.forEach((block, index) => {
      block.querySelector('.test-number').textContent = `${index + 1}.`;
    });
  }
}

// Function to update remove button visibility
function updateRemoveButtons() {
  const testBlocks = document.querySelectorAll('.test-block');
  const totalTests = testBlocks.length;

  testBlocks.forEach((block, index) => {
    let removeButton = block.querySelector('.remove-test-btn');
    
    if (totalTests > 1) {
      // Multiple tests - ensure remove buttons exist
      if (!removeButton) {
        // Add remove button if it doesn't exist
        const testResultLabel = block.querySelector('.test-result');
        if (testResultLabel) {
          removeButton = document.createElement('button');
          removeButton.type = 'button';
          removeButton.className = 'remove-test-btn';
          removeButton.innerHTML = '×';
          removeButton.onclick = function() { removeTestBlock(this); };
          testResultLabel.appendChild(removeButton);
        }
      }
    } else {
      // Single test - remove any remove buttons
      if (removeButton) {
        removeButton.remove();
      }
    }
  });
}

// Function to update multiple tests timing note visibility
function updateMultipleTestsTimingNote() {
  const testBlocks = document.querySelectorAll('.test-block');
  const timingNote = document.getElementById('multipleTestsTimingNote');
  
  if (!timingNote) return;
  
  if (testBlocks.length > 1) {
    // Show timing note for multiple tests
    timingNote.style.display = 'block';
  } else {
    // Hide timing note for single test
    timingNote.style.display = 'none';
  }
}

// Optionally, you can attach event listeners here if needed

// Validate advanced fields before form submission
document.getElementById('dashboardForm').addEventListener('submit', function(event) {
  var advDiv = document.getElementById('advancedFields');
  // Only validate if advanced fields are visible
  if (advDiv.style.display !== 'none') {
    var covidPrevalenceInput = document.getElementById('covidPrevalence');
    var positivityRateInput = document.getElementById('positivityRate');
    var covidPrevalenceValue = parseFloat(covidPrevalenceInput.value);
    var positivityRateValue = parseFloat(positivityRateInput.value);
    var errorMessage = '';

    if (!isNaN(covidPrevalenceValue)) {
      if (covidPrevalenceValue < 0 || covidPrevalenceValue > 100) {
        errorMessage += 'Covid Prevalence must be between 0 and 100. ';
      }
    }

    if (!isNaN(positivityRateValue)) {
      if (positivityRateValue < 0 || positivityRateValue > 100) {
        errorMessage += 'Positivity Rate must be between 0 and 100. ';
      }
    }

    if (errorMessage) {
      event.preventDefault();
      var errorMsg = document.getElementById('errorMessage');
      if (errorMsg) {
        errorMsg.innerText = errorMessage;
      }
    }
    // We don't need to set scrollToResults flag anymore as we use the scrollPos approach
  }
});

function toggleAdvancedRangeDisplay() {
  var confidenceIntervalsDisplay = document.getElementById('confidenceIntervalsDisplay');
  var toggleBtn = document.getElementById('toggleAdvancedRange');

  if (confidenceIntervalsDisplay) {
    var currentDisplay = window.getComputedStyle(confidenceIntervalsDisplay).display;
    if (currentDisplay === 'none') {
      confidenceIntervalsDisplay.style.display = 'block';

      // Check if uncertainty data is needed but not loaded
      var uncertaintyLoading = document.getElementById('uncertaintyLoading');
      var confidenceSections = confidenceIntervalsDisplay.querySelectorAll('.confidence-interval-section');

      // Check if we need to request uncertainty calculation
      if (uncertaintyLoading || confidenceSections.length === 0 ||
          Array.from(confidenceSections).some(section => section.textContent.includes('Calculating'))) {
        console.log("Requesting uncertainty calculation...");
        // Request uncertainty calculation via AJAX
        requestMonteCarloCalculation();
      }
    } else {
      confidenceIntervalsDisplay.style.display = 'none';
    }
  }
}

// Function to request Monte Carlo calculation via AJAX
function requestMonteCarloCalculation() {
  // Get the current form data
  var form = document.getElementById('dashboardForm');
  if (!form) return;

  var formData = new FormData(form);

  // Add a flag to request Monte Carlo calculation
  formData.append('calculate_monte_carlo', 'true');

  // Add loading indicator for uncertainty analysis
  var uncertaintyContainer = document.querySelector('.confidence-interval-section');
  if (uncertaintyContainer) {
    uncertaintyContainer.innerHTML = '<p style="font-size: smaller;"><span id="uncertaintyLoading">Calculating uncertainty ranges...<i class="fas fa-spinner fa-spin"></i></span></p>';
  }

  console.log("Sending Monte Carlo calculation request");

  // Make AJAX request
  fetch(window.location.href, {
    method: 'POST',
    body: formData
  })
  .then(async response => {
    if (!response.ok) {
      // Try to parse error response as JSON
      try {
        const errorData = await response.json();
        if (errorData.error) {
          // Display the specific error message
          var errorMsg = document.getElementById('calculationErrorMessage');
          if (errorMsg) {
            errorMsg.innerHTML = errorData.error;
            errorMsg.style.display = 'block';
            errorMsg.style.color = '#ef4444';
            errorMsg.style.backgroundColor = '#fef2f2';
            errorMsg.style.border = '1px solid #fecaca';
            errorMsg.style.padding = '1rem';
            errorMsg.style.borderRadius = '0.5rem';
            errorMsg.style.marginBottom = '1rem';
          }
          throw new Error(errorData.error);
        }
      } catch (jsonError) {
        // Fall back to generic error if JSON parsing fails
      }
      throw new Error('Network response was not ok');
    }
    return response.text();
  })
  .then(html => {
    console.log("Received Monte Carlo response");

    // Parse the response HTML
    var parser = new DOMParser();
    var doc = parser.parseFromString(html, 'text/html');

    // Extract all confidence interval sections from the response
    var newConfidenceSections = doc.querySelectorAll('.confidence-interval-section');
    var confidenceIntervalsDisplay = document.getElementById('confidenceIntervalsDisplay');
    var currentConfidenceContainer = document.querySelector('.confidence-interval-section')?.parentNode || confidenceIntervalsDisplay;

    console.log("Confidence sections:", {
      newCount: newConfidenceSections.length,
      containerFound: currentConfidenceContainer ? "Found" : "Not found",
      confidenceIntervalsDisplayFound: confidenceIntervalsDisplay ? "Found" : "Not found"
    });

    if (newConfidenceSections.length > 0 && currentConfidenceContainer) {
      // Remove all existing confidence interval sections
      var existingSections = currentConfidenceContainer.querySelectorAll('.confidence-interval-section');
      existingSections.forEach(section => section.remove());

      // Add all new confidence interval sections
      newConfidenceSections.forEach(section => {
        currentConfidenceContainer.appendChild(section.cloneNode(true));
      });

      // Apply risk colors to all Monte Carlo bounds
      var mcBounds = currentConfidenceContainer.querySelectorAll('.mc-bound');
      console.log(`Found ${mcBounds.length} uncertainty bounds to colorize`);

      mcBounds.forEach(bound => {
        // Extract percentage value
        var percentText = bound.textContent.trim();
        var percentValue = parseFloat(percentText) / 100;

        if (!isNaN(percentValue)) {
          console.log(`Colorizing bound: ${percentText} to color value ${percentValue}`);
          bound.style.color = getRiskColor(percentValue);
        }
      });

      // Add the confidence interval explainer if it doesn't exist
      var existingExplainer = currentConfidenceContainer.querySelector('.confidence-interval-explainer');
      if (!existingExplainer) {
        var newExplainer = doc.querySelector('.confidence-interval-explainer');
        if (newExplainer) {
          console.log("Adding confidence interval explainer");
          currentConfidenceContainer.appendChild(newExplainer.cloneNode(true));
        }
      }
    }
  })
  .catch(error => {
    console.error('Error fetching Monte Carlo data:', error);
    var monteCarloRange = document.getElementById('monteCarloRange');
    if (monteCarloRange) {
      monteCarloRange.innerHTML = '<span style="color: #ef4444;">Error calculating Monte Carlo simulation. Please try again.</span>';
    }
  });
}

// Function to setup validation for a test block
function setupTestBlockValidation(testBlock) {
  // Find all selects in this test block
  const selects = testBlock.querySelectorAll('select');
  selects.forEach(function(select) {
    // Add invalid event listener to each select
    select.addEventListener('invalid', function(e) {
      // Prevent default validation popup
      e.preventDefault();

      // Add custom validation class
      this.classList.add('validation-error');

      // Clear validation state when user interacts with the field
      this.addEventListener('change', function() {
        this.classList.remove('validation-error');
      }, { once: true });
    });
  });
}

// Run once on page load to initialize test numbering and validation
document.addEventListener('DOMContentLoaded', function() {
  // Initialize test block numbering and remove buttons
  updateTestBlockHeaders();
  updateRemoveButtons();
  updateMultipleTestsTimingNote();

  // Setup validation for all existing test blocks
  document.querySelectorAll('.test-block').forEach(function(testBlock) {
    setupTestBlockValidation(testBlock);
  });
});

// AJAX form submission for test calculator: update result without full page reload
document.addEventListener('DOMContentLoaded', function() {
  // Track whether this is the first calculation in this session
  let isFirstCalculation = true;

  var dashboardForm = document.getElementById('dashboardForm');
  if (dashboardForm) {
    dashboardForm.addEventListener('submit', async function(event) {
      // Allow built-in validation handlers to run first
      if (event.defaultPrevented) return;

      // Prevent default form submission to avoid page reload
      event.preventDefault();

      // Show loading indicator if needed
      const submitBtn = document.querySelector('button[type="submit"]');
      let restoreButton;
      if (submitBtn) {
        const originalHTML = submitBtn.innerHTML;
        submitBtn.innerHTML = 'Calculating... <i class="fas fa-spinner fa-spin"></i>';

        // Restore original HTML when loading completes (in success or error)
        restoreButton = () => {
          submitBtn.innerHTML = originalHTML;
        };
      }

      var form = this;
      var action = form.getAttribute('action') || window.location.href;
      var formData = new FormData(form);

      try {
        // Send the form data via AJAX
        var response = await fetch(action, {
          method: 'POST',
          body: formData
        });

        // Check for rate limiting first
        if (response.status === 429) {
          // Display rate limit message to user below the Calculate button
          var errorMsg = document.getElementById('calculationErrorMessage');
          if (errorMsg) {
            errorMsg.innerHTML = '<strong>Please slow down!</strong> You\'ve made too many requests. Please wait a minute and try again.';
            errorMsg.style.display = 'block';
            errorMsg.style.color = '#856404';
            errorMsg.style.backgroundColor = '#fff3cd';
            errorMsg.style.border = '1px solid #ffeaa7';
            errorMsg.style.padding = '1rem';
            errorMsg.style.borderRadius = '0.5rem';
            errorMsg.style.marginBottom = '1rem';
          }
          // Reset submit button and return early
          if (submitBtn && typeof restoreButton === 'function') restoreButton();
          return;
        }

        if (!response.ok) {
          // Try to parse error response as JSON
          try {
            const errorData = await response.json();
            if (errorData.error) {
              // Display the specific error message
              var errorMsg = document.getElementById('calculationErrorMessage');
              if (errorMsg) {
                errorMsg.innerHTML = errorData.error;
                errorMsg.style.display = 'block';
                errorMsg.style.color = '#ef4444';
                errorMsg.style.backgroundColor = '#fef2f2';
                errorMsg.style.border = '1px solid #fecaca';
                errorMsg.style.padding = '1rem';
                errorMsg.style.borderRadius = '0.5rem';
                errorMsg.style.marginBottom = '1rem';
              }
              if (submitBtn && typeof restoreButton === 'function') restoreButton();
              return;
            }
          } catch (jsonError) {
            // Fall back to generic error if JSON parsing fails
          }
          throw new Error('Network response was not ok');
        }

        // Parse the HTML response
        var html = await response.text();

        // Log HTML for debugging
        console.log("Raw HTML response snippet:", html.substring(0, 500) + "...");

        var parser = new DOMParser();
        var doc = parser.parseFromString(html, 'text/html');

        // Update error message if any
        var newError = doc.getElementById('errorMessage');
        var oldError = document.getElementById('errorMessage');
        if (newError && oldError) oldError.innerHTML = newError.innerHTML;
        
        // Clear any calculation error messages on successful calculation
        var calcErrorMsg = document.getElementById('calculationErrorMessage');
        if (calcErrorMsg) {
          calcErrorMsg.style.display = 'none';
          calcErrorMsg.innerHTML = '';
        }

        // Update result container
        var newRisk = doc.getElementById('riskContainer');
        var oldRisk = document.getElementById('riskContainer');

        if (newRisk && oldRisk) {
          // Update the result container with new content
          oldRisk.innerHTML = newRisk.innerHTML;

          // Make sure the result container is visible
          oldRisk.style.display = 'block';

          // Apply risk color using the shared utility to main risk value
          const riskElement = oldRisk.querySelector('#testRiskValue');
          if (riskElement) {
            // Extract risk value from text content
            const riskText = riskElement.textContent.trim();
            const riskValue = parseFloat(riskText) / 100;

            if (!isNaN(riskValue)) {
              riskElement.style.color = getRiskColor(riskValue);
            }
          }

          // Get advanced range elements and color them if present
          const advancedRange = oldRisk.querySelector('#advancedRange');
          if (advancedRange) {
            // Apply colors to extreme bound values
            const extremeElements = advancedRange.querySelectorAll('[id$="BoundExtreme"]');
            extremeElements.forEach(elem => {
              if (elem.id.includes('lower')) {
                // For lower bound extreme, use very low risk color
                elem.style.color = getRiskColor(0.000001);
              } else if (elem.id.includes('upper')) {
                // For upper bound extreme, use very high risk color
                elem.style.color = getRiskColor(0.999999);
              }
            });

            // Handle all other values in the range
            const scriptTags = advancedRange.querySelectorAll('script');
            // Remove script tags that were inserted for initial color setting
            // to avoid duplicating event handlers
            scriptTags.forEach(script => script.remove());
          }

          // Handle calculation details for the Explain calculation feature
          // First, directly extract and log all script tags for inspection
          const allScripts = oldRisk.querySelectorAll('script');
          console.log(`Found ${allScripts.length} script tags in risk container`);

          allScripts.forEach((script, index) => {
            console.log(`Script ${index + 1} content:`, script.textContent.substring(0, 200) + "...");
          });

          // Look for a script tag with calculationDetails JSON
          let calculationDetails = null;

          // Directly extract from the HTML response - more reliable method
          const scriptWithCalcData = Array.from(allScripts).find(script =>
            script.textContent.includes('calculationDetails') && script.textContent.includes('step1')
          );

          if (scriptWithCalcData) {
            console.log("Found script with calculation details, attempting to extract JSON");

            try {
              // Use a better regex pattern to match the JSON
              const jsonPattern = /const\s+calculationDetails\s*=\s*({.+?step1.+?step2.+?step3.+?step4.+?});/s;
              const match = scriptWithCalcData.textContent.match(jsonPattern);

              if (match && match[1]) {
                console.log("Found JSON string:", match[1]);

                // Try to parse the JSON
                try {
                  calculationDetails = JSON.parse(match[1]);
                  console.log("Successfully parsed calculation details:", calculationDetails);
                } catch (parseError) {
                  console.error("Parse error:", parseError);

                  // Try with regex replacements
                  try {
                    const cleanedJson = match[1]
                      .replace(/'/g, '"')
                      .replace(/(\w+):/g, '"$1":')
                      .replace(/\n/g, ' ');

                    calculationDetails = JSON.parse(cleanedJson);
                    console.log("Parsed calculation details with cleanup:", calculationDetails);
                  } catch (fallbackError) {
                    console.error("Fallback parse failed:", fallbackError);
                  }
                }

                // If we have data, populate the calculation panel
                if (calculationDetails && typeof window.populateCalculationSteps === 'function') {
                  window.populateCalculationSteps(calculationDetails);
                }
              }
            } catch (e) {
              console.error("Error processing script with calculation details:", e);
            }
          } else {
            // Fallback: look for debug-calculation-details div
            const debugDiv = oldRisk.querySelector('#debug-calculation-details pre');
            if (debugDiv) {
              try {
                console.log("Found debug calculation details div, parsing contents");
                calculationDetails = JSON.parse(debugDiv.textContent);
                console.log("Parsed debug calculation details:", calculationDetails);

                if (calculationDetails && typeof window.populateCalculationSteps === 'function') {
                  window.populateCalculationSteps(calculationDetails);
                }
              } catch (e) {
                console.error("Error parsing debug details:", e);
              }
            } else {
              console.log("No calculation details found in response");

              // Try direct access to the DOM elements (fallback)
              const step1 = oldRisk.querySelector('#step1Detail');
              const step2 = oldRisk.querySelector('#step2Detail');
              const step3 = oldRisk.querySelector('#step3Detail');
              const step4 = oldRisk.querySelector('#step4Detail');

              console.log("DOM elements in new HTML:", {step1, step2, step3, step4});

              // If elements exist with content, we can directly transfer their innerHTML
              if (step1 && step1.innerHTML && step1.innerHTML !== 'Loading...') {
                document.getElementById('step1Detail').innerHTML = step1.innerHTML;
              }
              if (step2 && step2.innerHTML && step2.innerHTML !== 'Loading...') {
                document.getElementById('step2Detail').innerHTML = step2.innerHTML;
              }
              if (step3 && step3.innerHTML && step3.innerHTML !== 'Loading...') {
                document.getElementById('step3Detail').innerHTML = step3.innerHTML;
              }
              if (step4 && step4.innerHTML && step4.innerHTML !== 'Loading...') {
                document.getElementById('step4Detail').innerHTML = step4.innerHTML;
              }
            }
          }

          // Only scroll on first calculation
          if (isFirstCalculation) {
            // Smooth scroll to the result container
            oldRisk.scrollIntoView({
              behavior: 'smooth',
              block: 'nearest'
            });

            // Mark that we've now calculated once
            isFirstCalculation = false;
          }
        }

        // Reset submit button if needed
        if (submitBtn && typeof restoreButton === 'function') restoreButton();
      } catch (err) {
        console.error('Submission error:', err);
        
        // Display generic error message for network/other errors
        var errorMsg = document.getElementById('calculationErrorMessage');
        if (errorMsg) {
          errorMsg.innerHTML = 'An error occurred while calculating. Please try again.';
          errorMsg.style.display = 'block';
          errorMsg.style.color = '#ef4444';
          errorMsg.style.backgroundColor = '#fef2f2';
          errorMsg.style.border = '1px solid #fecaca';
          errorMsg.style.padding = '1rem';
          errorMsg.style.borderRadius = '0.5rem';
          errorMsg.style.marginBottom = '1rem';
        }
        
        // Reset submit button if needed
        if (submitBtn && typeof restoreButton === 'function') restoreButton();
      }
    });

    // Reset first calculation state when the form is cleared
    document.querySelector('button[onclick="clearDashboard()"]').addEventListener('click', function() {
      isFirstCalculation = true;
    });

    // Also expose a method to reset the first calculation state that can be called from clearDashboard
    window.resetTestCalculation = function() {
      isFirstCalculation = true;
    };
  }
});
