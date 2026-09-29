# -*- coding: utf-8 -*-
"""
💕 ربات چت دخترونه - هوشمند با یادگیری
"""

import os
import json
import random
import time
from rubka import Robot

# ==================================================
# تنظیمات
# ==================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("توکن ربات یافت نشد!")

bot = Robot(token=BOT_TOKEN)

CHAT_FILE = "chat.json"
LEARNED_FILE = "learned.json"
ADMINS_FILE = "admins.json"

RECENT_MESSAGES = {}


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


def is_duplicate(chat_id, text):
    """ضد تکرار - چک میکنه توی ۳ ثانیه اخیر این متن اومده یا نه"""
    now = time.time()
    chat_key = str(chat_id)

    if chat_key not in RECENT_MESSAGES:
        RECENT_MESSAGES[chat_key] = {}

    RECENT_MESSAGES[chat_key] = {
        t: ts for t, ts in RECENT_MESSAGES[chat_key].items()
        if now - ts < 3
    }

    if text in RECENT_MESSAGES[chat_key]:
        return True

    RECENT_MESSAGES[chat_key][text] = now
    return False


# ==================================================
# لود اولیه
# ==================================================
CHAT_DATA = load_json(CHAT_FILE, {"responses": {}, "fallbacks": [], "replies_to_bot": []})
RESPONSES = CHAT_DATA.get("responses", {})
FALLBACKS = CHAT_DATA.get("fallbacks", [
    "😄 چی می‌گی؟ خودمم نفهمیدم",
    "هوم؟ 🤔 یه کم واضح‌تر بگو",
    "😅 راستش رو بخوای، نمی‌دونم چی بگم",
    "ببخشید، متوجه نشدم 🤷‍♀️",
    "چی گفتی؟ یه بار دیگه بگو 😄",
    "من که چیزی نفهمیدم! 😂",
    "شرمنده، بلد نیستم 😅 ولی خب، گفتی چی؟",
    "هوم... نمی‌دونم چی بگم والا 🤔",
])
REPLIES_TO_BOT = CHAT_DATA.get("replies_to_bot", [
    "چیه؟ 😄 با من کاری داری؟",
    "جانم؟ چیزی گفتی؟ 😏",
    "😄 چیه، دلبری می‌کنی؟",
    "خب؟ 😊 بگو ببینم چی می‌خوای",
    "😏 چرا پیام منو ریپلای می‌کنی؟",
    "خب؟ بگو دیگه، منتظرم 😄",
])

LEARNED = load_json(LEARNED_FILE, {})
ADMINS = load_json(ADMINS_FILE, ["u0Iopfm0841d28cb88ee368ba5f966b6"])

print(f"✅ {len(RESPONSES)} پاسخ اصلی لود شد")
print(f"✅ {len(LEARNED)} کلمه یادگرفته لود شد")
print(f"✅ {len(ADMINS)} ادمین تنظیم شده")


# ==================================================
# توابع کمکی
# ==================================================
def get_chat_id(message):
    for attr in ['chat_id', 'chat']:
        if hasattr(message, attr):
            val = getattr(message, attr)
            if attr == 'chat' and hasattr(val, 'id'):
                return val.id
            if attr == 'chat_id':
                return val
    return None


def get_message_id(message):
    for attr in ['id', 'message_id']:
        if hasattr(message, attr):
            val = getattr(message, attr)
            if val is not None:
                return val
    return None


def get_sender_id(message):
    for attr in ['sender_id', 'author_id', 'from_id', 'sender']:
        if hasattr(message, attr):
            val = getattr(message, attr)
            if val is not None:
                return val
    return None


def get_reply_to_id(message):
    """آیدی پیامی که بهش ریپلای زده شده"""
    for attr in ['reply_to_message_id', 'reply_to_id', 'reply_to']:
        if hasattr(message, attr):
            val = getattr(message, attr)
            if val is not None:
                if hasattr(val, 'id'):
                    return val.id
                return val
    return None


def is_admin(sender_id):
    if not sender_id:
        return False
    return str(sender_id) in [str(a) for a in ADMINS]


def find_response(text):
    """جستجو در پاسخ‌ها (اول یادگرفته، بعد اصلی)"""
    text_lower = text.lower().strip()

    # ۱. اول کلمه یادگرفته
    if text_lower in LEARNED:
        r = LEARNED[text_lower]
        return random.choice(r) if isinstance(r, list) else r

    # ۲. بعد پاسخ اصلی
    if text_lower in RESPONSES:
        r = RESPONSES[text_lower]
        return random.choice(r) if isinstance(r, list) else r

    return None


def get_fallback():
    """جواب پیش‌فرض وقتی کلمه رو نمی‌شناسه"""
    return random.choice(FALLBACKS)


def get_reply_to_bot():
    """جواب وقتی کسی به پیام ربات ریپلای می‌زنه"""
    return random.choice(REPLIES_TO_BOT)


async def send_with_reply(chat_id, text, message_id):
    """ارسال پیام با ریپلای"""
    try:
        await bot.send_message(chat_id, text, reply_to_message_id=message_id)
    except Exception:
        try:
            await bot.send_message(chat_id, text, reply_to=message_id)
        except Exception:
            await bot.send_message(chat_id, text)


# ==================================================
# دستورات
# ==================================================
async def handle_learn(text, chat_id, sender_id, message_id):
    """/learn کلمه جواب - آموزش دادن"""
    if not text.startswith("/learn"):
        return False

    if not is_admin(sender_id):
        return True

    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await send_with_reply(
            chat_id,
            "📝 فرمت: /learn کلمه جواب\nمثال: /learn چطوری خوبم عزیزم 😊",
            message_id
        )
        return True

    trigger = parts[1].lower().strip()
    response = parts[2].strip()

    if trigger not in LEARNED:
        LEARNED[trigger] = []

    if not isinstance(LEARNED[trigger], list):
        LEARNED[trigger] = [LEARNED[trigger]]

    LEARNED[trigger].append(response)
    save_json(LEARNED_FILE, LEARNED)

    await send_with_reply(chat_id, f"✅ یاد گرفتم!\n\n🔹 کلمه: {trigger}\n🔹 جواب: {response}", message_id)
    return True


