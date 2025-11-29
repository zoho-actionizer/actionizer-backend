# API documentation

## /analyse-intent
```json
{
  "actions": [
    {
      "type": "jira_ticket",
      "title": "...",
      "description": "...",
      "parsed": {... any date/time detection ...}
    }
  ]
}
```
> This endpoint uses LLM to classify “does this message imply a Jira/PJ/Calendar/WorkDrive action?”.

## /execute-action
```json
{
  "action_type": "jira_ticket",
  "fields": {
    "title": "...",
    "description": "...",
    "due_date": "2025-01-09T19:00:00Z"
  }
}
```
### output
```json
{ "success": true, "link": "https://jira/XYZ-123" }
```
