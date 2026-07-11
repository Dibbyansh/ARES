# Simple sequential coordinator — runs agents in a fixed order
from agents.classifier import classify_incident
from agents.planner import plan_tasks
from agents.assigner import assign_teams
from agents.tracker import activate_teams, stabilize_incident, close_incident
from agents.alerter import send_alert


def handle_incident(incident_text):
    """Process an incident through agents in fixed sequence."""
    
    print("⚡ Processing incident...")
    print("-" * 60)
    
    # Shared state dict passed through each agent
    incident_data = {
        "incident": incident_text,
    }
    
    # Step 1: Classify type, severity, location, and save to DB
    print("\n🔍 Step 1: Classifying incident...")
    incident_data = classify_incident(incident_data)
    
    print(f"   Type: {incident_data.get('event_type', 'unknown')}")
    print(f"   Category: {incident_data.get('category', 'unknown')}")
    print(f"   Severity: {incident_data.get('severity', 'unknown')}")
    print(f"   Location: {incident_data.get('location', 'unknown')}")
    
    # Abort if classification failed to produce an incident ID
    if not incident_data.get("incident_id"):
        print("❌ Could not classify incident. Please try again.")
        return
    
    event_type = incident_data.get("event_type", "new")
    
    # Resolve events skip planning — go straight to closing
    if event_type == "resolve":
        print("\n📊 Step 2: Closing incident...")
        close_incident(incident_data)
        print("\n✅ Incident closed successfully!")
        print_summary(incident_data)
        return
    
    # Step 2: Generate response tasks using RAG guidelines
    print("\n📋 Step 2: Planning response tasks...")
    incident_data = plan_tasks(incident_data)
    
    if incident_data.get("tasks"):
        print(f"   Generated {len(incident_data['tasks'])} tasks:")
        for i, task in enumerate(incident_data["tasks"], 1):
            priority = task.get("priority", "?").upper()
            print(f"   {i}. [{priority}] {task.get('task')}")
    else:
        print("   No new tasks needed.")
    
    # Step 3: Match available teams to tasks via AI
    if incident_data.get("tasks"):
        print("\n🧑‍🚒 Step 3: Assigning teams to tasks...")
        incident_data = assign_teams(incident_data)
        
        if incident_data.get("assignments"):
            print(f"   Assigned {len(incident_data['assignments'])} teams:")
            for assignment in incident_data["assignments"]:
                print(f"   - {assignment['team_name']} → {assignment['task']}")
        else:
            print("   No teams available or assigned.")

    # Step 4: Mark assigned tasks as in_progress
    if incident_data.get("assignments"):
        print("\n📊 Step 4: Activating teams...")
        activate_teams(incident_data)
        print("   ✓ Teams are now working on their tasks")
    
    # Step 5 (stabilizing): Complete urgent tasks when situation improves
    if event_type == "stabilizing":
        print("\n📊 Step 5: Stabilizing incident...")
        stabilize_incident(incident_data)
        print("   ✓ High-priority tasks completed")
    

    # Step 5 (new): Send Telegram alert for brand-new incidents
    if event_type == "new":
        print("\n🚨 Step 5: Sending alert...")
        send_alert(incident_data)
        print("   ✓ Alert sent (if Telegram is configured)")
    
    print("\n✅ Processing complete!")
    print_summary(incident_data)


def print_summary(incident_data):
    """Print incident summary to console."""
    
    print("\n" + "=" * 60)
    print("INCIDENT SUMMARY")
    print("=" * 60)
    
    print(f"Incident ID: {incident_data.get('incident_id')}")
    print(f"Type: {incident_data.get('event_type', 'unknown')}")
    print(f"Category: {incident_data.get('category', 'unknown')}")
    print(f"Severity: {incident_data.get('severity', 'unknown')}")
    print(f"Location: {incident_data.get('location', 'unknown')}")
    
    if incident_data.get("tasks"):
        print(f"\nTasks ({len(incident_data['tasks'])}):")
        for i, task in enumerate(incident_data["tasks"], 1):
            priority = task.get("priority", "?").upper()
            print(f"  {i}. [{priority}] {task.get('task')}")
    
    if incident_data.get("assignments"):
        print(f"\nTeam Assignments:")
        for assignment in incident_data["assignments"]:
            print(f"  - {assignment['team_name']} → {assignment['task']}")
    
    # Derive display status from event type
    status = "closed" if incident_data.get("event_type") == "resolve" else "active"
    print(f"\nStatus: {status}")
    print("=" * 60)
