import httpx
import requests
import json

from src.auth import zoho_headers
from .urls import PROJECT_API


async def create_zoho_project_task(
    access_token: str,
    portal_id: str,
    project_id: str,
    name: str,
    description: str,
    start_date: str = None,
    end_date: str = None,
    priority: str = None,
    owner_ids: list[str] = None
):
    """Create a task inside a Zoho Projects project.

    Args:
        access_token (str):
            Valid Zoho OAuth access token with Zoho Projects scope.
        portal_id (str):
            Portal ID of the Zoho Projects portal.
        project_id (str):
            The project under which the task is created.
        name (str):
            Name/title of the task.
        description (str):
            Detailed description of the task.
        start_date (str, optional):
            Task start date. Must be in "YYYY-MM-DD" format.
        end_date (str, optional):
            Task end date. Must be in "YYYY-MM-DD" format.
        priority (str, optional):
            Task priority ("High", "Medium", "Low").
        owner_ids (list[str], optional):
            List of user IDs to assign as owners.

    Returns:
        dict: JSON response from Zoho Projects API containing created task details.

    Raises:
        httpx.HTTPStatusError: If Zoho Projects API returns an error status.
    """

    url = f"{PROJECT_API}/portal/{portal_id}/projects/{project_id}/tasks/"

    # Build task body exactly as Zoho expects
    task_data = {
        "name": name,
        "description": description
    }

    if start_date:
        task_data["start_date"] = start_date  # YYYY-MM-DD
    if end_date:
        task_data["end_date"] = end_date
    if priority:
        task_data["priority"] = priority
    if owner_ids:
        task_data["owner"] = [{"id": oid} for oid in owner_ids]

    payload = {"task": task_data}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers=zoho_headers(access_token),
            json=payload
        )
        resp.raise_for_status()
        return resp.json()


async def update_zoho_project_task(
    access_token: str,
    portal_id: str,
    project_id: str,
    task_id: str,
    **updates
):
    """Update fields of a Zoho Projects task.

    Zoho uses POST (not PATCH/PUT) for updating tasks.

    Args:
        access_token (str):
            Valid Zoho OAuth access token.
        portal_id (str):
            Zoho Projects portal ID.
        project_id (str):
            Project ID containing the task.
        task_id (str):
            ID of the task to update.
        **updates:
            Arbitrary task fields to update. Must follow Zoho format:
            - name: str
            - description: str
            - start_date: "YYYY-MM-DD"
            - end_date: "YYYY-MM-DD"
            - priority: "High" | "Medium" | "Low"
            - owner: [{"id": "123"}]
            - any other valid Zoho task field.

    Returns:
        dict: Updated task response.

    Raises:
        httpx.HTTPStatusError: On API failure.
    """
    url = f"{PROJECT_API}/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/"

    payload = {"task": updates}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=zoho_headers(access_token), json=payload)
        resp.raise_for_status()
        return resp.json()

async def list_zoho_project_tasks(
    access_token: str,
    portal_id: str,
    project_id: str,
    owner_id: str | None = None,
    status: str | None = None,
):
    """List tasks inside a Zoho Projects project.

    Args:
        access_token (str):
            Zoho OAuth access token.
        portal_id (str):
            Zoho Projects portal ID.
        project_id (str):
            Project ID whose tasks are listed.
        owner_id (str, optional):
            Filter tasks by owner ID.
        status (str, optional):
            Filter by task status
            (Open, Closed, In Progress, On Hold).

    Returns:
        dict: JSON list of tasks returned by Zoho Projects API.
    """
    url = f"{PROJECT_API}/portal/{portal_id}/projects/{project_id}/tasks/"

    params = {}
    if owner_id:
        params["owner"] = owner_id
    if status:
        params["task_status"] = status

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=zoho_headers(access_token), params=params)
        resp.raise_for_status()
        return resp.json()

async def search_zoho_project_tasks(
    access_token: str,
    portal_id: str,
    project_id: str,
    query: str
):
    """Search tasks inside a Zoho Projects project.

    Zoho Projects does not provide a dedicated search endpoint.
    Searching is done by passing `search=<text>` to the tasks list API.

    Args:
        access_token (str):
            Valid Zoho OAuth access token.
        portal_id (str):
            Zoho Projects portal ID.
        project_id (str):
            Project to search within.
        query (str):
            Free text to match against task names and descriptions.

    Returns:
        dict: JSON search results from Zoho Projects.
    """
    url = f"{PROJECT_API}/portal/{portal_id}/projects/{project_id}/tasks/"

    params = {"search": query}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=zoho_headers(access_token), params=params)
        resp.raise_for_status()
        return resp.json()

async def create_zoho_project_task_in_milestone(
    access_token: str,
    portal_id: str,
    project_id: str,
    milestone_id: str,
    name: str,
    description: str,
    start_date: str | None = None,
    end_date: str | None = None,
    priority: str | None = None,
    owner_ids: list[str] | None = None,
):
    """Create a task inside a specific milestone.

    Args:
        access_token (str):
            Zoho OAuth access token.
        portal_id (str):
            Zoho Projects portal ID.
        project_id (str):
            Project ID containing the milestone.
        milestone_id (str):
            Target milestone ID.
        name (str):
            Task name.
        description (str):
            Task description.
        start_date (str, optional):
            "YYYY-MM-DD".
        end_date (str, optional):
            "YYYY-MM-DD".
        priority (str, optional):
            Task priority ("High", "Medium", "Low").
        owner_ids (list[str], optional):
            User IDs to assign.

    Returns:
        dict: Zoho API response for created milestone task.
    """
    url = f"{PROJECT_API}/portal/{portal_id}/projects/{project_id}/milestones/{milestone_id}/tasks/"

    task = {
        "name": name,
        "description": description,
    }
    if start_date:
        task["start_date"] = start_date
    if end_date:
        task["end_date"] = end_date
    if priority:
        task["priority"] = priority
    if owner_ids:
        task["owner"] = [{"id": oid} for oid in owner_ids]

    payload = {"task": task}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=zoho_headers(access_token), json=payload)
        resp.raise_for_status()
        return resp.json()
