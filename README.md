# Calendar-Aware Flight Planner (Experimental)

This project explores **calendar-aware flight planning** by filtering flight
options based on real Google Calendar constraints. Instead of choosing flights
first and fitting life around them, this tool treats your schedule as a
first-class input.

The UI is built with Streamlit and integrates:
- Google Flights (via SerpAPI)
- Google Calendar (OAuth)
- Dynamic filtering based on activities

⚠️ This is an experimental project, not a production booking tool.

---

## How it works (high level)

1. Flights are fetched from Google Flights using SerpAPI
2. Your Google Calendar is queried for activities on relevant travel days
3. Flights are filtered:
   - Outbound flights must arrive **before** the first activity
   - Inbound flights must depart **after** the last activity
4. A Streamlit UI lets you cycle through valid options
5. Selected flights are previewed directly on your calendar

As you add new activities and move around existing ones, the possible flights will update automatically. 
The intention is to allow you to plan your trips flexibily without having to keep searching up new flights.

---

## Requirements

- Python 3.10+
- A SerpAPI account and API key
- A Google Cloud project with:
  - Google Calendar API enabled
  - OAuth client credentials

---

## Setup

### 1. Clone the repository

```
bash
git clone https://github.com/<your-username>/Travel-Software.git
cd Travel-Software
```

### 2. Create and activate a virtual environment (recommended)

```
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
```

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Configure SerpAPI

Get your SerpAPI key from https://serpapi.com/google-flights-api

Then add it to your environment:
```
export SERPAPI_KEY="your_api_key_here"
```

### 5. Configure Google Calendar OAuth

a. Create OAuth credentials

- Go to Google Cloud Console

- Enable Google Calendar API

- Create OAuth client credentials

- Download the credentials JSON file

b. Add credentials to the project

Rename the downloaded file to:
```
credentials.json
```
and place it in the project root directoy

⚠️ This file should not be committed to GitHub.

### 6. Choose the calendar to use

Create a file named:
```
travel_calendar_id.txt
```
with a single line containing the calendar ID to query.

You can find the calendar ID by going to https://calendar.google.com/ -> My calendars -> Hover over one of the calendars and press the 3 dots -> Settings and Sharing -> Scroll down to "Calendar ID", which will be a super long piece of text ending with @group.calendar.google.com

### 7. Update the flight and date information

At the top of plan_trip.py, make sure to change:
- ORIGIN (3 digit airport code)
- DEST (3 digit airport code)
- DEPART_DATE (YYYY-MM-DD)
- RETURN_DATE (YYYY-MM-DD)
- TRIP_NAME (Short description of the trip)

On the first run, SERPAPI will save a json file called 
```
flights_{ORIGIN}_{DEST}_{DEPART_DATE}_{RETURN_DATE}.json.
```
In subsequent runs for the same set of parameters, the script will automatically use the saved file (to save your API credits).

### 8. Run the streamlit app
```
python -m streamlit run plan_trip.py
```

On first run:
- A browser window will open for Google authentication
- A local token.json file will be created automatically

⚠️ token.json contains OAuth access and refresh tokens and must never be committed to GitHub.

### 9. Play with the tool

- You can adjust the inbound and outbound flights separately using the obvious arrow buttons.
- Make sure to share any comments you have!
