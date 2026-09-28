from flask import Flask, jsonify, render_template, request
from openpyxl import load_workbook
from datetime import datetime, timedelta
from pathlib import Path
import random
import os
import time
import requests

app = Flask(__name__)
BASE = Path(__file__).resolve().parent
EXCEL_FILE = BASE / "vegetable_data.xlsx"

# Government of India OGD/AGMARKNET daily mandi-price resource.
MARKET_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
MARKET_API_KEY = os.environ.get("DATA_GOV_API_KEY", "").strip() or "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"  # shared public demo key; use your own key for reliable access
MARKET_STATE = os.environ.get("MARKET_STATE", "Andhra Pradesh").strip()
MARKET_CACHE = {}
MARKET_CACHE_SECONDS = 600


def load_vegetables():
    wb = load_workbook(EXCEL_FILE, data_only=True)
    ws = wb["VegetableData"]
    headers = [c.value for c in ws[1]]
    return [dict(zip(headers, row)) for row in ws.iter_rows(min_row=2, values_only=True)]


VEGETABLES = load_vegetables()

# ONLY WEIGHT IS MANUALLY ENTERED.
# Temperature and humidity are automatic demo sensor values.
state = {
    "tray_id": "TRAY-01",
    "weight_kg": 20.0,
    "temperature_c": 12.0,
    "humidity": 85.0,
    "harvest_date": datetime.now().strftime("%Y-%m-%d"),
}


def get_record():
    return next(v for v in VEGETABLES if v["tray_id"] == state["tray_id"])


def analyse():
    record = get_record()
    temp = float(state["temperature_c"])
    humidity = float(state["humidity"])
    weight = float(state["weight_kg"])
    harvest = datetime.strptime(str(state["harvest_date"]), "%Y-%m-%d")
    days_stored = max(0, (datetime.now() - harvest).days)
    max_days = int(record["max_storage_days"])

    temp_ok = record["min_temp_c"] <= temp <= record["max_temp_c"]
    humidity_ok = record["min_humidity"] <= humidity <= record["max_humidity"]
    age_ratio = days_stored / max_days if max_days else 1
    bad_conditions = int(not temp_ok) + int(not humidity_ok)

    if days_stored >= max_days or bad_conditions == 2:
        risk = "High Risk"
        status = "Affected / Sell Immediately"
    elif age_ratio >= 0.70 or bad_conditions == 1:
        risk = "Medium Risk"
        status = "Monitor / Sell Soon"
    else:
        risk = "Low Risk"
        status = "Fresh"

    sell_after = int(record["recommended_sell_after_days"])
    remaining_sell_days = max(0, sell_after - days_stored)
    sell_message = "Recommended selling time: NOW" if remaining_sell_days == 0 else f"Recommended selling time: within {remaining_sell_days} day(s)"
    remaining_storage = max(0, max_days - days_stored)

    if risk == "High Risk":
        alert = f"FARMER ALERT: {record['vegetable']} is at high risk. {record['alert_message']}"
    elif risk == "Medium Risk":
        alert = f"FARMER WARNING: {record['vegetable']} needs attention. Consider selling soon."
    else:
        alert = ""

    return {
        "tray_id": record["tray_id"],
        "vegetable": record["vegetable"],
        "weight_kg": round(weight, 1),
        "temperature_c": round(temp, 1),
        "humidity": round(humidity, 1),
        "recommended_temperature": f"{record['min_temp_c']}–{record['max_temp_c']} °C",
        "recommended_humidity": f"{record['min_humidity']}–{record['max_humidity']} %",
        "days_stored": days_stored,
        "max_storage_days": max_days,
        "remaining_storage_days": remaining_storage,
        "risk": risk,
        "status": status,
        "temperature_ok": temp_ok,
        "humidity_ok": humidity_ok,
        "sell_message": sell_message,
        "storage_message": f"You can store it for approximately {remaining_storage} more day(s).",
        "alert": alert,
        "temperature_source": "Automatic sensor / ESP32",
        "humidity_source": "Automatic sensor / ESP32",
        "weight_source": "Manual farmer entry",
    }


def demo_market_rows(vegetable):
    """Fallback only: clearly marked demo data when no government API key is configured."""
    base_prices = {
        "Tomato": 2200, "Onion": 2800, "Potato": 2400, "Carrot": 3200,
        "Cabbage": 1800, "Cauliflower": 3000, "Brinjal": 2600, "Okra": 3600,
        "Capsicum": 4200, "Cucumber": 2300, "Spinach": 2800, "Coriander": 3500,
        "Peas": 5200, "Beans": 4800, "Beetroot": 3000, "Radish": 2200,
        "Bitter Gourd": 3400, "Bottle Gourd": 2000, "Pumpkin": 1800, "Garlic": 7000,
    }
    base = base_prices.get(vegetable, 3000)
    rows = []
    today = datetime.now().date()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        modal = max(500, base + ((i * 137 + len(vegetable) * 41) % 601) - 300)
        rows.append({
            "date": d.isoformat(),
            "min_price": round(modal * 0.88),
            "max_price": round(modal * 1.12),
            "modal_price": round(modal),
            "market": "Demo Market",
            "state": MARKET_STATE,
            "source": "Demo data - add DATA_GOV_API_KEY for government daily rates",
        })
    return rows


