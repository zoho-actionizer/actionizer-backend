from jira import JIRA


def create_jira_ticket(title, description, project_key):
    jira = JIRA(
        server="https://your-domain.atlassian.net",
        basic_auth=("email@example.com", "api_token")
    )

    issue = jira.create_issue(fields={
        "project": {"key": project_key},
        "summary": title,
        "description": description,
        "issuetype": {"name": "Task"}
    })

    return {
        "id": issue.id,
        "key": issue.key,
        "url": f"https://your-domain.atlassian.net/browse/{issue.key}"
    }

def create(payload) -> dict:
    return {"id": "...", "url": "..."}
