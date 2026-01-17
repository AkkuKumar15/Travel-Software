# ============================================
# Filename: plan_trip.py
# Purpose: Flight planning engine using SerpAPI + Google Calendar
# UI: Streamlit (no terminal input)
# ============================================

import json
import os
from datetime import datetime, timedelta
import pytz
import requests
import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from streamlit.runtime.scriptrunner import add_script_run_ctx
import time


# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------
API_KEY = os.getenv("SERPAPI_KEY")
if not API_KEY:
    raise ValueError("API_KEY is not set. Please set SERPAPI_KEY.")

ORIGIN = "IAH"
DEST = "GUA"

DEPART_DATE = "2026-01-22"
RETURN_DATE = "2026-01-25"

TRIP_NAME = "Texas → Guatemala Trip"
JSON_FILE = f"flights_{ORIGIN}_{DEST}_{DEPART_DATE}_{RETURN_DATE}.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

with open("travel_calendar_id.txt", "r") as f:
    TRAVEL_CAL_ID = f.read().strip()

TZ = pytz.timezone("America/Chicago")

# -----------------------------------------------------
# GOOGLE CALENDAR AUTH
# -----------------------------------------------------
def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as t:
            t.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

# -----------------------------------------------------
# SERPAPI
# -----------------------------------------------------
def fetch_one_way(origin, dest, date):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "api_key": API_KEY,
        "departure_id": origin,
        "arrival_id": dest,
        "outbound_date": date,
        "type": "2",
        "deep_search": "true",
    }
    return requests.get(url, params=params).json()

# -----------------------------------------------------
# PARSER
# -----------------------------------------------------
def extract_flights(raw):
    flights = []
    flight_id = 0

    for block in raw.get("best_flights", []) + raw.get("other_flights", []):
        segments = []
        for seg in block.get("flights", []):
            segments.append({
                "dep": seg["departure_airport"]["id"],
                "dep_time": seg["departure_airport"]["time"],
                "arr": seg["arrival_airport"]["id"],
                "arr_time": seg["arrival_airport"]["time"],
                "airline": seg.get("airline", "Unknown"),
            })

        flights.append({
            "id": flight_id,
            "price": block.get("price"),
            "segments": segments,
        })
        flight_id += 1

    return flights

# -----------------------------------------------------
# TIME HELPERS
# -----------------------------------------------------
def parse_dt(s):
    return TZ.localize(datetime.strptime(s, "%Y-%m-%d %H:%M"))

# -----------------------------------------------------
# CALENDAR ACTIVITY CONSTRAINTS
# -----------------------------------------------------
def get_day_constraints(service, date_obj):
    # print("DEBUG calendar:", TRAVEL_CAL_ID)
    # print("DEBUG date:", date_obj)

    start = TZ.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0))
    end = TZ.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59))

    events = service.events().list(
        calendarId=TRAVEL_CAL_ID,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True
    ).execute().get("items", [])

    starts, ends = [], []

    for ev in events:
        # Skip ALL flight preview events (outbound or inbound)
        private = ev.get("extendedProperties", {}).get("private", {})
        if "flight_preview" in private:
            continue

        if "dateTime" in ev["start"]:
            starts.append(datetime.fromisoformat(ev["start"]["dateTime"]))
        if "dateTime" in ev["end"]:
            ends.append(datetime.fromisoformat(ev["end"]["dateTime"]))

    return (min(starts) if starts else None), (max(ends) if ends else None)


# -----------------------------------------------------
# FILTERS
# -----------------------------------------------------
def filter_arrival_flights(flights, latest_allowed):
    if latest_allowed is None:
        return flights
    return [
        f for f in flights
        if parse_dt(f["segments"][-1]["arr_time"]) <= latest_allowed
    ]

def filter_departure_flights(flights, earliest_allowed):
    if earliest_allowed is None:
        return flights
    return [
        f for f in flights
        if parse_dt(f["segments"][0]["dep_time"]) >= earliest_allowed
    ]

# -----------------------------------------------------
# CALENDAR PREVIEWS
# -----------------------------------------------------
def clear_previews(service, tag):
    evs = service.events().list(
        calendarId=TRAVEL_CAL_ID,
        privateExtendedProperty=f"flight_preview={tag}"
    ).execute().get("items", [])

    for e in evs:
        service.events().delete(calendarId=TRAVEL_CAL_ID, eventId=e["id"]).execute()

