import asyncio
from src.api.schemas import MessageMeta
from src.intent.analysis import call_llm
from src.integrations import TOOLS_INFO


async def test():
    message = "We need to fix the payment bug before tomorrow 5 PM"
    metadata = MessageMeta(
        channel="general",
        sender="alice",
        timestamp="2025-01-10T12:00:00Z",
        message_id="msg123",
    )

    resp = await call_llm(message, metadata, TOOLS_INFO)
    print(resp)


    if __name__ == "__main__":
        asyncio.run(test())