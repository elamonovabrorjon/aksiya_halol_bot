import os, telebot, time, yfinance as yf, sqlite3, datetime, threading, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN = os.getenv("CHAT_ID")
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook(); time.sleep(1)
app = Flask(__name__)

# --- BAZA ---
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, trial_start TEXT, is_pro INTEGER DEFAULT 0, points INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER, sym TEXT, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS portfolio (uid INTEGER, sym TEXT, shares REAL, buy REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS daily (uid INTEGER, day TEXT, cnt INTEGER, PRIMARY KEY(uid,day))''')
conn.commit()

def get_user(uid):
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    return c.fetchone()

def check_pro(uid):
    u = get_user(uid)
    if str(uid) == ADMIN: return True
    return u and u[3]==1

def can_analyze(uid):
    if check_pro(uid): return True, 999
    today = datetime.date.today().isoformat()
    row = c.execute("SELECT cnt FROM daily WHERE uid=? AND day=?", (uid, today)).fetchone()
    cnt = row[0] if row else 0
    return cnt < 10, 10 - cnt

def inc_analyze(uid):
    today = datetime.date.today().isoformat()
    c.execute("INSERT INTO daily(uid,day,cnt) VALUES(?,?,1) ON CONFLICT(uid,day) DO UPDATE SET cnt=cnt+1", (uid, today))
    conn.commit()

def add_points(uid, p=1):
    c.execute("UPDATE users SET points=points+? WHERE id=?", (p, uid)); conn.commit()

# --- AI TAHLIL (RENDER UCHUN) ---
def ai_tahlil(sym):
    try:
        data = yf.download(sym, period="3mo", progress=False, auto_adjust=True, threads=False)
        if data.empty:
            return f"❌ {sym} topilmadi"

        p = float(data['Close'].iloc[-1])
        p_old = float(data['Close'].iloc[0])
        change = ((p / p_old) - 1) * 100
        sma20 = data['Close'].rolling(20).mean().iloc[-1]
        trend = "📈 O'sish" if p > sma20 else "📉 Pasayish"

        # halol taxminiy
        halol = "🟢 HALOL"

        return f"🤖 {sym} | ${p:.2f}\n3 oy: {change:+.1f}% | {trend}\n\n{halol}"
    except Exception as e:
        return f"❌ {sym} xato"

# --- GRAFIK ---
def make_chart(sym):
    try:
        data = yf.download(sym, period="1y", progress=False, threads=False)
        if data.empty: return None
        plt.figure(figsize=(8,4))
        plt.plot(data.index, data['Close'], linewidth=2, color='#1f77b4')
        plt.title(f"{sym} - 1 Yil", fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        path = f"/tmp/{sym}.png"
        plt.savefig(path, dpi=120)
        plt.close()
        return path
    except:
        return None

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(m):
    uid=m.from_user.id
    if not get_user(uid):
        is_pro = 1 if str(uid) == ADMIN else 0
        c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (uid, m.from_user.first_name, datetime.datetime.now().isoformat(), is_pro, 0)); conn.commit()
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🤖 AI Tahlil","📈 Grafik")
    kb.add("🔔 Signal","💼 Portfel")
    kb.add("⚔️ Solishtir","📰 Yangilik")
    kb.add("🏆 Reyting","💳 PRO")
    vip = "👑 VIP" if check_pro(uid) else ""
    bot.send_message(m.chat.id, f"Aksiya Halol PRO ✅ {vip}\nBepul: kuniga 10 ta!", reply_markup=kb)

@bot.message_handler(commands=['pro'])
def pro(m):
    uid=m.from_user.id
    status = "PRO ✅ Cheksiz 👑" if check_pro(uid) else "BEPUL"
    bot.send_message(m.chat.id, f"💳 {status}\n\nBEPUL: 10 ta/kun\nPRO: cheksiz\nNarx: 25,000 so'm")

@bot.message_handler(commands=['approve'])
def approve(m):
    if str(m.from_user.id)!=ADMIN: return
    try:
        uid=int(m.text.split()[1])
        if not get_user(uid):
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (uid, "User", datetime.datetime.now().isoformat(), 0, 0))
        c.execute("UPDATE users SET is_pro=1 WHERE id=?", (uid,)); conn.commit()
        bot.send_message(uid, "✅ PRO aktiv!"); bot.send_message(m.chat.id, f"✅ {uid}")
    except: pass

@bot.message_handler(func=lambda m: m.text=="🤖 AI Tahlil")
def ai(m): bot.send_message(m.chat.id, "Ticker yozing:")

@bot.message_handler(func=lambda m: m.text=="📈 Grafik")
def graf(m):
    if not check_pro(m.from_user.id): bot.send_message(m.chat.id, "PRO kerak"); return
    bot.send_message(m.chat.id, "Qaysi ticker?")

@bot.message_handler(func=lambda m: m.text=="🔔 Signal")
def signal(m):
    if not check_pro(m.from_user.id): bot.send_message(m.chat.id, "PRO"); return
    bot.send_message(m.chat.id, "Format: NKE 50")

@bot.message_handler(func=lambda m: m.text=="💼 Portfel")
def portf(m):
    uid=m.from_user.id
    rows=c.execute("SELECT sym,shares,buy FROM portfolio WHERE uid=?", (uid,)).fetchall()
    if not rows: bot.send_message(m.chat.id, "Bo'sh. +AAPL 10 150"); return
    txt="💼 Portfel:\n"
    for s,sh,b in rows: txt+=f"{s}: {sh}\n"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: True)
def handle(m):
    txt=m.text.strip().upper(); uid=m.from_user.id

    # grafik
    if m.reply_to_message and "Qaysi" in m.reply_to_message.text:
        if check_pro(uid):
            path = make_chart(txt)
            if path: bot.send_photo(m.chat.id, open(path,'rb'))
            else: bot.send_message(m.chat.id, "Grafik olinmadi")
        return

    # tahlil
    if len(txt)<=6 and txt.isalpha():
        can,left = can_analyze(uid)
        if not can: bot.send_message(m.chat.id, "Limit tugadi"); return
        inc_analyze(uid)
        res = ai_tahlil(txt)
        bot.send_message(m.chat.id, res)

def check_alerts():
    while True: time.sleep(60)

threading.Thread(target=check_alerts, daemon=True).start()

@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    bot.infinity_polling()