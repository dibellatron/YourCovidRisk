# COVID Risk Calculator - Technical Architecture Documentation

*Last updated: August 9, 2025*

## Overview

The COVID Risk Calculator is a Flask-based web application that provides two main calculators:
1. **Exposure Risk Calculator** - Estimates COVID-19 transmission risk in various scenarios
2. **Test Calculator** - Estimates infection probability based on test results

The application uses advanced Monte Carlo simulations, Bayesian statistics, and aerosol physics models to provide scientifically-grounded risk assessments.

## Application Architecture

### Core Framework
- **Backend**: Flask web framework with Blueprint architecture
- **Frontend**: Vanilla JavaScript with Chart.js for visualizations
- **Styling**: Custom CSS with CSS Grid/Flexbox layouts
- **Testing**: Jest for JavaScript, pytest for Python
- **Deployment**: Heroku-compatible with Gunicorn WSGI server

## File Structure & Dependencies

### 1. Application Entry Points

#### `app.py`
- **Purpose**: Main Flask application entry point expected by Gunicorn
- **Dependencies**: 
  - `covid_app.create_app()` - Application factory
  - `config.py` - Configuration management
- **Functionality**: Creates Flask app instance, handles development browser auto-opening

#### `run_dev.py` / `run_prod.py`
- **Purpose**: Development and production server runners
- **Dependencies**: `app.py`
- **Functionality**: Environment-specific server startup

### 2. Core Application Factory

#### `covid_app/__init__.py`
- **Purpose**: Flask application factory with security, rate limiting, and blueprint registration
- **Key Dependencies**:
  - `flask-talisman` - Security headers and CSP
  - `flask-limiter` - Rate limiting and DoS protection
  - `config.py` - Environment-based configuration
  - Blueprint modules: `main.py`, `exposure.py`, `testcalc.py`
  - `calculators/formatting.py` - Jinja2 filters
- **Security Features**:
  - Content Security Policy (CSP)
  - Rate limiting (200/hour, 50/minute general; 30/minute for calculators)
  - Bot detection and stricter limits
  - HTTPS enforcement in production

#### `config.py`
- **Purpose**: Environment-based configuration management
- **Configurations**: Development, Production, Testing
- **Features**: Debug mode control, logging levels, security settings

### 3. Blueprint Architecture

#### `covid_app/blueprints/main.py`
- **Purpose**: Homepage and FAQ routes
- **Routes**:
  - `/` - Homepage (index.html)
  - `/faq` - FAQ page (faq.html)
- **Dependencies**: Flask templates

#### `covid_app/blueprints/exposure.py`
- **Purpose**: Exposure risk calculator routes and API endpoints
- **Routes**:
  - `/exposure` - Main calculator page
  - `/calculate-time-varying-risk` - AJAX endpoint for risk calculations
- **Key Dependencies**:
  - `calculators/exposure_calculator.py` - Core calculation engine
  - `calculators/time_varying_prevalence.py` - Time-varying risk modeling
  - `calculators/validators.py` - Input validation
  - `calculators/formatting.py` - Response formatting
- **Data Sources**:
  - PMC prevalence data
  - Walgreens positivity rates
  - CDC wastewater data

#### `covid_app/blueprints/testcalc.py`
- **Purpose**: Test calculator routes and API endpoints
- **Routes**:
  - `/test` - Main test calculator page
  - POST endpoint for test result calculations
- **Key Dependencies**:
  - `calculators/test_calculator.py` - Core test calculation engine
  - `calculators/validators.py` - Input validation
  - `calculators/formatting.py` - Response formatting
- **Data Sources**:
  - Walgreens state-level positivity data
  - PMC regional prevalence estimates

### 4. Calculation Engine

#### Core Calculator Modules

##### `calculators/exposure_calculator.py`
- **Purpose**: Main exposure risk calculation engine
- **Key Features**:
  - Henriques aerosol physics model implementation
  - Monte Carlo uncertainty analysis
  - Bayesian prevalence integration
  - Immunocompromised risk adjustments
