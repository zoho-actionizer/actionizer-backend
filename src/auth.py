
import os
from fastapi import HTTPException
from typing import Any
import requests
import time
import httpx
from constants import DEFAULT_TIMEOUT, ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET
from integrations.zoho.urls import ZOHO_ACCOUNTS_URL


def zoho_headers(access_token):
    return {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }


ZOHO_REFRESH_STORE: dict[str, dict[str, Any]] = {}  # keyed by user_or_tenant


def get_stored_refresh_token(tenant: str):
    """
    Simple in-memory store for demo.
    ZOHO_REFRESH_STORE[tenant] = {"refresh_token": "...", "access_token": "...", "expiry_ts": 12345}
    """
    entry = ZOHO_REFRESH_STORE.get(tenant)
    if not entry:
        return None
    return entry.get("refresh_token")
    
    
async def get_valid_zoho_access_token_for_tenant(tenant: str):
    """
    Returns a valid access_token for tenant, refreshing if necessary.
    """
    entry = ZOHO_REFRESH_STORE.get(tenant)
    if not entry:
        raise HTTPException(status_code=400, detail="No OAuth entry for tenant; perform OAuth flow first")
    if entry.get("access_token") and entry.get("expiry_ts", 0) > time.time() + 60:
        return entry["access_token"]

    refreshed = await refresh_zoho_access_token(entry["refresh_token"])
    entry["access_token"] = refreshed["access_token"]
    entry["expiry_ts"] = refreshed["expiry_ts"]
    ZOHO_REFRESH_STORE[tenant] = entry
    return entry["access_token"]


async def refresh_zoho_access_token(refresh_token: str) -> dict[str, Any]:
    """
    Call Zoho Accounts to exchange refresh token for access token.
    Returns dict containing access_token, expires_in, expiry_ts.
    """
    url = f"{ZOHO_ACCOUNTS_URL}/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        r = await client.post(url, params=params)
        r.raise_for_status()
        data = r.json()
    return {
        "access_token": data["access_token"],
        "expires_in": int(data.get("expires_in", 3600)),
        "expiry_ts": int(time.time()) + int(data.get("expires_in", 3600))
    }
