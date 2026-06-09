import os, telebot, time, yfinance as yf, sqlite3, datetime, threading, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN = os.getenv("CHAT_ID") # sizning ID ingiz
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
    # ADMIN avtomatik VIP
    if str(uid) == ADMIN:
        return True
    return u and u[3]==1

def can_analyze(uid):
    if check_pro(uid):
        return True, 999
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

# --- AI TAHLIL (TUZATILGAN) ---
def ai_tahlil(sym):
    try:
        t = yf.Ticker(sym)
        info = t.info or {}
        hist = t.history(period="5d")

        p = info.get('currentPrice') or info.get('regularMarketPrice') or (hist['Close'].iloc[-1] if not hist.empty else 0)

        if p == 0:
            return f"❌ {sym} topilmadi. To'g'ri yozing: AAPL, NKE, TSLA"

        pm = (info.get('profitMargins') or 0)*100
        roe = (info.get('returnOnEquity') or 0)*100
        de = info.get('debtToEquity') or 0
        div = (info.get('dividendYield') or 0)*100
        payout = (info.get('payoutRatio') or 0)*100

        halol = "🟢 HALOL" if de<33 and payout<100 else "🟡 SHUBHALI" if de<100 else "🔴 HARAMGA YAQIN"

        txt = f"🤖 {sym} | ${p:.2f}\nPM {pm:.1f}% | ROE {roe:.1f}%\nQarz {de:.0f}% | Div {div:.1f}%\n\n{halol}"
        return txt
    except Exception as e:
        return f"❌ {sym} ma'lumot olishda xato. 1 daqiqadan keyin urinib ko'ring."

# --- GRAFIK ---
def make_chart(sym):
    try:
        hist = yf.Ticker(sym).history(period="1y")
        plt.figure(figsize=(6,3)); plt.plot(hist.index, hist['Close']); plt.title(sym)
        plt.tight_layout(); path=f"/tmp/{sym}.png"; plt.savefig(path); plt.close()
        return path
    except:
        return None

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(m):
    uid=m.from_user.id
    if not get_user(uid):
        # ADMIN avtomatik PRO
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
    can, left = can_analyze(uid)
    status = "PRO ✅ Cheksiz 👑" if check_pro(uid) else f"BEPUL (bugun {10-left}/10)"
    txt = f"💳 {status}\n\nBEPUL: kuniga 10 ta\nPRO: cheksiz\nNarx: 25,000 so'm/oy\nTo'lov: /tolov"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(commands=['tolov'])
def tolov(m):
    bot.send_message(ADMIN, f"💰 To'lov: {m.from_user.first_name} ID:{m.from_user.id}")
    bot.send_message(m.chat.id, "Adminga yuborildi")

@bot.message_handler(commands=['approve'])
def approve(m):
    if str(m.from_user.id)!=ADMIN: return
    try:
        uid=int(m.text.split()[1])
        if not get_user(uid):
            c.execute("INSERT INTO users VALUES (?,?,?,?,?)", (uid, "User", datetime.datetime.now().isoformat(), 0, 0))
        c.execute("UPDATE users SET is_pro=1 WHERE id=?", (uid,)); conn.commit()
        bot.send_message(uid, "✅ PRO aktiv!"); bot.send_message(m.chat.id, f"✅ {uid} PRO")
    except Exception as e:
        bot.send_message(m.chat.id, f"Xato: {e}")

@bot.message_handler(func=lambda m: m.text=="🤖 AI Tahlil")
def ai(m): bot.send_message(m.chat.id, "Ticker yozing:"); add_points(m.from_user.id)

@bot.message_handler(func=lambda m: m.text=="📈 Grafik")
def graf(m):
    if not check_pro(m.from_user.id): bot.send_message(m.chat.id, "Grafik PRO da"); return
    bot.send_message(m.chat.id, "Qaysi?")

@bot.message_handler(func=lambda m: m.text=="🔔 Signal")
def signal(m):
    if not check_pro(m.from_user.id): bot.send_message(m.chat.id, "PRO kerak"); return
    bot.send_message(m.chat.id, "Format: NKE 50")

@bot.message_handler(func=lambda m: m.text=="💼 Portfel")
def portf(m):
    uid=m.from_user.id
    rows=c.execute("SELECT sym,shares,buy FROM portfolio WHERE uid=?", (uid,)).fetchall()
    if not rows: bot.send_message(m.chat.id, "Bo'sh. +AAPL 10 150"); return
    txt="💼 Portfel:\n"; total=0
    for s,sh,b in rows:
        p=yf.Ticker(s).info.get('currentPrice',0) or 0; pl=(p-b)*sh; total+=pl
        txt+=f"{s}: {sh} | {pl:+.0f}$\n"
    txt+=f"\nJami: {total:+.0f}$"; bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text in ["⚔️ Solishtir","📰 Yangilik","🏆 Reyting","💳 PRO"])
def others(m):
    if m.text=="⚔️ Solishtir": bot.send_message(m.chat.id, "AAPL vs MSFT")
    elif m.text=="📰 Yangilik": bot.send_message(m.chat.id, "PRO kerak" if not check_pro(m.from_user.id) else "Yangiliklar...")
    elif m.text=="🏆 Reyting":
        rows=c.execute("SELECT name,points FROM users ORDER BY points DESC LIMIT 10").fetchall()
        txt="🏆 TOP:\n"+"\n".join([f"{i+1}. {n} - {p}" for i,(n,p) in enumerate(rows)])
        bot.send_message(m.chat.id, txt)
    else: pro(m)

@bot.message_handler(func=lambda m: True)
def handle(m):
    txt=m.text.strip().upper(); uid=m.from_user.id

    if " " in m.text and len(m.text.split())==2:
        try:
            sym,price=m.text.split(); sym=sym.upper(); price=float(price)
            if sym.isalpha() and check_pro(uid):
                c.execute("INSERT INTO alerts VALUES (NULL,?,?,?)", (uid,sym,price)); conn.commit()
                bot.send_message(m.chat.id, f"✅ {sym} ${price}"); return
        except: pass

    if m.text.startswith("+"):
        try: _,sym,sh,buy=m.text.split(); c.execute("INSERT INTO portfolio VALUES (?,?,?,?)", (uid,sym.upper(),float(sh),float(buy))); conn.commit(); bot.send_message(m.chat.id, "Qo'shildi"); return
        except: pass

    if " VS " in txt:
        a,b=txt.split(" VS "); bot.send_message(m.chat.id, f"⚔️\n{ai_tahlil(a)}\n\n{ai_tahlil(b)}"); return

    if len(txt)<=6 and txt.isalpha():
        can,left = can_analyze(uid)
        if not can:
            bot.send_message(m.chat.id, "❌ Limit tugadi. /pro"); return
        inc_analyze(uid); add_points(uid)
        res = ai_tahlil(txt)
        vip_txt = "" if check_pro(uid) else f"\n\n📊 Qoldi: {left-1} ta"
        bot.send_message(m.chat.id, res + vip_txt)

def check_alerts():
    while True:
        for uid,sym,price in c.execute("SELECT uid,sym,price FROM alerts").fetchall():
            p=yf.Ticker(sym).info.get('currentPrice',0) or 0
            if p and abs(p-price)/price < 0.01:
                try: bot.send_message(uid, f"🔔 {sym} ${p:.2f}")
                except: pass
                c.execute("DELETE FROM alerts WHERE uid=? AND sym=?", (uid,sym)); conn.commit()
        time.sleep(60)

threading.Thread(target=check_alerts, daemon=True).start()

@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000)).start()
    bot.infinity_polling()
