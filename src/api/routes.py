import logging


from fastapi import APIRouter, HTTPException, status

from src.integrations.zoho.workdrive import workdrive_action
from src.api.schemas import AnalyzeIntentRequest, AnalyzeIntentResponse, ExecuteActionRequest, ExecuteActionResponse, PrefillHint, SuggestedAction
from src.auth import UserNotFound, get_zoho_access_token
from src.integrations import TOOLS_INFO
from src.integrations.jira import create_jira_ticket
from src.integrations.zoho.calendar import create_zoho_calendar_event
from src.integrations.zoho.projects import create_zoho_project_task
from src.intent.analysis import call_llm

logger = logging.getLogger(__name__)

router = APIRouter()
_actions_db: dict[str, SuggestedAction] = {}


@router.post("/analyze-intent", response_model=AnalyzeIntentResponse)
async def analyze_intent(req: AnalyzeIntentRequest):
    """
    Uses Gemini to analyze the message and return ranked integration suggestions with prefill hints.
    The LLM must return strict JSON per the prompt schema.
    """
    # Provide the LLM with the tool descriptions and ask for strict JSON output
    llm_out = await call_llm(req.message_text, req.metadata, TOOLS_INFO)
    try:
        suggestions = []
        for s in llm_out:
            logger.debug(f"Processing suggestion: {s.get('tool')}")
            suggestion = SuggestedAction(
                tool=s["tool"],
                score=float(s.get("score", 0.0)),
                title=s.get("title", ""),
                description=s.get("description"),
                expected_fields=s.get("expected_fields", []),
                prefill=s.get("prefill", {})
            )
            suggestions.append(suggestion)
            _actions_db[str(suggestion.action_id)] = suggestion
            logger.info(f"Stored action {suggestion.action_id} for tool {suggestion.tool}")
        return AnalyzeIntentResponse(suggestions=suggestions)
    except Exception as e:
        logger.error(f"Invalid LLM schema or parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid LLM schema or parse error: {e}")


@router.post("/execute-action", response_model=ExecuteActionResponse)
async def execute_action(req: ExecuteActionRequest):
    """
    Executes the chosen integration action with the provided fields.
    Supported tools: jira, zoho_projects (create task), zoho_calendar (create event), zoho_workdrive (find & share file)
    """
    action = _actions_db[str(req.action_id)]
    tool = action.tool
    fields = action.prefill
    filtered_keys = [x for x in req.updated_params.keys() if x in set(action.expected_fields)]
    fields.update({k:req.updated_params[k] for k in filtered_keys})

    logger.debug(f"Executing action {req.action_id} for tool {tool}")

    # Short-circuit common validation
    if tool == "jira":
        logger.info(f"Processing Jira action")
        # required fields: project_key, summary, description (issuetype optional)
        project_key = fields.get("project_key")
        summary = fields.get("summary")
        description = fields.get("description", "")
        issuetype = fields.get("issuetype", "Task")
        duedate = fields.get("duedate")
        if not project_key or not summary:
            logger.warning("Missing project_key or summary for Jira")
            raise HTTPException(status_code=400, detail="Missing project_key or summary for Jira")
        jira_res = await create_jira_ticket(project_key, summary, description, issuetype, duedate)
        logger.info(f"Jira ticket created successfully")
        return ExecuteActionResponse(success=True, result={"jira": jira_res})

    # Zoho flows require tenant OAuth setup ensure we have access token for tenant
    try:
        logger.debug("Retrieving Zoho access token")
        access_token = await get_zoho_access_token()  # TODO: fix tenant configuration
    except UserNotFound:
        logger.warning("User not found, authorization required")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization not done")


    async def f(*args):return None
    func = f
    args = [access_token]

    if tool == "zoho_calendar":
        logger.info("Processing Zoho Calendar action")
        calendar_id = fields.get("calendar_id")
        title = fields.get("title")
        start_iso = fields.get("start_iso")
        end_iso = fields.get("end_iso")
        if not (calendar_id and title and start_iso and end_iso):
            logger.warning("Missing calendar_id/title/start_iso/end_iso")
            raise HTTPException(status_code=400, detail="Missing calendar_id/title/start_iso/end_iso")
        args.extend(
            [calendar_id, title, start_iso, end_iso, fields.get("location"), fields("description", None)]
        )
        func = create_zoho_calendar_event

    elif tool == "zoho_workdrive":
        logger.info("Processing Zoho WorkDrive action")
        # We support: search by name_or_query or direct file_id; then upload to Cliq chat if provided
        org_id = fields.get("org_id")
        name_or_query = fields.get("name_or_query")
        file_id = fields.get("file_id")
        # Optional: target cliq chat/channel posting info
        cliq_target = fields.get("cliq_target")  # dict with { "type": "chat"|"channel", "id": "<id>", "post_as": "<bot>" }
        if not (name_or_query or file_id):
            logger.warning("Missing file_id or name_or_query for WorkDrive")
            raise HTTPException(status_code=400, detail="Provide file_id or name_or_query")
        
        func = workdrive_action
        args.extend((org_id, name_or_query, file_id, cliq_target, fields))

    elif tool == "zoho_projects":
        logger.info("Processing Zoho Projects action")
        # create task via Projects REST API
        portal_id = fields.get("portal_id")
        project_id = fields.get("project_id")
        name = fields.get("name")
        description = fields.get("description", "")
        start_date = fields.get("start_date", None),
        end_date = fields.get("end_date", None),
        priority = fields.get("priority", None),
        owner_ids = fields.get("owner_ids", None)

        if not (portal_id and project_id and name):
            logger.warning("Missing portal_id, project_id, or name for Projects")
            raise HTTPException(status_code=400, detail="Missing portal_id, project_id, or name")
        args.extend((portal_id, project_id, name, description, start_date, end_date, priority, owner_ids))
        func = create_zoho_project_task

    try:
        logger.debug(f"Calling function with args")
        r = await func(*args)
        logger.info(f"Action executed successfully")
        return ExecuteActionResponse(success=True, result={"action_resp": r})
    except Exception as exp:
        logger.exception(f"Action execution failed: {exp}")
        raise HTTPException(status_code=400, detail=f"{exp}") from exp
