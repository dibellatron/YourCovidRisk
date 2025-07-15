// Dynamic import of ESM module
beforeAll(async () => {
import { computeVolume, computeACH } from '../../../static/js/calculations/environment.js';

describe('computeVolume', () => {
  const baseData = {
    carTypes: [{ value: 'suv', volume: 4 }],
    airplaneTypes: [{ value: 'medium', volume: 125 }],
    carAchValues: ['2.5'],
    airplaneAchValues: ['15.00'],
    environments: [
      { options: [{ value: '1', volume: 10 }] }
    ]
  };

  test('uses customVolume override when advancedEnabled is true', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: '1', carType: '', airplaneType: '', customVolume: '500', covidRiskData: baseData, advancedEnabled: true
      })
    ).toBe(500);
  });

  test('ignores customVolume when advancedEnabled is false', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: '1', carType: '', airplaneType: '', customVolume: '500', covidRiskData: baseData, advancedEnabled: false
      })
    ).toBe(10); // Should use environment volume instead
  });

  test('ignores customVolume when advancedEnabled is not provided (defaults to false)', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: '1', carType: '', airplaneType: '', customVolume: '500', covidRiskData: baseData
      })
    ).toBe(10); // Should use environment volume instead
  });

  test('calculates distance-based volume for Outdoors (6 feet default)', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Outdoors', achValue: '', carType: '', airplaneType: '', customVolume: '', covidRiskData: baseData
      })
    ).toBeCloseTo(6.69, 2); // 6 feet = 1.83m, 1.83² × 2 ≈ 6.69 m³
  });

  test('calculates distance-based volume for Outdoors with custom distance', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Outdoors', achValue: '', carType: '', airplaneType: '', customVolume: '', covidRiskData: baseData, distanceFeet: '10'
      })
    ).toBeCloseTo(18.58, 2); // 10 feet = 3.05m, 3.05² × 2 ≈ 18.6 m³
  });

  test('calculates distance-based volume for Outdoors at 20 feet', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Outdoors', achValue: '', carType: '', airplaneType: '', customVolume: '', covidRiskData: baseData, distanceFeet: '20'
      })
    ).toBeCloseTo(74.32, 2); // 20 feet = 6.1m, 6.1² × 2 ≈ 74.3 m³
  });

  test('looks up car volume for matching ACH value', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: '2.5', carType: 'suv', airplaneType: '', customVolume: '', covidRiskData: baseData
      })
    ).toBe(4);
  });

  test('looks up airplane volume for matching ACH value', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: '15.00', carType: '', airplaneType: 'medium', customVolume: '', covidRiskData: baseData
      })
    ).toBe(125);
  });

  test('uses generic environment volume fallback', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: '1', carType: '', airplaneType: '', customVolume: '', covidRiskData: baseData
      })
    ).toBe(10);
  });

  test('returns 0 when no match found', () => {
    expect(
      computeVolume({
        indoorOutdoor: 'Indoors', achValue: 'unknown', carType: '', airplaneType: '', customVolume: '', covidRiskData: baseData
      })
    ).toBe(0);
  });
});

describe('computeACH', () => {
  test('uses customACH override when positive', () => {
    expect(
      computeACH({ indoorOutdoor: 'Indoors', achValue: '5', customACH: '20' })
    ).toBe(20);
  });

  test('returns 1600 for Outdoors when no customACH', () => {
    expect(
      computeACH({ indoorOutdoor: 'Outdoors', achValue: '', customACH: '' })
    ).toBe(1600);
  });

  test('parses numeric ACH value when no custom', () => {
    expect(
      computeACH({ indoorOutdoor: 'Indoors', achValue: '6.5', customACH: '' })
    ).toBe(6.5);
  });

  test('returns 0 for invalid ACH value', () => {
    expect(
      computeACH({ indoorOutdoor: 'Indoors', achValue: 'foo', customACH: '' })
    ).toBe(0);
  });
});