- **Dependencies**:
  - `immunity_decay.py` - Immunity factor calculations
  - `environment_data.py` - Environmental parameters
  - `viral_load_distributions.py` - Viral load modeling
  - `risk_distribution.py` - Risk distribution analysis
- **Scientific Models**:
  - Wells-Riley equation with Henriques modifications
  - Aerosol physics (emission, dilution, decay)
  - Activity-based emission scaling
  - Environmental factor adjustments (RH, CO2, temperature)

##### `calculators/test_calculator.py`
- **Purpose**: Test result probability calculation engine
- **Key Features**:
  - Bayesian test interpretation
  - Multiple test integration
  - Symptom-based priors
  - Prevalence-adjusted calculations
- **Dependencies**:
  - `test_performance_data.py` - Test sensitivity/specificity data
  - `monte_carlo_ci.py` - Confidence interval calculations
  - `bayesian_test_integration.py` - Multi-test Bayesian analysis
- **Scientific Models**:
  - Bayes' theorem for test interpretation
  - Symptom likelihood ratios
  - Test performance characteristics

#### Supporting Calculation Modules

##### `calculators/immunity_decay.py`
- **Purpose**: Immunity factor calculations based on Chemaitelly et al. research
- **Models**: Exponential decay models for vaccination and infection-acquired immunity

##### `calculators/time_varying_prevalence.py`
- **Purpose**: Time-varying prevalence and risk calculations
- **Data Sources**: CDC, PMC, Walgreens data integration
- **Features**: Temporal risk modeling, prevalence trend analysis

##### `calculators/environment_data.py`
- **Purpose**: Environmental parameter data (cars, airplanes, buildings)
- **Data**: ACH rates, occupancy patterns, ventilation characteristics

##### `calculators/validators.py`
- **Purpose**: Input validation and sanitization
- **Features**: Type checking, range validation, error handling

##### `calculators/formatting.py`
- **Purpose**: Response formatting and Jinja2 filters
- **Features**: Percentage formatting, confidence interval display

##### Viral Load & Bayesian Models
- `calculators/viral_load_distributions.py` - Viral load probability distributions
- `calculators/enhanced_bayesian_viral_load_model.py` - Advanced Bayesian viral load modeling
- `calculators/correlated_error_bayesian_model.py` - Correlated error modeling
- `calculators/error_state_bayesian_model.py` - Error state Bayesian analysis
- `calculators/bayesian_viral_load_model.py` - Base Bayesian viral load model
- `calculators/uncertain_viral_load_model.py` - Uncertainty propagation
- `calculators/fixed_viral_load_model.py` - Fixed parameter models
- `calculators/corrected_viral_load_model.py` - Model corrections
- `calculators/final_viral_load_model.py` - Final integrated model
- `calculators/full_uncertain_model.py` - Full uncertainty analysis

##### Risk Analysis & Monte Carlo
- `calculators/risk_distribution.py` - Risk distribution visualization
- `calculators/monte_carlo_ci.py` - Monte Carlo confidence intervals
- `calculators/detection_curves.py` - Test detection curve analysis
- `calculators/calculation_steps.py` - Step-by-step calculation breakdown
- `calculators/viral_load_unit_conversion.py` - Unit conversion utilities

##### Test Integration
- `calculators/test_performance_data.py` - Test sensitivity/specificity database
- `calculators/bayesian_test_integration.py` - Multi-test Bayesian integration

### 5. Frontend Architecture

#### HTML Templates

##### Base Templates
- `templates/base_analytics.html` - Google Analytics integration

##### Page Templates
- `templates/index.html` - Homepage with calculator cards
- `templates/faq.html` - FAQ with collapsible sections
- `templates/rate_limit.html` - Rate limit error page
- `templates/refactoring_guide.html` - Technical documentation

##### Exposure Calculator Templates
- `templates/exposure_calculator.html` - Main calculator interface
- `templates/exposure_hero.html` - Calculator header section
- `templates/exposure_about_you.html` - User information section
- `templates/exposure_other_people.html` - Other people configuration
- `templates/exposure_activity_levels.html` - Activity level controls
- `templates/exposure_environment.html` - Environmental parameters
- `templates/macros/exposure_controls.html` - Reusable form controls
- `templates/components/uncertainty_analysis.html` - Uncertainty visualization

