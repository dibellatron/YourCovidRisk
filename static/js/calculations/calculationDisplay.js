/**
 * calculationDisplay.js
 *
 * Module for displaying calculation steps in the Covid Test Calculator.
 * Handles the "Explain calculation" feature to explain how the probability was calculated.
 *
 * IMPORTANT: The Python backend (test_calculator.py) is the source of truth for the
 * calculation text. The JavaScript in this file should only handle the display logic
 * and use the content provided by the backend.
 */

/**
 * Toggle the calculation panel visibility
 */
function toggleCalculationDisplay() {
  const panel = document.getElementById('calculationPanel');
  const toggleBtn = document.getElementById('toggleCalculation');

  if (!panel || !toggleBtn) return;

  if (panel.style.display === 'none' || panel.style.display === '') {
    panel.style.display = 'block';
    toggleBtn.innerHTML = 'Hide explanation';
  } else {
    panel.style.display = 'none';
    toggleBtn.innerHTML = 'Explain calculation';
  }
}

/**
 * Format a decimal as a percentage string
 * Helper function for fallback display logic
 */
function formatPercent(value) {
  if (typeof value !== 'number') return '0%';
  return (value * 100).toFixed(1) + '%';
}

/**
 * Populate the calculation steps panel with data from the backend
 * Python backend (test_calculator.py) is the source of truth for text content
 */
function populateCalculationSteps(data) {
  console.log("populateCalculationSteps called with data:", data);

  // Get the elements
  const step1Elem = document.getElementById('step1Detail');
  const step2Elem = document.getElementById('step2Detail');
  const step3Elem = document.getElementById('step3Detail');
  const step2Section = step2Elem?.closest('.calculation-section');
  const step3Section = step3Elem?.closest('.calculation-section');

  if (!step1Elem || !step2Elem || !step3Elem || !step2Section || !step3Section) {
    console.error("Calculation display elements not found");
    return;
  }

  try {
    // Check if this is a manual prior case
    const isManualPrior = data?.step1?.detail &&
                        data?.step1?.detail.includes("entered prior probability") &&
                        !data?.step1?.detail.includes("overrides all other inputs");

    // Check if this is a symptomatic case
    const isSymptomatic = data?.step3?.symptoms === "yes";
    
    // Check if this is an "I'm not sure" case
    const isUnsure = data?.step3?.symptoms === "I'm not sure";

    // Get confidence interval step elements
    const step4Elem = document.getElementById('step4Detail');
    const step4Section = step4Elem?.closest('.calculation-section');
    const step4TitleElem = document.getElementById('step4Title');

    // Update step visibility and numbering based on manual prior, symptomatic status, or unsure status
    if (isUnsure) {
      // For "I'm not sure" case, hide empty sections completely
      const step1TitleElem = step1Elem?.previousElementSibling;
      const step2TitleElem = step2Elem?.previousElementSibling;
      const step3TitleElem = document.getElementById('step3Title');
      
      if (step1TitleElem) step1TitleElem.style.display = 'none';
      if (step2TitleElem) step2TitleElem.style.display = 'none';
      if (step3TitleElem) step3TitleElem.style.display = 'none';
      if (step4TitleElem) step4TitleElem.style.display = 'none';
      
      // Hide step2 and step3 sections entirely for "I'm not sure" case
      step2Section.style.display = 'none';
      step3Section.style.display = 'none';
      
    } else if (isManualPrior || isSymptomatic) {
      // Hide step 2 section (caution adjustment)
      step2Section.style.display = 'none';

      // Renumber step 3 to be step 2
      const step3TitleElem = document.getElementById('step3Title');
      if (step3TitleElem && data?.step3?.title) {
        step3TitleElem.textContent = `2. ${data.step3.title}`;
      }

      // Renumber step 4 to be step 3
      if (step4TitleElem && data?.step4?.title) {
        step4TitleElem.textContent = `3. ${data.step4.title}`;
      }
    } else {
      // Show step 2 for asymptomatic non-manual prior cases
      step2Section.style.display = '';

      // Keep original numbering
      const step3TitleElem = document.getElementById('step3Title');
      if (step3TitleElem && data?.step3?.title) {
        step3TitleElem.textContent = `3. ${data.step3.title}`;
      }

      // Keep original numbering for step 4
      if (step4TitleElem && data?.step4?.title) {
        step4TitleElem.textContent = `4. ${data.step4.title}`;
      }
    }

    // Populate content for all steps
    if (data?.step1?.detail) {
      step1Elem.innerHTML = data.step1.detail;
    }

    // Only populate step2 and step3 if not "I'm not sure" case
    if (!isUnsure) {
      if (data?.step2?.detail) {
        step2Elem.innerHTML = data.step2.detail;
      }

      // For step 3, use the detailed HTML content provided by the Python backend
      if (data?.step3?.detail) {
        step3Elem.innerHTML = data.step3.detail;

        // Add client-side enhancement - fix FAQ links to use proper URL if needed
        const faqLinks = step3Elem.querySelectorAll('a[href="#faq"]');
        faqLinks.forEach(link => {
          // If we have a proper FAQ URL in the page, use it
          const faqElement = document.getElementById('faq');
          if (faqElement) {
            link.href = "#faq";
          }
        });
      } else {
        console.warn("Missing step3 detail data");
        step3Elem.innerHTML = "<p>No calculation details were provided.</p>";
      }
    }

    // For step 4 (confidence interval), use the HTML content from the Python backend
    if (step4Elem && data?.step4?.detail) {
      step4Elem.innerHTML = data.step4.detail;
    } else if (step4Elem && !isUnsure) {
      console.warn("Missing step4 detail data");
      step4Elem.innerHTML = "<p>No confidence interval details were provided.</p>";
    }
  } catch (error) {
    console.error("Error in populateCalculationSteps:", error);
  }
}

// Export functions for external use
export { toggleCalculationDisplay, populateCalculationSteps };
