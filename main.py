# -*- coding: utf-8 -*-
"""
🎭 ربات چت شخصیت‌محور روبیکا
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

CONFIG_FILE = "config.json"
PERSONALITIES_FOLDER = "personalities"

# حافظه موقت برای جلوگیری از تکرار
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
    """چک میکنه که همین متن توی ۱۰ ثانیه اخیر اومده یا نه"""
    now = time.time()
    chat_key = str(chat_id)
    
    if chat_key not in RECENT_MESSAGES:
        RECENT_MESSAGES[chat_key] = {}
    
    # پاک کردن پیام‌های قدیمی
    RECENT_MESSAGES[chat_key] = {
        t: ts for t, ts in RECENT_MESSAGES[chat_key].items()
        if now - ts < 10
    }
    
    if text in RECENT_MESSAGES[chat_key]:
        return True
    
    RECENT_MESSAGES[chat_key][text] = now
    return False


# ==================================================
# لود اولیه
# ==================================================
CONFIG = load_json(CONFIG_FILE, {
    "admins": [],
    "default_personality": "friend",
    "groups": {},
    "link_filter": True
})

PERSONALITIES = {}
if os.path.exists(PERSONALITIES_FOLDER):
    for filename in os.listdir(PERSONALITIES_FOLDER):
        if filename.endswith(".json"):
            name = filename.replace(".json", "")
            PERSONALITIES[name] = load_json(os.path.join(PERSONALITIES_FOLDER, filename))

print(f"✅ {len(PERSONALITIES)} شخصیت لود شد")
print(f"✅ شخصیت‌ها: {list(PERSONALITIES.keys())}")


# ==================================================
# توابع کمکی
# ==================================================
def save_config():
    save_json(CONFIG_FILE, CONFIG)


def is_admin(sender_id):
    if not sender_id:
        return False
    return str(sender_id) in [str(a) for a in CONFIG.get("admins", [])]


def is_group_active(chat_id):
    groups = CONFIG.get("groups", {})
    group = groups.get(str(chat_id), {})
    return group.get("active", False)


def get_group_personality(chat_id):
    groups = CONFIG.get("groups", {})
    group = groups.get(str(chat_id), {})
    name = group.get("personality", CONFIG.get("default_personality", "friend"))
    if name not in PERSONALITIES:
        name = CONFIG.get("default_personality", "friend")
    return PERSONALITIES.get(name, {}), name


def register_group(chat_id):
    groups = CONFIG.get("groups", {})
    if str(chat_id) not in groups:
        groups[str(chat_id)] = {
            "personality": CONFIG.get("default_personality", "friend"),
            "active": True
        }
        CONFIG["groups"] = groups
        save_config()


def is_link(text):
    patterns = ["http://", "https://", "t.me/", "rubika.ir/", "www."]
    text_lower = text.lower()
    return any(p in text_lower for p in patterns)


def find_response(text, personality):
    text_lower = text.lower().strip()
    responses = personality.get("responses", {})
    if text_lower in responses:
        r = responses[text_lower]
        return random.choice(r) if isinstance(r, list) else r
    return None


def get_sender_id(message):
    for attr in ['sender_id', 'author_id', 'from_id', 'sender']:
        if hasattr(message, attr):
            val = getattr(message, attr)
            if val is not None:
                return val
    return None


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


async def send_with_reply(chat_id, text, message_id):
    """ارسال پیام با ریپلای (اگه ممکن باشه)"""
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
async def handle_personality_list(text, chat_id, message_id):
    if text not in ["/personalities", "شخصیت ها", "شخصیتها", "/list"]:
        return False
    
    _, current = get_group_personality(chat_id)
    msg = "🎭 **شخصیت‌های موجود:**\n\n"
    for name, data in PERSONALITIES.items():
        display = data.get("_name", name)
        marker = "✅ " if name == current else "🔹 "
        msg += f"{marker}{name} - {display}\n"
    msg += "\n📝 برای فعال‌سازی: /set اسم_شخصیت"
    await send_with_reply(chat_id, msg, message_id)
    return True


async def handle_set_personality(text, chat_id, sender_id, message_id):
    if not text.startswith("/set"):
        return False
    
    if not is_admin(sender_id):
        await send_with_reply(chat_id, "❌ فقط ادمین می‌تونه شخصیت رو تغییر بده!", message_id)
        return True
    
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        available = ", ".join(PERSONALITIES.keys())
        await send_with_reply(chat_id, f"📝 فرمت: /set اسم_شخصیت\n\n🎭 شخصیت‌ها:\n{available}", message_id)
        return True
    
    name = parts[1].strip().lower()
    if name not in PERSONALITIES:
        available = ", ".join(PERSONALITIES.keys())
        await send_with_reply(chat_id, f"❌ شخصیت پیدا نشد!\n\n🎭 شخصیت‌ها:\n{available}", message_id)
        return True
    
    register_group(chat_id)
    CONFIG["groups"][str(chat_id)]["personality"] = name
    CONFIG["groups"][str(chat_id)]["active"] = True
    save_config()
    
    display = PERSONALITIES[name].get("_name", name)
    await send_with_reply(chat_id, f"✅ شخصیت فعال شد: {display} 🎭", message_id)
    return True


async def handle_current(text, chat_id, message_id):
    if text != "/current":
        return False
    _, name = get_group_personality(chat_id)
    display = PERSONALITIES.get(name, {}).get("_name", name)
    await send_with_reply(chat_id, f"🎭 شخصیت فعلی: {display}", message_id)
    return True


async def handle_off(text, chat_id, sender_id, message_id):
    if text != "/off":
        return False
    if not is_admin(sender_id):
        return True
    register_group(chat_id)
    CONFIG["groups"][str(chat_id)]["active"] = False
    save_config()
    await send_with_reply(chat_id, "🔴 ربات خاموش شد.", message_id)
    return True


async def handle_on(text, chat_id, sender_id, message_id):
    if text != "/on":
        return False
    if not is_admin(sender_id):
        return True
    register_group(chat_id)
    CONFIG["groups"][str(chat_id)]["active"] = True
    save_config()
    await send_with_reply(chat_id, "🟢 ربات روشن شد.", message_id)
    return True


async def handle_help(text, chat_id, sender_id, message_id):
    if text != "/help":
        return False
    if not is_admin(sender_id):
        return True
    msg = (
        "📚 راهنمای ربات\n\n"
        "🎭 /set اسم_شخصیت - فعال‌سازی\n"
        "📋 /personalities - لیست شخصیت‌ها\n"
        "👤 /current - شخصیت فعلی\n"
        "🔴 /off - خاموش کردن\n"
        "🟢 /on - روشن کردن\n\n"
        "برای لیست شخصیت‌ها بنویس: شخصیت ها"
    )
    await send_with_reply(chat_id, msg, message_id)
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
        
        # 🚫 چک کردن پیام تکراری
        if is_duplicate(chat_id, text):
            print(f"⚠️ پیام تکراری نادیده گرفته شد: {text[:30]}")
            return
        
        sender_id = get_sender_id(message)
        message_id = get_message_id(message)
        
        # 🔗 فیلتر لینک
        if CONFIG.get("link_filter") and is_group_active(chat_id) and is_link(text):
            try:
                await bot.delete_message(chat_id, message_id)
            except Exception as e:
                print(f"⚠️ خطا در حذف لینک: {e}")
            return
        
        # 🎯 دستورات
        if await handle_help(text, chat_id, sender_id, message_id):
            return
        if await handle_personality_list(text, chat_id, message_id):
            return
        if await handle_set_personality(text, chat_id, sender_id, message_id):
            return
        if await handle_current(text, chat_id, message_id):
            return
        if await handle_off(text, chat_id, sender_id, message_id):
            return
        if await handle_on(text, chat_id, sender_id, message_id):
            return
        
        # 🚫 اگه گروه فعال نباشه
        if not is_group_active(chat_id):
            return
        
        # 💬 پاسخ با شخصیت (با ریپلای)
        personality, _ = get_group_personality(chat_id)
        response = find_response(text, personality)
        if response:
            await send_with_reply(chat_id, response, message_id)
    
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()


# ==================================================
# اجرا
# ==================================================
if __name__ == "__main__":
    print("🤖 ربات چت شخصیت‌محور v2 در حال اجراست...")
    bot.run()
