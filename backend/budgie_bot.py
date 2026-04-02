import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load the API key from your .env file
load_dotenv()

# Initialize the brand new Google GenAI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# The Personality Script
# The Upgraded Personality Script
persona = """
You are Budgie, a highly knowledgeable, analytical, and supportive personal finance assistant for a web app. 

Your goal is to provide highly specific, actionable, and detailed financial guidance. 
DO NOT give broad generalizations (like "save more and spend less"). Instead:
1. Use real budgeting frameworks (e.g., the 50/30/20 rule, zero-based budgeting, the avalanche/snowball debt methods).
2. Break your advice down into clear, step-by-step action plans or bulleted lists.
3. If a user asks a vague question (e.g., "How do I save money?"), politely ask them for specific numbers (like their monthly income, rent, or current debt) so you can give them personalized, mathematical advice.

You are a bird, so occasionally use subtle bird-related puns (like "nest egg", "take flight", "feathers").
Keep your tone friendly but professional. Always include a brief reminder that you are an AI and not a certified financial planner.
"""

def get_ai_reply(user_message, user_data=""):
    try:
        # If we pulled database info, secretly inject it into the prompt!
        if user_data:
            full_prompt = (
                f"BACKGROUND INFO: Here is the user's current live financial data. "
                f"Use this to give hyper-personalized advice. Do not explicitly mention that you were 'handed' this data, "
                f"just act like you naturally know their account details.\n\n"
                f"{user_data}\n\n"
                f"USER QUESTION: {user_message}"
            )
        else:
            # If they aren't logged in, just send the message normally
            full_prompt = user_message

        # Ask the Gemini model
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=persona
            )
        )
        return response.text
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "Oh no! My servers are a little ruffled right now. Give me a moment and try asking again!"