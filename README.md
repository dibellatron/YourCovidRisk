# YourCovidRisk.com - COVID Risk Calculators

*Last updated: August 9, 2025*

**Comprehensive Flask web application for rigorous COVID-19 risk assessment**

Live site: [YourCovidRisk.com](https://yourcovidrisk.com)  
Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## Features

### 🦠 Exposure Risk Calculator
- **Advanced aerosol physics modeling** using the Henriques et al. integrated transmission model
- **Monte Carlo uncertainty analysis** with confidence intervals and risk distributions
- **Real-time prevalence data** integration from CDC wastewater surveillance (state-specific) and PMC modeling
- **Comprehensive environmental factors**: ventilation (ACH), humidity, CO2 levels, temperature effects
- **Activity-based emission modeling**: breathing, speaking, singing, shouting with distance sensitivity
- **Immunity decay modeling** based on Chemaitelly et al. research for vaccination and infection protection
- **Immunocompromised adjustments** for vulnerable populations
- **Indoor/outdoor scenarios** with pre-configured environments (offices, restaurants, gyms, cars, airplanes, etc.)

### 🧪 Test Calculator
- **Bayesian test interpretation** with multiple test integration
- **Advanced error state modeling** for correlated test results
- **Symptom-based priors** and prevalence adjustments
- **Comprehensive test database** with sensitivity/specificity for major rapid test brands
- **Monte Carlo confidence intervals** for uncertainty quantification

### 🔬 Scientific Foundation
- Built on peer-reviewed research and validated transmission models
- Uses CERN CAiMIRA methodology for Monte Carlo exposure calculations
- Integrates latest COVID epidemiological data and variant-specific parameters
- Transparent methodology with detailed FAQ and scientific explanations

### 🛡️ Security & Performance
- **Rate limiting** with bot detection to prevent abuse
- **Content Security Policy** and security headers via Flask-Talisman
- **Input validation** and sanitization for all user inputs
- **Error handling** with user-friendly messages

## Quick Start

### Prerequisites
- Python 3.12+
- pip

### Installation
```bash
git clone https://github.com/dibellatron/CovidRisk.git
cd CovidRisk
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Application
```bash
# Development mode
python app.py

# Production mode with Gunicorn
gunicorn app:app
```

Open http://127.0.0.1:5000 in your browser.

## Development

### Code Organization
```
├── app.py                    # Main Flask application entry point
├── config.py                 # Environment-based configuration
├── covid_app/                # Flask application factory and blueprints
│   ├── __init__.py          # App factory with security and rate limiting
│   └── blueprints/          # Route handlers
│       ├── main.py          # Homepage and FAQ routes
│       ├── exposure.py      # Exposure calculator routes
│       └── testcalc.py      # Test calculator routes
├── calculators/             # Pure Python calculation logic
│   ├── exposure_calculator.py    # Core exposure risk calculations
│   ├── test_calculator.py        # Test result probability calculations
│   ├── immunity_decay.py         # Immunity modeling (Chemaitelly et al.)
│   ├── time_varying_prevalence.py # Time-varying risk calculations
│   ├── environment_data.py       # Environmental parameter data
│   ├── validators.py             # Input validation utilities
│   └── formatting.py            # Output formatting
├── templates/               # Jinja2 HTML templates
├── static/                  # CSS, JavaScript, and static assets
├── tests/                   # Python and JavaScript test suites
├── PMC/                     # PMC prevalence data processing
├── Walgreens/              # Test positivity data processing
└── wastewater/             # CDC wastewater surveillance integration
    ├── data/                # CDC wastewater data files
    └── pull_cdc_wastewater.py # Current CDC wastewater data fetching
```

### Development Setup
```bash
# Install development dependencies
pip install pytest pytest-cov mypy black ruff pre-commit

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=calculators --cov=covid_app tests/

# Type checking
mypy calculators/ covid_app/

# Code formatting and linting
black .
ruff check .
```

### JavaScript Testing
```bash
# Install Node.js dependencies (for JavaScript testing)
npm install

# Run JavaScript tests
npm test

# Run with coverage
npm run coverage
```

## Data Sources & Updates

The application integrates real-time COVID data from multiple sources:

### Automated Data Updates
1. **Weekly Walgreens Positivity Data**
   - Script: `Walgreens/update_walgreens.py`
   - Updates state-level test positivity rates (used by Test Calculator only)

2. **CDC Wastewater Surveillance Data**
   - Script: `wastewater/pull_cdc_wastewater.py`
   - Fetches current state-specific wastewater viral activity levels from CDC
   - Converts WVAL to prevalence using calibrated multiplier (0.00293)
   - Outputs: `wastewater/data/cdc_wastewater_current.csv` and dated files
   - Used by Exposure Risk Calculator for state-specific prevalence

3. **PMC Prevalence Data**
   - Script: `PMC/pull_prevalence_monitored.py` (production) or `PMC/pull_prevalence.py` (manual)
   - Uses Tesseract OCR to analyze PMC prevalence charts
   - Automatically generates prevalence distributions for uncertainty calculations
   - Used by Test Calculator for regional prevalence estimates
   - Requires Tesseract OCR system installation

### Heroku Deployment
For automated data updates on Heroku:

```bash
# Add Heroku Scheduler
heroku addons:create scheduler:standard

# Add Tesseract OCR support (required for PMC scripts)
heroku buildpacks:add https://github.com/pathwaysmedical/heroku-buildpack-tesseract
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set FLASK_ENV=production

# Configure scheduled jobs in Heroku dashboard:
# - Weekly: "python Walgreens/update_walgreens_monitored.py"
# - Weekly: "python PMC/pull_prevalence_monitored.py"
```

**Note**: The dedicated Tesseract buildpack handles OCR system dependencies required for PMC image analysis.

## Testing

### Python Tests
```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_calculators.py
pytest tests/test_endpoints.py

# Run with coverage report
pytest --cov=calculators --cov=covid_app --cov-report=html tests/
```

### JavaScript Tests
```bash
# Run JavaScript test suite
npm test

# Test specific modules
npm test -- --testNamePattern="exposure"
```

## Scientific Methodology

### Exposure Risk Calculator
- **Core Model**: Henriques et al. (2025) integrated airborne transmission model
- **Monte Carlo Engine**: Derived from CERN CAiMIRA methodology
- **Immunity Modeling**: Chemaitelly et al. (2025) reinfection protection data
- **Environmental Physics**: Wells-Riley equation with aerosol size distribution
- **Prevalence Integration**: Bayesian hierarchical models for wastewater-to-prevalence conversion

### Test Calculator
- **Bayesian Framework**: Bayes' theorem with symptom-informed priors
- **Error State Modeling**: Correlated test results for multiple tests
- **Test Performance Database**: Comprehensive sensitivity/specificity data from clinical studies
- **Uncertainty Quantification**: Monte Carlo confidence intervals

## Configuration

### Environment Variables
- `FLASK_ENV`: Set to `production` for production deployment
- `SECRET_KEY`: Flask secret key (auto-generated if not set)

### Rate Limiting
- General: 1000 requests/hour, 50 requests/minute
- Calculator endpoints: 30 calculations/minute
- Stricter limits for detected bots


## License

This project is open source and available under the [MIT License](LICENSE).

## Attribution

This tool builds upon substantial open-source research:

- **CERN CAiMIRA**: Monte Carlo exposure calculations methodology
- **Henriques et al. (2025)**: Integrated airborne transmission model
- **Chemaitelly et al. (2025)**: COVID reinfection protection research
- **CDC NWSS**: Wastewater surveillance data
- **PMC**: COVID prevalence modeling
- **Walgreens**: Test positivity rate data

## Disclaimer

This tool provides mathematical calculations for educational purposes only. It is not intended as medical advice, diagnosis, or treatment. Always consult healthcare professionals for medical decisions.
