import os
import asyncio
import re
import json

import dotenv
import google.generativeai as genai

from .prompt import PROMPT_TEMPLATE
from src.api.schemas import MessageMeta


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


async def _call_gemini_llm(prompt: str):
    """
    Calls Gemini 2.0 Flash using official google-generativeai SDK.
    Returns raw text output from the model.
    """
    response = await model.generate_content_async(prompt)
    json_block = re.search(r'(\{.*\})', response.text, re.DOTALL)
    assert json_block, f"No json found in llm resp {response.text=}"
    tools = json.loads(json_block.group())
    return sorted(tools["suggestions"], key=lambda x: x["score"], reverse=True)

async def call_llm(message, message_metadata: MessageMeta, tools):
    """Calls gemini to get best tool calls with their parameters
    """
    prompt = PROMPT_TEMPLATE.format(
        message_text=message,
        metadata_json=message_metadata.model_dump(),
        tool_info=tools,
    )
    return await _call_gemini_llm(prompt)

"""sample output

[
  {
    "tool": "jira",
    "score": 0.9,
    "title": "Create Jira ticket for payment bug",
    "description": "Create a Jira ticket to track and resolve the payment bug.",
    "expected_fields": [
      "project_key",
      "summary",
      "description",
      "issuetype",
      "duedate"
    ],
    "prefill": {
      "summary": "Payment bug fix",
      "description": "Describe the payment bug in detail.",
      "issuetype": "Bug",
      "duedate": "2025-01-11T17:00:00Z"
    }
  },
  {
    "tool": "zoho_projects",
    "score": 0.7,
    "title": "Create Zoho Projects task for payment bug",
    "description": "Create a Zoho Projects task to track and resolve the payment bug.",
    "expected_fields": [
      "portal_id",
      "project_id",
      "name",
      "description",
      "start_date",
      "end_date"
    ],
    "prefill": {
      "name": "Fix payment bug",
      "description": "Describe the payment bug in detail.",
      "end_date": "2025-01-11"
    }
  },
  {
    "tool": "zoho_calendar",
    "score": 0.3,
    "title": "Create Zoho Calendar event for payment bug fix",
    "description": "Create a Zoho Calendar event to schedule time for fixing the payment bug.",
    "expected_fields": [
      "calendar_id",
      "title",
      "start_iso",
      "end_iso",
      "description",
      "location"
    ],
    "prefill": {
      "title": "Payment bug fix",
      "start_iso": "2025-01-11T09:00:00Z",
      "end_iso": "2025-01-11T17:00:00Z",
      "description": "Schedule time to work on fixing the payment bug."
    }
  }
]

"""