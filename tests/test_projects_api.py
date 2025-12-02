
import asyncio
import os
from integrations.zoho.projects import create_zoho_project_task


async def main(token):
    result = await create_zoho_project_task(
        access_token=token,
        portal_id="123456789",
        project_id="987654321",
        name="Implement Quick Actions feature",
        description="LLM based contextual action engine",
        start_date="2025-02-10",
        end_date="2025-02-12",
        priority="High"
    )
    return print(result)

asyncio.run(main(os.getenv("")))