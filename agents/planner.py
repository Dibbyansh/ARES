# Planner agent — generates prioritized response tasks using RAG guidelines
from tools.llm import ask_ai
from tools.rag import search_guidelines
from tools.db import save_tasks
from utils.json_parser import parse_json


def plan_tasks(incident_data):
    """Generate prioritized response tasks using RAG guidelines."""
    
    # Retrieve relevant emergency guidelines via semantic search
    category = incident_data.get("category", "general")
    guidelines = search_guidelines(category)
    
    if guidelines:
        guidelines_text = f"Relevant emergency guidelines:\n{guidelines}"
    else:
        guidelines_text = "No specific guidelines found - use general best practices."
    
    event_type = incident_data.get("event_type", "new")
    
    if event_type == "new":
        return plan_new_tasks(incident_data, guidelines_text)
    else:
        return plan_new_tasks(incident_data, guidelines_text)


def plan_new_tasks(incident_data, guidelines_text):
    """Ask AI to create top 4-5 critical tasks and save them to DB."""
    
    risks = incident_data.get("risks", [])
    if risks:
        risks_text = "\n".join(f"  - {risk}" for risk in risks)
    else:
        risks_text = "  (none identified)"
    
    # Ask AI to produce top 4-5 critical tasks with priorities
    prompt = f"""{guidelines_text}

Incident: {incident_data["incident"]}
Category: {incident_data.get("category")}
Severity: {incident_data.get("severity")}
Location: {incident_data.get("location")}

Key Risks:
{risks_text}

Generate the TOP 4-5 most critical response tasks.

Priority levels:
- "high" = Direct threat to life, must be done immediately
- "medium" = Prevents escalation, important but not life-threatening
- "low" = Documentation, cleanup, post-incident activities

For this incident, focus on HIGH and MEDIUM priority tasks only.
Do NOT include low priority tasks yet.

Return ONLY this JSON (maximum 5 tasks):
{{
  "tasks": [
    {{"task": "Evacuate all occupants immediately", "priority": "high"}},
    {{"task": "Establish water supply for suppression", "priority": "high"}},
    {{"task": "Set up perimeter and traffic control", "priority": "medium"}}
  ]
}}"""
    
    response = ask_ai(prompt)
    
    plan = parse_json(response)
    
    if not plan or not plan.get("tasks"):
        print("❌ Could not generate tasks")
        incident_data["tasks"] = []
        incident_data["task_ids"] = []
        return incident_data
    
    # Persist tasks to DB and store returned IDs
    tasks = plan.get("tasks", [])
    incident_data["tasks"] = tasks
    incident_data["task_ids"] = save_tasks(
        incident_data["incident_id"],
        tasks
    )
    
    return incident_data