##### Test Calculator Templates
- `templates/test_calculator.html` - Test calculator interface
- `templates/macros/calculation_display.html` - Calculation explanation macro

#### CSS Architecture

##### Global Styles
- `static/styles.css` - Global design system
  - CSS custom properties (color palette, spacing, typography)
  - Component styles (buttons, cards, forms)
  - Layout utilities (flexbox, grid)
  - Responsive design breakpoints
  - Animation definitions

##### Calculator-Specific Styles
- `static/exposure-calculator.css` - Exposure calculator layouts
  - Slider styling and positioning
  - Form section layouts
  - Results visualization
- `static/test-calculator.css` - Test calculator specific styles
- `static/css/risk-distribution.css` - Risk distribution charts

##### Icon Library
- `static/fontawesome/` - Complete Font Awesome icon library
  - `css/all.min.css` - Compiled CSS
  - `webfonts/` - Font files
  - `svgs/` - SVG icons

#### JavaScript Architecture

##### Core Application Scripts
- `static/data.js` - Global data definitions and constants
- `static/exposure-calculator.js` - Main exposure calculator logic
  - Form handling and validation
  - AJAX communication with backend
  - Results visualization
  - Error handling
- `static/test-calculator.js` - Test calculator functionality
  - Dynamic form management
  - Test block addition/removal
  - Result calculation triggers
- `static/exposure-utils.js` - Exposure calculator utilities

##### Utility Modules
- `static/js/utils/analytics.js` - Google Analytics event tracking
- `static/js/utils/debug.js` - Debug utilities and logging
- `static/js/utils/riskColorScale.js` - Risk-based color calculations

##### Form Management
- `static/js/formHandler.js` - Generic form handling utilities
- `static/js/stateManager.js` - Application state management
- `static/js/slider-init.js` - Form validation and select wrapper initialization
- `static/js/slider-labels.js` - Clickable slider labels

##### Slider System
- `static/js/sliders/bindSliders.js` - Slider event binding
- `static/js/sliders/genericSlider.js` - Generic slider functionality
- `static/js/sliders/peopleSlider.js` - People count slider
- `static/js/data/sliderData.js` - Slider configuration data

##### Calculation Modules
- `static/js/calculations/calculationDisplay.js` - Calculation explanation display
- `static/js/calculations/environment.js` - Environmental calculations
- `static/js/calculations/exhalation.js` - Exhalation rate calculations
- `static/js/calculations/immuneSusceptibility.js` - Immune susceptibility
- `static/js/calculations/maskFilter.js` - Mask filtration calculations
- `static/js/calculations/repeatedExposureRisk.js` - Repeated exposure modeling

##### Visualization
- `static/js/uncertainty/riskDistribution.js` - Risk distribution charts using Chart.js

### 6. Data Sources & Processing

#### Primary Data Files
- `wastewater/data/cdc_wastewater_current.csv` - Current state-specific prevalence data (Exposure Calculator)
- `PMC/Prevalence/prevalence_current.csv` - Current COVID prevalence by region (Test Calculator)
- `Walgreens/walgreens_clean/covid_current.csv` - Current positivity rates by state (Test Calculator)
- `wastewater/data/cdc_weekly_prevalence_2023_2025.csv` - CDC weekly prevalence data (time-varying calculations)
- `data/quanta_emission_rates.csv` - Quanta emission rates for risk calculations

#### Data Processing Scripts
- `wastewater/pull_cdc_wastewater.py` - Pull current CDC wastewater surveillance data
- `PMC/generate_distributions_manual.py` - Generate prevalence distributions
- `PMC/pull_prevalence.py` - Pull PMC prevalence data
- `Walgreens/update_walgreens.py` - Update Walgreens positivity data
- `scripts/daily_repeated_exposure.py` - Daily exposure calculations
- `shared/job_utils.py` - Utility functions for data processing jobs

