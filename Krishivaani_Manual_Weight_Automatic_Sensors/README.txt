KRISHIVAANI - MANUAL WEIGHT + AUTOMATIC SENSORS + DAILY MARKET RATES

Run in PowerShell:
1. python -m pip install -r requirements.txt
2. python app.py
3. Open http://127.0.0.1:5000

Only weight is entered manually. Temperature/humidity are automatic demo sensor values and can later come from ESP32.

MARKET RATES:
The Market Insights section loads the Government of India OGD/AGMARKNET daily mandi-price resource for Andhra Pradesh. The project includes a shared public demo API key so the live section can work without adding a key for a demo. Because the shared key is rate-limited, for reliable use create your own free data.gov.in API key and set it before starting Flask:

$env:DATA_GOV_API_KEY="YOUR_KEY"
$env:MARKET_STATE="Andhra Pradesh"
python app.py

Important: this is daily reported mandi/wholesale data, not a tick-by-tick real-time quote. The UI shows the arrival/report date and source. Prices are in INR per quintal.

The app refreshes market data every 10 minutes and refreshes dashboard data every 10 seconds.
1 KG MARKET RATE: The Market Insights panel also shows 1 kg market rate (modal ₹/quintal ÷ 100), current entered weight, and estimated produce value.
