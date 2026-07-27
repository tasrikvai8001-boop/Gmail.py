import importlib.util
import subprocess
import sys
import os
import time
import json
import random
import threading

# Flask ও Telebot অটো-ইনস্টল চেক
if importlib.util.find_spec("flask") is None or importlib.util.find_spec("telebot") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "pyTelegramBotAPI"])

from flask import Flask
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ============================================
# --- STYLE PATCH FOR TELEBOT BUTTONS ---
# ============================================
_old_inline_dict = InlineKeyboardButton.to_dict
def _new_inline_dict(self):
    d = _old_inline_dict(self)
    if hasattr(self, 'style'): d['style'] = self.style
    return d
InlineKeyboardButton.to_dict = _new_inline_dict

_old_kb_dict = KeyboardButton.to_dict
def _new_kb_dict(self):
    d = _old_kb_dict(self)
    if hasattr(self, 'style'): d['style'] = self.style
    return d
KeyboardButton.to_dict = _new_kb_dict

def ibtn(text, callback_data=None, url=None, style=None):
    kwargs = {'text': text}
    if callback_data: kwargs['callback_data'] = callback_data
    if url: kwargs['url'] = url
    b = InlineKeyboardButton(**kwargs)
    if style: b.style = style
    return b

def rbtn(text, style=None):
    b = KeyboardButton(text=text)
    if style: b.style = style
    return b

# ============================================
# --- WEB SERVER FOR RENDER (KEEP ALIVE) ---
# ============================================
app = Flask('')

@app.route('/')
def home():
    return "📧 NR Gmail Shop BDT Bot is Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ============================================
# --- CONFIGURATION ---
# ============================================
BOT_TOKEN = "8879290215:AAFYA2TYq_y92oTn28ISTC_oB4XJGuJV0-Y"  # আপনার বট টোকেন
ADMIN_ID = 7833766898          # আপনার টেলিগ্রাম ID (Integer)
BOT_NAME = "📧 𝒩𝑅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒉𝒐𝒑 𝑩𝑫𝑻 📩"
DATA_FILE = "nr_gmail_shop_data.json"

bot = telebot.TeleBot(BOT_TOKEN, num_threads=50)
db_lock = threading.RLock()

# ============================================
# --- DATABASE MANAGEMENT ---
# ============================================
def load_db():
    with db_lock:
        default_db = {
            "users": {},
            "banned_users": [],
            "force_channels": [],
            "ref_bonus_verify": 0.40,
            "min_withdraw": 50.0,
            "new_mail_price": 10.0,
            "old_mail_price": 15.0,
            "used_mail_price": 8.0,
            "new_mail_password": "NRGmailShopPass@2026",
            "recovery_gmail": "nr_recovery2026@gmail.com",
            "maintenance_mode": False,
            "used_emails_database": [],  # Anti-Duplicate Check
            "withdraw_methods": {
                "bKash": True,
                "Nagad": True,
                "Binance": True
            },
            "custom_buttons": [],
            "pending_new_mails": {},
            "pending_old_mails": {},
            "pending_used_mails": {},
            "pending_withdraws": {}
        }
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump(default_db, f, indent=4)
            return default_db
        try:
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                for key, val in default_db.items():
                    if key not in data:
                        data[key] = val
                return data
        except:
            return default_db

def save_db(data):
    with db_lock:
        try:
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Database Save Error:", e)

def get_user(user_id, name="User", username=""):
    data = load_db()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "name": name,
            "username": username,
            "balance": 0.0,
            "total_ref_bonus": 0.0,
            "total_withdraw": 0.0,
            "pending_withdraw": 0.0,
            "success_mails": 0,
            "pending_mails": 0,
            "lang": None,  # 'bn' or 'en'
            "referred_by": None,
            "ref_rewarded": False,
            "referral_list": [],
            "active_new_mail_session": None,
            "state": None,
            "temp_data": {}
        }
        save_db(data)
    return data["users"][uid]

def update_user(user_id, key, val):
    data = load_db()
    uid = str(user_id)
    if uid in data["users"]:
        data["users"][uid][key] = val
        save_db(data)

# ============================================
# --- RANDOM CREDENTIALS GENERATOR ---
# ============================================
FIRST_NAMES = ["Tanvir", "Shakib", "Rahim", "Sabbir", "Arif", "Mahmud", "Fahim", "Naim", "Abrar", "Tamim"]
LAST_NAMES = ["Hossain", "Islam", "Ahmed", "Chowdhury", "Khan", "Uddin", "Rahman", "Mia", "Sarker", "Ali"]

def generate_gmail_details():
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    rand_num = random.randint(10000, 99999)
    email = f"{fn.lower()}{ln.lower()}{rand_num}@gmail.com"
    return fn, ln, email

# ============================================
# --- FORCE JOIN CHECKER ---
# ============================================
def check_force_join(user_id):
    data = load_db()
    left_channels = []
    for ch in data.get("force_channels", []):
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                left_channels.append(ch)
        except:
            left_channels.append(ch)
    return left_channels

def get_force_join_markup(left_channels):
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in left_channels:
        clean_ch = ch.replace("@", "")
        markup.add(ibtn(f"📢 Join {ch}", url=f"https://t.me/{clean_ch}", style="primary"))
    markup.add(ibtn("✅ Verify Now", callback_data="verify_join", style="success"))
    return markup

