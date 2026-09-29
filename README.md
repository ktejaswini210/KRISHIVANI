# KRISHIVANI

KRISHIVANI is a Flask-based smart agriculture dashboard for monitoring vegetable freshness and estimating market value. It combines manual weight entry with automatic temperature and humidity simulation, and provides market insights for daily mandi pricing in Andhra Pradesh.

## Features

- Manual entry of vegetable weight by the farmer
- Automatic temperature and humidity values for demo/ESP32-compatible workflows
- Freshness and storage-risk analysis by tray and vegetable type
- Recommended selling time and storage-life alerts
- Estimated produce value based on daily market rate
- Market data integration with the Government of India OGD/AGMARKNET API
- Demo fallback data when the live API is unavailable or rate-limited

## Tech Stack

- Python
- Flask
- OpenPyXL
- Requests
- HTML/CSS

## Project Structure

- `app.py` — Flask application and business logic
- `templates/` — HTML templates
- `static/` — CSS files and frontend assets
- `vegetable_data.xlsx` — vegetable storage and recommendation dataset
- `requirements.txt` — Python dependencies

## Setup

1. Open a terminal in the project folder.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Start the application:

```bash
python app.py
```

4. Open the app in a browser:

```text
http://127.0.0.1:5000
```

## Environment Variables

For live market data, set the following before running the app:

```bash
$env:DATA_GOV_API_KEY="YOUR_KEY"
$env:MARKET_STATE="Andhra Pradesh"
python app.py
```

If no API key is provided, the app falls back to demo market values clearly marked as demo data.

## Notes

- The app is designed for daily mandi pricing data, not live tick-by-tick pricing.
- Weight is intentionally manual; temperature and humidity are treated as automatic sensor values.
- For production deployment, use a proper WSGI server such as Gunicorn and configure environment variables in the hosting platform.

## Free Hosting Recommendation

This project is best hosted on a Python-friendly free platform such as Render or PythonAnywhere. It is a Flask app with no database and a simple file-based Excel dataset, so it fits free-tier web hosting well.

## License

This project is intended for educational and prototype use.