#### Wastewater Analysis System
- `wastewater/estimate_prevalence.py` - Main prevalence estimation
- **Stan Models** (Bayesian statistical modeling):
  - `wastewater/stan/calibrated_hierarchical_model.stan`
  - `wastewater/stan/hierarchical_ww_prev_model.stan`
  - `wastewater/stan/time_varying_hierarchical_model.stan`
  - `wastewater/stan/ww_prev_model.stan`

### 7. Testing Infrastructure

#### Python Tests
- `tests/test_calculators.py` - Calculator module testing
- `tests/test_endpoints.py` - Flask route testing
- `tests/test_monte_carlo.py` - Monte Carlo simulation testing
- `tests/test_validators.py` - Validation function testing

#### JavaScript Tests
- `tests/js/calculations/environment.test.js` - Environment calculation tests
- `tests/js/calculations/exhalation.test.js` - Exhalation calculation tests
- `tests/js/calculations/immuneSusceptibility.test.js` - Immune susceptibility tests
- `tests/js/calculations/maskFilter.test.js` - Mask filtration tests
- `tests/js/slider-labels.test.js` - Slider functionality tests
- `tests/js/stateManager.test.js` - State management tests

#### Test Configuration
- `package.json` - Jest test configuration and npm scripts
- `babel.config.js` - Babel transpilation for tests
- `jest.config.cjs` - Jest test runner configuration

### 8. Configuration & Deployment

#### Deployment Configuration
- `Procfile` - Heroku deployment specification (`web: gunicorn app:app`)
- `runtime.txt` - Python runtime version specification (3.12.0)
- `requirements.txt` - Python package dependencies

#### Development Configuration
- `package-lock.json` - Locked npm dependency versions
- `mypy.ini` - MyPy type checker configuration
- `pyproject.toml` - Python project metadata

#### Static Assets
- `static/favicon.svg`, `static/favicon-*.png` - Website favicons
- `static/apple-touch-icon.png` - Apple device icon

## Data Flow Architecture

### 1. Exposure Calculator Flow
```
User Input → exposure_calculator.html → exposure-calculator.js → 
/calculate-time-varying-risk endpoint → exposure_calculator.py → 
[immunity_decay.py, environment_data.py, viral_load_distributions.py] → 
JSON Response → Risk Visualization
```

### 2. Test Calculator Flow
```
User Input → test_calculator.html → test-calculator.js → 
/test POST endpoint → test_calculator.py → 
[test_performance_data.py, bayesian_test_integration.py] → 
JSON Response → Probability Display
```

### 3. Data Processing Flow
```
External APIs → [PMC/pull_prevalence.py, Walgreens/update_walgreens.py] → 
CSV Files → [time_varying_prevalence.py, exposure_calculator.py] → 
Risk Calculations
```

## Scientific Models Implemented

### 1. Aerosol Physics (Henriques et al.)
- **Files**: `calculators/exposure_calculator.py`
- **Model**: Modified Wells-Riley equation with aerosol physics
- **Parameters**: Emission rates, dilution, decay, filtration

### 2. Immunity Decay (Chemaitelly et al.)
- **Files**: `calculators/immunity_decay.py`
- **Model**: Exponential decay for vaccination/infection immunity
- **Data Source**: Meta-analysis of protection durability

### 3. Bayesian Test Interpretation
- **Files**: `calculators/test_calculator.py`, `calculators/bayesian_test_integration.py`
- **Model**: Bayes' theorem with symptom priors
- **Integration**: Multiple test results with correlation

### 4. Monte Carlo Uncertainty
- **Files**: `calculators/monte_carlo_ci.py`, `calculators/risk_distribution.py`
- **Method**: Bootstrap sampling for confidence intervals
- **Visualization**: Risk distribution histograms

## Security Features

### 1. Content Security Policy
- **File**: `covid_app/__init__.py`
- **Protection**: XSS prevention, resource loading restrictions

### 2. Rate Limiting
- **Implementation**: Flask-Limiter with bot detection
- **Limits**: 200/hour general, 30/minute for calculators
- **Bot Handling**: Stricter limits for automated requests

### 3. Input Validation
- **Files**: `calculators/validators.py`
- **Methods**: Type checking, range validation, sanitization

