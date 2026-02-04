"""
Week 2: First script – send a message to Gemini, get a reply.
Run this to see: your message → AI → reply. No WhatsApp yet; that comes later.
Loads .env from the parent folder (phase) so your GEMINI_API_KEY is found.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from phase folder (parent of week2)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Use the new Google GenAI SDK
try:
    from google import genai
except ImportError:
    print("Run: pip install google-genai python-dotenv")
    exit(1)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Missing GEMINI_API_KEY in .env (keep .env in the phase folder)")
    exit(1)

# Simple restaurant-bot style instruction (same idea as the guide)
SYSTEM = (
    "You are a friendly restaurant bot in Pakistan. "
    "Reply in Roman Urdu or English, keep it short. "
    "If someone says they want food or order, say you're ready to take the order and ask what they want."
)


def get_reply(user_message: str) -> str:
    client = genai.Client(api_key=API_KEY)
    full_prompt = f"{SYSTEM}\n\nCustomer says: {user_message}"
    # Free tier: try gemini-2.5-flash. If 429 quota error, check aistudio.google.com
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
    )
    return response.text if response.text else "(no reply)"


if __name__ == "__main__":
    print("Week 2 – Gemini reply test (restaurant bot style)\n")
    msg = input("Type a message (or press Enter for demo): ").strip()
    if not msg:
        msg = "bhai 2 biryani chahiye"
        print(f"Demo message: {msg}\n")
    print("Reply:", get_reply(msg))
