import httpx
from auth import zoho_headers
from constants import DEFAULT_TIMEOUT


async def create_zoho_calendar_event(access_token, calendar_id, title, start_iso, end_iso, location=None, description=None):
    """
    Use RFC3339 / ISO timestamps (Zoho expects those); confirm exact expected field names in the Calendar API doc. 
    """
    base = "https://calendar.zoho.com/api/v1"
    url = f"{base}/calendars/{calendar_id}/events"

    payload = {
        "title": title,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso}
    }
    if location: payload["location"] = location
    if description: payload["description"] = description

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(url, params=zoho_headers(access_token))
        r.raise_for_status()
        return r.json()

def create(payload) -> dict:
    return {"id": "...", "url": "..."}