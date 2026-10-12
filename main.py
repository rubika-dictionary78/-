import os
import json
from rubka import Client
from openai import OpenAI

# ⚙️ تنظیمات - از متغیرهای محیطی یا مستقیم
RUBIKA_TOKEN = os.getenv("RUBIKA_BOT_TOKEN", "توکن_روبیکا_ات_رو_بذار")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "کلید_دیپ‌سیک_ات_رو_بذار")

rubika = Client(RUBIKA_TOKEN)
deepseek = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

# 📂 بارگذاری داده‌های قبلی
def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default or {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# تاریخچه چت هر کاربر
chat_history = load_json("json.چت", {})

@rubika.on_message()
def handle_message(message):
    user_id = str(message.sender_id)
    text = message.text
    
    if not text:
        return
    
    # ساخت تاریخچه برای کاربر جدید
    if user_id not in chat_history:
        chat_history[user_id] = [
            {"role": "system", "content": "تو یه دستیار هوشمند و مفید هستی. به فارسی جواب بده."}
        ]
    
    chat_history[user_id].append({"role": "user", "content": text})
    
    # فقط ۲۰ پیام آخر رو نگه دار
    if len(chat_history[user_id]) > 21:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-20:]
    
    try:
        # درخواست به DeepSeek
        response = deepseek.chat.completions.create(
            model="deepseek-chat",
            messages=chat_history[user_id]
        )
        reply = response.choices[0].message.content
        
        chat_history[user_id].append({"role": "assistant", "content": reply})
        save_json("json.چت", chat_history)
        
        message.reply(reply)
    
    except Exception as e:
        message.reply(f"❌ خطا: {str(e)}")

if __name__ == "__main__":
    print("🤖 ربات DeepSeek روشن شد...")
    rubika.run()
