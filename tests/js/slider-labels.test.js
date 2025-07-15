/**
 * @jest-environment jsdom
 */
const fs = require('fs');
const path = require('path');

describe('slider-labels.js generic click behavior', () => {
  let addClickableLabels;

  beforeAll(() => {
    // Load and evaluate the slider-labels script in this JSDOM environment
    const scriptContent = fs.readFileSync(
      path.resolve(__dirname, '../../static/js/slider-labels.js'),
      'utf8'
    );
    const scriptEl = document.createElement('script');
    scriptEl.textContent = scriptContent;
    document.head.appendChild(scriptEl);
    addClickableLabels = window.addClickableLabels;
  });

  beforeEach(() => {
    // Set up a minimal 5-option slider fixture
    document.body.innerHTML = `
      <div class="slider-container">
        <input type="range" id="test_slider" min="1" max="5" step="1" value="3">
        <div class="slider-labels five-options">
          <span>Not at all</span>
          <span>Slightly</span>
          <span>Moderately</span>
          <span>Very</span>
          <span>Extremely</span>
        </div>
      </div>
    `;
  });

  test('clicking each label sets the slider value and active class', () => {
    const container = document.querySelector('.slider-container');
    const slider = container.querySelector('input[type="range"]');

    // Attach click handlers: this replaces each label element with a clone
    addClickableLabels();

    // Re-query labels to get the cloned elements now in the DOM
    const labels = Array.from(container.querySelectorAll('.slider-labels span'));

    labels.forEach((label, idx) => {
      // Simulate clicking the cloned label
      label.dispatchEvent(new MouseEvent('click', { bubbles: true }));

      // Expect slider.value = min + idx * step
      const expected = String(
        parseInt(slider.min, 10) + idx * parseInt(slider.step, 10)
      );
      expect(slider.value).toBe(expected);

      // Active class should be on the clicked label only
      labels.forEach(l => {
        expect(l.classList.contains('active')).toBe(l === label);
      });
    });
  });
  test('clicking each label on a 4-option slider sets the correct values', () => {
    document.body.innerHTML = `
      <div class="slider-container">
        <input type="range" id="test_slider4" min="0" max="3" step="1" value="1">
        <div class="slider-labels four-options">
          <span>Low</span>
          <span>Medium</span>
          <span>High</span>
          <span>Max</span>
        </div>
      </div>
    `;
    const container4 = document.querySelector('.slider-container');
    const slider4 = container4.querySelector('input[type="range"]');
    addClickableLabels();
    const labels4 = Array.from(container4.querySelectorAll('.slider-labels span'));
    labels4.forEach((label, idx) => {
      label.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      expect(slider4.value).toBe(String(parseInt(slider4.min, 10) + idx * parseInt(slider4.step, 10)));
      labels4.forEach(l => expect(l.classList.contains('active')).toBe(l === label));
    });
  });

  test('clicking each label on a 3-option slider sets the correct values', () => {
    document.body.innerHTML = `
      <div class="slider-container">
        <input type="range" id="test_slider3" min="0" max="2" step="1" value="1">
        <div class="slider-labels three-options">
          <span>Small</span>
          <span>Medium</span>
          <span>Large</span>
        </div>
      </div>
    `;
    const container3 = document.querySelector('.slider-container');
    const slider3 = container3.querySelector('input[type="range"]');
    addClickableLabels();
    const labels3 = Array.from(container3.querySelectorAll('.slider-labels span'));
    labels3.forEach((label, idx) => {
      label.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      expect(slider3.value).toBe(String(parseInt(slider3.min, 10) + idx * parseInt(slider3.step, 10)));
      labels3.forEach(l => expect(l.classList.contains('active')).toBe(l === label));
    });
  });
});
