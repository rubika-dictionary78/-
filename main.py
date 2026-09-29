# -*- coding: utf-8 -*-
"""
🎭 ربات چت شخصیت‌محور روبیکا
نسخه فروشگاهی - Multi-Personality Chat Bot
"""

import os
import json
import random
from robobot import Bot

# ==================================================
# تنظیمات اولیه
# ==================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("توکن ربات یافت نشد!")

bot = Bot(BOT_TOKEN)

CONFIG_FILE = "config.json"
PERSONALITIES_FOLDER = "personalities"


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
# لود اولیه
# ==================================================
CONFIG = load_json(CONFIG_FILE, {
    "admins": [],
    "default_personality": "friend",
    "groups": {},
    "link_filter": True,
    "notify_admin": True
})

# لود همه شخصیت‌ها
PERSONALITIES = {}
if os.path.exists(PERSONALITIES_FOLDER):
    for filename in os.listdir(PERSONALITIES_FOLDER):
        if filename.endswith(".json"):
            name = filename.replace(".json", "")
            PERSONALITIES[name] = load_json(os.path.join(PERSONALITIES_FOLDER, filename))

print(f"✅ {len(PERSONALITIES)} شخصیت لود شد")
print(f"✅ {len(CONFIG.get('admins', []))} ادمین تنظیم شده")
print(f"✅ {len(CONFIG.get('groups', {}))} گروه ثبت شده")


# ==================================================
# توابع کمکی
# ==================================================
def save_config():
    save_json(CONFIG_FILE, CONFIG)


def is_admin(chat_id):
    """چک میکنه که کاربر ادمین هست یا نه"""
    return str(chat_id) in [str(a) for a in CONFIG.get("admins", [])]


def is_group_active(chat_id):
    """چک میکنه که گروه فعال هست یا نه"""
    groups = CONFIG.get("groups", {})
    if str(chat_id) not in groups:
        return False
    return groups[str(chat_id)].get("active", False)


def get_group_personality(chat_id):
    """شخصیت فعال گروه رو برمی‌گردونه"""
    groups = CONFIG.get("groups", {})
    group_data = groups.get(str(chat_id), {})
    personality_name = group_data.get("personality", CONFIG.get("default_personality", "friend"))
    
    if personality_name not in PERSONALITIES:
        # اگه شخصیت پیدا نشد، پیش‌فرض
        personality_name = CONFIG.get("default_personality", "friend")
    
    return PERSONALITIES.get(personality_name, {}), personality_name


def register_group(chat_id, personality=None):
    """گروه جدید رو ثبت میکنه"""
    groups = CONFIG.get("groups", {})
    if str(chat_id) not in groups:
        groups[str(chat_id)] = {
            "personality": personality or CONFIG.get("default_personality", "friend"),
            "active": True
        }
        CONFIG["groups"] = groups
        save_config()
        return True
    return False


def is_link(text):
    """چک میکنه که متن حاوی لینک هست یا نه"""
    link_patterns = ["http://", "https://", "t.me/", "rubika.ir/", "www.", ".com/", ".ir/", ".net/", ".org/", ".xyz/"]
    text_lower = text.lower()
    return any(p in text_lower for p in link_patterns)


def find_response(text, personality):
    """
    پیدا کردن پاسخ مناسب از شخصیت
    ساختار شخصیت: {"_name": "...", "responses": {"کلمه": ["پاسخ1", "پاسخ2"]}}
    """
    text_lower = text.lower().strip()
    
    # ۱. اول از responses (ساختار جدید)
    responses = personality.get("responses", {})
    if text_lower in responses:
        r = responses[text_lower]
        return random.choice(r) if isinstance(r, list) else r
    
    # ۲. حالت قدیمی (بدون responses)
    for key, value in personality.items():
        if key.startswith("_"):
            continue
        if text_lower == key.lower():
            return random.choice(value) if isinstance(value, list) else value
    
    return None


# ==================================================
# دستورات ادمین
# ==================================================
async def handle_set_personality(text, chat_id, sender_id):
    """تنظیم شخصیت برای گروه: /set اسم_شخصیت"""
    if not is_admin(sender_id):
        await bot.send_message(chat_id, "❌ فقط ادمین می‌تونه شخصیت رو تغییر بده!")
        return True
    
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        available = "\n".join([f"🔹 {name}" for name in PERSONALITIES.keys()])
        await bot.send_message(chat_id, f"📝 فرمت: /set اسم_شخصیت\n\n🎭 شخصیت‌ها:\n{available}")
        return True
    
    personality_name = parts[1].strip().lower()
    if personality_name not in PERSONALITIES:
        available = "\n".join([f"🔹 {name}" for name in PERSONALITIES.keys()])
        await bot.send_message(chat_id, f"❌ شخصیت پیدا نشد!\n\n🎭 شخصیت‌ها:\n{available}")
        return True
    
    # ثبت گروه اگه جدید باشه
    register_group(chat_id)
    
    # تغییر شخصیت
    CONFIG["groups"][str(chat_id)]["personality"] = personality_name
    CONFIG["groups"][str(chat_id)]["active"] = True
    save_config()
    
    display_name = PERSONALITIES[personality_name].get("_name", personality_name)
    await bot.send_message(chat_id, f"✅ شخصیت فعال شد: «{display_name}» 🎭")
    return True


