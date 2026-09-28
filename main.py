# -*- coding: utf-8 -*-
"""
ربات دیکشنری پیشرفته روبیکا - نسخه RoboBot
"""

import os
import json
import random
import requests
from robobot import Bot

# ==================================================
# تنظیمات
# ==================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID") or "0")

if not BOT_TOKEN:
    raise ValueError("توکن ربات یافت نشد!")

bot = Bot(BOT_TOKEN)

WORDS_FILE = "words.json"
RESPONSES_FILE = "responses.json"
CHAT_FOLDER = "chat"
LEARNED_FILE = "learned.json"

# ==================================================
# توابع لود و ذخیره
# ==================================================
def load_json(filename, default=None):
    if default is None:
        default = {}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"خطا در لود {filename}: {e}")
            return default
    return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"خطا در ذخیره {filename}: {e}")
        return False


# ==================================================
# لود دیتا
# ==================================================
WORDS = load_json(WORDS_FILE)
RESPONSES = load_json(RESPONSES_FILE)
LEARNED = load_json(LEARNED_FILE)

CHAT_DATA = {}
BAD_WORDS = []

if os.path.exists(CHAT_FOLDER):
    for filename in os.listdir(CHAT_FOLDER):
        if filename.endswith(".json"):
            data = load_json(os.path.join(CHAT_FOLDER, filename))
            for key, value in data.items():
                if key == "bad_words":
                    BAD_WORDS = value
                else:
                    CHAT_DATA[key] = value

print(f"✅ {len(WORDS)} کلمه لود شد")
print(f"✅ {len(RESPONSES)} پاسخ عمومی لود شد")
print(f"✅ {len(CHAT_DATA)} دسته چت لود شد")
print(f"✅ {len(BAD_WORDS)} کلمه ممنوعه لود شد")


# ==================================================
# توابع ترجمه
# ==================================================
def translate_api(word, source="en", target="fa"):
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": word, "langpair": f"{source}|{target}"}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("responseStatus") == 200:
            result = data["responseData"]["translatedText"]
            if result and result.lower() != word.lower():
                return result
        return None
    except Exception as e:
        print(f"خطا در ترجمه API: {e}")
        return None


def get_translation(word):
    word_lower = word.lower().strip()
    if word_lower in WORDS:
        return WORDS[word_lower], "دیکشنری محلی"
    if word_lower in LEARNED:
        return LEARNED[word_lower], "یادگرفته شده"
    result = translate_api(word_lower, "en", "fa")
    if result:
        return result, "API"
    result = translate_api(word, "fa", "en")
    if result:
        return result, "API"
    return None, None


# ==================================================
# فیلتر فحش
# ==================================================
def contains_bad_word(text):
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word.lower() in text_lower:
            return True
    return False


# ==================================================
# توابع پردازش
# ==================================================
async def handle_chat_response(text, chat_id, bot):
    if text in RESPONSES:
        response_list = RESPONSES[text]
        response = random.choice(response_list) if isinstance(response_list, list) else response_list
        await bot.send_message(chat_id, response)
        return True
    
    for category, responses in CHAT_DATA.items():
        if text == category or category in text:
            response = random.choice(responses) if isinstance(responses, list) else responses
            await bot.send_message(chat_id, response)
            return True
    
    return False


async def handle_translation(text, chat_id, bot):
    if " " in text or len(text) > 30:
        return False
    
    translation, source = get_translation(text)
    if translation:
        result_text = f"📖 {text}\n\n🔤 ترجمه: {translation}\n\n📌 منبع: {source}"
        await bot.send_message(chat_id, result_text)
        return True
    return False


async def handle_learn_command(text, chat_id, bot):
    if not text.startswith("/learn"):
        return False
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await bot.send_message(chat_id, "❌ فرمت: /learn english معنی")
        return True
    english_word = parts[1].lower().strip()
    persian_meaning = parts[2].strip()
    LEARNED[english_word] = persian_meaning
    save_json(LEARNED_FILE, LEARNED)
    await bot.send_message(chat_id, f"✅ {english_word} = {persian_meaning}")
    return True


async def handle_help_command(text, chat_id, bot):
    if text != "/help":
        return False
    help_text = "📚 راهنمای ربات\n\n🔤 ترجمه: فقط کلمه رو بفرست\n📝 آموزش کلمه: /learn apple سیب\n📊 آمار: /stats\n\n💕 دسته‌های چت:\nعاشقانه، دلبرانه، ناز، جوک، تبریک، تسلیت، تشکر، خانواده، کمک، متفرقه"
    await bot.send_message(chat_id, help_text)
    return True


async def handle_stats_command(text, chat_id, bot):
    if text != "/stats":
        return False
    stats_text = f"📊 آمار ربات:\n\n📖 کلمات دیکشنری: {len(WORDS)}\n💬 پاسخ‌های عمومی: {len(RESPONSES)}\n💕 دسته‌های چت: {len(CHAT_DATA)}\n🧠 کلمات یادگرفته: {len(LEARNED)}\n🚫 کلمات ممنوعه: {len(BAD_WORDS)}"
    await bot.send_message(chat_id, stats_text)
    return True


# ==================================================
# هندلر اصلی پیام
# ==================================================
@bot.on_message()
async def handle_message(bot, message):
    try:
        chat_id = message.chat_id if hasattr(message, 'chat_id') else None
        
        if chat_id is None:
            print("⚠️ chat_id پیدا نشد")
            return
        
        if ALLOWED_GROUP_ID != 0 and chat_id != ALLOWED_GROUP_ID:
            return
        
        text = message.text.strip() if hasattr(message, 'text') and message.text else None
        if not text:
            return
        
        # ۱. فیلتر فحش
        if contains_bad_word(text):
            await bot.send_message(chat_id, "🚫 این پیام به دلیل کلمات نامناسب حذف شد.")
            return
        
        # ۲. دستورات
        if await handle_help_command(text, chat_id, bot):
            return
        if await handle_stats_command(text, chat_id, bot):
            return
        if await handle_learn_command(text, chat_id, bot):
            return
        
        # ۳. پاسخ‌های چت
        if await handle_chat_response(text, chat_id, bot):
            return
        
        # ۴. ترجمه
        if await handle_translation(text, chat_id, bot):
            return
    
    except Exception as e:
        print(f"❌ خطا در هندلر: {e}")
        import traceback
        traceback.print_exc()


# ==================================================
# اجرا
# ==================================================
if __name__ == "__main__":
    print("🤖 ربات در حال اجراست...")
    bot.run()
