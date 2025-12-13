# ============================================
# Filename: serp_api_test.py
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


from serpapi import GoogleSearch
import os
import json

# Put your SerpAPI key in an environment variable SERPAPI_KEY
API_KEY = "d60f31589fcdb11b34dd08a3303a68bb22a3062f6428ecffb64d230133bc0bfc"

OUTPUT_FILE = "flights_cache.json"   # local saved results

def fetch_flights_oneway(origin, destination, depart_date):
    params = {
        "engine": "google_flights",
        "api_key": API_KEY,
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": depart_date,
        "type": 2,               # 2 = one-way
        "deep_search": True,
        "hl": "en",
        "gl": "us",
        "currency": "USD"
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    return results


def parse_flight_option(option):
    """Extracts price, airlines, segments, stops, duration."""
    price = option.get("price", "?")
    airlines = option.get("airlines", ["Unknown"])
    flights = option.get("flights", [])
    layovers = option.get("layovers", [])
    segments_clean = []

    for seg in flights:
        dep_airport = seg["departure_airport"]["id"]
        dep_time = seg["departure_airport"]["time"]
        arr_airport = seg["arrival_airport"]["id"]
        arr_time = seg["arrival_airport"]["time"]
        airline = seg.get("airline", "Unknown")

        segments_clean.append({
            "dep": dep_airport,
            "dep_time": dep_time,
            "arr": arr_airport,
            "arr_time": arr_time,
            "airline": airline,
            "airplane": seg.get("airplane"),
        })

    return {
        "price": price,
        "airlines": airlines,
        "segments": segments_clean,
        "stops": len(layovers),
        "total_duration": option.get("total_duration", "?")
    }


def print_flight(label, flight):
    print(f"\n✈️  {label}")
    print(f"Price: ${flight['price']}")
    print(f"Airlines: {', '.join(flight['airlines'])}")
    print(f"Total Duration: {flight['total_duration']} minutes")
    print(f"Stops: {flight['stops']}")

    print("Segments:")
    for seg in flight["segments"]:
        print(f"  {seg['dep']} → {seg['arr']}")
        print(f"    {seg['dep_time']} → {seg['arr_time']}")
        print(f"    Airline: {seg['airline']}")
        if seg.get("airplane"):
            print(f"    Airplane: {seg['airplane']}")

    print("--------------------------------------------------")


if __name__ == "__main__":
    origin_airport = "AUS"
    dest_airport = "SJO"
    depart = "2026-03-05"

    print("\n📡 Fetching one-way flights from SerpAPI...\n")
    data = fetch_flights_oneway(origin_airport, dest_airport, depart)

    # Save full result for future use
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"💾 Saved full SerpAPI result to: {OUTPUT_FILE}")

    # Extract and print best & other flights
    best = data.get("best_flights", [])
    others = data.get("other_flights", [])

    # Print best flights
    for i, option in enumerate(best, start=1):
        parsed = parse_flight_option(option)
        print_flight(f"BEST OPTION {i}", parsed)

    # Print other flights
    for i, option in enumerate(others, start=1):
        parsed = parse_flight_option(option)
        print_flight(f"OTHER OPTION {i}", parsed)