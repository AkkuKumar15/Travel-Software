# ============================================
# Filename: create_travel_calendar.py
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


from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_travel_calendar():
    service = get_calendar_service()

    calendar_body = {
        "summary": "Travel",
        "timeZone": "America/Chicago"
    }

    created_calendar = service.calendars().insert(body=calendar_body).execute()

    new_calendar_id = created_calendar["id"]

    print("\n🎉 Created new API-linked Travel calendar!")
    print("Calendar ID:", new_calendar_id)

    # Save for other scripts
    with open("travel_calendar_id.txt", "w") as f:
        f.write(new_calendar_id)

    print("\n📄 Saved to travel_calendar_id.txt")
    print("You can now use this ID in all scripts.\n")


if __name__ == "__main__":
    create_travel_calendar()
