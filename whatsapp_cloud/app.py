"""
WhatsApp Cloud API – Flask webhook. Receives messages, replies using Groq only.
"""
import os
import time
import hmac
import hashlib
import logging
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request

# Load .env from phase folder
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import requests

import db

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Config from env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token_123")
APP_SECRET = os.getenv("META_APP_SECRET", "")
DEFAULT_RESTAURANT_ID = 1
GRAPH_API_VERSION = "v21.0"
BOT_NO_EMOJI = os.getenv("BOT_NO_EMOJI", "1").lower() in ("1", "true", "yes")
BOT_BRAND = os.getenv("BOT_BRAND", "ReplyFlow by MadeReal")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")


def _get_system_and_user_prompt(menu_text: str, history_text: str, new_message: str) -> tuple[str, str]:
    no_emoji = " Do NOT use emojis. Plain text only." if BOT_NO_EMOJI else ""
    system = (
        "You are a friendly restaurant bot in Pakistan. You MUST reply in Roman Urdu (Urdu in English letters: bhej do, bilkul, ji, bhai, thora teekha, jaldi). "
        "Roman Urdu is your FIRST and ONLY default language. Start every reply in Roman Urdu. "
        "Only if the customer writes ONLY in English (no Urdu words), you may reply in English. Otherwise always Roman Urdu. "
        "Do NOT use Hindi/Hinglish. Use Pakistani Urdu slang. Keep it short. "
        f"If anyone asks who built you, say '{BOT_BRAND}'."
        + no_emoji
        + " Use this menu only. If they order, confirm and ask address. Do not make up prices."
    )
    user = f"""Menu:
{menu_text}

Previous conversation:
{history_text}

Customer says: {new_message}

Reply (short, friendly):"""
    return system, user


def _get_ai_reply_groq(system: str, user: str) -> str:
    """Call Groq chat API (free tier, OpenAI-compatible)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 512,
    }
    for attempt in range(2):
        try:
            r = requests.post(url, json=body, headers=headers, timeout=60)
            if r.status_code == 429 and attempt == 0:
                log.warning("Groq rate limit, retrying in 15s...")
                time.sleep(15)
                continue
            r.raise_for_status()
            data = r.json()
            reply = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return (reply or "Sorry, try again.").strip()
        except requests.RequestException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 429 and attempt == 0:
                time.sleep(15)
                continue
            log.exception("Groq API error: %s", e)
            return "Abhi response nahi aa raha, thori der baad try karo."
    return "Abhi response nahi aa raha, thori der baad try karo."


def get_ai_reply(customer_phone: str, new_message: str, restaurant_id: int = DEFAULT_RESTAURANT_ID) -> tuple[str, int]:
    conv_id = db.get_or_create_conversation(restaurant_id, customer_phone)
    menu_text = db.get_menu_text(restaurant_id)
    history = db.get_conversation_history(conv_id)
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history) or "(no previous messages)"
    system, user = _get_system_and_user_prompt(menu_text, history_text, new_message)
    reply = _get_ai_reply_groq(system, user)
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
        if r.status_code >= 400:
            log.error("WhatsApp API %s: %s", r.status_code, r.text)
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
    """Voice not supported with Groq-only; ask user to type."""
    conv_id = db.get_or_create_conversation(DEFAULT_RESTAURANT_ID, customer_phone)
    reply = "Abhi voice support nahi hai. Apna message likh ke bhejo, bilkul jaldi reply karunga."
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
    """Meta sends POST with incoming messages. Reply using Groq."""
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
    if not GROQ_API_KEY:
        raise SystemExit("Set GROQ_API_KEY in .env (get one at console.groq.com)")
    log.info("AI: Groq only (voice messages get a fixed reply)")
    if not WHATSAPP_TOKEN:
        log.warning("WHATSAPP_ACCESS_TOKEN not set – webhook will verify but won't send replies")
    db.init_db()
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
