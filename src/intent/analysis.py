import os
import asyncio
import re
import json

import dotenv
import google.generativeai as genai

from .prompt import PROMPT_TEMPLATE
from api.schemas import MessageMeta


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")


async def _call_gemini_llm(prompt: str) -> str:
    """
    Calls Gemini 2.0 Flash using official google-generativeai SDK.
    Returns raw text output from the model.
    """
    response = await model.generate_content_async(prompt)
    json_block = re.search(r'(\{.*\})', response.text, re.DOTALL)
    assert json_block, f"No json found in llm resp {response.text=}"
    return json.loads(json_block.group())


async def call_llm(message, message_metadata: MessageMeta, tools):
    prompt = PROMPT_TEMPLATE.format(
        message_text=message,
        metadata_json=message_metadata.model_dump(),
        tools=tools,
    )
    return await _call_gemini_llm(prompt)
