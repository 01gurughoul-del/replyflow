# Week 2 – First Code (Gemini Reply)

**Goal:** You have a script that sends a message to Gemini and prints the AI’s reply. Same flow as the bot will use later (message in → AI → reply out). No WhatsApp yet.

Your `.env` stays in the **phase** folder; this script loads it from there.

---

## Step 1: Install dependencies

In a terminal, from the **week2** folder:

```bash
cd week2
pip install -r requirements.txt
```

Or from **phase**:

```bash
pip install -r week2/requirements.txt
```

---

## Step 2: Run the script

From the **week2** folder:

```bash
cd week2
python week2_gemini_reply.py
```

- It will ask you to type a message. Type something like: **menu dikhao** or **2 biryani chahiye**
- Or press Enter to use the demo message: "bhai 2 biryani chahiye"
- You should see Gemini’s reply in Roman Urdu / English.

If you see an error: copy the full error, paste it in Cursor, and ask: “Fix this error in week2_gemini_reply.py”.

---

## Step 3: What you proved

- Your **.env** (in phase folder) is loaded and **GEMINI_API_KEY** works.
- **Message in → Gemini API → reply out.** This is the same flow your WhatsApp bot will use later (then we’ll add WhatsApp and a database).

---

## Next (Week 3–4)

- Add WhatsApp (e.g. WATI) so real messages hit your server.
- Add a database for menus and orders.
- Or we can do that step-by-step when you’re ready.
