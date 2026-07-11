# LLM client — single entry point for all AI calls via OpenRouter
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL

# OpenAI-compatible client pointed at OpenRouter
ai_client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY
)


def ask_ai(question):
    """Send a prompt to the LLM and return the text response."""
    
    try:
        response = ai_client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an emergency response AI assistant. "
                        "When asked to return JSON, return ONLY raw JSON with no extra text, "
                        "no markdown formatting, and no code fences."
                    )
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=0.3,  # Low temperature for consistent structured output
        )
        
        answer = response.choices[0].message.content
        return answer
        
    except Exception as error:
        print(f"❌ Error talking to AI: {error}")
        return ""
