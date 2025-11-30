import base64
from fastapi import HTTPException
import httpx
import requests
from src.api.schemas import ExecuteActionResponse
from src.auth import zoho_headers
from .urls import WORKDRIVE_API
import logging
logger = logging.getLogger(__name__)

async def create_workdrive_file(access_token, parent_id, name, content_bytes):
    url = f"{WORKDRIVE_API}/files"
    data = {"parent_id": parent_id, "name": name}
    files = {"content": (name, content_bytes)}

    headers = zoho_headers(access_token)
    del headers["Content-Type"]
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, data=data, files=files)
        r.raise_for_status()
        return r.json()
    
async def workdrive_download_file_bytes(access_token: str, file_id: str) -> bytes:
    """
    Returns raw bytes of the file. Use this when you want to re-upload into Cliq as binary.
    """
    url = f"{WORKDRIVE_API}/files/{file_id}/download"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.content

async def workdrive_search_files(access_token: str, org_id: str, query: str, limit: int = 10) -> list[dict]:
    """
    Search WorkDrive for files matching `query` (filename / partial). 
    Returns list of file metadata dicts (inspect returned JSON to adapt fields).
    """
    url = f"{WORKDRIVE_API}/files/search"
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    params = {
        "q": query,
        "limit": limit,
        "org_id": org_id
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

async def cliq_share_file_to_chat(
    authtoken: str, 
    chat_id: str, 
    filename: str, 
    file_bytes: bytes, 
    message_text: str | None = None
):
    """
    Uploads a file to a Cliq chat (chat_id). `authtoken` should be a valid Cliq auth token (Zoho-authtoken or Zoho-oauthtoken).
    """
    url = f"https://cliq.zoho.com/api/v2/chats/{chat_id}/files"
    headers = {
        "Authorization": authtoken
    }
    files = {
        "file": (filename, file_bytes)
    }
    data = {}
    if message_text:
        data["text"] = message_text
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers=headers, files=files, data=data)
        r.raise_for_status()
        return r.json()

async def workdrive_action(access_token, org_id, name_or_query, file_id, cliq_target, fields):
    # if file_id absent, search
    if not file_id:
        logger.debug(f"Searching for file: {name_or_query}")
        search_json = await workdrive_search_files(access_token, org_id, name_or_query, limit=5)
        # choose best match: first exact name or first result
        hits = search_json.get("data") or search_json.get("files") or search_json
        chosen = None
        for item in (hits or []):
            logger.debug(f"Evaluating search result: {item}")
            nm = item.get("name") or item.get("file_name") or item.get("title")
            if nm == name_or_query:
                logger.debug(f"Found exact match: {nm}")
                chosen = item; break
        if not chosen:
            chosen = (hits or [None])[0]
            logger.debug(f"Using first search result")
        if not chosen:
            logger.error("No file found in WorkDrive")
            raise HTTPException(status_code=404, detail="No file found in WorkDrive")
        file_id = chosen.get("id") or chosen.get("file_id")
        if not file_id:
            logger.debug("File_id not found, attempting download via URL")
            # maybe the search returned downloadUrl
            dl = chosen.get("download_url") or chosen.get("webUrl")
            if not dl:
                logger.error("Search result lacks file_id or download_url")
                raise HTTPException(status_code=500, detail="Search result lacks file_id or download_url")
            # download direct
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(dl, headers={"Authorization": f"Zoho-oauthtoken {access_token}"})
                r.raise_for_status()
                file_bytes = r.content
        else:
            logger.debug(f"Downloading file with id: {file_id}")
            file_bytes = await workdrive_download_file_bytes(access_token, file_id)

    else:
        logger.debug(f"Downloading file with id: {file_id}")
        file_bytes = await workdrive_download_file_bytes(access_token, file_id)

    # If a Cliq target is provided, post it
    if cliq_target:
        logger.info("Posting file to Cliq")
        target_type = cliq_target.get("type")
        target_id = cliq_target.get("id")
        if target_type != "chat":
            logger.warning(f"Unsupported Cliq target type: {target_type}")
            # For simplicity this code handles chat uploads. Channel variants: adapt endpoint.
            raise HTTPException(status_code=501, detail="Only chat target implemented in this demo")
        # We need a Cliq auth header — you can reuse Zoho product token (if it has Cliq scope) OR a bot token.
        # Here we assume the same Zoho OAuth token can be used for Cliq (if the token had cliq scope)
        res = await cliq_share_file_to_chat(access_token, target_id, fields.get("filename") or "file.bin", file_bytes, message_text=fields.get("message"))
        logger.info("File shared to Cliq successfully")
        return {"shared_to_cliq": res}
    else:
        logger.debug("Returning file as base64")
        # return file bytes base64 encoded for demo
        b64 = base64.b64encode(file_bytes).decode()
        return {"file_id": file_id, "file_base64": b64}

def create(payload) -> dict:
    return {"id": "...", "url": "..."}