"""
WhatsApp Cloud API – Flask webhook. Receives messages, replies using Claude Haiku.
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

# Config from env – APIFree (proxy) or direct Anthropic
APIFREE_API_KEY = os.getenv("APIFREE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20250929")  # APIFree uses this; Anthropic uses claude-haiku-4-5
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token_123")
APP_SECRET = os.getenv("META_APP_SECRET", "")
DEFAULT_RESTAURANT_ID = 1
GRAPH_API_VERSION = "v21.0"
BOT_NO_EMOJI = os.getenv("BOT_NO_EMOJI", "1").lower() in ("1", "true", "yes")
BOT_BRAND = os.getenv("BOT_BRAND", "ReplyFlow by MadeReal")
BOT_HOURS = os.getenv("BOT_HOURS", "")
RESTAURANT_NAME = os.getenv("RESTAURANT_NAME", "Moon Kitchen")


def _get_system_and_user_prompt(menu_text: str, history_text: str, new_message: str) -> tuple[str, str]:
    emoji_rule = " Do NOT use emojis. Plain text only." if BOT_NO_EMOJI else " You may use emojis occasionally (😊👍🍛) but don't spam."
    hours_note = (
        f" We're open {BOT_HOURS}. If they ask and it's outside these hours, say we're closed and when we open."
        if BOT_HOURS else ""
    )
    system = f"""You are a friendly restaurant assistant for {RESTAURANT_NAME} in Karachi, Pakistan.

PERSONALITY:
- Talk like a real Pakistani person from Karachi, not a corporate bot
- Be warm, casual, and relatable - like talking to a friend
- Use Roman Urdu naturally mixed with English (code-switching)
- Use local expressions: "yaar", "bhai", "aho", "bilkul", "dekho", "tension na lo", "scene hai"
- Be helpful but never pushy or salesy
{emoji_rule}{hours_note}
- If they ask who made/built the bot, say "{BOT_BRAND}".

YOUR ROLE:
You take orders AND chat with customers. Both matter equally. You're a friendly neighborhood restaurant helper.

MENU:
The current menu (items and prices) is provided in the user message below. Use ONLY that menu. Do not make up items or prices.

CONVERSATION PHILOSOPHY:
1. ALWAYS respond to what the customer ACTUALLY said first
   - They say "kya haal hai" → respond about how you are, THEN talk about food
   - They say "bore ho raha" → sympathize first, THEN suggest food
   - They ask random stuff → answer it naturally, THEN gently redirect
   - NEVER ignore their message and robotically say "kya order karna hai"

2. Natural conversation flow matters more than rushing to orders
   - Let them chat 2-4 messages if they want. Build rapport before selling. Happy customer > quick order.

3. Guide to orders naturally, not forcefully
   - Use soft transitions: "Waise...", "By the way...", "Agar bhook lagi ho..."
   - Read their vibe - if they're just chatting, don't force orders
   - After 3-4 casual messages: "Waise agar order karna ho to batana, main yahan hi hoon!"

4. Handle ANY topic they bring up (weather, politics, random questions) with brief, human responses and light humor, then naturally redirect. Never say "I can only help with orders".

EXAMPLES OF YOUR STYLE:
- "bhai kya scene hai" → "Scene theek chal raha hai yaar, maze mein. Tum batao kya haal? Bhook to nahi lagi?"
- "yar bore ho raha hoon" → "Aho yaar, samajh sakta hoon. Kuch khao na phir, mood fresh bhi ho jaega."
- "tumhara naam kya hai" → "Main {RESTAURANT_NAME} ka assistant hoon bhai. Orders bhi le sakta hoon. Kya scene hai?"
- "menu dikhao" → Share the menu from below, then "Sab kuch fresh banta hai. Kya try karoge?"
- "2 chicken biryani" → "Shabash! Spicy ya mild pasand karoge?"
- When they give address → "Perfect! Order confirm. 30-40 min mein pohonch jaega. Payment COD?"
- "jaldi bhejna" → "Bilkul bhai! Jitni jaldi ho sake bhej dete hain. Chill karo."

CRITICAL RULES:
- NEVER be robotic or formal. NEVER repeat "kya order karna hai" like a broken record.
- NEVER ignore what customer said to jump to orders. NEVER be pushy.
- Always mix Urdu naturally. Never say "I don't know" - give human responses.
- RESPOND to their actual message first. BUILD rapport. USE humor. GUIDE gently, never push."""

    user = f"""Current menu (use only these items and prices):
{menu_text}

Chat so far:
{history_text}

Customer: {new_message}

Your reply (conversational, natural, in character):"""
    return system, user


def _call_claude(system: str, user_content: str) -> str:
    """Call Claude Haiku via APIFree (preferred) or direct Anthropic API."""
    if APIFREE_API_KEY:
        url = "https://api.apifree.com/v1/anthropic/claude-haiku-4-5/messages"
        headers = {
            "x-apifree-key": APIFREE_API_KEY,
            "Content-Type": "application/json",
        }
    else:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 512,
        "system": system,
        "messages": [{"role": "user", "content": [{"type": "text", "text": user_content}]}],
    }
    for attempt in range(2):
        try:
            r = requests.post(url, json=body, headers=headers, timeout=60)
            if r.status_code == 429 and attempt == 0:
                log.warning("Claude rate limit, retrying in 20s...")
                time.sleep(20)
                continue
            if r.status_code == 400:
                try:
                    err_body = r.json()
                    log.error("Claude 400 Bad Request: %s", err_body)
                except Exception:
                    log.error("Claude 400 response: %s", r.text[:500])
                return "Abhi response nahi aa raha, thori der baad try karo."
            r.raise_for_status()
            data = r.json()
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return (block.get("text") or "").strip()
            return "Sorry, try again."
        except requests.RequestException as e:
            if attempt == 0:
                resp = getattr(e, "response", None)
                if resp is not None and resp.status_code == 429:
                    time.sleep(20)
                    continue
            log.exception("Claude API error: %s", e)
            return "Abhi response nahi aa raha, thori der baad try karo."
    return "Abhi response nahi aa raha, thori der baad try karo."


def get_ai_reply(customer_phone: str, new_message: str, restaurant_id: int = DEFAULT_RESTAURANT_ID) -> tuple[str, int]:
    conv_id = db.get_or_create_conversation(restaurant_id, customer_phone)
    menu_text = db.get_menu_text(restaurant_id)
    history = db.get_conversation_history(conv_id)
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history) or "(no previous messages)"
    system, user = _get_system_and_user_prompt(menu_text, history_text, new_message)
    reply = _call_claude(system, user)
    return reply or "Sorry, try again.", conv_id


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
    """Voice: Claude doesn't accept audio here – ask user to type."""
    conv_id = db.get_or_create_conversation(DEFAULT_RESTAURANT_ID, customer_phone)
    reply = "Abhi voice support nahi hai, apna message likh ke bhejo bilkul jaldi reply karunga."
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
    """Meta sends POST with incoming messages. Reply using Claude Haiku."""
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
    if not APIFREE_API_KEY and not ANTHROPIC_API_KEY:
        raise SystemExit("Set APIFREE_API_KEY (apifree.com) or ANTHROPIC_API_KEY in .env")
    log.info("AI: Claude Haiku via %s (%s)", "APIFree" if APIFREE_API_KEY else "Anthropic", CLAUDE_MODEL)
    if not WHATSAPP_TOKEN:
        log.warning("WHATSAPP_ACCESS_TOKEN not set – webhook will verify but won't send replies")
    db.init_db()
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
