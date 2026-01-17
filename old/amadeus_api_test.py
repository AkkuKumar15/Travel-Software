# ============================================
# Filename: amadeus_api_test.py
# Project: GRR API Contract 25-26
# Created Date: Th 11 Dec 2025
# Author: Akshaj Kumar
# -----
# Last Modified: Thu Dec 11 2025
# Modified By: Akshaj Kumar
# -----
# Confidential – Proprietary to Arrow Analytics
# -----
# HISTORY:
# Date & Time              	By	Comments
# -------------------------	---	---------------------------------------------------------
# ============================================


from amadeus import Client, ResponseError

amadeus = Client(
    client_id="ZzswbzPiXhOK66TdQllfGwZPBHGIG5dy",
    client_secret="74K1oFnGZsHWKb7K"
)

try:
    response = amadeus.shopping.flight_offers_search.get(
        originLocationCode="AUS",
        destinationLocationCode="SJO",
        departureDate="2026-03-05",
        returnDate="2026-03-12",
        adults=1,
        currencyCode="USD",
        max=5
    )


    flights = response.data

    for i, f in enumerate(flights[:3], 1):
        print(f"\nOption {i}")
        print(f"Price: ${f['price']['total']}")

        print("Outbound:")
        for seg in f["itineraries"][0]["segments"]:
            print(f"  {seg['departure']['iataCode']} → {seg['arrival']['iataCode']}")
            print(f"    {seg['departure']['at']} → {seg['arrival']['at']}")
            print(f"    Airline: {seg['carrierCode']}")
        
        print("Return:")
        for seg in f["itineraries"][1]["segments"]:
            print(f"  {seg['departure']['iataCode']} → {seg['arrival']['iataCode']}")
            print(f"    {seg['departure']['at']} → {seg['arrival']['at']}")
            print(f"    Airline: {seg['carrierCode']}")



except ResponseError as error:
    import json
    print(json.dumps(error.response.result, indent=2))
