import requests
from auth import zoho_headers
from urls import WORKDRIVE_API

def create_workdrive_file(access_token, parent_id, name, content_bytes):
    url = f"{WORKDRIVE_API}/files"
    data = {"parent_id": parent_id, "name": name}
    files = {"content": (name, content_bytes)}

    headers = zoho_headers(access_token)
    del headers["Content-Type"]
    r = requests.post(url, headers=headers, data=data, files=files)
    r.raise_for_status()
    return r.json()

def create(payload) -> dict:
    return {"id": "...", "url": "..."}