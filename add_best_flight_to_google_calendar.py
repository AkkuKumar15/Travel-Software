# ============================================
# Filename: add_best_flight_to_google_calendar.py
# Project: GRR API Contract 25-26
# Created Date: Sa 13 Dec 2025
# Author: Akshaj Kumar
# -----
# Last Modified: Sat Dec 13 2025
# Modified By: Akshaj Kumar
# -----
# Confidential – Proprietary to Arrow Analytics
# -----
# HISTORY:
# Date & Time              	By	Comments
# -------------------------	---	---------------------------------------------------------
# ============================================


import json
import os
from datetime import datetime
import pytz

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SERP_JSON_FILE = "flights_cache.json"   # your uploaded file
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# -----------------------------
# Convert SerpAPI time → RFC3339
# -----------------------------

def to_rfc3339(dt_str, tz_name="America/Chicago"):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    tz = pytz.timezone(tz_name)
    localized = tz.localize(dt)
    return localized.isoformat()

# -----------------------------
# Load best flight
# -----------------------------

def load_best_flight():
    with open(SERP_JSON_FILE, "r") as f:
        data = json.load(f)

    best = data["best_flights"][0]  # take first/best option
    price = best["price"]

    segments = []
    for seg in best["flights"]:
        segments.append({
            "dep": seg["departure_airport"]["id"],
            "dep_time": seg["departure_airport"]["time"],
            "arr": seg["arrival_airport"]["id"],
            "arr_time": seg["arrival_airport"]["time"],
            "airline": seg["airline"]
        })

    return {
        "price": price,
        "segments": segments
    }

# -----------------------------
# Google auth
# -----------------------------

def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

# -----------------------------
# Add flight events
# -----------------------------

def add_flight_to_calendar(service, flight):
    print("\n✈️ Adding BEST flight to Google Calendar...\n")

    price = flight["price"]

    for seg in flight["segments"]:
        dep = seg["dep"]
        arr = seg["arr"]
        airline = seg["airline"]
        dep_rfc = to_rfc3339(seg["dep_time"])
        arr_rfc = to_rfc3339(seg["arr_time"])

        # Title with airline included
        event = {
            "summary": f"{dep} → {arr} (${price}, {airline})",
            "start": {"dateTime": dep_rfc},
            "end": {"dateTime": arr_rfc},
            "colorId": "9"
        }

        created = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()

        print(f"✓ Created event: {created.get('htmlLink')}")

    print("\n🎉 DONE — flight added to your Google Calendar.\n")


# -----------------------------
# MAIN
# -----------------------------

if __name__ == "__main__":
    best_flight = load_best_flight()
    service = get_calendar_service()
    add_flight_to_calendar(service, best_flight)
