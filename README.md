# Phase – WhatsApp bot & AI guides

## Project structure

| Path | What it is |
|------|------------|
| **whatsapp_cloud/** | **Main WhatsApp bot** – Flask app, WhatsApp Cloud API, Gemini/DeepSeek, SQLite. Deploy this (e.g. Railway). |
| **week2/** | Lesson: Gemini API reply script + checklist. |
| **week3/** | Lesson: Webhook app (WATI-style), local testing, DB. |
| **COMPLETE_GIGA_AI_GUIDE.pdf** | Giga AI guide (PDF). |
| **WEEK_1_*.md**, **FREE_AI_SETUP.md**, **WHAT'S_NEXT.md** | Week 1 and setup guides. |

## Quick start (bot)

- `.env` in the **phase** folder (parent of `whatsapp_cloud`) with `GEMINI_API_KEY`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, etc. See `whatsapp_cloud/.env.example`.
- Run: `cd whatsapp_cloud && pip install -r requirements.txt && python app.py`
- Optional: `AI_PROVIDER=deepseek` and `DEEPSEEK_API_KEY` for more quota.

## Secrets

- Do not commit `.env`. It is listed in `.gitignore`.