### 4. HTTPS Enforcement
- **Implementation**: Flask-Talisman in production
- **Development**: Disabled for local testing

## Performance Optimizations

### 1. Caching
- **Static Assets**: Long-term caching headers
- **Data**: In-memory caching for prevalence data

### 2. Lazy Loading
- **JavaScript**: Modular loading of calculation components
- **Data**: On-demand loading of large datasets

### 3. Compression
- **Static Files**: Minified CSS/JS
- **Server**: Gzip compression via Heroku

## Monitoring & Analytics

### 1. Google Analytics
- **File**: `templates/base_analytics.html`
- **Tracking**: Page views, calculator usage, button clicks

### 2. Error Handling
- **Rate Limits**: Custom error pages
- **Validation**: User-friendly error messages
- **Logging**: Server-side error logging

## Complete File Inventory for Open-Source Cleanup

### CRITICAL: Files Actually Used by the Running Application

#### Python Application Files
1. `app.py` - Main Flask entry point
2. `config.py` - Environment configuration
3. `run_dev.py` - Development server
4. `run_prod.py` - Production server
5. `covid_app/__init__.py` - Flask app factory
6. `covid_app/blueprints/__init__.py`
7. `covid_app/blueprints/main.py` - Homepage/FAQ routes
8. `covid_app/blueprints/exposure.py` - Exposure calculator routes
9. `covid_app/blueprints/testcalc.py` - Test calculator routes
10. `calculators/__init__.py`
11. `calculators/exposure_calculator.py` - Core exposure calculations
12. `calculators/test_calculator.py` - Core test calculations
13. `calculators/immunity_decay.py` - Immunity modeling
14. `calculators/time_varying_prevalence.py` - Prevalence calculations
15. `calculators/environment_data.py` - Environmental data
16. `calculators/validators.py` - Input validation
17. `calculators/formatting.py` - Output formatting
18. `calculators/risk_distribution.py` - Risk distribution analysis
19. `calculators/monte_carlo_ci.py` - Monte Carlo confidence intervals
20. `calculators/test_performance_data.py` - Test sensitivity/specificity data
21. `calculators/bayesian_test_integration.py` - Bayesian test integration

#### Additional Calculator Dependencies
22. `calculators/viral_load_distributions.py` - Viral load modeling
23. `calculators/detection_curves.py` - Detection curve calibration
24. `calculators/calculation_steps.py` - Step breakdown
25. `scripts/__init__.py`
26. `scripts/daily_repeated_exposure.py`
27. `shared/job_utils.py`
28. `wastewater/pull_cdc_wastewater.py` - CDC wastewater data fetching script

#### HTML Templates
29. `templates/base_analytics.html` - Analytics base
30. `templates/index.html` - Homepage
31. `templates/faq.html` - FAQ page
32. `templates/exposure_calculator.html` - Exposure calculator main
33. `templates/exposure_hero.html` - Exposure header
34. `templates/exposure_about_you.html` - User info section
35. `templates/exposure_other_people.html` - Other people section
36. `templates/exposure_activity_levels.html` - Activity section
37. `templates/exposure_environment.html` - Environment section
38. `templates/components/uncertainty_analysis.html` - Uncertainty component
39. `templates/macros/exposure_controls.html` - Form control macros
40. `templates/test_calculator.html` - Test calculator main
41. `templates/macros/calculation_display.html` - Calculation display macro
42. `templates/rate_limit.html` - Rate limit error
43. `templates/faq_general.html` - General FAQ include
44. `templates/faq_exposure_calculator.html` - Exposure FAQ include
45. `templates/faq_test_calculator.html` - Test FAQ include

#### CSS Files
46. `static/styles.css` - Global styles
47. `static/exposure-calculator.css` - Exposure calculator styles
48. `static/test-calculator.css` - Test calculator styles (empty but referenced)
49. `static/css/risk-distribution.css` - Risk visualization styles

