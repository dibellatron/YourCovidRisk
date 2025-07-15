/**
 * @jest-environment jsdom
 */
// tests for stateManager.js
beforeAll(async () => {
import { saveFormState, restoreFormState } from '../../../static/js/stateManager.js';

beforeEach(() => {
  // Clear sessionStorage and DOM
  sessionStorage.clear();
  document.body.innerHTML = '';
});

describe('stateManager', () => {
  test('saveFormState stores inputs and selects', () => {
    // Setup DOM
    document.body.innerHTML = `
      <form class="form-container">
        <input name="a" value="1" />
        <select name="b"><option value="x" selected>x</option></select>
        <input name="c" value="" />
      </form>
    `;
    // Save
    saveFormState();
    const state = JSON.parse(sessionStorage.getItem('covidRiskFormState'));
    expect(state.a).toBe('1');
    expect(state.b).toBe('x');
    expect(state.b_text).toBe('x');
    // Unselected empty input stored as empty string
    expect(state.c).toBe('');
  });

  test('restoreFormState restores values without overriding non-empty', () => {
    // Initial DOM with server-provided values
    document.body.innerHTML = `
      <form id="priorForm" class="form-container">
        <input name="a" value="server" />
        <select name="b"><option value="x">X</option><option value="y">Y</option></select>
      </form>
    `;
    // Simulate saved client state
    const saved = { a: 'client', b: 'y', b_text: 'Y', ACH: '2.5', selected_environment_text: 'Env' };
    sessionStorage.setItem('covidRiskFormState', JSON.stringify(saved));
    // Add environment select and text field
    const envSelect = document.createElement('select');
    envSelect.id = 'ACH'; envSelect.innerHTML = '<option value=""></option><option value="2.5">Env</option>';
    document.body.appendChild(envSelect);
    const textInput = document.createElement('input');
    textInput.id = 'selected_environment_text'; textInput.value = '';
    document.body.appendChild(textInput);
    // Restore
    restoreFormState();
    // Expect form a was client
    expect(document.querySelector('input[name="a"]').value).toBe('client');
    // Expect select b restored to client value
    expect(document.querySelector('select[name="b"]').value).toBe('y');
    // Expect ACH select restored
    expect(document.getElementById('ACH').value).toBe('2.5');
    // Expect selected_environment_text restored
    expect(document.getElementById('selected_environment_text').value).toBe('Env');
  });
});