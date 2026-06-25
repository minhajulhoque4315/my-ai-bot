import os
import json
import logging
import anthropic
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Per-user conversation history & data store
user_data = {}

SYSTEM_PROMPT = """তুমি একজন বাংলাদেশী ব্যক্তির ব্যক্তিগত AI সহকারী। তুমি বাংলায় কথা বলো।

তুমি নিচের কাজগুলো করতে পারো:
1. পড়াশোনা: নোট বানানো, সারাংশ করা, প্রশ্ন তৈরি করা, বুঝিয়ে দেওয়া
2. টাকার হিসাব: খরচ ও আয় ট্র্যাক করা, বিশ্লেষণ করা
3. জব টাস্ক: ইমেইল লেখা, রিপোর্ট বানানো, পরিকল্পনা করা
4. রিমাইন্ডার: কাজের তালিকা তৈরি ও মনে করিয়ে দেওয়া
5. যেকোনো সাধারণ প্রশ্নের উত্তর দেওয়া

তুমি সবসময় বাংলায় উত্তর দেবে। সংক্ষিপ্ত ও কার্যকর উত্তর দেবে।

যখন কেউ টাকার হিসাব বলবে (যেমন: "বাজারে ৫০০ টাকা খরচ হলো"), তুমি সেটা লিস্টে যোগ করবে বলে জানাবে।
যখন কেউ রিমাইন্ডার চাইবে (যেমন: "কাল ডাক্তারের কাছে যেতে মনে করিয়ে দাও"), সেটা নোট করবে।

সর্বদা বন্ধুত্বপূর্ণ ও সহায়ক থাকো।"""

def get_user_context(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {
            "history": [],
            "transactions": [],
            "tasks": [],
            "reminders": []
        }
    return user_data[user_id]

def build_context_message(ctx: dict) -> str:
    parts = []
    if ctx["transactions"]:
        parts.append("📊 লেনদেনের তালিকা:\n" + "\n".join(
            f"- {t['type']}: {t['desc']} = ৳{t['amount']}" for t in ctx["transactions"][-10:]
        ))
    if ctx["tasks"]:
        parts.append("✅ কাজের তালিকা:\n" + "\n".join(
            f"- {'[সম্পন্ন]' if t['done'] else '[বাকি]'} {t['text']}" for t in ctx["tasks"][-10:]
        ))
    return "\n\n".join(parts) if parts else ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"আস্সালামু আলাইকুম {user.first_name}! 👋\n\n"
        "আমি আপনার ব্যক্তিগত AI সহকারী। আমাকে বলুন:\n\n"
        "📚 *পড়াশোনা* — 'এই টপিকটা বুঝিয়ে দাও'\n"
        "💰 *টাকার হিসাব* — 'বাজারে ৳৫০০ খরচ হলো'\n"
        "💼 *জব টাস্ক* — 'বসকে ইমেইল লিখে দাও'\n"
        "⏰ *রিমাইন্ডার* — 'কালকের কাজ মনে করিয়ে দাও'\n\n"
        "যেকোনো কিছু জিজ্ঞেস করুন! 🤖",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *আমি যা করতে পারি:*\n\n"
        "• যেকোনো বিষয় সারাংশ বা নোট করতে\n"
        "• আয়-ব্যয়ের হিসাব রাখতে\n"
        "• ইমেইল ও রিপোর্ট লিখতে\n"
        "• কাজের তালিকা বানাতে\n"
        "• যেকোনো প্রশ্নের উত্তর দিতে\n\n"
        "/summary — খরচের সারাংশ দেখুন\n"
        "/tasks — কাজের তালিকা দেখুন\n"
        "/clear — সব ডেটা মুছুন\n",
        parse_mode="Markdown"
    )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    transactions = ctx["transactions"]
    if not transactions:
        await update.message.reply_text("এখনো কোনো লেনদেন নেই। বলুন কত খরচ হলো!")
        return
    income = sum(t["amount"] for t in transactions if t["type"] == "আয়")
    expense = sum(t["amount"] for t in transactions if t["type"] == "খরচ")
    balance = income - expense
    text = "💰 *আপনার হিসাবের সারাংশ*\n\n"
    text += f"📈 মোট আয়: ৳{income:,.0f}\n"
    text += f"📉 মোট খরচ: ৳{expense:,.0f}\n"
    text += f"💵 ব্যালেন্স: ৳{balance:,.0f}\n\n"
    text += "*সাম্প্রতিক লেনদেন:*\n"
    for t in transactions[-5:]:
        sign = "+" if t["type"] == "আয়" else "-"
        text += f"{sign}৳{t['amount']:,.0f} — {t['desc']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    tasks = ctx["tasks"]
    if not tasks:
        await update.message.reply_text("কাজের তালিকা খালি! নতুন কাজ যোগ করুন।")
        return
    text = "✅ *আপনার কাজের তালিকা*\n\n"
    for i, t in enumerate(tasks, 1):
        status = "✓" if t["done"] else "○"
        text += f"{status} {i}. {t['text']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"history": [], "transactions": [], "tasks": [], "reminders": []}
    await update.message.reply_text("✅ সব ডেটা মুছে ফেলা হয়েছে।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    ctx = get_user_context(user_id)

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Build messages with history
    context_info = build_context_message(ctx)
    system = SYSTEM_PROMPT
    if context_info:
        system += f"\n\n[বর্তমান ডেটা]\n{context_info}"

    ctx["history"].append({"role": "user", "content": user_message})
    # Keep last 20 messages only
    history = ctx["history"][-20:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=system,
            messages=history
        )
        reply = response.content[0].text
        ctx["history"].append({"role": "assistant", "content": reply})

        # Auto-detect and store transactions
        keywords_expense = ["খরচ", "কিনলাম", "দিলাম", "পেমেন্ট", "বিল"]
        keywords_income = ["পেলাম", "আয়", "বেতন", "ইনকাম", "পাওয়া"]
        import re
        amount_match = re.search(r"[৳\$]?\s*(\d[\d,]*)", user_message)
        if amount_match:
            amount = float(amount_match.group(1).replace(",", ""))
            if any(k in user_message for k in keywords_expense):
                ctx["transactions"].append({"type": "খরচ", "desc": user_message[:50], "amount": amount, "date": datetime.now().strftime("%d/%m")})
            elif any(k in user_message for k in keywords_income):
                ctx["transactions"].append({"type": "আয়", "desc": user_message[:50], "amount": amount, "date": datetime.now().strftime("%d/%m")})

        # Auto-detect tasks
        task_keywords = ["করতে হবে", "মনে করিয়ে", "রিমাইন্ডার", "ভুলবো না", "task", "টাস্ক"]
        if any(k in user_message for k in task_keywords):
            ctx["tasks"].append({"text": user_message[:80], "done": False, "date": datetime.now().strftime("%d/%m")})

        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("দুঃখিত, একটা সমস্যা হয়েছে। আবার চেষ্টা করুন।")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot চালু হচ্ছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
