import logging


from fastapi import APIRouter, HTTPException

from api.schemas import AnalyzeIntentRequest, AnalyzeIntentResponse, ExecuteActionRequest, ExecuteActionResponse, PrefillHint, SuggestedAction
from auth import get_valid_zoho_access_token_for_tenant
from integrations import TOOLS_INFO
from integrations.jira import create_jira_ticket
from integrations.zoho.calendar import create_zoho_calendar_event
from integrations.zoho.projects import create_zoho_project_task
from intent.analysis import call_llm

logger = logging.getLogger(__name__)

router = APIRouter()
_actions_db = {}


@router.post("/analyze-intent", response_model=AnalyzeIntentResponse)
async def analyze_intent(req: AnalyzeIntentRequest):
    """
    Uses Gemini to analyze the message and return ranked integration suggestions with prefill hints.
    The LLM must return strict JSON per the prompt schema.
    """
    # Provide the LLM with the tool descriptions and ask for strict JSON output
    llm_out = await call_llm(req.message_text, req.metadata, TOOLS_INFO)
    # Validate and coerce into our response model
    try:
        # The LLM returns top-level {"suggestions": [...]}
        suggestions_raw = llm_out.get("suggestions", [])
        suggestions = []
        for s in suggestions_raw:
            # Basic validation/coercion
            suggestion = SuggestedAction(
                tool=s["tool"],
                score=float(s.get("score", 0.0)),
                title=s.get("title", ""),
                description=s.get("description"),
                expected_fields=s.get("expected_fields", []),
                prefill=[PrefillHint(**p) for p in s.get("prefill", [])]
            )
            suggestions.append(suggestion)
            _actions_db[str(suggestion.action_id)] = suggestion
        return AnalyzeIntentResponse(suggestions=suggestions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid LLM schema or parse error: {e}")


@router.post("/execute-action", response_model=ExecuteActionResponse)
async def execute_action(req: ExecuteActionRequest):
    """
    Executes the chosen integration action with the provided fields.
    Supported tools: jira, zoho_projects (create task), zoho_calendar (create event), zoho_workdrive (find & share file)
    """
    action = _actions_db[str(req.action_id)]
    tool = action.tool
    fields = action.expected_fields

    # Short-circuit common validation
    if tool == "jira":
        # required fields: project_key, summary, description (issuetype optional)
        project_key = fields.get("project_key")
        summary = fields.get("summary")
        description = fields.get("description", "")
        issuetype = fields.get("issuetype", "Task")
        duedate = fields.get("duedate")
        if not project_key or not summary:
            raise HTTPException(status_code=400, detail="Missing project_key or summary for Jira")
        jira_res = await create_jira_ticket(project_key, summary, description, issuetype, duedate)
        return ExecuteActionResponse(success=True, result={"jira": jira_res})

    # Zoho flows require tenant OAuth setup ensure we have access token for tenant
    access_token = await get_valid_zoho_access_token_for_tenant(tenant)  # TODO: fix tenant configuration
    auth_header_value = f"Zoho-oauthtoken {access_token}"
    args = [access_token]

    async def f(*args):return None
    func = f

    if tool == "zoho_calendar":
        calendar_id = fields.get("calendar_id")
        title = fields.get("title")
        start_iso = fields.get("start_iso")
        end_iso = fields.get("end_iso")
        if not (calendar_id and title and start_iso and end_iso):
            raise HTTPException(status_code=400, detail="Missing calendar_id/title/start_iso/end_iso")
        args.extend(
            [access_token, calendar_id, title, start_iso, end_iso, fields.get("location"), fields("description", None)]
        )
        func = create_zoho_calendar_event
        

    if tool == "zoho_workdrive":
        # We support: search by name_or_query or direct file_id; then upload to Cliq chat if provided
        org_id = fields.get("org_id")
        name_or_query = fields.get("name_or_query")
        file_id = fields.get("file_id")
        # Optional: target cliq chat/channel posting info
        cliq_target = fields.get("cliq_target")  # dict with { "type": "chat"|"channel", "id": "<id>", "post_as": "<bot>" }
        if not (name_or_query or file_id):
            raise HTTPException(status_code=400, detail="Provide file_id or name_or_query")
        # if file_id absent, search
        if not file_id:
            search_json = await workdrive_search_files(access_token, org_id, name_or_query, limit=5)
            # choose best match: first exact name or first result
            hits = search_json.get("data") or search_json.get("files") or search_json
            chosen = None
            for item in (hits or []):
                nm = item.get("name") or item.get("file_name") or item.get("title")
                if nm == name_or_query:
                    chosen = item; break
            if not chosen:
                chosen = (hits or [None])[0]
            if not chosen:
                raise HTTPException(status_code=404, detail="No file found in WorkDrive")
            file_id = chosen.get("id") or chosen.get("file_id")
            if not file_id:
                # maybe the search returned downloadUrl
                dl = chosen.get("download_url") or chosen.get("webUrl")
                if not dl:
                    raise HTTPException(status_code=500, detail="Search result lacks file_id or download_url")
                # download direct
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.get(dl, headers={"Authorization": f"Zoho-oauthtoken {access_token}"})
                    r.raise_for_status()
                    file_bytes = r.content
            else:
                file_bytes = await workdrive_download_file_bytes(access_token, file_id)

        else:
            file_bytes = await workdrive_download_file_bytes(access_token, file_id)

        # If a Cliq target is provided, post it
        if cliq_target:
            target_type = cliq_target.get("type")
            target_id = cliq_target.get("id")
            if target_type != "chat":
                # For simplicity this code handles chat uploads. Channel variants: adapt endpoint.
                raise HTTPException(status_code=501, detail="Only chat target implemented in this demo")
            # We need a Cliq auth header — you can reuse Zoho product token (if it has Cliq scope) OR a bot token.
            # Here we assume the same Zoho OAuth token can be used for Cliq (if the token had cliq scope)
            res = await cliq_share_file_to_chat(auth_header_value, target_id, fields.get("filename") or "file.bin", file_bytes, message_text=fields.get("message"))
            return ExecuteActionResponse(success=True, result={"shared_to_cliq": res})
        else:
            # return file bytes base64 encoded for demo
            b64 = base64.b64encode(file_bytes).decode()
            return ExecuteActionResponse(success=True, result={"file_id": file_id, "file_base64": b64})

    if tool == "zoho_projects":
        # create task via Projects REST API
        portal_id = fields.get("portal_id")
        project_id = fields.get("project_id")
        name = fields.get("name")
        description = fields.get("description", "")
        if not (portal_id and project_id and name):
            raise HTTPException(status_code=400, detail="Missing portal_id, project_id, or name")
        args.extend([portal_id, project_id, name, description])
        func = create_zoho_project_task

    try:
        r = await func(*args)
        return ExecuteActionResponse(success=True, result={"resp": r})
    except Exception as exp:
        logger.exception("")
        raise HTTPException(status_code=400, detail=f"{exp}") from exp
