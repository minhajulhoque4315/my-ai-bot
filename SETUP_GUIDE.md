# 🤖 আপনার Personal AI Telegram Bot — সেটআপ গাইড

## ধাপ ১ — Anthropic API Key নিন (ফ্রি)

1. এই লিংকে যান: https://console.anthropic.com
2. Sign up করুন (Google দিয়েও হবে)
3. বাম মেনু থেকে **"API Keys"** ক্লিক করুন
4. **"Create Key"** বাটন চাপুন
5. Key টা কপি করে সেভ করুন (একবারই দেখাবে!)

---

## ধাপ ২ — GitHub-এ কোড আপলোড করুন

1. https://github.com যান, অ্যাকাউন্ট না থাকলে বানান
2. **"New repository"** বাটন চাপুন
3. নাম দিন: `my-ai-bot`
4. **"Create repository"** চাপুন
5. এই ৩টা ফাইল আপলোড করুন:
   - `bot.py`
   - `requirements.txt`
   - `railway.toml`

---

## ধাপ ৩ — Railway-তে Deploy করুন (ফ্রি)

1. https://railway.app যান
2. **"Login with GitHub"** দিয়ে ঢুকুন
3. **"New Project"** → **"Deploy from GitHub repo"** বেছে নিন
4. আপনার `my-ai-bot` রিপো বেছে নিন
5. Deploy শুরু হবে (৩০ সেকেন্ড লাগবে)

---

## ধাপ ৪ — Environment Variables যোগ করুন

Railway-তে আপনার প্রজেক্টে গিয়ে:

1. **"Variables"** ট্যাবে ক্লিক করুন
2. **"New Variable"** চাপুন এবং যোগ করুন:

```
TELEGRAM_TOKEN = আপনার_telegram_bot_token
ANTHROPIC_API_KEY = আপনার_anthropic_api_key
```

3. **"Deploy"** চাপুন

---

## ধাপ ৫ — Bot চালু করুন!

Telegram-এ আপনার বটে গিয়ে `/start` লিখুন।

---

## Bot-কে যা বলতে পারবেন:

| আপনি বলবেন | Bot কী করবে |
|-----------|------------|
| "বাজারে ৫০০ টাকা খরচ হলো" | হিসাবে যোগ করবে |
| "আজকের বেতন পেলাম ২০০০০" | আয় নোট করবে |
| "কাল ডাক্তার দেখাতে হবে মনে করিয়ে দাও" | টাস্কে যোগ করবে |
| "Photosynthesis বুঝিয়ে দাও" | সহজে ব্যাখ্যা করবে |
| "বসকে ইমেইল লিখে দাও প্রজেক্ট আপডেট দিয়ে" | ইমেইল লিখবে |
| `/summary` | খরচের সারাংশ দেখাবে |
| `/tasks` | কাজের তালিকা দেখাবে |
| `/clear` | সব ডেটা মুছবে |

---

## সমস্যা হলে?

Railway-তে **"Logs"** ট্যাব দেখুন। Claude-কে error message পাঠালে সাহায্য করবে।
