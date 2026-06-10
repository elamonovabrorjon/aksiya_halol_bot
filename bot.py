import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import threading
import time
import json
import os
from datetime import datetime
import yfinance as yf
import pandas as pd
import ta

# ===================== SOZLAMALAR =====================
TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
ADMIN_ID = 745170275

bot = telebot.TeleBot(TOKEN)

# ===================== FOYDALANUVCHILARNI SAQLASH =====================
USERS_FILE = "users.json"
SCHEDULE_FILE = "schedule.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_user(user_id, username=None):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    return users

def get_all_users():
    return load_users()

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f)
    return {"hour": 9, "minute": 0, "enabled": False, "message": "Kunlik signal hali sozlanmagan"}

def save_schedule(schedule):
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule, f)

# ===================== TAHLIL FUNKSIYALARI =====================
def get_data(symbol, tf="1h"):
    period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "30m": "5d", "1h": "1mo", "4h": "1mo", "1d": "3mo"}
    df = yf.download(symbol, period=period_map.get(tf, "5d"), interval=tf, progress=False)
    
    if df.empty:
        return df
    
    df['rsi'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    return df

def analyze_trend(df):
    if len(df) < 20:
        return "NEUTRAL"
    last = df.iloc[-1]
    if last['ema9'] > last['ema21'] > last['ema50']:
        return "STRONG UP 📈"
    elif last['ema9'] < last['ema21'] < last['ema50']:
        return "STRONG DOWN 📉"
    elif last['ema9'] > last['ema21']:
        return "WEAK UP ↗️"
    elif last['ema9'] < last['ema21']:
        return "WEAK DOWN ↘️"
    return "RANGE ↔️"

def generate_full_analysis():
    """Kunlik tahlil yaratish"""
    symbols = {
        "🏦 BITCOIN": "BTC-USD",
        "🥇 GOLD": "XAUUSD=X",
        "💶 EUR/USD": "EURUSD=X",
        "📈 S&P 500": "^GSPC",
        "🛢️ OIL": "CL=F"
    }
    
    analysis = f"📊 **KUNLIK BOZOR TAHLILI**\n📅 {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for name, symbol in symbols.items():
        try:
            df = get_data(symbol, "4h")
            if not df.empty:
                last = df.iloc[-1]
                trend = analyze_trend(df)
                rsi = last['rsi'] if not pd.isna(last['rsi']) else 50
                
                analysis += f"{name}\n"
                analysis += f"💰 Narx: ${round(last['Close'], 2)}\n"
                analysis += f"📈 Trend: {trend}\n"
                analysis += f"📊 RSI: {round(rsi, 1)}\n"
                
                # Signal
                if rsi < 30 and "UP" in trend:
                    analysis += f"🎯 SIGNAL: **BUY 🟢**\n"
                elif rsi > 70 and "DOWN" in trend:
                    analysis += f"🎯 SIGNAL: **SELL 🔴**\n"
                else:
                    analysis += f"🎯 SIGNAL: HOLD ⚪\n"
                
                analysis += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        except:
            continue
    
    analysis += f"\n💡 *Maslahat: Har doim stop-loss ishlating!*"
    return analysis

# ===================== KUNLIK XABAR FUNKSIYASI =====================
def send_daily_report():
    """Sozlangan vaqtda kunlik xabar yuborish"""
    while True:
        schedule = load_schedule()
        
        if schedule.get("enabled", False):
            now = datetime.now()
            target_hour = schedule.get("hour", 9)
            target_minute = schedule.get("minute", 0)
            
            if now.hour == target_hour and now.minute == target_minute:
                # Xabar yuborish
                users = get_all_users()
                custom_msg = schedule.get("message", "Kunlik tahlil")
                
                # Tahlil yaratish
                analysis = generate_full_analysis()
                
                for user_id in users:
                    try:
                        bot.send_message(user_id, f"🌅 **KUNLIK SIGNAL**\n\n{custom_msg}\n\n{analysis}", parse_mode='Markdown')
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"Xatolik: {user_id} - {e}")
                
                print(f"✅ Kunlik xabar yuborildi: {len(users)} ta foydalanuvchiga - {datetime.now()}")
                
                # Takrorlanmasligi uchun 60 sekund kutish
                time.sleep(60)
        
        time.sleep(30)

# ===================== ASOSIY MENU =====================
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("👑 ADMIN PANEL"))
    return markup

def admin_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("📊 SIGNAL"),
        KeyboardButton("🏦 STOCK"),
        KeyboardButton("💰 FOREX"),
        KeyboardButton("🥇 CRYPTO"),
        KeyboardButton("✅ HALOL STOCKS"),
        KeyboardButton("⚙️ BACKTEST"),
        KeyboardButton("⏰ KUNLIK XABAR"),
        KeyboardButton("📢 BROADCAST"),
        KeyboardButton("👥 USERS"),
        KeyboardButton("🔙 MAIN MENU")
    ]
    for btn in buttons:
        markup.add(btn)
    return markup

# ===================== TELEGRAM HANDLERS =====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    save_user(user_id, message.from_user.username)
    
    welcome = """
👋 **Assalomu alaykum!**

Botga xush kelibsiz.

👇 Quyidagi tugmani bosing
"""
    bot.send_message(message.chat.id, welcome, parse_mode='Markdown', reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "👑 ADMIN PANEL")
