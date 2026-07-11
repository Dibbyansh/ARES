# JSON parser — extracts structured data from AI responses
import json


def parse_json(text):
    """Parse JSON from AI text, stripping code fences if present."""
    
    if not text:
        return None

    text = text.strip()

    # Strip markdown code fences that models sometimes wrap around JSON
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        data = json.loads(text)
        return data
        
    except json.JSONDecodeError as error:
        print(f"⚠️  Could not parse JSON: {error}")
        print(f"   Text was: {text[:100]}...")
        return None
    
    except Exception as error:
        print(f"⚠️  Unexpected error parsing JSON: {error}")
        return None
