# Paste this in WATI (one-time setup)

Your bot and ngrok are running. Do this once:

---

## 1. Open WATI Webhooks

- Go to: **https://app.wati.io** (log in if needed)
- Click **More** (or **Settings**) in the sidebar
- Click **Webhooks**

---

## 2. Add this Webhook URL

Copy this **entire line** and paste it in the "Webhook URL" or "Callback URL" field:

```
https://readier-boris-monographically.ngrok-free.dev/webhook/wati
```

---

## 3. Enable the right event

- Turn **ON** the event for **"Message received"** (or "Messages" → "Incoming message")
- Save / Update

---

## 4. Test on WhatsApp

Send a message to your WATI WhatsApp number:

- **menu dikhao**
- or **2 biryani chahiye**

You should get a reply from the bot.

---

**Note:** If you restart ngrok, the URL may change (free plan). If the bot stops replying, run `ngrok http 5000` again, copy the new **https** URL from the ngrok window, and update the webhook in WATI to:

`https://NEW_URL/webhook/wati`
