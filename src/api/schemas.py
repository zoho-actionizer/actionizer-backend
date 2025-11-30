import uuid
from pydantic import BaseModel, Field
from typing import Optional, Any

class MessageMeta(BaseModel):
    channel: Optional[str] = None
    sender: Optional[str] = None
    timestamp: Optional[str] = None
    message_id: Optional[str] = None


class AnalyzeIntentRequest(BaseModel):
    message_text: str
    metadata: MessageMeta
    tenant: Optional[str] = Field(None, description="tenant id or org id to resolve tokens")


# class PrefillHint(BaseModel):
#     field: str
#     value: Optional[Any] = None


class SuggestedAction(BaseModel):
    tool: str  # e.g., "jira", "zoho_projects", "zoho_calendar", "zoho_workdrive"
    score: float  # relevance score (0-1)
    title: str
    description: Optional[str]
    prefill: dict[str, Any]
    # expected_fields informs frontend what fields to show in preview form
    expected_fields: list[str] = []
    action_id: uuid.UUID = Field(default_factory=uuid.uuid4)


class AnalyzeIntentResponse(BaseModel):
    suggestions: list[SuggestedAction]


class ExecuteActionRequest(BaseModel):
    action_id: str
    updated_params: dict[str, Any]


class ExecuteActionResponse(BaseModel):
    success: bool
    result: dict[str, Any]