# Week 1 Lesson – Taught by Your AI (No Videos Needed)

---

## Part 1: What is an API?

### The restaurant analogy

Imagine a **restaurant**:

- **You (the customer)** sit at the table. You want food. You don’t go into the kitchen. You don’t know how the stove works. You just tell the **waiter** what you want.
- The **waiter** is the link. They take your order to the **kitchen**. The kitchen cooks. The waiter brings the food back to you.
- You get what you wanted **without** having to cook or touch the kitchen.

An **API** is like that **waiter**.

- **You (your app)** want something: e.g. “Send this message to the customer” or “What did the customer just say?”
- You don’t talk to WhatsApp’s servers directly. You don’t talk to Claude’s brain directly. You talk to their **API**.
- The **API** takes your request, talks to the real system (WhatsApp’s servers, Claude’s model), and brings back the **response** to you.

So: **API = the waiter that lets your app “order” things from another service and get a “response” back.**

---

### Why it matters for your bot

Your bot will use **several** APIs:

| Service   | What you ask the API              | What the API gives you back        |
|----------|------------------------------------|------------------------------------|
| WhatsApp | “Send this text to this number”    | Done. Or: “Here’s the message we received.” |
| Claude   | “Here’s the menu, history, and new message. Reply as the restaurant bot.” | The bot’s reply text |
| (Later)  | Database                           | “Save this.” / “Give me this customer’s orders.” |

You don’t build WhatsApp. You don’t build Claude. You build **your small app** that **calls these APIs** in the right order. So understanding “API = waiter between you and another service” is enough for Week 1.

---

### One sentence

**An API is how your program asks another service (like WhatsApp or Claude) to do something and get a result back.**

---

## Part 2: WhatsApp Business API Basics

### What problem it solves

- Customers already use **WhatsApp** to message businesses (e.g. “2 biryani bhej do”).
- You want **your code** to see that message and reply (using Claude, your database, etc.).
- Your code runs on **your server** (e.g. Railway). WhatsApp runs on **Meta’s servers**. They need a safe, official way to talk. That way is the **WhatsApp Business API**.

So: **WhatsApp Business API = the official “waiter” between your server and WhatsApp.** Your server says “send this” or “what did we receive?” and the API does it.

---

### How the flow works (simple version)

1. **Customer** sends a WhatsApp message to the **business number** (e.g. Khan Biryani’s number).
2. **WhatsApp** receives it. Instead of a human opening the app, **WhatsApp** forwards that message to **your server** (using the API and a middleman like WATI).
3. **Your server** gets: “Message from +92…: bhai 2 biryani bhej do.”
4. Your server does its work (database, Claude, etc.) and decides the reply.
5. Your server tells the API: “Send this reply to +92…”
6. The API tells **WhatsApp** to deliver it. **Customer** sees the reply in WhatsApp.

So: **messages come IN through the API to your server, and replies go OUT from your server through the API to WhatsApp.** You never touch WhatsApp’s app; you only talk to the API.

---

### Important: you don’t use “personal WhatsApp”

- **Personal WhatsApp** = for humans. Using it with bots/automation can get the number **banned**.
- **WhatsApp Business API** = for businesses. You use it through a provider (e.g. WATI, Twilio). You get a business number (or use your existing business number). This is **allowed** and stable for your bot.

So for your project: **WhatsApp Business API via a provider (e.g. WATI)** = the right “door” for messages in and out.

---

### What you need to remember

1. **API** = your app talks to WhatsApp (and Claude, DB) through a “waiter” (the API).
2. **WhatsApp Business API** = the official way your server sends and receives WhatsApp messages.
3. **Flow:** Customer → WhatsApp → (API) → Your server → your logic (DB + Claude) → reply → (API) → WhatsApp → Customer.
4. Use **Business API** (e.g. via WATI), not personal WhatsApp, for the bot.

---

## You’re done with the “watching” part

You now know:

- What an API is (waiter between your app and other services).
- How WhatsApp Business API fits in (messages in/out for your bot, the right way).

Next in Week 1: create your accounts (Claude, Railway, Vercel) and do your 5 restaurant visits. Then Week 2: Cursor + first script.
