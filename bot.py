import os
import re
import logging
from datetime import datetime
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

user_data = {}

SYSTEM_PROMPT = """তুমি একজন বাংলাদেশী ব্যক্তির ব্যক্তিগত AI সহকারী। তুমি সবসময় বাংলায় কথা বলো।

তুমি নিচের কাজগুলো করতে পারো:
1. পড়াশোনা: নোট বানানো, সারাংশ করা, প্রশ্ন তৈরি করা, বুঝিয়ে দেওয়া
2. টাকার হিসাব: খরচ ও আয় ট্র্যাক করা, বিশ্লেষণ করা
3. জব টাস্ক: ইমেইল লেখা, রিপোর্ট বানানো, পরিকল্পনা করা
4. রিমাইন্ডার: কাজের তালিকা তৈরি করা
5. যেকোনো সাধারণ প্রশ্নের উত্তর দেওয়া

সবসময় সংক্ষিপ্ত ও কার্যকর উত্তর দেবে। বন্ধুত্বপূর্ণ থাকবে।"""

def get_user_context(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "history": [],
            "transactions": [],
            "tasks": []
        }
    return user_data[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"আস্সালামু আলাইকুম {user.first_name}! 👋\n\n"
        "আমি আপনার ব্যক্তিগত AI সহকারী। আমাকে বলুন:\n\n"
        "📚 পড়াশোনা — 'এই টপিকটা বুঝিয়ে দাও'\n"
        "💰 টাকার হিসাব — 'বাজারে ৳৫০০ খরচ হলো'\n"
        "💼 জব টাস্ক — 'বসকে ইমেইল লিখে দাও'\n"
        "✅ রিমাইন্ডার — 'কালকের কাজ মনে করিয়ে দাও'\n\n"
        "যেকোনো কিছু জিজ্ঞেস করুন! 🤖"
    )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    transactions = ctx["transactions"]
    if not transactions:
        await update.message.reply_text("এখনো কোনো লেনদেন নেই।")
        return
    income = sum(t["amount"] for t in transactions if t["type"] == "আয়")
    expense = sum(t["amount"] for t in transactions if t["type"] == "খরচ")
    balance = income - expense
    text = "💰 *হিসাবের সারাংশ*\n\n"
    text += f"📈 মোট আয়: ৳{income:,.0f}\n"
    text += f"📉 মোট খরচ: ৳{expense:,.0f}\n"
    text += f"💵 ব্যালেন্স: ৳{balance:,.0f}\n\n*সাম্প্রতিক:*\n"
    for t in transactions[-5:]:
        sign = "+" if t["type"] == "আয়" else "-"
        text += f"{sign}৳{t['amount']:,.0f} — {t['desc']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ctx = get_user_context(user_id)
    tasks = ctx["tasks"]
    if not tasks:
        await update.message.reply_text("কাজের তালিকা খালি!")
        return
    text = "✅ *কাজের তালিকা*\n\n"
    for i, t in enumerate(tasks, 1):
        status = "✓" if t["done"] else "○"
        text += f"{status} {i}. {t['text']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"history": [], "transactions": [], "tasks": []}
    await update.message.reply_text("✅ সব ডেটা মুছে ফেলা হয়েছে।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    ctx = get_user_context(user_id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Build history for context
    history_text = ""
    for h in ctx["history"][-10:]:
        role = "ব্যবহারকারী" if h["role"] == "user" else "সহকারী"
        history_text += f"{role}: {h['content']}\n"

    # Add stored data as context
    extra = ""
    if ctx["transactions"]:
        extra += "\n[লেনদেন তালিকা]\n" + "\n".join(
            f"- {t['type']}: {t['desc']} ৳{t['amount']}" for t in ctx["transactions"][-10:]
        )
    if ctx["tasks"]:
        extra += "\n[কাজের তালিকা]\n" + "\n".join(
            f"- {'সম্পন্ন' if t['done'] else 'বাকি'}: {t['text']}" for t in ctx["tasks"][-10:]
        )

    full_prompt = f"{SYSTEM_PROMPT}{extra}\n\n[কথোপকথন]\n{history_text}ব্যবহারকারী: {user_message}\nসহকারী:"

    try:
        response = model.generate_content(full_prompt)
        reply = response.text

        ctx["history"].append({"role": "user", "content": user_message})
        ctx["history"].append({"role": "assistant", "content": reply})

        # Auto-detect transactions
        amount_match = re.search(r"[৳\$]?\s*(\d[\d,]*)", user_message)
        if amount_match:
            amount = float(amount_match.group(1).replace(",", ""))
            if any(k in user_message for k in ["খরচ", "কিনলাম", "দিলাম", "পেমেন্ট", "বিল"]):
                ctx["transactions"].append({"type": "খরচ", "desc": user_message[:50], "amount": amount, "date": datetime.now().strftime("%d/%m")})
            elif any(k in user_message for k in ["পেলাম", "আয়", "বেতন", "ইনকাম"]):
                ctx["transactions"].append({"type": "আয়", "desc": user_message[:50], "amount": amount, "date": datetime.now().strftime("%d/%m")})

        # Auto-detect tasks
        if any(k in user_message for k in ["করতে হবে", "মনে করিয়ে", "রিমাইন্ডার", "ভুলবো না"]):
            ctx["tasks"].append({"text": user_message[:80], "done": False})

        await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("দুঃখিত, একটু সমস্যা হয়েছে। আবার চেষ্টা করুন।")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot চালু হচ্ছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
