import pytest

from app import app as flask_app


@pytest.fixture
def client():
    """Flask test client with HTTPS scheme to avoid Talisman redirects."""
    # Enable testing mode and disable Talisman enforcement entirely
    flask_app.config['TESTING'] = True
    flask_app.extensions.pop('talisman', None)
    # Simulate HTTPS for test_client if needed
    with flask_app.test_client() as client:
        # Simulate HTTPS to satisfy Talisman's checks
        client.environ_base['wsgi.url_scheme'] = 'https'
        # Also set forwarded proto header
        client.environ_base['HTTP_X_FORWARDED_PROTO'] = 'https'
        yield client


def test_get_index(client):
    resp = client.get('/', follow_redirects=True)
    assert resp.status_code == 200
    # Check page title or heading
    assert b'YourCovidRisk.com' in resp.data


def test_get_faq(client):
    resp = client.get('/faq', follow_redirects=True)
    assert resp.status_code == 200
    assert b'<title>FAQ' in resp.data


def test_get_test_calculator(client):
    resp = client.get('/test', follow_redirects=True)
    assert resp.status_code == 200
    assert b'<title>Covid Test Calculator' in resp.data


def test_post_test_calculator(client):
    # Minimal valid form data for test calculator
    data = {
        'symptoms': 'yes',
        'test_type': 'Metrix',
        'test_result': 'negative',
        'covid_cautious': 'Moderately',
        'covid_cautious_level': 'Moderately',
        'covidPrevalence': '',
        'positivityRate': '',
        'priorProbability': '',
        'advanced': '',
    }
    resp = client.post('/test', data=data, follow_redirects=True)
    assert resp.status_code == 200
    # Should render risk message
    assert b'id="riskMessage"' in resp.data


def test_get_exposure_calculator(client):
    resp = client.get('/exposure', follow_redirects=True)
    assert resp.status_code == 200
    assert b'<title>Covid Exposure Risk Calculator' in resp.data


def test_post_exposure_calculator(client):
    # Minimal valid form data for exposure calculator
    payload = {
        'f_e': '1', 'f_i': '1', 'omicron': '3.3',
        'C0': '0.08', 'Q0': '0.08', 'p': '0.08',
        'ACH': '1', 'environment_volume': '1000',
        'delta_t': '3600', 'x': '6', 'activity_choice': '1',
        'gamma': '1', 'covid_prevalence': '1', 'immune': '1',
        'N': '1', 'percentage_masked': '0', 'masked_percentage_value': '0',
    }
    resp = client.post('/exposure', data=payload, follow_redirects=True)
    assert resp.status_code == 200
    # Should show result container
    assert b'id="result"' in resp.data
    # And risk message inside
    assert b'id="riskMessage"' in resp.data