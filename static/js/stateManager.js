// stateManager.js — save and restore form state to sessionStorage
/**
 * Save current form state (all inputs/selects) to sessionStorage under 'covidRiskFormState'.
 */
export function saveFormState() {
  const state = {};
  document.querySelectorAll('input[name], select[name]').forEach(element => {
    if (element.name) {
      state[element.name] = element.value;
      if (element.tagName === 'SELECT' && element.selectedIndex > -1) {
        state[element.name + '_text'] = element.options[element.selectedIndex].textContent;
      }
    }
  });
  // Also store environment text
  const ach = document.getElementById('ACH');
  if (ach && ach.selectedIndex > -1) {
    state.selected_environment_text = ach.options[ach.selectedIndex].textContent;
  }
  sessionStorage.setItem('covidRiskFormState', JSON.stringify(state));
}

/**
 * Restore form state from sessionStorage (if available), merging with server-provided defaults.
 */
export function restoreFormState() {
  const stored = sessionStorage.getItem('covidRiskFormState');
  if (!stored) return;
  const state = JSON.parse(stored);
  // Restore environment text separately
  if (state.selected_environment_text) {
    const textField = document.getElementById('selected_environment_text');
    if (textField) {
      textField.value = state.selected_environment_text;
      // Apply to select via existing handler
      const event = new Event('change');
      document.getElementById('ACH').dispatchEvent(event);
    }
  }
  // Restore all fields
  document.querySelectorAll('input[name], select[name]').forEach(element => {
    const key = element.name;
    if (key && state[key] != null && state[key] !== '') {
      element.value = state[key];
    }
  });
}