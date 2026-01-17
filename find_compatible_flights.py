# ============================================
# Filename: find_compatible_flights.py
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

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events"
]

SERP_JSON_FILE = "flights_cache.json"

# Load your new API-created Travel calendar ID
with open("travel_calendar_id.txt", "r") as f:
    TRAVEL_CAL_ID = f.read().strip()


# -------------------------
# TIME HELPERS
# -------------------------

def parse_time(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


def to_rfc3339(dt_str, tz="America/Chicago"):
    dt = parse_time(dt_str)
    tz_obj = pytz.timezone(tz)
    return tz_obj.localize(dt).isoformat()


# -------------------------
# GOOGLE CALENDAR AUTH
# -------------------------

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


# -------------------------
# LOAD FLIGHTS
# -------------------------

def load_all_flights():
    with open(SERP_JSON_FILE, "r") as f:
        data = json.load(f)

    all_opts = data.get("best_flights", []) + data.get("other_flights", [])

    parsed = []
    for opt in all_opts:
        parsed.append({
            "price": opt["price"],
            "segments": [
                {
                    "dep": seg["departure_airport"]["id"],
                    "dep_time": seg["departure_airport"]["time"],
                    "arr": seg["arrival_airport"]["id"],
                    "arr_time": seg["arrival_airport"]["time"],
                    "airline": seg["airline"]
                }
                for seg in opt["flights"]
            ]
        })

    return parsed


# -------------------------
# DETERMINE EARLIEST ACTIVITY
# -------------------------

def get_day_activity_bounds(service, date):
    """
    Returns:
      earliest_activity_start,
      latest_activity_end
    for the given date.
    """
    tz = pytz.timezone("America/Chicago")

    day_start = tz.localize(datetime(date.year, date.month, date.day, 0, 0))
    day_end   = tz.localize(datetime(date.year, date.month, date.day, 23, 59))

    events = service.events().list(
        calendarId=TRAVEL_CAL_ID,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True
    ).execute().get("items", [])

    if not events:
        return None, None

    starts = []
    ends   = []

    for e in events:
        if "dateTime" in e["start"]:
            starts.append(datetime.fromisoformat(e["start"]["dateTime"]))
        if "dateTime" in e["end"]:
            ends.append(datetime.fromisoformat(e["end"]["dateTime"]))

    earliest = min(starts) if starts else None
    latest   = max(ends)   if ends   else None

    return earliest, latest



# -------------------------
# FILTER FLIGHTS
# -------------------------

def filter_arrival_flights(flights, earliest_activity):
    if earliest_activity is None:
        return flights

    tz = pytz.timezone("America/Chicago")
    valid = []

    for f in flights:
        last_seg = f["segments"][-1]
        arrival_time = tz.localize(parse_time(last_seg["arr_time"]))

        if arrival_time <= earliest_activity:
            valid.append(f)

    return valid

def filter_departure_flights(flights, latest_activity):
    """
    Keep only flights whose FIRST SEGMENT departs AFTER the last activity ends.
    """
    if latest_activity is None:
        return flights  # nothing scheduled → all flights allowed

    tz = pytz.timezone("America/Chicago")
    valid = []

    for f in flights:
        first_seg = f["segments"][0]
        dep_time = tz.localize(parse_time(first_seg["dep_time"]))

        # Valid only if the flight leaves AFTER the last activity ends
        if dep_time >= latest_activity:
            valid.append(f)

    return valid


# -------------------------
# DELETE PREVIEW EVENTS
# -------------------------

def delete_temp_events(service):
    events = service.events().list(
        calendarId=TRAVEL_CAL_ID,
        privateExtendedProperty="flight_preview=temp"
    ).execute()

    for ev in events.get("items", []):
        service.events().delete(
            calendarId=TRAVEL_CAL_ID,
            eventId=ev["id"]
        ).execute()

    # This workaround is no longer needed — API-created calendars auto-refresh.
    service.calendarList().get(calendarId=TRAVEL_CAL_ID).execute()


# -------------------------
# ADD FLIGHT OPTION
# -------------------------

def add_flight_option(service, flight):
    price = flight["price"]

    for seg in flight["segments"]:
        dep = seg["dep"]
        arr = seg["arr"]
        airline = seg["airline"]

        start = to_rfc3339(seg["dep_time"])
        end = to_rfc3339(seg["arr_time"])

        event = {
            "summary": f"{dep} → {arr} (${price}, {airline})",
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "colorId": "9",
            "extendedProperties": {
                "private": {"flight_preview": "temp"}
            }
        }

        service.events().insert(
            calendarId=TRAVEL_CAL_ID,
            body=event
        ).execute()


# -------------------------
# MAIN LOOP — CYCLE OPTIONS
# -------------------------

def cycle_flight_options():
    service = get_calendar_service()
    flights = load_all_flights()

    # Ask user which mode to use
    mode = input("Filter by arrival or departure? (a/d): ").strip().lower()
    if mode not in ("a", "d"):
        print("Invalid choice. Use 'a' or 'd'.")
        return

    # Determine date from first flight's arrival (good enough for now)
    sample_arr = flights[0]["segments"][-1]["arr_time"]
    arr_dt = parse_time(sample_arr)
    date = arr_dt.date()

    # Get both earliest + latest activity times
    earliest, latest = get_day_activity_bounds(service, date)

    # Apply chosen filter
    if mode == "a":
        flights = filter_arrival_flights(flights, earliest)
        print("\nUsing ARRIVAL filtering...")
    else:
        flights = filter_departure_flights(flights, latest)
        print("\nUsing DEPARTURE filtering...")

    if not flights:
        print("❌ No flights fit your schedule.")
        return

    idx = 0
    n = len(flights)

    print("\nUse ENTER to cycle through valid flights. Press q to quit.\n")

    while True:
        delete_temp_events(service)
        add_flight_option(service, flights[idx])

        print(f"Showing option {idx+1} of {n}")
        user = input("ENTER = next, q = quit: ")

        if user.lower() == "q":
            delete_temp_events(service)
            print("Cleaned up preview events. Exiting.")
            break

        idx = (idx + 1) % n



if __name__ == "__main__":
    cycle_flight_options()
