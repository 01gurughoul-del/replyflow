"""
WhatsApp Cloud API – Flask webhook. Receives messages, replies using Gemini.
"""
import os
import hmac
import hashlib
import logging
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request

# Load .env from phase folder
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google import genai
from google.genai import types
import requests

import db

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Config from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token_123")
APP_SECRET = os.getenv("META_APP_SECRET", "")
DEFAULT_RESTAURANT_ID = 1
GRAPH_API_VERSION = "v21.0"
# Style: set BOT_NO_EMOJI=1 to disable emojis, BOT_STYLE=formal/casual to adjust tone
BOT_NO_EMOJI = os.getenv("BOT_NO_EMOJI", "1").lower() in ("1", "true", "yes")
BOT_BRAND = os.getenv("BOT_BRAND", "ReplyFlow by MadeReal")


def get_ai_reply(customer_phone: str, new_message: str, restaurant_id: int = DEFAULT_RESTAURANT_ID) -> tuple[str, int]:
    conv_id = db.get_or_create_conversation(restaurant_id, customer_phone)
    menu_text = db.get_menu_text(restaurant_id)
    history = db.get_conversation_history(conv_id)
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history) or "(no previous messages)"

    no_emoji = " Do NOT use emojis. Plain text only." if BOT_NO_EMOJI else ""
    system = (
        "You are a friendly restaurant bot in Pakistan. Reply ONLY in Roman Urdu (Urdu written in English letters, "
        "how Pakistani people text: bhej do, bilkul, ji, bhai, thora teekha, jaldi, etc). "
        "Do NOT use Hindi/Hinglish. Use Pakistani Urdu slang and expressions. Keep it short. "
        f"If anyone asks who built you or who you work for, say '{BOT_BRAND}'."
        + no_emoji
        + " Use this menu to answer. If they order, confirm items and ask for address. Do not make up prices."
    )
    prompt = f"""Menu:
{menu_text}

Previous conversation:
{history_text}

Customer says: {new_message}

Reply (short, friendly):"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    reply = (response.text or "").strip()
    return reply, conv_id


def send_whatsapp_message(phone_number_id: str, to: str, text: str) -> bool:
    """Send reply via WhatsApp Cloud API."""
    if not WHATSAPP_TOKEN:
        log.warning("WHATSAPP_ACCESS_TOKEN not set")
        return False
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to.lstrip("+"),
        "type": "text",
        "text": {"body": text},
    }
    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        log.exception("WhatsApp send failed: %s", e)
        return False


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify X-Hub-Signature-256 using app secret."""
    if not APP_SECRET or not signature:
        return True
    expected = "sha256=" + hmac.new(APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_webhook(data: dict) -> list[dict]:
    """Extract messages from Cloud API. Each item: {from, text?, audio_id?, phone_number_id, mime_type?}."""
    result = []
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = str(value.get("metadata", {}).get("phone_number_id", ""))
            for msg in value.get("messages", []):
                from_num = str(msg.get("from", ""))
                if not from_num or not phone_number_id:
                    continue
                msg_type = msg.get("type", "")
                if msg_type == "text":
                    body = (msg.get("text", {}) or {}).get("body", "").strip()
                    if body:
                        result.append({"from": from_num, "text": body, "phone_number_id": phone_number_id})
                elif msg_type == "audio" or msg_type == "voice":
                    audio = msg.get("audio") or msg.get("voice") or {}
                    media_id = audio.get("id")
                    mime = audio.get("mime_type", "audio/ogg")
                    if media_id:
                        result.append({
                            "from": from_num,
                            "audio_id": str(media_id),
                            "phone_number_id": phone_number_id,
                            "mime_type": mime,
                        })
    return result


def download_media(media_id: str) -> bytes | None:
    """Download media from WhatsApp Cloud API."""
    if not WHATSAPP_TOKEN:
        return None
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}"
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        media_url = data.get("url")
        if not media_url:
            return None
        r2 = requests.get(media_url, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=15)
        r2.raise_for_status()
        return r2.content
    except Exception as e:
        log.exception("Download media failed: %s", e)
        return None