#### JavaScript Files
50. `static/data.js` - Global data definitions
51. `static/exposure-calculator.js` - Exposure calculator main logic
52. `static/test-calculator.js` - Test calculator main logic
53. `static/js/exposure-utils.js` - Exposure utilities
54. `static/js/formHandler.js` - Form handling
55. `static/js/stateManager.js` - State management
56. `static/js/slider-init.js` - Slider initialization
57. `static/js/slider-labels.js` - Slider label handling
58. `static/js/calculations/environment.js` - Environment calculations
59. `static/js/calculations/exhalation.js` - Exhalation calculations
60. `static/js/calculations/immuneSusceptibility.js` - Immune calculations
61. `static/js/calculations/maskFilter.js` - Mask calculations
62. `static/js/calculations/repeatedExposureRisk.js` - Repeated exposure
63. `static/js/calculations/calculationDisplay.js` - Calculation display
64. `static/js/sliders/bindSliders.js` - Slider binding
65. `static/js/sliders/genericSlider.js` - Generic slider logic
66. `static/js/sliders/peopleSlider.js` - People slider
67. `static/js/data/sliderData.js` - Slider configuration
68. `static/js/uncertainty/riskDistribution.js` - Risk distribution viz
69. `static/js/utils/analytics.js` - Analytics tracking
70. `static/js/utils/debug.js` - Debug utilities
71. `static/js/utils/riskColorScale.js` - Risk color mapping

#### Static Assets
72. `static/favicon.svg`
73. `static/favicon.ico`
74. `static/favicon-16x16.png`
75. `static/favicon-32x32.png`
76. `static/apple-touch-icon.png`

#### FontAwesome
77. `static/fontawesome/css/all.min.css` - Main CSS
78. `static/fontawesome/webfonts/fa-solid-900.woff2` - Solid icons
79. `static/fontawesome/webfonts/fa-regular-400.woff2` - Regular icons
80. `static/fontawesome/webfonts/fa-brands-400.woff2` - Brand icons

#### Data Files
81. `PMC/Prevalence/prevalence_current.csv` - Current prevalence
82. `PMC/PrecomputedDistributions/generation_timestamp.json` - Timestamp
83. `Walgreens/walgreens_clean/covid_current.csv` - Current positivity
84. `Walgreens/walgreens_clean/covid_history_national.csv` - Historical national
85. `Walgreens/walgreens_clean/covid_history_states.csv` - Historical states
86. `wastewater/data/cdc_weekly_prevalence_2023_2025.csv` - CDC weekly prevalence data
87. `wastewater/data/cdc_wastewater_current.csv` - Current CDC wastewater data (Exposure Calculator)
88. `wastewater/data/cdc_wastewater_[date].csv` - Dated CDC wastewater snapshots

#### Configuration Files
89. `requirements.txt` - Python dependencies
90. `Procfile` - Heroku deployment
91. `.python-version` - Python version specification
92. `package.json` - Node dependencies (for testing)
93. `babel.config.js` - Babel configuration
94. `jest.config.cjs` - Jest configuration
95. `mypy.ini` - Type checking config
96. `pyproject.toml` - Python project metadata

#### Test Files
97. `tests/test_calculators.py`
98. `tests/test_endpoints.py`
99. `tests/test_monte_carlo.py`
100. `tests/test_validators.py`
101. `tests/js/calculations/environment.test.js`
102. `tests/js/calculations/exhalation.test.js`
103. `tests/js/calculations/immuneSusceptibility.test.js`
104. `tests/js/calculations/maskFilter.test.js`
105. `tests/js/slider-labels.test.js`
106. `tests/js/stateManager.test.js`

**TOTAL: 106 files that are ACTUALLY USED by the running application**


## Development Workflow

### 1. Local Development
```bash
python run_dev.py  # Start development server
npm test          # Run JavaScript tests
pytest tests/     # Run Python tests
```

### 2. Deployment
```bash
git push heroku main  # Deploy to Heroku
# Procfile automatically starts: gunicorn app:app
```

### 3. Data Updates
- PMC prevalence: Manual update via `PMC/pull_prevalence.py`
- Walgreens data: Automated via `Walgreens/update_walgreens.py`
- Wastewater analysis: `wastewater/estimate_prevalence.py`

This architecture provides a robust, scientifically-grounded COVID risk assessment platform with comprehensive uncertainty analysis and real-time data integration.
