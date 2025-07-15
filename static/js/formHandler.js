// formHandler.js — handle AJAX form submit and reset state management
/**
 * Initialize AJAX form submission and reset handlers for the exposure calculator.
 */
export function initFormHandler() {
  let isFirstCalculation = true;
  const priorForm = document.getElementById('priorForm');
  if (!priorForm) return;

  // Intercept submit to do AJAX update
  priorForm.addEventListener('submit', async function(event) {
    // Run any pre-submit field updates (e.g., mask filters)
    if (typeof handleFormSubmit === 'function') {
      handleFormSubmit(event);
    }
    if (event.defaultPrevented) return;
    event.preventDefault();

    // Record scroll position
    const scrollBefore = window.scrollY || window.pageYOffset;

    // Show loading indicator
    const submitBtn = document.querySelector('button[type="submit"]');
    let restoreBtn;
    if (submitBtn) {
      const orig = submitBtn.innerHTML;
      submitBtn.innerHTML = 'Calculating... <i class="fas fa-spinner fa-spin"></i>';
      restoreBtn = () => { submitBtn.innerHTML = orig; };
    }

    const formElem = this;
    const action = formElem.getAttribute('action') || window.location.href;
    const data = new FormData(formElem);
    try {
      const resp = await fetch(action, { method: 'POST', body: data });
      if (!resp.ok) throw new Error('Network response was not ok');
      const html = await resp.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const newRes = doc.getElementById('result');
      const oldRes = document.getElementById('result');
      if (newRes && oldRes) {
        oldRes.innerHTML = newRes.innerHTML;
        oldRes.style.display = 'block';
        if (isFirstCalculation) {
          oldRes.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          isFirstCalculation = false;
        } else {
          window.scrollTo({ top: scrollBefore, behavior: 'auto' });
        }
      }
    } catch (err) {
      console.error('Submission error:', err);
    } finally {
      if (submitBtn && typeof restoreBtn === 'function') restoreBtn();
    }
  });

  // Reset scroll state on reset button
  const resetBtn = document.querySelector('button[type="reset"]');
  if (resetBtn) resetBtn.addEventListener('click', () => { isFirstCalculation = true; });
  // Also listen for custom formReset event
  document.addEventListener('formReset', () => { isFirstCalculation = true; });
}