# Week 3 – WhatsApp bot (WATI + Gemini + DB)

Real bot: customer sends WhatsApp message → WATI webhook → your server → Gemini → reply sent back via WATI. All conversations and menu stored in SQLite.

---

## 1. Env

In the **phase** folder (parent of week3), your `.env` should have:

- `GEMINI_API_KEY` – you have this.
- `WATI_API_KEY` – from [wati.io](https://wati.io) → **More → API Docs** (copy API key and endpoint).
- `WATI_API_ENDPOINT` – optional; default is `https://live-mt-server.wati.io`.

Add to `.env`:

```env
WATI_API_KEY=your_key_here
WATI_API_ENDPOINT=https://live-mt-server.wati.io
```

---

## 2. Install and run locally

```bash
cd week3
pip install -r requirements.txt
python app.py
```

Server runs at `http://localhost:5000`. DB file: `week3/bot.db` (created on first run, with a default restaurant and sample menu).

---

## 3. Expose the webhook (so WATI can call you)

WATI must send “message received” to a **public URL**. Options:

- **ngrok:** `ngrok http 5000` → use the `https://...` URL as webhook.
- **Railway:** Deploy this app to Railway, then use `https://your-app.railway.app/webhook/wati` as webhook.

In WATI: **More → Webhooks** → add URL `https://YOUR_PUBLIC_URL/webhook/wati` → enable “Message received”.

---

## 4. Test

- Send a WhatsApp message to your WATI-connected number (e.g. “menu dikhao” or “2 biryani chahiye”).
- WATI POSTs to `/webhook/wati` → app gets reply from Gemini and sends it back via WATI.
- Check server logs and `bot.db` (conversations, messages).

---

## 5. Default data

- One restaurant (id=1) with sample menu: Chicken Biryani Rs.350, Mutton Biryani Rs.450, Raita Rs.50.
- To add more items or restaurants, use SQLite or we can add a small admin script later.

---

## 6. Next (Week 4 / later)

- Deploy to Railway (same repo, add `Procfile` or start command: `python app.py`).
- Add a simple dashboard (e.g. Vercel + Next.js) to view conversations and edit menu.
- Map multiple WATI numbers to different restaurants (env or DB).