# ============================================
# --- KEYBOARDS (ENGLISH & BANGLA) ---
# ============================================
def get_main_menu(user_id):
    data = load_db()
    user = get_user(user_id)
    lang = user.get("lang", "bn")
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    if lang == "en":
        markup.add(rbtn("💰 𝑩𝒂𝒍𝒂𝒏𝒄𝒆", style="primary"), rbtn("👥 𝑩𝒆𝒇𝒆𝒓𝒓𝒂𝒍", style="primary"))
        markup.add(rbtn("📧 𝑵𝒆𝒘 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆", style="primary"), rbtn("👴 𝑶𝒍𝒅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆", style="primary"))
        markup.add(rbtn("♻️ 𝑼𝒔𝒆𝒅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆", style="primary"), rbtn("📥 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘", style="primary"))
        markup.add(rbtn("🏆 𝑳𝒆𝒂𝒅𝒆𝒓𝒃𝒐𝒂𝒓𝒅", style="primary"))
    else:
        markup.add(rbtn("💰 মোট ব্যালেন্স", style="primary"), rbtn("👥 রেফার", style="primary"))
        markup.add(rbtn("📧 নতুন জিমেইল সেল", style="primary"), rbtn("👴 পুরাতন জিমেইল সেল", style="primary"))
        markup.add(rbtn("♻️ ইউজ জিমেইল সেল", style="primary"), rbtn("📥 উইথড্র করুন", style="primary"))
        markup.add(rbtn("🏆 লিডারবোর্ড", style="primary"))

    for cb in data.get("custom_buttons", []):
        markup.add(rbtn(cb, style="primary"))

    if str(user_id) == str(ADMIN_ID):
        markup.add(rbtn("⚙️ Admin Panel", style="danger"))

    return markup

def get_admin_inline_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        ibtn("📢 Set Channel", callback_data="adm_set_channel", style="primary"),
        ibtn("🎁 Set Ref Bonus", callback_data="adm_set_ref_bonus", style="primary")
    )
    markup.add(
        ibtn("💳 Set Min Withdraw", callback_data="adm_set_min_withdraw", style="primary"),
        ibtn("📥 Pending New Mail", callback_data="adm_p_new", style="warning")
    )
    markup.add(
        ibtn("📥 Pending Old Mail", callback_data="adm_p_old", style="warning"),
        ibtn("📥 Pending Use Mail", callback_data="adm_p_used", style="warning")
    )
    markup.add(
        ibtn("💸 Pending Withdraw", callback_data="adm_p_with", style="danger"),
        ibtn("📢 Broadcast", callback_data="adm_broadcast", style="primary")
    )
    markup.add(
        ibtn("🔑 New Mail Pass Set", callback_data="adm_set_pass", style="secondary"),
        ibtn("⛔ Ban User", callback_data="adm_ban", style="danger")
    )
    markup.add(
        ibtn("🟢 Unban User", callback_data="adm_unban", style="success"),
        ibtn("➕ Add Mainmenu Button", callback_data="adm_add_btn", style="success")
    )
    markup.add(
        ibtn("🗑️ Delete Button", callback_data="adm_del_btn", style="danger"),
        ibtn("➕ Add Balance", callback_data="adm_add_bal", style="success")
    )
    markup.add(
        ibtn("➖ Cut Balance", callback_data="adm_cut_bal", style="danger"),
        ibtn("📊 Bot Statistics", callback_data="adm_stats", style="secondary")
    )
    markup.add(
        ibtn("🏷️ Set Mail Prices", callback_data="adm_set_prices", style="primary"),
        ibtn("🔎 User Search", callback_data="adm_search", style="secondary")
    )
    markup.add(
        ibtn("🔴 Maintenance Mode", callback_data="adm_maint", style="danger"),
        ibtn("📁 Export Data", callback_data="adm_export", style="primary")
    )
    markup.add(
        ibtn("❌ Close Panel", callback_data="adm_close", style="danger")
    )
    return markup

# ============================================
# --- HANDLERS ---
# ============================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    data = load_db()

    if data.get("maintenance_mode") and str(user_id) != str(ADMIN_ID):
        bot.send_message(message.chat.id, "🔴 <b>বট বর্তমানে মেইনটেন্যান্স মোডে আছে। কিছুক্ষণ পর আবার চেষ্টা করুন।</b>", parse_mode="HTML")
        return

    if str(user_id) in data.get("banned_users", []):
        bot.send_message(message.chat.id, "⛔ আপনি এই বটে ব্লকড আছেন।")
        return

    user = get_user(user_id, message.from_user.first_name, message.from_user.username or "")
    update_user(user_id, "state", None)

    args = message.text.split()
    if len(args) > 1 and user.get("referred_by") is None:
        ref_id = args[1]
        if ref_id != str(user_id) and ref_id in data["users"]:
            update_user(user_id, "referred_by", ref_id)

    left = check_force_join(user_id)
    if left:
        msg = f"👋 <b>Welcome to {BOT_NAME}!</b>\n\nবটটি ব্যবহার করতে নিচের চ্যানেলগুলোতে জয়েন করুন এবং <b>Verify Now</b> বাটনে ক্লিক করুন:"
        bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=get_force_join_markup(left))
        return

    if not user.get("lang"):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            ibtn("English 🇬🇧", callback_data="setlang_en", style="primary"),
            ibtn("বাংলা 🇧🇩", callback_data="setlang_bn", style="success")
        )
        bot.send_message(message.chat.id, "🌐 <b>মেসেজের ভাষা নির্ধারণ করুন / Select Bot Language:</b>", parse_mode="HTML", reply_markup=markup)
        return

    welcome_text = f"<b>Welcome back to {BOT_NAME}!</b>\nনিচের মেনু থেকে আপনার পছন্দ অনুযায়ী অপশন বেছে নিন:"
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=get_main_menu(user_id))