def admin_button(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz!")
        return
    
    msg = """
✨ **Assalomu alaykum admin!**

Quyidagi menyu orqali boshqaruv qiling:
"""
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=admin_panel())

@bot.message_handler(func=lambda message: message.text == "⏰ KUNLIK XABAR")
def schedule_menu(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz!")
        return
    
    schedule = load_schedule()
    status = "✅ YOQILGAN" if schedule.get("enabled") else "❌ O'CHIRILGAN"
    
    msg = f"""
⏰ **KUNLIK XABAR SOZLAMALARI**

📊 Holat: {status}
⏱️ Vaqt: {schedule.get('hour', 9)}:{schedule.get('minute', 0):02d}

📝 Xabar matni:
{schedule.get('message', 'Sozlanmagan')}

━━━━━━━━━━━━━━━━━━━━━━
Kerakli tugmani bosing:
"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🕐 VAQTNI SOZLASH"),
        KeyboardButton("📝 XABAR MATNINI SOZLASH"),
        KeyboardButton("🔛 XABARNI YOQISH"),
        KeyboardButton("🔴 XABARNI O'CHIRISH"),
        KeyboardButton("🔙 MAIN MENU")
    )
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🕐 VAQTNI SOZLASH")
def set_time(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "⏰ Vaqtni kiriting (masalan: `09:30` yoki `14:00`):", parse_mode='Markdown')
    bot.register_next_step_handler(message, save_time)

def save_time(message):
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            schedule = load_schedule()
            schedule["hour"] = hour
            schedule["minute"] = minute
            save_schedule(schedule)
            bot.reply_to(message, f"✅ Vaqt sozlandi: {hour:02d}:{minute:02d}")
        else:
            bot.reply_to(message, "❌ Noto'g'ri vaqt! 00:00 dan 23:59 gacha kiriting.")
    except:
        bot.reply_to(message, "❌ Noto'g'ri format! Masalan: 09:30")

@bot.message_handler(func=lambda message: message.text == "📝 XABAR MATNINI SOZLASH")
def set_message_text(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "📝 Kunlik xabar matnini yozing:\n\n*Eslatma: Bot avtomatik tahlilni ham qo'shib yuboradi*", parse_mode='Markdown')
    bot.register_next_step_handler(message, save_message_text)

def save_message_text(message):
    schedule = load_schedule()
    schedule["message"] = message.text
    save_schedule(schedule)
    bot.reply_to(message, f"✅ Xabar matni saqlandi!\n\nMatn: {message.text[:100]}...")

@bot.message_handler(func=lambda message: message.text == "🔛 XABARNI YOQISH")
def enable_schedule(message):
    if message.from_user.id != ADMIN_ID:
        return
    schedule = load_schedule()
    schedule["enabled"] = True
    save_schedule(schedule)
    bot.reply_to(message, f"✅ Kunlik xabar YOQILDI!\n⏰ Vaqt: {schedule['hour']:02d}:{schedule['minute']:02d}")

@bot.message_handler(func=lambda message: message.text == "🔴 XABARNI O'CHIRISH")
def disable_schedule(message):
    if message.from_user.id != ADMIN_ID:
        return
    schedule = load_schedule()
    schedule["enabled"] = False
    save_schedule(schedule)
    bot.reply_to(message, "❌ Kunlik xabar O'CHIRILDI!")

@bot.message_handler(func=lambda message: message.text == "📢 BROADCAST")
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz!")
        return
    bot.reply_to(message, "📢 Yubormoqchi bo'lgan xabaringizni yozing:")
    bot.register_next_step_handler(message, send_broadcast)

def send_broadcast(message):
    broadcast_text = message.text
    users = get_all_users()
    
    success = 0
    fail = 0
    
    bot.reply_to(message, f"⏳ {len(users)} ta foydalanuvchiga yuborilmoqda...")
    
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 **XABAR**\n\n{broadcast_text}", parse_mode='Markdown')
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
    
    bot.send_message(ADMIN_ID, f"✅ Yuborildi!\n✅ Muvaffaqiyatli: {success}\n❌ Xatolik: {fail}")

@bot.message_handler(func=lambda message: message.text == "👥 USERS")
def show_users(message):
    if message.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    bot.reply_to(message, f"📊 **STATISTIKA**\n\n👥 Jami foydalanuvchilar: {len(users)}")

@bot.message_handler(func=lambda message: message.text == "🔙 MAIN MENU")
def back_to_main(message):
    bot.send_message(message.chat.id, "🔙 Asosiy menyu", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "📊 SIGNAL")
def signal_quick(message):
    msg = bot.reply_to(message, "⏳ Tahlil qilinmoqda...")
    analysis = generate_full_analysis()
    bot.edit_message_text(analysis, message.chat.id, msg.message_id, parse_mode='Markdown')

# ===================== BOSHLASH =====================
if __name__ == "__main__":
    print("🤖 BOT ISHGA TUSHDI")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("=" * 40)
    print("⏰ Kunlik xabar vaqtini o'zingiz sozlaysiz:")
    print("   Admin panel -> KUNLIK XABAR -> VAQTNI SOZLASH")
    print("   Masalan: 09:30 yoki 14:00")
    print("=" * 40)
    
    # Kunlik xabar thread
    daily_thread = threading.Thread(target=send_daily_report, daemon=True)
    daily_thread.start()
    
    bot.infinity_polling()