async def handle_forget(text, chat_id, sender_id, message_id):
    """/forget کلمه - پاک کردن یک کلمه یادگرفته"""
    if not text.startswith("/forget"):
        return False

    if not is_admin(sender_id):
        return True

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await send_with_reply(chat_id, "📝 فرمت: /forget کلمه", message_id)
        return True

    trigger = parts[1].lower().strip()
    if trigger in LEARNED:
        del LEARNED[trigger]
        save_json(LEARNED_FILE, LEARNED)
        await send_with_reply(chat_id, f"🗑️ کلمه «{trigger}» پاک شد.", message_id)
    else:
        await send_with_reply(chat_id, f"❌ کلمه «{trigger}» پیدا نشد.", message_id)
    return True


async def handle_list_learned(text, chat_id, sender_id, message_id):
    """/learned - لیست کلمات یادگرفته"""
    if text != "/learned":
        return False

    if not is_admin(sender_id):
        return True

    if not LEARNED:
        await send_with_reply(chat_id, "📝 هنوز چیزی یاد نگرفتم.", message_id)
        return True

    msg = f"🧠 کلمات یادگرفته ({len(LEARNED)}):\n\n"
    for key in list(LEARNED.keys())[:30]:
        msg += f"🔹 {key}\n"

    if len(LEARNED) > 30:
        msg += f"\n... و {len(LEARNED) - 30} کلمه دیگه"

    await send_with_reply(chat_id, msg, message_id)
    return True


async def handle_help(text, chat_id, sender_id, message_id):
    """/help - راهنما"""
    if text != "/help":
        return False

    if not is_admin(sender_id):
        return True

    msg = (
        "📚 راهنمای ربات\n\n"
        "🧠 /learn کلمه جواب — آموزش\n"
        "🗑️ /forget کلمه — حذف کلمه\n"
        "📋 /learned — لیست کلمات یادگرفته\n"
        "📊 /stats — آمار\n"
        "❓ /help — راهنما"
    )
    await send_with_reply(chat_id, msg, message_id)
    return True


async def handle_stats(text, chat_id, sender_id, message_id):
    """/stats - آمار"""
    if text != "/stats":
        return False

    msg = (
        f"📊 آمار ربات:\n\n"
        f"💬 پاسخ‌های اصلی: {len(RESPONSES)}\n"
        f"🧠 کلمات یادگرفته: {len(LEARNED)}\n"
        f"👥 ادمین‌ها: {len(ADMINS)}"
    )
    await send_with_reply(chat_id, msg, message_id)
    return True


async def handle_add_admin(text, chat_id, sender_id, message_id):
    """/addadmin - اضافه کردن ادمین (فقط ادمین اصلی)"""
    if not text.startswith("/addadmin"):
        return False

    # فقط اگه خودت ادمین باشی
    if not is_admin(sender_id):
        return True

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await send_with_reply(chat_id, "📝 فرمت: /addadmin آیدی_عددی", message_id)
        return True

    new_admin = parts[1].strip()
    if new_admin not in ADMINS:
        ADMINS.append(new_admin)
        save_json(ADMINS_FILE, ADMINS)
        await send_with_reply(chat_id, f"✅ ادمین جدید اضافه شد.", message_id)
    else:
        await send_with_reply(chat_id, "❌ این کاربر از قبل ادمینه.", message_id)
    return True


# ==================================================
# هندلر اصلی
# ==================================================
@bot.on_message()
async def handle_message(_bot, message):
    try:
        chat_id = get_chat_id(message)
        if chat_id is None:
            return

        text = message.text.strip() if hasattr(message, 'text') and message.text else None
        if not text:
            return

        # 🚫 ضد تکرار
        if is_duplicate(chat_id, text):
            return

        sender_id = get_sender_id(message)
        message_id = get_message_id(message)
        reply_to_id = get_reply_to_id(message)

        # 🎯 دستورات
        if await handle_help(text, chat_id, sender_id, message_id):
            return
        if await handle_stats(text, chat_id, sender_id, message_id):
            return
        if await handle_learn(text, chat_id, sender_id, message_id):
            return
        if await handle_forget(text, chat_id, sender_id, message_id):
            return
        if await handle_list_learned(text, chat_id, sender_id, message_id):
            return
        if await handle_add_admin(text, chat_id, sender_id, message_id):
            return

        # 💬 جواب به پیام
        if reply_to_id:
            # کسی به یه پیام ریپلای زده
            # اگه متنش کلمه کلیدیه، جواب بده. وگرنه یه جواب بامزه بده
            response = find_response(text)
            if response:
                await send_with_reply(chat_id, response, message_id)
            else:
                await send_with_reply(chat_id, get_reply_to_bot(), message_id)
        else:
            # پیام معمولی
            response = find_response(text)
            if response:
                await send_with_reply(chat_id, response, message_id)
            else:
                # اگه کلمه رو نمی‌شناخت، یه جواب پیش‌فرض می‌ده
                # ولی فقط با احتمال ۳۰٪، تا گروه رو شلوغ نکنه
                if random.random() < 0.3:
                    await send_with_reply(chat_id, get_fallback(), message_id)

    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()


# ==================================================
# اجرا
# ==================================================
if __name__ == "__main__":
    print("🤖 ربات دخترونه در حال اجراست...")
    bot.run()