async def handle_personality_list(text, chat_id):
    """لیست شخصیت‌ها: /personalities یا «شخصیت ها»"""
    if text not in ["/personalities", "شخصیت ها", "شخصیتها", "/list"]:
        return False
    
    _, current_name = get_group_personality(chat_id)
    
    msg = "🎭 **شخصیت‌های موجود:**\n\n"
    for name, data in PERSONALITIES.items():
        display = data.get("_name", name)
        desc = data.get("_description", "")
        marker = "✅ " if name == current_name else "🔹 "
        msg += f"{marker}**{name}** - {display}\n"
        if desc:
            msg += f"   _{desc}_\n"
    
    msg += "\n📝 برای فعال‌سازی: /set اسم_شخصیت"
    await bot.send_message(chat_id, msg)
    return True


async def handle_current(text, chat_id):
    """شخصیت فعلی: /current"""
    if text != "/current":
        return False
    
    personality, name = get_group_personality(chat_id)
    display = personality.get("_name", name)
    await bot.send_message(chat_id, f"🎭 شخصیت فعلی این گروه: **{display}**")
    return True


async def handle_admin_help(text, chat_id, sender_id):
    """راهنما: /help"""
    if text != "/help":
        return False
    
    help_text = (
        "📚 **راهنمای ربات چت**\n\n"
        "🎭 **دستورات ادمین:**\n"
        "`/set اسم_شخصیت` - فعال‌سازی شخصیت\n"
        "`/personalities` - لیست شخصیت‌ها\n"
        "`/current` - شخصیت فعلی\n"
        "`/off` - خاموش کردن ربات در گروه\n"
        "`/on` - روشن کردن ربات در گروه\n\n"
        "🎭 **برای دیدن شخصیت‌ها بنویسید:**\n"
        "`شخصیت ها`"
    )
    
    if is_admin(sender_id):
        await bot.send_message(chat_id, help_text)
    return True


async def handle_off(text, chat_id, sender_id):
    """خاموش کردن ربات: /off"""
    if text != "/off":
        return False
    
    if not is_admin(sender_id):
        return True
    
    register_group(chat_id)
    CONFIG["groups"][str(chat_id)]["active"] = False
    save_config()
    await bot.send_message(chat_id, "🔴 ربات خاموش شد.")
    return True


async def handle_on(text, chat_id, sender_id):
    """روشن کردن ربات: /on"""
    if text != "/on":
        return False
    
    if not is_admin(sender_id):
        return True
    
    register_group(chat_id)
    CONFIG["groups"][str(chat_id)]["active"] = True
    save_config()
    await bot.send_message(chat_id, "🟢 ربات روشن شد.")
    return True


# ==================================================
# هندلر اصلی
# ==================================================
@bot.on_message()
async def handle_message(bot, message):
    try:
        chat_id = message.chat_id if hasattr(message, 'chat_id') else None
        if chat_id is None:
            return
        
        # گرفتن آیدی فرستنده (اگه موجود باشه)
        sender_id = None
        if hasattr(message, 'sender_id'):
            sender_id = message.sender_id
        elif hasattr(message, 'author_id'):
            sender_id = message.author_id
        elif hasattr(message, 'from_id'):
            sender_id = message.from_id
        
        text = message.text.strip() if hasattr(message, 'text') and message.text else None
        if not text:
            return
        
        # 🔗 فیلتر لینک (اگه گروه فعال باشه)
        if CONFIG.get("link_filter") and is_group_active(chat_id) and is_link(text):
            try:
                await bot.delete_message(chat_id, message.id)
            except Exception as e:
                print(f"⚠️ خطا در پاک کردن لینک: {e}")
            return
        
        # 🎯 دستورات ادمین
        if await handle_help_command(text, chat_id, sender_id):
            return
        if await handle_personality_list(text, chat_id):
            return
        if await handle_set_personality(text, chat_id, sender_id):
            return
        if await handle_current(text, chat_id):
            return
        if await handle_off(text, chat_id, sender_id):
            return
        if await handle_on(text, chat_id, sender_id):
            return
        
        # 🚫 اگه گروه فعال نباشه، جواب نده
        if not is_group_active(chat_id):
            return
        
        # 💬 پاسخ با شخصیت فعال
        personality, _ = get_group_personality(chat_id)
        response = find_response(text, personality)
        if response:
            await bot.send_message(chat_id, response)
    
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()


# ==================================================
# اجرا
# ==================================================
if __name__ == "__main__":
    print("🤖 ربات چت شخصیت‌محور در حال اجراست...")
    bot.run()
