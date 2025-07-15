// Dynamic import of ESM module
beforeAll(async () => {
import { computeInhalationFilter, computeExhalationFilter } from '../../../static/js/calculations/maskFilter.js';

describe('computeInhalationFilter', () => {
  const fiLookupTable = {
    'cloth': { 'good': 0.6, 'poor': 0.8 },
    'n95': { 'perfect': 0.05 }
  };

  test('defaults to 1 when not masked', () => {
    expect(computeInhalationFilter({ masked: 'No', maskType: 'cloth', fitFactor: null, fiLookupTable })).toBe(1);
  });

  test('uses lookup value when masked and lookup available', () => {
    const val = computeInhalationFilter({ masked: 'Yes', maskType: 'cloth', fitFactor: 'good', fiLookupTable });
    expect(val).toBe(0.6);
  });

  test('overrides lookup with custom fitFactor > 0', () => {
    const val = computeInhalationFilter({ masked: 'Yes', maskType: 'cloth', fitFactor: '2', fiLookupTable });
    // 1 / 2 = 0.5
    expect(val).toBeCloseTo(0.5);
  });

  test('handles missing lookup gracefully and uses default 1', () => {
    const val = computeInhalationFilter({ masked: 'Yes', maskType: 'unknown', fitFactor: null, fiLookupTable });
    expect(val).toBe(1);
  });

  test('clamps negative values and values >1 to [0,1]', () => {
    const weirdTable = { 'm': { 'f': -0.5 } };
    expect(computeInhalationFilter({ masked: 'Yes', maskType: 'm', fitFactor: 'f', fiLookupTable: weirdTable })).toBe(0);
    // override with fitFactor of 0.1, yields 1/0.1=10 -> clamped to 1
    const val2 = computeInhalationFilter({ masked: 'Yes', maskType: 'm', fitFactor: '0.1', fiLookupTable: weirdTable });
    expect(val2).toBe(1);
  });
});

describe('computeExhalationFilter', () => {
  const maskTypesData = [
    { value: 'surgical', f_value: 0.7 },
    { value: 'cloth', f_value: 0.9 }
  ];

  test('fraction = sliderValue/100, clamped to [0,1]', () => {
    expect(computeExhalationFilter({ sliderValue: 50, othersMaskType: '', maskTypesData }).fraction).toBe(0.5);
    expect(computeExhalationFilter({ sliderValue: 200, othersMaskType: '', maskTypesData }).fraction).toBe(1);
    expect(computeExhalationFilter({ sliderValue: -10, othersMaskType: '', maskTypesData }).fraction).toBe(0);
  });

  test('feValue defaults to 1 when fraction=0 or type not provided', () => {
    const { feValue } = computeExhalationFilter({ sliderValue: 0, othersMaskType: 'surgical', maskTypesData });
    expect(feValue).toBe(1);
  });

  test('feValue set from maskTypesData when fraction>0', () => {
    const { feValue } = computeExhalationFilter({ sliderValue: 75, othersMaskType: 'surgical', maskTypesData });
    expect(feValue).toBe(0.7);
  });

  test('feValue remains 1 when mask type not found', () => {
    const { feValue } = computeExhalationFilter({ sliderValue: 50, othersMaskType: 'n95', maskTypesData });
    expect(feValue).toBe(1);
  });
});