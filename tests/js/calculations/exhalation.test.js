// Dynamic import of ESM module
beforeAll(async () => {
import { computeExhalationFlowRate, getMultiplier } from '../../../static/js/calculations/exhalation.js';

describe('getMultiplier', () => {
  const multipliers = { a: { b: 3 }, x: { y: 0.5 } };
  test('returns correct multiplier if present', () => {
    expect(getMultiplier(multipliers, 'a', 'b')).toBe(3);
    expect(getMultiplier(multipliers, 'x', 'y')).toBe(0.5);
  });
  test('returns 1 if physical key missing', () => {
    expect(getMultiplier(multipliers, 'nope', 'b')).toBe(1);
  });
  test('returns 1 if vocal key missing', () => {
    expect(getMultiplier(multipliers, 'a', 'nope')).toBe(1);
  });
});

describe('computeExhalationFlowRate', () => {
  test('scales multiplier by 0.08', () => {
    expect(computeExhalationFlowRate(0)).toBe(0);
    expect(computeExhalationFlowRate(1)).toBeCloseTo(0.08, 5);
    expect(computeExhalationFlowRate(2.5)).toBeCloseTo(0.2, 5);
  });
});