@bot.message_handler(commands=['developer'])
def developer_cmd(message):
    msg = "<b>ডেলিভারি এবং কাস্টমাইজড বট ডেভেলপার:</b>\n\nএই রকম সেম বট কম টাকায় তৈরি করে নিতে চাইলে এনাকে মেসেজ করুন 👇"
    markup = InlineKeyboardMarkup()
    markup.add(ibtn("👨‍💻 Contact Developer", url="https://t.me/devoloper54", style="success"))
    bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

# ============================================
# --- CALLBACK HANDLER ---
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = load_db()

    # অ্যাডমিন একশন চেক (String Format Conversion Safe Check)
    if call.data.startswith("adm_"):
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "❌ আপনার এই প্যানেল ব্যবহারের অনুমতি নেই!", show_alert=True)
            return

        act = call.data.replace("adm_", "")
        bot.answer_callback_query(call.id)  # Stop Loading

        if act == "close":
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass

        elif act == "set_channel":
            update_user(user_id, "state", "admin_set_channel")
            bot.send_message(call.message.chat.id, "📢 চ্যানেল ইউজারনেম সেন্ড করুন (যেমন: `@mychannel`):")

        elif act == "set_ref_bonus":
            update_user(user_id, "state", "admin_set_ref_bonus")
            bot.send_message(call.message.chat.id, "🎁 নতুন রেফার বোনাস অ্যামাউন্ট লিখুন:")

        elif act == "set_min_withdraw":
            update_user(user_id, "state", "admin_set_min_withdraw")
            bot.send_message(call.message.chat.id, "💳 নতুন মিনিমাম উইথড্র অ্যামাউন্ট লিখুন:")

        elif act == "set_pass":
            update_user(user_id, "state", "admin_set_pass")
            bot.send_message(call.message.chat.id, "🔑 নতুন জিমেইলের জন্য ফিক্সড পাসওয়ার্ড লিখুন:")

        elif act == "add_btn":
            update_user(user_id, "state", "admin_add_custom_btn")
            bot.send_message(call.message.chat.id, "➕ নতুন বাটনের নাম লিখুন:")

        elif act == "del_btn":
            custom_btns = data.get("custom_buttons", [])
            if not custom_btns:
                bot.send_message(call.message.chat.id, "❌ কোনো ডিলিট করার মতো কাস্টম বাটন নেই!")
            else:
                markup = InlineKeyboardMarkup(row_width=1)
                for btn in custom_btns:
                    markup.add(ibtn(f"🗑️ Delete: {btn}", callback_data=f"del_cbtn_{btn}", style="danger"))
                bot.send_message(call.message.chat.id, "🗑️ <b>যে বাটনটি মুছে ফেলতে চান তাতে চাপ দিন:</b>", parse_mode="HTML", reply_markup=markup)

        elif act == "add_bal":
            update_user(user_id, "state", "admin_add_bal")
            bot.send_message(call.message.chat.id, "➕ লিখুন: `USER_ID AMOUNT`", parse_mode="Markdown")

        elif act == "cut_bal":
            update_user(user_id, "state", "admin_cut_bal")
            bot.send_message(call.message.chat.id, "➖ লিখুন: `USER_ID AMOUNT`", parse_mode="Markdown")

        elif act == "ban":
            update_user(user_id, "state", "admin_ban_user")
            bot.send_message(call.message.chat.id, "⛔ Ban করার জন্য USER_ID লিখুন:")

        elif act == "unban":
            update_user(user_id, "state", "admin_unban_user")
            bot.send_message(call.message.chat.id, "🟢 Unban করার জন্য USER_ID লিখুন:")

        elif act == "set_prices":
            update_user(user_id, "state", "admin_set_prices")
            bot.send_message(call.message.chat.id, "🏷️ লিখুন: `NEW_PRICE OLD_PRICE USED_PRICE`", parse_mode="Markdown")

        elif act == "search":
            update_user(user_id, "state", "admin_search_user")
            bot.send_message(call.message.chat.id, "🔎 ইউজার তথ্য দেখতে USER_ID লিখুন:")

        elif act == "broadcast":
            update_user(user_id, "state", "admin_broadcast")
            bot.send_message(call.message.chat.id, "📢 ব্রডকাস্ট মেসেজটি লিখুন:")

        elif act == "maint":
            data["maintenance_mode"] = not data["maintenance_mode"]
            save_db(data)
            st = "চালু (ON)" if data["maintenance_mode"] else "বন্ধ (OFF)"
            bot.send_message(call.message.chat.id, f"🔴 মেইনটেন্যান্স মোড বর্তমানে: {st}")

        elif act == "stats":
            msg = (f"📊 <b>Bot Overall Statistics</b>\n\n"
                   f"👥 Total Users: {len(data['users'])}\n"
                   f"📩 Pending New Mails: {len(data['pending_new_mails'])}\n"
                   f"👴 Pending Old Mails: {len(data['pending_old_mails'])}\n"
                   f"♻️ Pending Used Mails: {len(data['pending_used_mails'])}\n"
                   f"💸 Pending Withdraws: {len(data['pending_withdraws'])}\n"
                   f"📧 Used Emails Saved in DB: {len(data['used_emails_database'])}")
            bot.send_message(call.message.chat.id, msg, parse_mode="HTML")

        elif act == "export":
            with open(DATA_FILE, "rb") as f:
                bot.send_document(call.message.chat.id, f)

        elif act in ["p_new", "p_old", "p_used", "p_with"]:
            bot.send_message(call.message.chat.id, f"📥 পেন্ডিং তালিকা থেকে রিভিউ করুন (লাইভ নোটিফিকেশন থেকে এপ্রুভ বা রিজেক্ট করুন)।")
        return

    elif call.data == "verify_join":
        left = check_force_join(user_id)
        if left:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো সব চ্যানেলে জয়েন করেননি!", show_alert=True)
            return

        bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!")
        
        user = get_user(user_id)
        if user.get("referred_by") and not user.get("ref_rewarded"):
            ref_id = str(user["referred_by"])
            if ref_id in data["users"]:
                ref_bonus = data.get("ref_bonus_verify", 0.40)
                data["users"][ref_id]["balance"] += ref_bonus
                data["users"][ref_id]["total_ref_bonus"] += ref_bonus
                
                data["users"][ref_id]["referral_list"].append({
                    "id": user_id,
                    "name": call.from_user.first_name,
                    "username": call.from_user.username or "",
                    "active": False
                })
                data["users"][str(user_id)]["ref_rewarded"] = True
                save_db(data)
                try:
                    bot.send_message(ref_id, f"🎉 <b>New Referral Joined!</b>\nআপনি রেফার বোনাস <b>৳{ref_bonus:.2f}</b> পেয়েছেন!", parse_mode="HTML")
                except:
                    pass

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

        if not user.get("lang"):
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("English 🇬🇧", callback_data="setlang_en", style="primary"),
                ibtn("বাংলা 🇧🇩", callback_data="setlang_bn", style="success")
            )
            bot.send_message(call.message.chat.id, "🌐 <b>মেসেজের ভাষা নির্ধারণ করুন / Select Bot Language:</b>", parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "✅ একাউন্ট ভেরিফাইড!", reply_markup=get_main_menu(user_id))

    elif call.data.startswith("setlang_"):
        lang = call.data.replace("setlang_", "")
        update_user(user_id, "lang", lang)
        bot.answer_callback_query(call.id, "Language Saved!")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        
        welcome_txt = "✅ <b>Language set successfully!</b>" if lang == "en" else "✅ <b>ভাষা সফলভাবে সেট করা হয়েছে!</b>"
        bot.send_message(call.message.chat.id, welcome_txt, parse_mode="HTML", reply_markup=get_main_menu(user_id))

    elif call.data == "submit_new_mail_check":
        user = get_user(user_id)
        session = user.get("active_new_mail_session")

        if not session:
            bot.answer_callback_query(call.id, "❌ আপনার কোনো সক্রিয় টাস্ক নেই!", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "⏳ <b>অপেক্ষা করুন চেক করা হচ্ছে……</b>", parse_mode="HTML")
        time.sleep(2)
        try: bot.delete_message(call.message.chat.id, msg.message_id)
        except: pass

        elapsed = time.time() - session.get("start_time", 0)

        if elapsed < 120:
            bot.send_message(call.message.chat.id, "❌ <b>আপনি জিমেইল অ্যাকাউন্ট খুলেননি! সঠিক নিয়মে অ্যাকাউন্ট তৈরি করে চেষ্টা করুন।</b>", parse_mode="HTML")
        else:
            email = session["email"]
            if email in data.get("used_emails_database", []):
                bot.send_message(call.message.chat.id, "⚠️ <b>এই জিমেইলটি ইতিমধ্যেই সিস্টেমে জমা হয়েছে!</b>", parse_mode="HTML")
                update_user(user_id, "active_new_mail_session", None)
                return

            req_key = f"new_{user_id}_{int(time.time())}"
            data["pending_new_mails"][req_key] = {
                "user_id": user_id,
                "first_name": session["first_name"],
                "last_name": session["last_name"],
                "email": email,
                "password": session["password"],
                "price": data.get("new_mail_price", 10.0),
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            data["used_emails_database"].append(email)
            
            uid = str(user_id)
            data["users"][uid]["pending_mails"] += 1
            data["users"][uid]["active_new_mail_session"] = None
            save_db(data)

            bot.send_message(call.message.chat.id, "✅ <b>আপনার জিমেইল সাবমিট করা হয়েছে। ৬-৭২ ঘন্টার মধ্যে যাচাই করে ব্যালেন্স যোগ করা হবে।</b>", parse_mode="HTML")

            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("✅ Approve", callback_data=f"appr_new_{req_key}", style="success"),
                ibtn("❌ Reject", callback_data=f"rej_new_{req_key}", style="danger")
            )
            bot.send_message(ADMIN_ID, f"📩 <b>New Gmail Submitted!</b>\nUser: <code>{user_id}</code>\nEmail: <code>{email}</code>\nPass: <code>{session['password']}</code>", parse_mode="HTML", reply_markup=markup)

    elif call.data.startswith("with_select_"):
        method = call.data.replace("with_select_", "")
        user = get_user(user_id)
        
        if user["balance"] < data.get("min_withdraw", 50.0):
            bot.answer_callback_query(call.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! মিনিমাম উইথড্র ৳{data.get('min_withdraw', 50.0)}", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        uid = str(user_id)
        data["users"][uid]["temp_data"] = {"withdraw_method": method}
        data["users"][uid]["state"] = "enter_withdraw_acc"
        save_db(data)

        bot.send_message(call.message.chat.id, f"📲 <b>আপনার {method} নম্বর/এড্রেস দিন:</b>", parse_mode="HTML")

    elif call.data.startswith("del_cbtn_") and str(user_id) == str(ADMIN_ID):
        btn_name = call.data.replace("del_cbtn_", "")
        if btn_name in data.get("custom_buttons", []):
            data["custom_buttons"].remove(btn_name)
            save_db(data)
            bot.answer_callback_query(call.id, f"✅ '{btn_name}' বাটনটি ডিলিট করা হয়েছে!", show_alert=True)
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass

    elif call.data.startswith("appr_") or call.data.startswith("rej_"):
        if str(user_id) != str(ADMIN_ID): return
        
        bot.answer_callback_query(call.id)
        action, mail_type, req_key = call.data.split("_", 2)
        target_dict = None
        if mail_type == "new": target_dict = data["pending_new_mails"]
        elif mail_type == "old": target_dict = data["pending_old_mails"]
        elif mail_type == "used": target_dict = data["pending_used_mails"]

        if target_dict and req_key in target_dict:
            item = target_dict[req_key]
            u_id = str(item["user_id"])
            price = item["price"]

            if action == "appr":
                data["users"][u_id]["balance"] += price
                data["users"][u_id]["success_mails"] += 1
                if data["users"][u_id]["pending_mails"] > 0:
                    data["users"][u_id]["pending_mails"] -= 1

                if data["users"][u_id]["success_mails"] >= 3:
                    ref_by = data["users"][u_id].get("referred_by")
                    if ref_by and ref_by in data["users"]:
                        for r in data["users"][ref_by]["referral_list"]:
                            if str(r["id"]) == u_id:
                                r["active"] = True

                del target_dict[req_key]
                save_db(data)
                bot.edit_message_text(f"✅ Approved! ৳{price} added to {u_id}", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, f"🎉 আপনার জিমেইল অনুমোদিত হয়েছে! <b>৳{price}</b> ব্যালেন্সে যোগ করা হয়েছে।", parse_mode="HTML")
                except: pass

            elif action == "rej":
                if data["users"][u_id]["pending_mails"] > 0:
                    data["users"][u_id]["pending_mails"] -= 1
                del target_dict[req_key]
                save_db(data)
                bot.edit_message_text(f"❌ Rejected for {u_id}", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, "❌ আপনার জমা দেওয়া জিমেইলটি বাতিল করা হয়েছে।", parse_mode="HTML")
                except: pass

    elif call.data.startswith("wappr_") or call.data.startswith("wrej_"):
        if str(user_id) != str(ADMIN_ID): return
        bot.answer_callback_query(call.id)
        action, w_key = call.data.split("_", 1)
        
        if w_key in data["pending_withdraws"]:
            w_item = data["pending_withdraws"][w_key]
            u_id = str(w_item["user_id"])
            amt = w_item["amount"]

            if action == "wappr":
                data["users"][u_id]["total_withdraw"] += amt
                if data["users"][u_id]["pending_withdraw"] >= amt:
                    data["users"][u_id]["pending_withdraw"] -= amt
                del data["pending_withdraws"][w_key]
                save_db(data)
                bot.edit_message_text(f"✅ Withdrawal Approved (৳{amt}) for {u_id}", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, f"🎉 আপনার ৳{amt} উইথড্র সফলভাবে সম্পন্ন হয়েছে!", parse_mode="HTML")
                except: pass

            elif action == "wrej":
                data["users"][u_id]["balance"] += amt
                if data["users"][u_id]["pending_withdraw"] >= amt:
                    data["users"][u_id]["pending_withdraw"] -= amt
                del data["pending_withdraws"][w_key]
                save_db(data)
                bot.edit_message_text(f"❌ Withdrawal Rejected & Refunded (৳{amt}) for {u_id}", call.message.chat.id, call.message.message_id)
                try: bot.send_message(u_id, f"❌ আপনার ৳{amt} উইথড্র বাতিল করা হয়েছে এবং ব্যালেন্স ব্যাক দেওয়া হয়েছে।", parse_mode="HTML")
                except: pass

# ============================================
# --- MAIN MESSAGE HANDLER ---
# ============================================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()
    data = load_db()

    if text.lower() == "/developer":
        developer_cmd(message)
        return

    if data.get("maintenance_mode") and str(user_id) != str(ADMIN_ID):
        bot.send_message(message.chat.id, "🔴 <b>বট বর্তমানে মেইনটেন্যান্স মোডে আছে।</b>", parse_mode="HTML")
        return

    if str(user_id) in data.get("banned_users", []):
        bot.send_message(message.chat.id, "⛔ আপনি ব্লকড আছেন।")
        return

    left = check_force_join(user_id)
    if left:
        bot.send_message(message.chat.id, "⚠️ <b>আপনি চ্যানেল থেকে লিভ নিয়েছেন! কাজ চালিয়ে যেতে আবার জয়েন করুন:</b>", parse_mode="HTML", reply_markup=get_force_join_markup(left))
        return

    user = get_user(user_id, message.from_user.first_name, message.from_user.username or "")

    # ==================== MAIN MENU BUTTON COMMANDS (RESETS STATE) ====================
    all_main_menu_btns = [
        "💰 মোট ব্যালেন্স", "💰 𝑩𝒂𝒍𝒂𝒏𝒄𝒆",
        "👥 রেফার", "👥 𝑩𝒆𝒇𝒆𝒓𝒓𝒂𝒍",
        "📧 নতুন জিমেইল সেল", "📧 𝑵𝒆𝒘 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆",
        "👴 পুরাতন জিমেইল সেল", "👴 𝑶𝒍𝒅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆",
        "♻️ ইউজ জিমেইল সেল", "♻️ 𝑼𝒔𝒆𝒅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆",
        "📥 উইথড্র করুন", "📥 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘",
        "🏆 লিডারবোর্ড", "🏆 𝑳𝒆𝒂𝒅𝒆𝒓𝒃𝒐𝒂𝒓𝒅",
        "⚙️ Admin Panel"
    ] + data.get("custom_buttons", [])

    # ইউজার কোনো বাটনে চাপ দিলে অটোমেটিক তার আগের State মুছে যাবে
    if text in all_main_menu_btns:
        update_user(user_id, "state", None)

        if text in ["💰 মোট ব্যালেন্স", "💰 𝑩𝒂𝒍𝒂𝒏𝒄𝒆"]:
            msg = (f"👤 <b>Account Details Dashboard</b>\n\n"
                   f"💰 মোট ব্যালেন্স: <b>৳{user['balance']:.2f}</b>\n"
                   f"🎁 মোট রেফার বোনাস: <b>৳{user['total_ref_bonus']:.2f}</b>\n"
                   f"📤 মোট উইথড্র: <b>৳{user['total_withdraw']:.2f}</b>\n"
                   f"⏳ পেন্ডিং উইথড্র: <b>৳{user['pending_withdraw']:.2f}</b>\n\n"
                   f"✅ সাকসেস মেইল: <b>{user['success_mails']} টি</b>\n"
                   f"⏳ পেন্ডিং মেইল: <b>{user['pending_mails']} টি</b>")
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
            return

        elif text in ["👥 রেফার", "👥 𝑩𝒆𝒇𝒆𝒓𝒓𝒂𝒍"]:
            bot_uname = bot.get_me().username
            ref_link = f"https://t.me/{bot_uname}?start={user_id}"
            
            msg = (f"👥 <b>Refer & Earn Program</b>\n\n"
                   f"🔗 <b>আপনার রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
                   f"📜 <b>রেফারেল রুলস:</b>\n"
                   f"১. আপনার লিংক থেকে জয়েন করে ভেরিফাই করলে পাবেন <b>৳{data.get('ref_bonus_verify', 0.40)}</b>!\n"
                   f"২. আপনার রেফার করা ব্যক্তি <b>৩ টি জিমেইল সেল</b> দিলে সে আপনার Active Refer সদস্য হবে!\n\n"
                   f"📊 <b>মোট রেফার করা সদস্য:</b> {len(user['referral_list'])} জন")
            
            markup = InlineKeyboardMarkup()
            markup.add(ibtn("📋 আপনার রেফারেল লিস্ট দেখুন", callback_data="show_ref_list", style="primary"))
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)
            return

        elif text in ["📧 নতুন জিমেইল সেল", "📧 𝑵𝒆𝒘 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆"]:
            fn, ln, email = generate_gmail_details()
            passw = data.get("new_mail_password", "NRGmailShopPass@2026")
            
            uid = str(user_id)
            data["users"][uid]["active_new_mail_session"] = {
                "first_name": fn,
                "last_name": ln,
                "email": email,
                "password": passw,
                "start_time": time.time()
            }
            save_db(data)

            msg = (f"📧 <b>নতুন জিমেইল তৈরির তথ্য:</b>\n\n"
                   f"👤 First Name: <code>{fn}</code>\n"
                   f"👤 Last Name: <code>{ln}</code>\n"
                   f"✉️ Gmail Address: <code>{email}</code>\n"
                   f"🔑 Password: <code>{passw}</code>\n"
                   f"💰 Rate: <b>৳{data.get('new_mail_price', 10.0)}</b>\n\n"
                   f"ℹ️ <i>লেখাগুলোর ওপর ক্লিক করে কপি করুন। অ্যাকাউন্ট সম্পূর্ণ তৈরি করা শেষ হলে নিচের Subject বাটনে চাপ দিন।</i>")
            
            markup = InlineKeyboardMarkup()
            markup.add(ibtn("✅ Subject / জিমেইল খোলা শেষ", callback_data="submit_new_mail_check", style="success"))
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)
            return

        elif text in ["👴 পুরাতন জিমেইল সেল", "👴 𝑶𝒍𝒅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆"]:
            update_user(user_id, "state", "enter_old_mail_address")
            update_user(user_id, "temp_data", {"type": "old"})
            bot.send_message(message.chat.id, "👴 <b>আপনার পুরাতন জিমেইল এড্রেসটি এখানে সাবমিট করুন 👇</b>", parse_mode="HTML")
            return

        elif text in ["♻️ ইউজ জিমেইল সেল", "♻️ 𝑼𝒔𝒆𝒅 𝑮𝒎𝒂𝒊𝒍 𝑺𝒂𝒍𝒆"]:
            update_user(user_id, "state", "enter_old_mail_address")
            update_user(user_id, "temp_data", {"type": "used"})
            bot.send_message(message.chat.id, "♻️ <b>আপনার ইউজড (Used) জিমেইল এড্রেসটি এখানে সাবমিট করুন 👇</b>", parse_mode="HTML")
            return

        elif text in ["📥 উইথড্র করুন", "📥 𝑾𝒊𝒕𝒉𝒅𝒓𝒂𝒘"]:
            min_w = data.get("min_withdraw", 50.0)
            msg = f"📥 <b>উইথড্র সিস্টেম</b>\n\nবর্তমান মিনিমাম উইথড্র: <b>৳{min_w:.2f}</b>\nনিচে থেকে আপনার পেমেন্ট মেথড সিলেক্ট করুন:"
            
            markup = InlineKeyboardMarkup(row_width=2)
            btns = []
            for m, enabled in data.get("withdraw_methods", {}).items():
                if enabled: btns.append(ibtn(m, callback_data=f"with_select_{m}", style="primary"))
            markup.add(*btns)
            bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)
            return

        elif text in ["🏆 লিডারবোর্ড", "🏆 𝑳𝒆𝒂𝒅𝒆𝒓𝒃𝒐𝒂𝒓𝒅"]:
            msg = "🏆 <b>24 Hours Top Leaderboard Rewards</b> 🏆\n\n"
            msg += "🥇 টপ ১০ জনের জন্য বিশেষ পুরস্কার বোনাস:\n"
            msg += "• ১০টির বেশি সেল/রেফার: <b>৳৫০ বোনাস</b>\n"
            msg += "• ৭ - ১০ নম্বর পজিশন: <b>৳২০ বোনাস</b>\n"
            msg += "• ৪ - ৭ নম্বর পজিশন: <b>৳১০ বোনাস</b>\n"
            msg += "• ২ - ৪ নম্বর পজিশন: <b>৳২ বোনাস</b>\n\n"
            msg += "📊 <i>প্রতি ২৪ ঘন্টা পর অটোমেটিক বোনাস প্রদান ও রিসেট করা হয়।</i>"
            bot.send_message(message.chat.id, msg, parse_mode="HTML")
            return

        elif text == "⚙️ Admin Panel" and str(user_id) == str(ADMIN_ID):
            bot.send_message(message.chat.id, "⚙️ <b>Admin Control Panel:</b>", parse_mode="HTML", reply_markup=get_admin_inline_menu())
            return

    # ==================== USER STATE FLOWS ====================
    state = user.get("state")

    if state == "enter_old_mail_address":
        if "@gmail.com" not in text:
            bot.send_message(message.chat.id, "❌ সঠিক জিমেইল এড্রেস লিখুন (যেমন: test@gmail.com):")
            return
        
        if text in data.get("used_emails_database", []):
            bot.send_message(message.chat.id, "⚠️ এই জিমেইলটি ইতিমধ্যেই জমা দেওয়া হয়েছে!")
            update_user(user_id, "state", None)
            return

        uid = str(user_id)
        data["users"][uid]["temp_data"]["email"] = text
        data["users"][uid]["state"] = "enter_old_mail_pass"
        save_db(data)
        bot.send_message(message.chat.id, "🔑 <b>আপনার জিমেইলের পাসওয়ার্ড দিন:</b>", parse_mode="HTML")
        return

    elif state == "enter_old_mail_pass":
        uid = str(user_id)
        data["users"][uid]["temp_data"]["password"] = text
        data["users"][uid]["state"] = "enter_old_mail_rec"
        save_db(data)
        
        rec_gmail = data.get("recovery_gmail", "nr_recovery2026@gmail.com")
        msg = (f"⚠️ <b>গুরুত্বপূর্ণ ধাপ:</b>\n\n"
               f"নিচের রিকভারি জিমেইলটি আপনার মেইলে যুক্ত করুন এবং ফোন থেকে রিমুভ/সাইন আউট করুন:\n"
               f"<code>{rec_gmail}</code>\n\n"
               f"কাজ শেষে নিশ্চিত হতে উপরে দেওয়া রিকভারি জিমেইলটি রি-টাইপ করে নিচে সেন্ড করুন 👇")
        bot.send_message(message.chat.id, msg, parse_mode="HTML")
        return

    elif state == "enter_old_mail_rec":
        uid = str(user_id)
        m_type = user["temp_data"].get("type", "old")
        
        req_key = f"{m_type}_{user_id}_{int(time.time())}"
        email = user["temp_data"]["email"]
        price = data.get(f"{m_type}_mail_price", 15.0)

        item_data = {
            "user_id": user_id,
            "email": email,
            "password": user["temp_data"]["password"],
            "recovery": text,
            "price": price,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        if m_type == "old":
            data["pending_old_mails"][req_key] = item_data
        else:
            data["pending_used_mails"][req_key] = item_data

        data["used_emails_database"].append(email)
        data["users"][uid]["pending_mails"] += 1
        data["users"][uid]["state"] = None
        data["users"][uid]["temp_data"] = {}
        save_db(data)

        bot.send_message(message.chat.id, "✅ <b>আপনার জিমেইল তথ্য জমা হয়েছে! এডমিন অতি দ্রুত রিভিউ করবে।</b>", parse_mode="HTML", reply_markup=get_main_menu(user_id))
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            ibtn("✅ Approve", callback_data=f"appr_{m_type}_{req_key}", style="success"),
            ibtn("❌ Reject", callback_data=f"rej_{m_type}_{req_key}", style="danger")
        )
        bot.send_message(ADMIN_ID, f"📩 <b>New {m_type.upper()} Mail Submitted!</b>\nUser: <code>{user_id}</code>\nEmail: <code>{email}</code>\nPass: <code>{item_data['password']}</code>", parse_mode="HTML", reply_markup=markup)
        return

    elif state == "enter_withdraw_acc":
        uid = str(user_id)
        data["users"][uid]["temp_data"]["acc_num"] = text
        data["users"][uid]["state"] = "enter_withdraw_amt"
        save_db(data)
        bot.send_message(message.chat.id, f"💵 <b>উইথড্র টাকার পরিমাণ লিখুন (মিনিমাম ৳{data.get('min_withdraw', 50.0)}):</b>", parse_mode="HTML")
        return

    elif state == "enter_withdraw_amt":
        try:
            amt = float(text)
            min_w = data.get("min_withdraw", 50.0)
            if amt < min_w:
                bot.send_message(message.chat.id, f"❌ মিনিমাম উইথড্র লিমিট ৳{min_w:.2f}")
                return
            if amt > user["balance"]:
                bot.send_message(message.chat.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! বর্তমান ব্যালেন্স: ৳{user['balance']:.2f}")
                return

            uid = str(user_id)
            method = user["temp_data"]["withdraw_method"]
            acc_num = user["temp_data"]["acc_num"]

            data["users"][uid]["balance"] -= amt
            data["users"][uid]["pending_withdraw"] += amt
            data["users"][uid]["state"] = None
            data["users"][uid]["temp_data"] = {}

            w_key = f"w_{user_id}_{int(time.time())}"
            data["pending_withdraws"][w_key] = {
                "user_id": user_id,
                "method": method,
                "acc_num": acc_num,
                "amount": amt,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_db(data)

            bot.send_message(message.chat.id, "🕊️ <b>আপনার উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে। ধৈর্য ধরে অপেক্ষা করুন!</b>", parse_mode="HTML", reply_markup=get_main_menu(user_id))

            admin_msg = (f"💸 <b>NEW WITHDRAWAL REQUEST!</b>\n\n"
                         f"👤 Name: {user['name']}\n"
                         f"🔗 Username: @{user['username']}\n"
                         f"🆔 User ID: <code>{user_id}</code>\n"
                         f"💳 Method: {method}\n"
                         f"📱 Account: <code>{acc_num}</code>\n"
                         f"💰 Amount: ৳<b>{amt:.2f}</b>\n"
                         f"⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                ibtn("✅ Approve", callback_data=f"wappr_{w_key}", style="success"),
                ibtn("❌ Reject", callback_data=f"wrej_{w_key}", style="danger")
            )
            bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML", reply_markup=markup)
            return
        except ValueError:
            bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন:")
            return

    # ==================== ADMIN STATE FLOWS ====================
    if str(user_id) == str(ADMIN_ID) and state:
        if state == "admin_set_channel":
            if text.startswith("@"):
                data["force_channels"].append(text)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ চ্যানেল যুক্ত হয়েছে: {text}")
            else:
                bot.send_message(message.chat.id, "❌ `@` দিয়ে ইউজারনেম দিন।")
            update_user(user_id, "state", None)
            return

        elif state == "admin_set_ref_bonus":
            try:
                data["ref_bonus_verify"] = float(text)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ নতুন রেফার ভেরিফাই বোনাস: ৳{float(text)}")
            except: bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন।")
            update_user(user_id, "state", None)
            return

        elif state == "admin_set_min_withdraw":
            try:
                data["min_withdraw"] = float(text)
                save_db(data)
                bot.send_message(message.chat.id, f"✅ নতুন মিনিমাম উইথড্র: ৳{float(text)}")
            except: bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন।")
            update_user(user_id, "state", None)
            return

        elif state == "admin_set_pass":
            data["new_mail_password"] = text
            save_db(data)
            bot.send_message(message.chat.id, f"✅ নিউ মেইল পাসওয়ার্ড আপডেট হয়েছে: `{text}`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "admin_add_custom_btn":
            data["custom_buttons"].append(text)
            save_db(data)
            bot.send_message(message.chat.id, f"✅ মেইন মেনুতে নতুন বাটন যুক্ত হয়েছে: {text}", reply_markup=get_main_menu(user_id))
            update_user(user_id, "state", None)
            return

        elif state == "admin_add_bal":
            try:
                t_id, amt = text.split()
                t_id, amt = str(t_id), float(amt)
                if t_id in data["users"]:
                    data["users"][t_id]["balance"] += amt
                    save_db(data)
                    bot.send_message(message.chat.id, f"✅ Added ৳{amt} to {t_id}")
                    try: bot.send_message(t_id, f"🎉 Admin added ৳{amt} to your balance!")
                    except: pass
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `USER_ID AMOUNT`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "admin_cut_bal":
            try:
                t_id, amt = text.split()
                t_id, amt = str(t_id), float(amt)
                if t_id in data["users"]:
                    data["users"][t_id]["balance"] -= amt
                    save_db(data)
                    bot.send_message(message.chat.id, f"✅ Deducted ৳{amt} from {t_id}")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `USER_ID AMOUNT`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "admin_ban_user":
            data["banned_users"].append(text.strip())
            save_db(data)
            bot.send_message(message.chat.id, f"⛔ User {text} Banned!")
            update_user(user_id, "state", None)
            return

        elif state == "admin_unban_user":
            if text.strip() in data["banned_users"]:
                data["banned_users"].remove(text.strip())
                save_db(data)
                bot.send_message(message.chat.id, f"🟢 User {text} Unbanned!")
            update_user(user_id, "state", None)
            return

        elif state == "admin_set_prices":
            try:
                p_new, p_old, p_used = text.split()
                data["new_mail_price"] = float(p_new)
                data["old_mail_price"] = float(p_old)
                data["used_mail_price"] = float(p_used)
                save_db(data)
                bot.send_message(message.chat.id, "✅ দাম আপডেট হয়েছে!")
            except: bot.send_message(message.chat.id, "❌ ফরম্যাট: `NEW_PRICE OLD_PRICE USED_PRICE`", parse_mode="Markdown")
            update_user(user_id, "state", None)
            return

        elif state == "admin_search_user":
            t_id = text.strip()
            if t_id in data["users"]:
                u = data["users"][t_id]
                msg = (f"🔎 <b>User History ({t_id})</b>\n\n"
                       f"👤 Name: {u['name']}\n"
                       f"💰 Balance: ৳{u['balance']:.2f}\n"
                       f"📊 Success Mails: {u['success_mails']}\n"
                       f"⏳ Pending Mails: {u['pending_mails']}\n"
                       f"👥 Total Refers: {len(u['referral_list'])}\n"
                       f"📥 Withdraws: ৳{u['total_withdraw']:.2f}")
                bot.send_message(message.chat.id, msg, parse_mode="HTML")
            else: bot.send_message(message.chat.id, "❌ ইউজার পাওয়া যায়নি।")
            update_user(user_id, "state", None)
            return

        elif state == "admin_broadcast":
            count = 0
            for u in data["users"]:
                try:
                    bot.send_message(u, f"📢 <b>Broadcast Notice:</b>\n\n{text}", parse_mode="HTML")
                    count += 1
                except: pass
            bot.send_message(message.chat.id, f"✅ {count} জনের কাছে মেসেজ পাঠানো হয়েছে!")
            update_user(user_id, "state", None)
            return

# ============================================
# --- BOT STARTUP ---
# ============================================
if __name__ == "__main__":
    keep_alive()
    print(f"🚀 {BOT_NAME} Started Successfully...")
    bot.infinity_polling()
