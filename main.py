# -*- coding: utf-8 -*-
"""
ربات دیکشنری پیشرفته روبیکا
قابلیت‌ها:
- ترجمه کلمات
- پاسخ‌های چت (عاشقانه، دلبرانه، ناز دخترانه)
- فیلتر فحش
- تلفظ صوتی (TTS)
- سیستم آموزش کلمات
"""

import os
import json
import random
import requests
from rubka import Robot
from rubka.context import Message

# ==================================================
# تنظیمات اولیه
# ==================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_GROUP_ID = int(os.getenv("ALLOWED_GROUP_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("توکن ربات یافت نشد! BOT_TOKEN رو توی Railway تنظیم کن.")

bot = Robot(token=BOT_TOKEN)

# فایل‌ها
WORDS_FILE = "words.json"
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


# لود دیتا
WORDS = load_json(WORDS_FILE)
LEARNED = load_json(LEARNED_FILE)

# لود همه فایل‌های چت
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
        return WORDS[word_lower], "محلی"
    if word_lower in LEARNED:
        return LEARNED[word_lower], "یادگرفته"
    result = translate_api(word_lower, "en", "fa")
    if result:
        return result, "API"
    result = translate_api(word, "fa", "en")
    if result:
        return result, "API"
    return None, None


# ==================================================
# تلفظ صوتی (TTS)
# ==================================================
def create_voice_file(text, lang="en"):
    """ساخت فایل صوتی تلفظ کلمه"""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        filename = f"voice_{random.randint(1000, 9999)}.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"خطا در ساخت فایل صوتی: {e}")
        return None


# ==================================================
# فیلتر فحش
# ==================================================
def contains_bad_word(text):
    """بررسی وجود کلمات ممنوعه"""
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word.lower() in text_lower:
            return True
    return False


# ==================================================
# پردازش پیام
# ==================================================
def handle_chat_response(message):
    text = message.text.strip()
    
    # جستجو توی همه دسته‌ها
    for category, responses in CHAT_DATA.items():
        if text in responses or text == category:
            if isinstance(responses, list):
                response = random.choice(responses)
            else:
                response = responses
            bot.send_message(message.chat.id, response)
            return True
    return False


def handle_translation(message):
    text = message.text.strip()
    if " " in text or len(text) > 30:
        return False
    
    translation, source = get_translation(text)
    if translation:
        result_text = f"📖 **{text}**\n\n🔤 ترجمه: **{translation}**\n\n📌 منبع: {source}"
        bot.send_message(message.chat.id, result_text)
        return True
    return False


def handle_voice_command(message):
    """تلفظ صوتی کلمه: /voice hello"""
    if not message.text.startswith("/voice"):
        return False
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ فرمت: `/voice word`\nمثال: `/voice hello`")
        return True
    
    word = parts[1].strip()
    
    # تشخیص زبان
    persian_chars = set("آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی")
    lang = "fa" if any(c in persian_chars for c in word) else "en"
    
    bot.send_message(message.chat.id, f"🔊 در حال ساخت فایل صوتی برای: **{word}**")
    
    voice_file = create_voice_file(word, lang)
    if voice_file:
        try:
            bot.send_voice(message.chat.id, voice_file)
            os.remove(voice_file)
        except Exception as e:
            print(f"خطا در ارسال فایل صوتی: {e}")
            bot.send_message(message.chat.id, "❌ ارسال فایل صوتی پشتیبانی نمیشه.")
    else:
        bot.send_message(message.chat.id, "❌ خطا در ساخت فایل صوتی.")
    
    return True


def handle_learn_command(message):
    if not message.text.startswith("/learn"):
        return False
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.send_message(message.chat.id, "❌ فرمت: `/learn english معنی`")
        return True
    
    english_word = parts[1].lower().strip()
    persian_meaning = parts[2].strip()
    
    LEARNED[english_word] = persian_meaning
    save_json(LEARNED_FILE, LEARNED)
    
    bot.send_message(
        message.chat.id,
        f"✅ یاد گرفته شد!\n📖 **{english_word}** = **{persian_meaning}**"
    )
    return True


def handle_help_command(message):
    if message.text != "/help":
        return False
    
    help_text = """📚 **راهنمای ربات**

🔤 **ترجمه:** فقط کلمه رو بفرست

🔊 **تلفظ صوتی:** `/voice hello`

📝 **آموزش کلمه:** `/learn apple سیب`

📊 **آمار:** `/stats`

💕 **عاشقانه:** کلمه `عاشقانه` رو بفرست
💋 **دلبرانه:** کلمه `دلبرانه` رو بفرست
😘 **ناز دخترانه:** کلمه `ناز دخترانه` رو بفرست
"""
    bot.send_message(message.chat.id, help_text)
    return True


def handle_stats_command(message):
    if message.text != "/stats":
        return False
    
    stats_text = f"""📊 **آمار ربات:**

📖 کلمات دیکشنری: **{len(WORDS)}**
💬 دسته‌های چت: **{len(CHAT_DATA)}**
🧠 کلمات یادگرفته: **{len(LEARNED)}**
🚫 کلمات ممنوعه: **{len(BAD_WORDS)}**
"""
    bot.send_message(message.chat.id, stats_text)
    return True


# ==================================================
# هندلر اصلی
# ==================================================
@bot.on_message()
def handle_message(message: Message):
    
    # فقط گروه مجاز
    if ALLOWED_GROUP_ID != 0 and message.chat.id != ALLOWED_GROUP_ID:
        return
    
    if not message.text:
        return
    
    text = message.text.strip()
    
    # ۱. فیلتر فحش (اول از همه)
    if contains_bad_word(text):
        try:
            bot.delete_message(message.chat.id, message.id)
            bot.send_message(message.chat.id, "🚫 این پیام حذف شد (کلمات نامناسب).")
        except Exception as e:
            print(f"خطا در حذف پیام: {e}")
        return
    
    # ۲. دستورات
    if handle_help_command(message):
        return
    if handle_stats_command(message):
        return
    if handle_learn_command(message):
        return
    if handle_voice_command(message):
        return
    
    # ۳. پاسخ‌های چت
    if handle_chat_response(message):
        return
    
    # ۴. ترجمه
    if handle_translation(message):
        return


# ==================================================
# اجرا
# ==================================================
if __name__ == "__main__":
    print("🤖 ربات در حال اجراست...")
    bot.run()
