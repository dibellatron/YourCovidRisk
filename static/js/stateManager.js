// stateManager.js — save and restore form state to sessionStorage with tab isolation
// Generate unique tab identifier to prevent cross-tab state interference
if (!window.name) {
  window.name = 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}
export const TAB_STORAGE_KEY = 'covidRiskFormState_' + window.name;

/**
 * Save current form state (all inputs/selects) to sessionStorage under tab-specific key.
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
  sessionStorage.setItem(TAB_STORAGE_KEY, JSON.stringify(state));
}

/**
 * Restore form state from sessionStorage (if available), merging with server-provided defaults.
 * Uses tab-specific storage key to prevent cross-tab interference.
 */
export function restoreFormState() {
  const stored = sessionStorage.getItem(TAB_STORAGE_KEY);
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