def fetch_market_rows(vegetable):
    """Fetch latest daily mandi records from the Government of India's OGD API."""
    if not MARKET_API_KEY:
        return demo_market_rows(vegetable), False

    cache_key = (vegetable.lower(), MARKET_STATE.lower())
    cached = MARKET_CACHE.get(cache_key)
    if cached and time.time() - cached["time"] < MARKET_CACHE_SECONDS:
        return cached["rows"], True

    params = {
        "api-key": MARKET_API_KEY,
        "format": "json",
        "limit": 100,
        "offset": 0,
        "sort[arrival_date]": "desc",
        "filters[state.keyword]": MARKET_STATE,
        "filters[commodity]": vegetable,
    }
    try:
        response = requests.get(MARKET_API_URL, params=params, timeout=12)
        response.raise_for_status()
        payload = response.json()
        records = payload.get("records", [])
        cleaned = []
        for r in records:
            try:
                date_raw = str(r.get("arrival_date", "")).strip()
                date_obj = datetime.strptime(date_raw, "%d/%m/%Y") if "/" in date_raw else datetime.strptime(date_raw, "%Y-%m-%d")
                min_price = float(str(r.get("min_price", "0")).replace(",", ""))
                max_price = float(str(r.get("max_price", "0")).replace(",", ""))
                modal_price = float(str(r.get("modal_price", "0")).replace(",", ""))
            except (TypeError, ValueError):
                continue
            cleaned.append({
                "date": date_obj.date().isoformat(),
                "min_price": round(min_price),
                "max_price": round(max_price),
                "modal_price": round(modal_price),
                "market": r.get("market", ""),
                "state": r.get("state", MARKET_STATE),
                "source": "Government of India OGD / AGMARKNET",
            })

        # Keep one representative row per day (highest-volume response order is not assumed).
        by_date = {}
        for row in cleaned:
            by_date.setdefault(row["date"], []).append(row)
        rows = []
        for date_key in sorted(by_date.keys(), reverse=True)[:7]:
            day_rows = by_date[date_key]
            rows.append({
                "date": date_key,
                "min_price": round(sum(x["min_price"] for x in day_rows) / len(day_rows)),
                "max_price": round(sum(x["max_price"] for x in day_rows) / len(day_rows)),
                "modal_price": round(sum(x["modal_price"] for x in day_rows) / len(day_rows)),
                "market": f"{len(day_rows)} market(s)",
                "state": day_rows[0]["state"],
                "source": "Government of India OGD / AGMARKNET",
            })
        if not rows:
            raise RuntimeError("No matching daily market records")

        MARKET_CACHE[cache_key] = {"time": time.time(), "rows": rows}
        return rows, True
    except Exception:
        return demo_market_rows(vegetable), False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/data")
def data():
    return jsonify(analyse())


@app.route("/api/weight", methods=["POST"])
def update_weight():
    payload = request.get_json(silent=True) or {}
    try:
        weight = float(payload.get("weight_kg"))
        if weight < 0 or weight > 10000:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid weight in kg."}), 400
    state["weight_kg"] = weight
    return jsonify(analyse())


@app.route("/api/market")
def market():
    vegetable = get_record()["vegetable"]
    rows, live = fetch_market_rows(vegetable)
    latest = rows[0] if rows else None
    modal_price = float(latest["modal_price"]) if latest else 0.0
    price_per_kg = round(modal_price / 100, 2)
    estimated_value = round(float(state["weight_kg"]) * price_per_kg, 2)

    return jsonify({
        "vegetable": vegetable,
        "state": MARKET_STATE,
        "rows": rows,
        "latest": latest,
        "live": live,
        "unit": "₹ / quintal",
        "price_per_kg": price_per_kg,
        "weight_kg": round(float(state["weight_kg"]), 1),
        "estimated_value": estimated_value,
        "source": "Government of India OGD / AGMARKNET (latest daily reported data)" if live else "Demo fallback — live government request failed",
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/demo/<int:number>/<mode>")
def demo(number, mode):
    if number < 1 or number > len(VEGETABLES):
        return jsonify({"error": "Invalid tray"}), 400
    if mode not in ["normal", "medium", "high"]:
        return jsonify({"error": "Invalid mode"}), 400

    record = VEGETABLES[number - 1]
    state["tray_id"] = record["tray_id"]
    # Weight is never changed here. The manually entered weight remains.
    if mode == "normal":
        age_days = 0
        state["temperature_c"] = round((record["min_temp_c"] + record["max_temp_c"]) / 2, 1)
        state["humidity"] = round((record["min_humidity"] + record["max_humidity"]) / 2, 1)
    elif mode == "medium":
        age_days = max(1, int(record["max_storage_days"] * 0.75))
        state["temperature_c"] = round(record["max_temp_c"] + 2, 1)
        state["humidity"] = round((record["min_humidity"] + record["max_humidity"]) / 2, 1)
    else:
        age_days = int(record["max_storage_days"]) + 1
        state["temperature_c"] = round(record["max_temp_c"] + 8, 1)
        state["humidity"] = max(0, round(record["min_humidity"] - 20, 1))

    state["harvest_date"] = (datetime.now() - timedelta(days=age_days)).strftime("%Y-%m-%d")
    return jsonify(analyse())


@app.route("/api/sensor", methods=["POST"])
def sensor():
    payload = request.get_json(silent=True) or {}
    for key in ["tray_id", "temperature_c", "humidity", "harvest_date"]:
        if key in payload:
            state[key] = payload[key]
    # Weight intentionally stays manual; it is not accepted from this sensor endpoint.
    return jsonify(analyse())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
