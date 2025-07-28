// COVID Risk Calculator Data
const covidRiskData = {
  // Mask types with their filtration efficiency values
  maskTypes: [
    { value: "Cloth", label: "Cloth", f_value: 0.6 },
    { value: "Surgical", label: "Surgical", f_value: 0.3 },
    { value: "KN94/95", label: "KN94/95", f_value: 0.45 },
    { value: "N95", label: "N95", f_value: 0.05 },
    { value: "N99", label: "N99", f_value: 0.01 },
    { value: "Elastomeric with P100/N100 filters", label: "Elastomeric with P100/N100 filters", f_value: 0.003 }
  ],
  
  // Lookup table for f_i values based on mask type and fit quality
  // Values represent penetration percentages as decimal values
  fiLookupTable: {
    "Cloth": {
      "Loose": 0.70,     // 70%
      "Average": 0.50,   // 50%
      "Snug": 0.30,      // 30%
      "Qualitative": null // N/A
    },
    "Surgical": {
      "Loose": 0.55,     // 55%
      "Average": 0.35,   // 35%
      "Snug": 0.18,      // 18%
      "Qualitative": null // N/A
    },
    "KN94/95": {
      "Loose": 0.45,     // 45%
      "Average": 0.30,   // 30%
      "Snug": 0.15,      // 15%
      "Qualitative": 0.05 // 5%
    },
    "N95": {
      "Loose": 0.25,     // 25%
      "Average": 0.12,   // 12%
      "Snug": 0.05,      // 5%
      "Qualitative": 0.01 // 1%
    },
    "N99": {
      "Loose": 0.25,     // 25%
      "Average": 0.12,   // 12%
      "Snug": 0.03,      // 3% 
      "Qualitative": 0.007 // 0.7%
    },
    "Elastomeric with P100/N100 filters": {
      "Loose": 0.15,     // 15%
      "Average": 0.06,   // 6%
      "Snug": 0.02,      // 2%
      "Qualitative": 0.005 // 0.5%
    }
  },

  // Time periods for vaccination and infection history
  timePeriods: Array.from({length: 12}, (_, i) => ({
    value: (i+1) === 1 ? "1 month ago" : `${i+1} months ago`,
    label: (i+1) === 1 ? "1 month ago" : `${i+1} months ago`
  })),


  // Number of people options
  peopleNumbers: [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 350,
    400, 450, 500, 600, 700, 800, 900, 1000, 1500, 2000, 2500, 3000
  ],

  // Car types with their volumes
  carTypes: [
    { value: "ordinary", label: "Ordinary-sized car", volume: 3 },
    { value: "suv", label: "SUV/Crossover", volume: 4 },
    { value: "pickup", label: "Pickup Truck", volume: 3.5 },
    { value: "minivan", label: "Minivan/Van", volume: 4.5 }
  ],

  // Airplane types with their volumes
  airplaneTypes: [
    { value: "small", label: "Small", volume: 65 },
    { value: "medium", label: "Medium (Boeing 737)", volume: 125 },
    { value: "large", label: "Large (A330)", volume: 215 },
    { value: "very_large", label: "Very Large (Boeing 777)", volume: 388 }
  ],

  // Car ACH values - they all have a default volume of 3 which gets updated based on car type
  carAchValues: ["1", "2.5", "6.5", "5", "30", "40", "74"],

  // Airplane ACH values to detect
  airplaneAchValues: ["15.00", "0.50"],

  // Percentage for other people masked
  maskedPercentages: [
    { value: "All", label: "All of them", percent: 1.0 },
    { value: "Most", label: "Most of them (75%)", percent: 0.75 },
    { value: "Half", label: "Half of them (50%)", percent: 0.5 },
    { value: "Some", label: "Some of them (25%)", percent: 0.25 }
  ],

  // Distances
  distances: [
    { value: "0.5", label: "Less than 1 foot" },
    { value: "1", label: "1 foot" },
    { value: "2", label: "2 feet" },
    { value: "3", label: "3 feet" },
    { value: "4", label: "4 feet" },
    { value: "5", label: "5 feet" },
    { value: "7.5", label: "6-9 feet" },
    { value: "12.5", label: "10-15 feet" },
    { value: "18", label: "16-20 feet" },
    { value: "20", label: "More than 20 feet" }
  ],

  // Environments with ACH values and volumes
  environments: [
    {
      group: "Home",
      options: [
        // Living room: ~50 m³ typical
        // Scenarios: Closed 0.3-0.5 ACH | Windows open 1-2 ACH | HVAC 5-8 ACH | Enhanced 10+ ACH
        { value: "1.0", label: "Living room", volume: 50, range: "0.3-10.0" },
        
        // Master bedroom: ~50 m³ typical  
        // Scenarios: Closed 0.3-0.5 ACH | Windows open 1-2 ACH | HVAC 5-6 ACH | Enhanced 5-10 ACH
        { value: "1.0", label: "Master bedroom", volume: 50, range: "0.3-10.0" },
        
        // Standard bedroom: ~27 m³ typical
        // Scenarios: Closed 0.3-0.5 ACH | Windows open 1-2 ACH | HVAC 5-6 ACH | Enhanced 5-10 ACH
        { value: "1.0", label: "Standard bedroom", volume: 27, range: "0.3-10.0" },
        
        // Kitchen: ~40 m³ typical
        // Scenarios: Closed 0.3-0.5 ACH | Windows open 1-3 ACH | HVAC/range hood 5-8 ACH | Enhanced 10-15+ ACH
        { value: "2.0", label: "Kitchen", volume: 40, range: "0.3-15.0" },
        
        // Bathroom: ~9-14 m³ typical (using 12 m³)
        // Scenarios: Closed 0.2-0.5 ACH | Windows open 1-3 ACH | Exhaust fan on 5-10 ACH | Fan+window 10-15+ ACH
        { value: "5.0", label: "Bathroom", volume: 12, range: "0.2-15.0" },
        
        // Home office: ~30-40 m³ typical (using 35 m³)
        // Scenarios: Closed 0.3-0.5 ACH | Windows open 1-2 ACH | HVAC 5-6 ACH | Enhanced 5-10+ ACH
        { value: "1.0", label: "Home office", volume: 35, range: "0.3-10.0" },
        
        // Basement: ~100-200 m³ typical (using 150 m³)
        // Scenarios: Closed 0.1-0.3 ACH | Windows open 1-3 ACH | HVAC 0.5-1.5 ACH | Enhanced 5-10+ ACH
        { value: "0.5", label: "Basement", volume: 150, range: "0.1-10.0" }
      ]
    },
    {
      group: "Offices",
      options: [
        { value: "3.50", label: "Private Office", volume: 40, range: "2.0-5.0" },
        { value: "3.50", label: "Small Office (2–10 people)", volume: 200, range: "2.0-5.0" },
        { value: "3.50", label: "Medium Office (11–40 people)", volume: 1000, range: "2.0-5.0" },
        { value: "3.50", label: "Large Office Floor (41+ people)", volume: 2000, range: "2.0-5.0" }
      ]
    },
    {
      group: "Dining",
      options: [
        { value: "3.98", label: "Restaurant", volume: 400, range: "0.67-7.3" },
        { value: "2.00", label: "Large home family dinner", volume: 200, range: "0.5-3.5" }
      ]
    },
    {
      group: "Leisure and retail",
      options: [
        { value: "2.60", label: "Mall common area", volume: 3000, range: "1.1-4.1" },
        { value: "1.88", label: "Supermarket", volume: 2000, range: "0.36-3.4" },
        { value: "2.2", label: "Gym", volume: 1300, range: "2.2-2.2" },
        { value: "2.09", label: "Sports arena", volume: 4000, range: "0.58-3.6" },
        { value: "2.18", label: "Museum/Gallery", volume: 1500, range: "0.66-3.7" },
        { value: "2.50", label: "Library", volume: 800, range: "1.0-4.0" },
        { value: "3.0", label: "Movie theater (auditorium)", volume: 2500, range: "1.5-6.0" }
      ]
    },
    {
      group: "Classrooms",
      options: [
        { value: "6.50", label: "Large university classroom", volume: 500, range: "2.0-11.0" },
        { value: "4.30", label: "Middle or high school classroom", volume: 200, range: "2.8-5.8" }
      ]
    },
    {
      group: "Healthcare",
      options: [
        { value: "9.00", label: "Dentist's office", volume: 80, range: "6.0-12.0" },
        { value: "5.30", label: "Hospital general examination room", volume: 100, range: "1.6-9.0" }
      ]
    },
    {
      group: "Places of Worship",
      options: [
        { value: "1.50", label: "Private Chapel (1–10 people)", volume: 70, range: "1.0-2.0" },
        { value: "2.00", label: "Small Congregational Hall (10–50 people)", volume: 300, range: "1.5-2.5" },
        { value: "2.50", label: "Medium Sanctuary (50–200 people)", volume: 1000, range: "2.0-3.0" },
        { value: "3.50", label: "Large Cathedral/Mosque (200–1,000 people)", volume: 6000, range: "3.0-4.0" },
        { value: "4.50", label: "Mega Sanctuary (1,000+ people)", volume: 10000, range: "4.0-5.0" }
      ]
    },
    {
      group: "Car",
      options: [
        { value: "1", label: "Parked: Windows Closed, No AC or Fan", volume: 3 },
        { value: "2.5", label: "Parked: Windows Closed, AC or Fan On", volume: 3, range: "2-3" },
        { value: "6.5", label: "Parked: Passenger Window Open", volume: 3 },
        { value: "5", label: "Driving: Windows Closed, No AC or Fan", volume: 3, range: "1.9-12" },
        { value: "30", label: "Driving: Windows Closed, AC or Fan On", volume: 3, range: "28-35.6" },
        { value: "40", label: "Driving: Passenger Window Partially Open", volume: 3, range: "20.9-36" },
        { value: "74", label: "Driving: Passenger Window Fully Open", volume: 3, range: "69-78.6" }
      ]
    },
    {
      group: "Hotels and airports",
      options: [
        { value: "3.00", label: "Airport terminal", volume: 5000, range: "1.5-4.5" },
        { value: "2.38", label: "Hotel lobby", volume: 1000, range: "0.86-3.9" }
      ]
    },
    {
      group: "Public transit",
      options: [
        { value: "15.00", label: "Airplane (HEPA system on)", volume: 150, range: "10.0-20.0" },
        { value: "0.50", label: "Airplane (HEPA system off)", volume: 150, range: "0.3-0.7" },
        { value: "7.50", label: "Subway car", volume: 100, range: "5.7-9.3" },
        { value: "54.00", label: "Bus with windows open", volume: 50, range: "36.0-72.0" },
        { value: "7.80", label: "City bus with windows closed, regular stops", volume: 50, range: "7.1-8.5" },
        { value: "1.42", label: "Bus with windows closed, no regular stops", volume: 50, range: "0.34-2.5" }
      ]
    }
  ]
};

// Make covidRiskData available globally
window.covidRiskData = covidRiskData;
