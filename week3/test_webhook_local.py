"""
Test the bot locally without WATI: simulate a webhook POST and print the reply.
Run: python test_webhook_local.py
Then: python test_webhook_local.py "menu dikhao"
"""
import sys
import requests

url = "http://localhost:5000/webhook/wati"
# Simulate WATI-like payload (adjust if your WATI sends different keys)
message = sys.argv[1] if len(sys.argv) > 1 else "bhai 2 biryani chahiye"
payload = {
    "value": {
        "messages": [
            {"from": "923001234567", "text": {"body": message}}
        ]
    }
}

if __name__ == "__main__":
    print("Sending to", url, "message:", message)
    r = requests.post(url, json=payload)
    print("Status:", r.status_code)
    data = r.json()
    print("Response:", data)
    if data.get("reply"):
        print("Bot reply:", data["reply"])
