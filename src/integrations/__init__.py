"""Integrations that are available in the extenstion

Each file typically exposes a simple `create` function.
"""
from textwrap import dedent


# def make_tool_info(funs):
#     return "\n".join([str(f.__doc__) for f in funs])

# TOOLS_INFO = make_tool_info()


TOOLS_INFO = dedent("""
    - jira: Create a Jira ticket. Expected fields: project_key, summary, description, issuetype (Task/Bug), duedate (ISO)
    - zoho_projects: Create Zoho Projects task. Expected fields: portal_id, project_id, name, description, start_date, end_date
    - zoho_calendar: Create Zoho Calendar event. Expected fields: calendar_id, title, start_iso, end_iso, description, location(optional)
    - zoho_workdrive: Retrieve or attach WorkDrive file. Expected fields: org_id, name_or_query, file_id (optional)
""")
