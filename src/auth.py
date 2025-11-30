
import atexit
from enum import StrEnum
import os
from fastapi import HTTPException
from typing import Any
import requests
import time
import httpx
from src.constants import DEFAULT_TIMEOUT, ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, SERVER_PORT, SERVER_HOST
from src.integrations.zoho.urls import ZOHO_ACCOUNTS_URL
import pickle
import sys


class ZohoTokenStore:
    access_token: str = ""
    refresh_token: str = ""
    expiry_ts: int | float = 0


class UserNotFound(KeyError):
    user_id: str


class Scopes(StrEnum):
    Projects="ZohoProjects.portals.ALL%20ZohoProjects.tasks.ALL"
    WorkDrive="WorkDrive.files.READ%20WorkDrive.files.ALL"
    Calendar="ZohoCalendar.event.ALL"
    # Cliq="ZohoCliq.Webhook.CREATE%20ZohoCliq.Chats.READ%20ZohoCliq.Chats.UPDATE"


GRANT_CODE_AUTH_URI = ZOHO_ACCOUNTS_URL + "/v2/auth?scope={scopes}&client_id={client_id}&response_type=code&access_type=offline&redirect_uri={redirect_uri}"

EXCHANGE_GRANT_CODE = ZOHO_ACCOUNTS_URL + "/v2/token" #"?grant_type=authorization_code&client_id={client_id}&client_secret={client_secret}&code={code}&redirect_uri={redirect_uri}"

REDIRECT_URI = f"http://{SERVER_HOST}:{SERVER_PORT}/authsuccess"

ZOHO_REFRESH_STORE: dict[str, ZohoTokenStore] = {}  # keyed by user_or_tenant

ZOHO_REFRESH_STORE["1"] = ZohoTokenStore()  # only one user for now
ZOHO_STORE_FILE = "zoho_token_store.pkl"

def load_zoho_store():
    global ZOHO_REFRESH_STORE
    if os.path.exists(ZOHO_STORE_FILE):
        with open(ZOHO_STORE_FILE, "rb") as f:
            ZOHO_REFRESH_STORE = pickle.load(f)
    else:
        ZOHO_REFRESH_STORE["1"] = ZohoTokenStore()

def save_zoho_store():
    with open(ZOHO_STORE_FILE, "wb") as f:
        pickle.dump(ZOHO_REFRESH_STORE, f)

load_zoho_store()
atexit.register(save_zoho_store)


def zoho_headers(access_token):
    return {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }


async def create_zoho_access_token(code, user_id="1") -> ZohoTokenStore:
    data = {
        "grant_type": "authorization_code",
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    async with httpx.AsyncClient() as ac:
        resp = await ac.post(EXCHANGE_GRANT_CODE, data=data)
        resp.raise_for_status()
        resp_json = resp.json()
        assert "error" not in resp_json, f"error in oauth flow {resp_json=}"

    # resp format
    # {
    #   "access_token": "1000.xxxxx",
    #   "refresh_token": "1000.xxxxx",
    #   "expires_in": 3600,
    #   "api_domain": "https://www.zohoapis.com"
    # }
    store = ZOHO_REFRESH_STORE[user_id]
    store.access_token = resp_json["access_token"]
    store.expiry_ts = time.time() + 3600
    store.refresh_token = resp_json["refresh_token"]
    return store


async def get_zoho_access_token(user_id="1"):
    """Returns a valid access token (refreshes if expired)."""
    if user_id not in ZOHO_REFRESH_STORE:
        raise UserNotFound(user_id)

    store = ZOHO_REFRESH_STORE[user_id]
    if store.access_token and store.expiry_ts > time.time() + 60:
        return store.access_token
    return await refresh_zoho_access_token(user_id)


async def refresh_zoho_access_token(user_id="1"):
    """Refresh the Zoho access token using a stored refresh token."""
    url = f"{ZOHO_ACCOUNTS_URL}/oauth/v2/token"
    store = ZOHO_REFRESH_STORE[user_id]

    params = {
        "grant_type": "refresh_token",
        "client_id": os.getenv("ZOHO_CLIENT_ID"),
        "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
        "refresh_token": store.refresh_token
    }

    async with httpx.AsyncClient(timeout=20) as cl:
        resp = await cl.post(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        store.access_token = data["access_token"]
        store.expiry_ts = time.time() + data.get("expires_in", 3600)

        return store.access_token
