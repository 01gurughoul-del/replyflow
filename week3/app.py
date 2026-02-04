"""
Week 3 – WhatsApp bot: WATI webhook → Gemini → reply → WATI send. DB stores conversations + menu.
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Load .env from phase folder (parent of week3)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google import genai
import requests

import db

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Config from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WATI_API_KEY = os.getenv("WATI_API_KEY")
WATI_ENDPOINT = os.getenv("WATI_API_ENDPOINT", "https://live-mt-server.wati.io").rstrip("/")
# For now: one restaurant (id=1). Later: map WATI number → restaurant_id
DEFAULT_RESTAURANT_ID = 1


def get_ai_reply(customer_phone: str, new_message: str, restaurant_id: int = DEFAULT_RESTAURANT_ID) -> str:
    """Get reply from Gemini using menu + conversation history."""
    conv_id = db.get_or_create_conversation(restaurant_id, customer_phone)
    menu_text = db.get_menu_text(restaurant_id)
    history = db.get_conversation_history(conv_id)

    history_text = "\n".join(
        f"{h['role']}: {h['content']}" for h in history
    ) or "(no previous messages)"

    system = (
        "You are a friendly restaurant bot in Pakistan. Reply in Roman Urdu or English, keep it short. "
        "Use this menu to answer. If they order, confirm items and ask for address. "
        "Do not make up prices; only use the menu below."
    )
    prompt = f"""Menu:
{menu_text}

Previous conversation:
{history_text}

Customer says: {new_message}

Reply (short, friendly):"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    reply = (response.text or "").strip()
    return reply, conv_id


def send_wati_message(customer_phone: str, text: str) -> bool:
    """Send reply via WATI API. customer_phone: digits only, e.g. 923001234567."""
    if not WATI_API_KEY:
        log.warning("WATI_API_KEY not set; skipping send")
        return False
    url = f"{WATI_ENDPOINT}/api/v1/sendSessionMessage/{customer_phone}"
    headers = {"Authorization": f"Bearer {WATI_API_KEY}", "Content-Type": "application/json"}
    # WATI often expects {"message": "..."} for session message
    body = {"message": text}
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        log.exception("WATI send failed: %s", e)
        return False


def parse_wati_webhook(data: dict) -> tuple[str | None, str | None]:
    """
    Extract customer_phone and message text from WATI webhook.
    WATI payloads vary; common shapes: value.messages[0].from, value.messages[0].text.body
    or event payload with contact/customer and text. Returns (phone, text) or (None, None).
    """
    phone = None
    text = None
    # Try common WATI / WhatsApp Business API shapes
    value = data.get("value") or data
    messages = value.get("messages") or []
    if messages:
        msg = messages[0]
        phone = msg.get("from") or msg.get("wa_id") or msg.get("sender")
        if isinstance(phone, int):
            phone = str(phone)
        if not phone and "contact" in msg:
            phone = msg["contact"].get("wa_id")
        tb = msg.get("text") or {}
        text = tb.get("body") if isinstance(tb, dict) else (msg.get("text") or msg.get("body"))
    # Alternative: top-level contact / message
    if not phone:
        phone = data.get("contact") or data.get("customerPhone") or (data.get("customer") or {}).get("phone")
    if not text:
        text = data.get("text") or data.get("message") or (data.get("message", {}) or {}).get("body")
    if phone and isinstance(phone, (int, float)):
        phone = str(int(phone))
    return (phone, text)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/webhook/wati", methods=["POST", "GET"])
def webhook_wati():
    """WATI sends message-received events here. Reply with Gemini and send back via WATI."""
    if request.method == "GET":
        # Some providers use GET for verification
        return jsonify({"status": "ok"})
    try:
        data = request.get_json() or {}
    except Exception:
        data = {}
    log.info("Webhook payload (keys): %s", list(data.keys()))

    phone, text = parse_wati_webhook(data)
    if not phone or not text:
        log.warning("Could not parse phone or text from webhook: %s", data)
        return jsonify({"status": "ignored"}), 200

    # Normalize phone: digits only
    customer_phone = "".join(c for c in str(phone) if c.isdigit())
    if not customer_phone:
        return jsonify({"status": "bad_phone"}), 200

    reply, conv_id = get_ai_reply(customer_phone, text)
    db.save_message(conv_id, "user", text)
    db.save_message(conv_id, "bot", reply)

    sent = send_wati_message(customer_phone, reply)
    out = {"status": "ok", "reply_sent": sent}
    if not sent:
        out["reply"] = reply  # so local test can see it without WATI
    return jsonify(out), 200


if __name__ == "__main__":
    if not GEMINI_API_KEY:
        raise SystemExit("Set GEMINI_API_KEY in .env (in phase folder)")
    db.init_db()
    # For local testing without WATI, set WATI_API_KEY when you have it
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
