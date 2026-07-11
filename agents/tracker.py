# Tracker agent — updates task and incident status as response progresses
from tools.db import (
    get_active_tasks,
    set_task_status,
    complete_task,
    complete_all_tasks,
    update_incident_status
)


def activate_teams(incident_data):
    """Move assigned tasks to in_progress status."""
    
    incident_id = incident_data.get("incident_id")
    
    if not incident_id:
        print("⚠️  No incident ID")
        return incident_data
    
    # Move all assigned tasks to in_progress
    tasks = get_active_tasks(incident_id)
    
    activated_count = 0
    for task in tasks:
        if task["status"] == "assigned":
            set_task_status(task["id"], "in_progress")
            activated_count += 1
    
    if activated_count > 0:
        print(f"   ✓ Activated {activated_count} tasks")
    
    return incident_data


def stabilize_incident(incident_data):
    """Complete urgent tasks and mark incident as stabilizing."""
    
    incident_id = incident_data.get("incident_id")
    
    if not incident_id:
        print("⚠️  No incident ID")
        return incident_data
    
    tasks = get_active_tasks(incident_id)
    
    # Complete urgent tasks and mark incident as stabilizing
    completed_count = 0
    for task in tasks:
        if task["priority"] in ("high", "medium"):
            complete_task(task["id"])
            completed_count += 1
    
    update_incident_status(incident_id, "stabilizing")
    
    if completed_count > 0:
        print(f"   ✓ Completed {completed_count} urgent tasks")
    
    return incident_data


def close_incident(incident_data):
    """Complete all tasks, free teams, and close the incident."""
    
    incident_id = incident_data.get("incident_id")
    
    if not incident_id:
        print("⚠️  No incident ID")
        return incident_data
    
    # Finish all tasks, release teams, and set status to closed
    complete_all_tasks(incident_id)
    
    update_incident_status(incident_id, "closed")
    
    print(f"   ✓ Incident {incident_id} closed")
    
    return incident_data