def add_preview(service, flight, tag, color):
    for seg in flight["segments"]:
        service.events().insert(
            calendarId=TRAVEL_CAL_ID,
            body={
                "summary": f"{seg['dep']} → {seg['arr']} (${flight['price']}, {seg['airline']})",
                "start": {"dateTime": parse_dt(seg["dep_time"]).isoformat()},
                "end": {"dateTime": parse_dt(seg["arr_time"]).isoformat()},
                "colorId": color,
                "extendedProperties": {"private": {"flight_preview": tag}},
            }
        ).execute()

# -----------------------------------------------------
# TRIP BLOCK
# -----------------------------------------------------
def create_trip_block(service):
    existing = service.events().list(
        calendarId=TRAVEL_CAL_ID,
        privateExtendedProperty="trip_block=yes"
    ).execute().get("items", [])

    if existing:
        return

    end = (datetime.strptime(RETURN_DATE, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    service.events().insert(
        calendarId=TRAVEL_CAL_ID,
        body={
            "summary": TRIP_NAME,
            "start": {"date": DEPART_DATE},
            "end": {"date": end},
            "colorId": "5",
            "extendedProperties": {"private": {"trip_block": "yes"}},
        }
    ).execute()

# -----------------------------------------------------
# STREAMLIT APP
# -----------------------------------------------------
def main():

    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()

    if time.time() - st.session_state.last_refresh > 5:
        st.session_state.last_refresh = time.time()
        st.rerun()

    st.set_page_config(page_title="Flight Planner", layout="wide")
    st.title("✈️ Calendar-Aware Flight Planner")

    service = get_calendar_service()

    # ---------- Load data ----------
    if "state" not in st.session_state:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE) as f:
                raw = json.load(f)
            out_raw = raw["outbound_raw"]
            in_raw = raw["inbound_raw"]
        else:
            out_raw = fetch_one_way(ORIGIN, DEST, DEPART_DATE)
            in_raw = fetch_one_way(DEST, ORIGIN, RETURN_DATE)
            with open(JSON_FILE, "w") as f:
                json.dump({"outbound_raw": out_raw, "inbound_raw": in_raw}, f, indent=2)

        outbound = extract_flights(out_raw)
        inbound = extract_flights(in_raw)

        st.session_state.state = {
            "all_out": outbound,
            "all_in": inbound,
            "idx_out": 0,
            "idx_in": 0,
        }

        create_trip_block(service)

    state = st.session_state.state

    # ---------- Apply constraints ----------
    out_date = parse_dt(state["all_out"][0]["segments"][-1]["arr_time"]).date()
    in_date = parse_dt(state["all_in"][0]["segments"][0]["dep_time"]).date()

    out_earliest_start, _ = get_day_constraints(service, out_date)
    _, in_latest_end = get_day_constraints(service, in_date)

    # print(out_earliest_start)

    valid_out = filter_arrival_flights(
        state["all_out"],
        out_earliest_start
    )

    valid_in = filter_departure_flights(
        state["all_in"],
        in_latest_end
    )


    state["idx_out"] %= max(1, len(valid_out))
    state["idx_in"] %= max(1, len(valid_in))

    # ---------- UI ----------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Outbound")
        if valid_out:
            f = valid_out[state["idx_out"]]
            st.write(f"**${f['price']}**")
            for s in f["segments"]:
                st.write(f"{s['dep']} → {s['arr']} ({s['dep_time']} → {s['arr_time']})")

            if st.button("⬅️ Outbound"):
                state["idx_out"] -= 1
            if st.button("➡️ Outbound"):
                state["idx_out"] += 1

            clear_previews(service, "outbound")
            add_preview(service, f, "outbound", "9")
        else:
            st.error("No outbound flights available")

    with col2:
        st.subheader("Inbound")
        if valid_in:
            f = valid_in[state["idx_in"]]
            st.write(f"**${f['price']}**")
            for s in f["segments"]:
                st.write(f"{s['dep']} → {s['arr']} ({s['dep_time']} → {s['arr_time']})")

            if st.button("⬅️ Inbound"):
                state["idx_in"] -= 1
            if st.button("➡️ Inbound"):
                state["idx_in"] += 1

            clear_previews(service, "inbound")
            add_preview(service, f, "inbound", "10")
        else:
            st.error("No inbound flights available")

    st.caption("Calendar constraints re-evaluated on every interaction.")

if __name__ == "__main__":
    main()
