# Classifier agent — determines incident type, severity, and saves to DB
from tools.llm import ask_ai
from tools.db import (
    get_recent_incidents,
    save_new_incident,
    save_incident_update,
    get_incident_history
)
from utils.json_parser import parse_json


def classify_incident(incident_data):
    """Classify incident type, severity, and location via AI and save to DB."""
    
    # Provide recent incidents so AI can link updates to existing ones
    recent = get_recent_incidents()
    
    # Build classification prompt with event-type detection rules
    prompt = f"""You are an emergency incident classifier.

Recent incidents in the system:
{recent}

New input: {incident_data["incident"]}

Your tasks:
1. Determine the TYPE:
   - "new" = Brand new emergency
   - "update" = New information about an existing incident
   - "stabilizing" = Situation is improving
   - "resolve" = Incident is completely over

2. If it's an update/stabilizing/resolve, identify which incident ID it relates to.
   If it's new, set incident_id to null.

3. Classify the incident:
   - Category: fire, flood, earthquake, medical, hazmat, vehicle_accident, power_outage, or other
   - Severity: low, medium, high, or critical
   - Location: Be specific about where it's happening
   - Risks: List up to 4 key risks (short phrases)

Return ONLY this JSON (no extra text):
{{
  "type": "new|update|stabilizing|resolve",
  "incident_id": number or null,
  "category": "...",
  "severity": "low|medium|high|critical",
  "location": "...",
  "risks": ["risk1", "risk2", "risk3", "risk4"]
}}"""
    
    response = ask_ai(prompt)
    
    classification = parse_json(response)
    
    if not classification:
        print("❌ Could not classify incident")
        return incident_data
    
    event_type = classification.get("type", "new")
    
    # Merge AI classification into incident state
    incident_data["category"] = classification.get("category")
    incident_data["severity"] = classification.get("severity")
    incident_data["location"] = classification.get("location")
    incident_data["risks"] = classification.get("risks", [])
    
    # Handle follow-up events on an existing incident
    if event_type in ("update", "stabilizing", "resolve"):
        incident_data["event_type"] = event_type
        incident_data["incident_id"] = classification.get("incident_id")
        
        if not incident_data["incident_id"]:
            print("⚠️  Could not match to existing incident - treating as new")
            incident_data["event_type"] = "new"
        else:
            # Record the update and load prior history for downstream agents
            incident_data["update_id"] = save_incident_update(
                incident_data["incident_id"],
                incident_data["incident"],
                event_type
            )
            
            history = get_incident_history(incident_data["incident_id"])
            incident_data["original_description"] = history.get("original_description")
            incident_data["all_updates"] = history.get("updates", [])
            incident_data["previous_tasks"] = history.get("previous_tasks", [])
            incident_data["previous_assignments"] = history.get("previous_assignments", [])
            
            return incident_data
    
    # Brand-new incident — insert into DB and get generated ID
    incident_data["event_type"] = "new"
    incident_data["incident_id"] = save_new_incident(
        description=incident_data["incident"],
        category=incident_data["category"],
        severity=incident_data["severity"],
        location=incident_data["location"],
        risks=incident_data["risks"],
        feed_id=incident_data.get("feed_id")
    )
    
    return incident_data
