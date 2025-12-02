
import asyncio

from src.auth import create_zoho_access_token
import os

async def test_auth():
    access_token = await create_zoho_access_token(os.getenv("ZOHO_CODE"))
    print(access_token)

if __name__ == "__main__":
    asyncio.run(test_auth())