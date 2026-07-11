# Assigner agent — matches available teams to planned tasks using AI
from tools.llm import ask_ai
from tools.db import get_available_teams, assign_team_to_task
from utils.json_parser import parse_json


def assign_teams(incident_data):
    """Match available teams to tasks via AI and save assignments to DB."""
    
    # Fetch teams not currently deployed
    teams = get_available_teams()
    
    tasks = incident_data.get("tasks", [])
    task_ids = incident_data.get("task_ids", [])
    
    if not teams:
        print("⚠️  No teams available")
        incident_data["assignments"] = []
        return incident_data
    
    if not tasks:
        print("⚠️  No tasks to assign")
        incident_data["assignments"] = []
        return incident_data
    
    # Format tasks and teams for the AI prompt
    tasks_text = "\n".join(
        f"  Task {i} [{task.get('priority', '?').upper()}]: {task.get('task')}"
        for i, task in enumerate(tasks)
    )
    
    teams_text = "\n".join(
        f"  Team {team['id']} | Type: {team['type']:<18} | {team['name']}\n"
        f"    Capabilities: {team['capabilities']}"
        for team in teams
    )
    
    # Ask AI to produce team-to-task mappings
    prompt = f"""You are assigning emergency response teams to tasks.

Incident Type: {incident_data.get("category")}
Severity: {incident_data.get("severity")}

Tasks to assign (prioritize HIGH priority first):
{tasks_text}

Available Teams:
{teams_text}

Assignment Rules:
1. Match team TYPE to task type first (fire team → fire task, medical → medical, etc.)
2. Each team can only be assigned to ONE task
3. Never reuse a team_id for multiple tasks
4. High-priority tasks MUST get a team, even if the match isn't perfect
5. Only leave a task unassigned if truly no suitable team exists

Return ONLY this JSON:
{{
  "assignments": [
    {{
      "task_index": 0,
      "team_id": 4,
      "reason": "Fire response team best suited for evacuation"
    }},
    {{
      "task_index": 1,
      "team_id": 7,
      "reason": "Engine company has water supply capabilities"
    }}
  ]
}}"""
    
    response = ask_ai(prompt)
    
    assignment_plan = parse_json(response)
    
    if not assignment_plan or not assignment_plan.get("assignments"):
        print("❌ Could not generate assignments")
        incident_data["assignments"] = []
        return incident_data
    
    # Validate and persist each assignment to the database
    assignments = []
    used_team_ids = set()
    team_lookup = {team["id"]: team["name"] for team in teams}
    
    for assignment in assignment_plan.get("assignments", []):
        task_index = assignment.get("task_index")
        team_id = assignment.get("team_id")
        reason = assignment.get("reason", "")
        
        if task_index is None or task_index >= len(task_ids):
            print(f"⚠️  Invalid task index: {task_index}")
            continue
        
        if team_id not in team_lookup:
            print(f"⚠️  Unknown team ID: {team_id}")
            continue
        
        # Prevent the same team being assigned twice
        if team_id in used_team_ids:
            print(f"⚠️  Team {team_id} already assigned, skipping duplicate")
            continue
        
        assign_team_to_task(task_ids[task_index], team_id)
        used_team_ids.add(team_id)
        
        assignments.append({
            "task": tasks[task_index].get("task"),
            "team_name": team_lookup[team_id],
            "reason": reason
        })
    
    incident_data["assignments"] = assignments
    return incident_data
