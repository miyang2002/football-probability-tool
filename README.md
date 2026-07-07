# Football Probability Tool

Local personal-use football probability analysis website.

## Run

```bash
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Test

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_app_health.py -q
```

## Data Sources

The initial app skeleton exposes a health check only. Future probability data
providers should document their source, refresh cadence, and required API keys
before being enabled locally.
