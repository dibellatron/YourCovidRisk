beforeAll(async () => {
import { computeImmuneValue } from '../../../static/js/calculations/immuneSusceptibility.js';

describe('computeImmuneValue', () => {
  test('returns 1 when no vaccination or infection', () => {
    expect(computeImmuneValue({ recentVaccination: 'No', vaccinationMonths: null, recentInfection: 'No', infectionMonths: null })).toBe(1);
  });

  test('vaccination only gives reduced susceptibility', () => {
    // Legacy model: months=0 => immune=1-(52.37-0)/100 = 1 - 0.5237 = ~0.4763
    const val = computeImmuneValue({ recentVaccination: 'Yes', vaccinationMonths: 0, recentInfection: 'No', infectionMonths: null });
    expect(val).toBeCloseTo(0.4763, 4);
  });

  test('infection only gives reduced susceptibility (Chemaitelly unvaccinated)', () => {
    // New Chemaitelly model: P(t) = 0.85 * exp(-0.12 * t)
    // months=0 => protection = 0.85 * exp(0) = 0.85, immune_val = 1 - 0.85 = 0.15
    const val = computeImmuneValue({ recentVaccination: 'No', vaccinationMonths: null, recentInfection: 'Yes', infectionMonths: 0 });
    expect(val).toBeCloseTo(0.15, 4);
  });

  test('infection + vaccination gives reduced susceptibility (Chemaitelly vaccinated)', () => {
    // New Chemaitelly model: P(t) = 0.95 * exp(-0.18 * t)
    // months=1 => protection = 0.95 * exp(-0.18) = 0.95 * 0.835 = 0.793, immune_val = 1 - 0.793 = 0.207
    const val = computeImmuneValue({ recentVaccination: 'Yes', vaccinationMonths: 2, recentInfection: 'Yes', infectionMonths: 1 });
    expect(val).toBeCloseTo(0.207, 2);
  });

  test('infection protection decays over time', () => {
    // Test unvaccinated stratum decay
    const val3mo = computeImmuneValue({ recentVaccination: 'No', vaccinationMonths: null, recentInfection: 'Yes', infectionMonths: 3 });
    const val6mo = computeImmuneValue({ recentVaccination: 'No', vaccinationMonths: null, recentInfection: 'Yes', infectionMonths: 6 });
    // Protection should decay, so susceptibility should increase
    expect(val6mo).toBeGreaterThan(val3mo);
  });

  test('clamps values below 0 and above 1', () => {
    // custom artificially set extremes
    const low = computeImmuneValue({ recentVaccination: 'Yes', vaccinationMonths: 1000, recentInfection: 'No', infectionMonths: null });
    expect(low).toBeGreaterThanOrEqual(0);
    const hi = computeImmuneValue({ recentVaccination: 'No', vaccinationMonths: null, recentInfection: 'Yes', infectionMonths: -100 });
    expect(hi).toBeLessThanOrEqual(1);
  });
});