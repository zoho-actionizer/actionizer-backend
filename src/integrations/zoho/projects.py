import requests
import json

from auth import zoho_headers
from urls import PROJECT_API


async def create_zoho_project_task(access_token, portal_id, project_id, name, description, start_date=None, end_date=None):

    # double-check endpoint in the Projects API docs; this is the typical pattern.
    url = f"{PROJECT_API}/portal/{portal_id}/projects/{project_id}/tasks/"

    payload = {
        "name": name,
        "description": description
    }
    if start_date: 
        payload["start_date"] = start_date
    if end_date:   
        payload["end_date"] = end_date

    r = requests.post(url, headers=zoho_headers(access_token), json=payload)
    r.raise_for_status()
    return r.json()  # inspect for task id & link per response schema

def create(payload) -> dict:
    return {"id": "...", "url": "..."}