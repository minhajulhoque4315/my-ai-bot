import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + (GEMINI_API_KEY or "")
)


def force_clear_telegram_session():
    """
    Forcibly kills any other getUpdates poller (old Railway deploy, local test run,
    accidental second process, leftover webhook, etc.) BEFORE this process tries to
    poll. This is what actually fixes '409 Conflict: terminated by other getUpdates
    request'. We hit the raw Bot API directly (not via the library) so this runs
    even before the Application object is built.
    """
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN missing, cannot clear session.")
        return

    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

    try:
        # 1. Remove any webhook AND drop queued updates tied to it.
        r = requests.post(f"{base}/deleteWebhook", json={"drop_pending_updates": True}, timeout=10)
        logger.info(f"deleteWebhook -> {r.status_code} {r.text}")
    except Exception as e:
        logger.warning(f"deleteWebhook failed: {e}")

    try:
        # 2. Calling getUpdates with a tiny timeout from THIS process claims the
        #    long-poll slot, which kicks out whatever stale process was holding it.
        r = requests.get(f"{base}/getUpdates", params={"timeout": 1, "offset": -1}, timeout=15)
        logger.info(f"getUpdates claim -> {r.status_code} {r.text[:200]}")
    except Exception as e:
        logger.warning(f"getUpdates claim failed: {e}")

    # Give Telegram's servers a moment to fully release the old session.
    import time
    time.sleep(2)


async def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "দুঃখিত, GEMINI_API_KEY সেট করা নেই। Railway Variables চেক করুন।"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "তুমি একজন সহায়ক ব্যক্তিগত AI অ্যাসিস্ট্যান্ট। বাংলায় উত্তর দাও, "
                            "সংক্ষিপ্ত ও কাজের মতো। ইমেইল/রিপোর্ট চাইলে সরাসরি লিখে দাও।\n\n"
                            f"ব্যবহারকারীর অনুরোধ: {prompt}"
                        )
                    }
                ]
            }
        ]
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        data = resp.json()
        if resp.status_code != 200:
            logger.error(f"Gemini error {resp.status_code}: {data}")
            return f"দুঃখিত, AI থেকে উত্তর পাওয়া যায়নি (কোড {resp.status_code})। কিছুক্ষণ পর আবার চেষ্টা করুন।"
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        logger.exception("Gemini call failed")
        return f"দুঃখিত, একটা সমস্যা হয়েছে: {e}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "হ্যালো! আমি আপনার পার্সোনাল AI সহকারী। 🤖\n\n"
        "আমাকে বলুন কী করতে হবে — যেমন:\n"
        "• 'বসকে ইমেইল লিখে দাও...'\n"
        "• '৫০০ টাকা বাজার খরচ হলো, হিসাব রাখো'\n"
        "• এই টেক্সটটার সারাংশ করো: ...\n\n"
        "যা বলবেন, চেষ্টা করব!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.chat.send_action("typing")
    reply = await call_gemini(user_text)
    await update.message.reply_text(reply)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


def main():
    if not TELEGRAM_TOKEN:
        raise SystemExit("TELEGRAM_TOKEN environment variable is missing.")

    # THE FIX: clear out any stale poller/webhook before we ever call run_polling.
    force_clear_telegram_session()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Starting bot polling...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