def transcribe_and_reply(customer_phone: str, audio_bytes: bytes, mime_type: str) -> tuple[str, int]:
    """Transcribe voice with Gemini and get bot reply."""
    conv_id = db.get_or_create_conversation(DEFAULT_RESTAURANT_ID, customer_phone)
    menu_text = db.get_menu_text(DEFAULT_RESTAURANT_ID)
    history = db.get_conversation_history(conv_id)
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history) or "(no previous messages)"
    no_emoji = " Do NOT use emojis. Plain text only." if BOT_NO_EMOJI else ""
    instr = (
        "You are a friendly restaurant bot in Pakistan. Reply ONLY in Roman Urdu (Pakistani style: bhej do, bilkul, ji, bhai). "
        f"Do NOT use Hindi/Hinglish or emojis. Keep it short. If anyone asks who built you, say '{BOT_BRAND}'."
        + no_emoji
        + "\n\nMenu:\n" + menu_text
        + "\n\nPrevious conversation:\n" + history_text
        + "\n\nA customer sent a VOICE MESSAGE. Transcribe what they said (Urdu/Roman Urdu/English) and reply as the bot. "
        "Output format: first line = transcribed text, blank line, then your reply."
    )
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            instr,
        ],
    )
    out = (response.text or "").strip()
    lines = out.split("\n")
    transcribed = ""
    reply = out
    for i, line in enumerate(lines):
        if line.strip() == "" and i > 0:
            transcribed = "\n".join(lines[:i]).strip()
            reply = "\n".join(lines[i + 1 :]).strip()
            break
    if not transcribed:
        transcribed = lines[0] if lines else "(voice)"
    if not reply:
        reply = "Sun nahi paya, phir se likh ke bhejo ya bolo."
    return reply, conv_id


@app.route("/webhook", methods=["GET"])
def webhook_verify():
    """Meta sends GET to verify the webhook. Return hub.challenge if verify_token matches."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN and challenge:
        return challenge
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    """Meta sends POST with incoming messages. Reply using Gemini."""
    raw = request.get_data()
    sig = request.headers.get("X-Hub-Signature-256", "")
    log.info("Webhook POST received")
    if not verify_signature(raw, sig):
        log.warning("Invalid webhook signature")
        return "Bad signature", 403

    try:
        data = request.get_json() or {}
    except Exception as e:
        log.warning("Webhook JSON parse failed: %s", e)
        data = {}

    messages = parse_webhook(data)
    log.info("Parsed %d message(s) from webhook", len(messages))
    if not messages:
        log.info("Webhook payload keys: %s", list(data.keys()) if data else "empty")

    for msg in messages:
        customer_phone = msg["from"]
        phone_number_id = msg["phone_number_id"]
        try:
            if "text" in msg:
                text = msg["text"]
                log.info("Message from %s: %s", customer_phone, text[:50])
                reply, conv_id = get_ai_reply(customer_phone, text)
                db.save_message(conv_id, "user", text)
                db.save_message(conv_id, "bot", reply)
                ok = send_whatsapp_message(phone_number_id, customer_phone, reply)
                log.info("WhatsApp send: %s", "ok" if ok else "FAILED")
            elif "audio_id" in msg:
                audio_bytes = download_media(msg["audio_id"])
                if audio_bytes:
                    log.info("Voice from %s", customer_phone)
                    reply, conv_id = transcribe_and_reply(
                        customer_phone, audio_bytes, msg.get("mime_type", "audio/ogg")
                    )
                    db.save_message(conv_id, "user", "[voice message]")
                    db.save_message(conv_id, "bot", reply)
                    ok = send_whatsapp_message(phone_number_id, customer_phone, reply)
                    log.info("WhatsApp send: %s", "ok" if ok else "FAILED")
                else:
                    log.warning("Could not download voice from %s", customer_phone)
        except Exception as e:
            log.exception("Error handling message from %s: %s", customer_phone, e)

    return "", 200


if __name__ == "__main__":
    if not GEMINI_API_KEY:
        raise SystemExit("Set GEMINI_API_KEY in .env")
    if not WHATSAPP_TOKEN:
        log.warning("WHATSAPP_ACCESS_TOKEN not set – webhook will verify but won't send replies")
    db.init_db()
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
