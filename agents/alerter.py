# Alerter agent — formats and sends incident notifications via Telegram
from tools.telegram import send_telegram_alert


def send_alert(incident_data):
    """Format incident details and send a Telegram alert."""
    
    # Pull key fields for the alert message
    category = incident_data.get("category", "UNKNOWN")
    severity = incident_data.get("severity", "UNKNOWN")
    location = incident_data.get("location", "Unknown location")
    incident_text = incident_data.get("incident", "")
    
    risks = incident_data.get("risks", [])
    if risks:
        risks_text = ", ".join(risks)
    else:
        risks_text = "none identified"
    
    assignments = incident_data.get("assignments", [])
    if assignments:
        teams_text = ", ".join(a["team_name"] for a in assignments)
    else:
        teams_text = "none yet"
    
    # Build Markdown-formatted Telegram message
    message = f"""🚨 *NEW INCIDENT*

*{category.upper()} / {severity.upper()}*
📍 {location}

{incident_text[:200]}

⚠️ Risks: {risks_text}
🟢 Teams: {teams_text}"""
    
    # Send via Telegram API (no-op if not configured)
    success = send_telegram_alert(message)
    
    if success:
        print("   ✓ Alert sent to Telegram")
    else:
        pass
    
    return incident_data
