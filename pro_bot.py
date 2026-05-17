import telebot
from telebot import types
import yfinance as yf
import html
from functools import lru_cache
import threading
from flask import Flask
import time
import os
import requests
from datetime import datetime

# ===================== VEB-SERVER =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot barqaror rejimda ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ===================== SOZLAMALAR VA TOKEN =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 5716183424  # Admin Telegram ID

# ===================== REJIMLAR SESSIYASI =====================
user_modes = {}      
uz_user_modes = {}   

# ===================== FOYDALANUVCHILAR BAZASI =====================
DB_FILE = "users.txt"

def save_user(user_id):
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, "w") as f: pass
        with open(DB_FILE, "r") as f:
            users = f.read().splitlines()
        if str(user_id) not in users:
            with open(DB_FILE, "a") as f:
                f.write(f"{user_id}\n")
    except:
        pass

def get_users_count():
    try:
        if not os.path.exists(DB_FILE): return 0
        with open(DB_FILE, "r") as f:
            return len(f.read().splitlines())
    except:
        return 0

# ===================== DATA CACHE =====================
@lru_cache(maxsize=150)
def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        return stock, stock.info, stock.history(period="1y")
    except:
        return None, None, None

# ===================== AI XIZMATI =====================
def ai_request(prompt: str):
    try:
        response = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt}], "model": "openai"},
            timeout=15
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return None

def get_ai_advice(ticker, price, pe, de, rsi, trend, halal):
    prompt = (
        f"Siz professional moliya tahlilchisiz. {ticker} aksiyasi uchun o'zbek tilida 2-3 ta gapdan iborat ixcham "
        f"tavsiya bering. Joriy narx: {price} USD, P/E: {pe}, RSI: {rsi}, Trend: {trend}, Shariat statusi: {halal}. "
        f"Faqat USD yoki $ belgisidan foydalaning. Sotib olish xavfsiz yoki xatarliligi haqida xolis fikr bering."
    )
    advice = ai_request(prompt)
    return advice if advice else "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."

# ===================== O'ZBEKISTON AKSIYALARI UCHUN AI =====================
def uzbekistan_stock_analysis(text_input: str):
    prompt = (
        f"Siz Toshkent Respublika Fond Birjasi (Toshkent RFB) bo'yicha professional moliya tahlilchisiz.\n"
        f"Foydalanuvchi quyidagi O'zbekiston kompaniyasini tahlil qilishni so'radi: '{text_input}'.\n\n"
        f"Iltimos, ushbu aksiya haqida o'zingizda bor eng so'nggi moliyaviy ma'lumotlar asosida "
        f"quyidagi tartibli va minimalist strukturada professional tahlil tayyorlab bering:\n\n"
        f"🇺🇿 <b>Kompaniya nomi:</b> [To'liq nomi va qisqartma tikeri]\n"
        f"📊 <b>Fundamental holati:</b> [Rentabelligi, sof foyda dinamikasi va dividend to'lashi haqida lo'nda baho]\n"
        f"⚠️ <b>Asosiy xavf-xatarlar (Risk):</b> [Birjadagi likvidlik muammolari yoki kamchiliklar]\n"
        f"🎯 <b>YAKUNIY QAROR:</b> [Sotib olish tavsiya etiladimi (BUY) yoki hozircha chetda turgan ma'qulmi (AVOID/SELL) - aniq xulosa]\n\n"
        f"Javob faqat toza o'zbek tilida bo'lsin. Pul birligi sifatida UZS (so'm) foydalanilsin."
    )
    res = ai_request(prompt)
    if res:
        return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI</b>\n━━━━━━━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━━━━━━━"
    return "❌ O'zbekiston aksiyasi tahlilida xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."

# ===================== FOND BOZORI YANGILIKLARI =====================
def get_market_news():
    try:
        url = "https://news.google.com/rss/search?q=stock+market+investing+news+bloomberg+reuters&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=10)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        news_list = []
        for item in root.findall('.//item')[:4]:
            title = item.find('title').text
            if " - " in title: title = title.split(" - ")[0]
            news_list.append(title)
        if not news_list: return "❌ Hozircha yangiliklar topilmadi."
        combined_news = "\n\n".join([f"- {t}" for t in news_list])
        prompt = f"Quyidagi jahon fond bozori yangiliklarini professional o'zbek tiliga juda lo'nda tarjima qilib bering:\n\n{combined_news}"
        uz_news = ai_request(prompt)
        return uz_news if uz_news else "❌ Yangiliklarni tarjima qilishda xatolik yuz berdi."
    except:
        return "🌐 Yangiliklar liniyasi band. Birozdan so'ng qayta urinib ko'ring."

# ===================== KRIPTO BOZORI FUNKSIYASI =====================
def get_crypto_market_summary():
    cryptos = {
        "BTC-USD": "Bitcoin (BTC)",
        "ETH-USD": "Ethereum (ETH)",
        "BNB-USD": "BNB",
        "SOL-USD": "Solana (SOL)",
        "XRP-USD": "Ripple (XRP)"
    }
    matn = "━━━━━━━━━━━━━━━━━━━━\n🪙 <b>JORIY KRIPTO BOZORI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for ticker, name in cryptos.items():
        try:
            coin = yf.Ticker(ticker)
            hist = coin.history(period="2d")
            if len(hist) >= 2:
                narx = hist['Close'].iloc[-1]
                old_narx = hist['Close'].iloc[-2]
                ozgarish = ((narx - old_narx) / old_narx) * 100
                belgi = "📈" if ozgarish >= 0 else "📉"
                matn += f"{belgi} <b>{name}</b>\n  └ Narx: <b>{narx:,.2f} USD</b> | Sutkalik: <b>{ozgarish:+.2f}%</b>\n\n"
        except:
            matn += f"❌ <b>{name}</b> ma'lumotlarini yuklab bo'lmadi.\n\n"
    matn += "━━━━━━━━━━━━━━━━━━━━"
    return matn

# ===================== BUGUNGI ENG KUCHLI O'SGAN VA TUSHGAN AKSIYALAR =====================
def get_market_movers():
    watch_list = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "INTC", "TSCO", "BABA", "XOM", "JPM", "NIO"]
    gainers = []
    losers = []
    
    for tiker in watch_list:
        try:
            stock = yf.Ticker(tiker)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                yopilish = hist['Close'].iloc[-1]
                ochilish = hist['Close'].iloc[-2]
                change = ((yopilish - ochilish) / ochilish) * 100
                data = {"ticker": tiker, "price": yopilish, "change": change}
                if change >= 0:
                    gainers.append(data)
                else:
                    losers.append(data)
        except:
            pass

    gainers = sorted(gainers, key=lambda x: x['change'], reverse=True)[:3]
    losers = sorted(losers, key=lambda x: x['change'])[:3]

    matn = "━━━━━━━━━━━━━━━━━━━━\n🔥 <b>BUGUNGI BOZOR YETAKCHILARI</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    matn += "🚀 <b>Eng ko'p o'sgan aksiyalar (Top Gainers):</b>\n"
    if gainers:
        for item in gainers:
            matn += f"  🟢 <b>{item['ticker']}</b>: {item['price']:.2f} USD (<b>{item['change']:+.2f}%</b>)\n"
    else:
        matn += "  └ Ma'lumot aniqlanmadi\n"

    matn += "\n📉 <b>Eng ko'p tushgan aksiyalar (Top Losers):</b>\n"
    if losers:
        for item in losers:
            matn += f"  🔴 <b>{item['ticker']}</b>: {item['price']:.2f} USD (<b>{item['change']:+.2f}%</b>)\n"
    else:
        matn += "  └ Ma'lumot aniqlanmadi\n"
    matn += "━━━━━━━━━━━━━━━━━━━━"
    return matn

# ===================== INDIKATORLAR VA MATEMATIKA =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period: return 50.0, "HOLD ↕️"
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()
        text_rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + text_rs))
        current_rsi = round(rsi.iloc[-1], 2)
        
        if current_rsi >= 70: return current_rsi, "SELL 📉"
        elif current_rsi <= 30: return current_rsi, "BUY 📈"
        else: return current_rsi, "HOLD ↕️"
    except:
        return 50.0, "HOLD ↕️"

def format_sana(data_input):
    if not data_input: return "—"
    try:
        if isinstance(data_input, (str, datetime)):
            if isinstance(data_input, str):
                for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S'):
                    try: return datetime.strptime(data_input.split()[0], fmt).strftime('%d.%m.%Y')
                    except: pass
                return data_input
            return data_input.strftime('%d.%m.%Y')
        return datetime.fromtimestamp(int(data_input)).strftime('%d.%m.%Y')
    except:
        return "—"

def format_katta_son(son):
    if not son or son == 0: return "—"
    minus = "-" if son < 0 else ""
    son = abs(son)
    if son >= 1e12: return f"{minus}{son/1e12:.2f} T"
    if son >= 1e9: return f"{minus}{son/1e9:.2f} B"
    if son >= 1e6: return f"{minus}{son/1e6:.2f} M"
    return f"{minus}{son:,}"

# ===================== PREMIUM TAHLIL ARXITEKTURASI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        
        if tiker_clean in ["BTC", "ETH", "BNB", "SOL", "XRP"]:
            tiker_clean = f"{tiker_clean}-USD"

        stock, info, hist = get_stock_data(tiker_clean)
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha ma'lumot topilmadi.", None, None

        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Kripto / Moliyaviy Aktiv')
        narx = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        
        high_52 = info.get('fiftyTwoWeekHigh', narx)
        low_52 = info.get('fiftyTwoWeekLow', narx)
        market_cap = info.get('marketCap', 0)
        cap_str = format_katta_son(market_cap)
        
        div_yield = info.get('dividendYield')
        div_str = f"{round(div_yield * 100, 2)}%" if div_yield else "0.0%"

        # Aksiyalar miqdori, float va hajm ma'lumotlari
        jami_aksiya = info.get('sharesOutstanding', 0)
        sotuvdagi_aksiya = info.get('floatShares', 0)
        kunlik_hajm = info.get('volume', 0)
        oylik_orta_hajm = info.get('averageVolume', 0)

        jami_aksiya_str = format_katta_son(jami_aksiya) + " dona" if jami_aksiya else "—"
        sotuvdagi_aksiya_str = format_katta_son(sotuvdagi_aksiya) + " dona" if sotuvdagi_aksiya else "—"
        kunlik_hajm_str = format_katta_son(kunlik_hajm) + " dona" if kunlik_hajm else "—"
        oylik_hajm_str = format_katta_son(oylik_orta_hajm) + " dona" if oylik_orta_hajm else "—"

        oxirgi_div_narx = info.get('lastDividendValue', '—')
        oxirgi_div_sana = format_sana(info.get('lastDividendDate'))
        kelgusi_div_narx = info.get('dividendRate', '—')
        kelgusi_div_sana_raw = info.get('exDividendDate')
        
        if kelgusi_div_sana_raw and info.get('lastDividendDate') and kelgusi_div_sana_raw == info.get('lastDividendDate'):
            kelgusi_div_sana = "—"
            kelgusi_div_str = "—"
        else:
            kelgusi_div_str = f"{round(kelgusi_div_narx / 4, 2)} USD" if (kelgusi_div_narx and kelgusi_div_narx != '—' and div_yield) else f"{kelgusi_div_narx} USD"
            kelgusi_div_sana = format_sana(kelgusi_div_sana_raw)

        qarz = info.get('totalDebt', 0)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        halal_status = "HALOL 🟢" if debt_ratio < 30 else ("SHUBHALI 🟡" if debt_ratio <= 40 else "HAROM 🔴")
        if "-USD" in tiker_clean: halal_status = "KRIPTO 🪙"

        pe_str = f"{round(info.get('trailingPE'), 2)}" if info.get('trailingPE') else "—"
        pb_str = f"{round(info.get('priceToBook'), 2)}" if info.get('priceToBook') else "—"
        eps_str = f"{round(info.get('trailingEps'), 2)}" if info.get('trailingEps') else "—"
        fcf_str = format_katta_son(info.get('freeCashflow'))

        target_price = info.get('targetMeanPrice', narx)
        upside = round(((target_price - narx) / narx) * 100, 2) if narx else 0.0
        dcf_status = f"Undervalued 🟢 ({upside:+.2f}%)" if upside > 10 else (f"Overvalued 🔴 ({upside:+.2f}%)" if upside < -10 else f"Fair Value 🟡 ({upside:+.2f}%)")

        closes = hist['Close']
        total_days = len(closes)
        
        def get_change(index):
            try:
                if total_days >= abs(index): return round(((closes.iloc[-1] - closes.iloc[index]) / closes.iloc[index]) * 100, 2)
            except: pass
            return 0.0

        ch_1d, ch_1w, ch_1m, ch_3m, ch_6m = get_change(-2), get_change(-6), get_change(-22), get_change(-64), get_change(-127)
        ch_1y = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2) if total_days > 0 else 0.0

        try:
            hist_3m = closes.iloc[-64:] if total_days >= 64 else closes
            diff_3m = hist_3m.max() - hist_3m.min()
            fib_38, fib_50, fib_61 = hist_3m.max() - (diff_3m * 0.382), hist_3m.max() - (diff_3m * 0.500), hist_3m.max() - (diff_3m * 0.618)
        except:
            fib_38 = fib_50 = fib_61 = narx

        rsi, rsi_signal = hisobla_rsi(closes)
        ma50 = closes.iloc[-50:].mean() if len(closes) >= 50 else narx
        macd_signal = "BUY" if narx > ma50 else "SELL"
        tp, sl = round(narx * 1.05, 2), round(narx * 0.97, 2)

        score = max(1.0, min(5.0, round(2.5 + (1.0 if rsi<=30 else (-1.0 if rsi>=70 else 0)) + (0.5 if narx>ma50 else 0) + (1.0 if debt_ratio<30 else 0), 1)))
        bot_decision = "STRONG BUY 🚀" if score >= 4.0 else ("BUY 🛒" if score >= 3.0 else ("AVOID ⚠️" if score >= 2.0 else "STRONG SELL 📉"))

        javob = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(long_name)}</b>
Sektor: <b>{html.escape(sector)}</b> | Status: <b>{halal_status}</b>
━━━━━━━━━━━━━━━━━━━━
Narx: <b>{narx:,.2f} USD</b>
52W M/M: <b>{high_52:,.2f} / {low_52:,.2f}</b>
Cap: <b>{cap_str}</b> | Div Yield: <b>{div_str}</b>
━━━━━━━━━━━━━━━━━━━━
📦 <b>Aksiyalar miqdori & Muomala:</b>
  └ 📊 Jami chiqarilgan: <b>{jami_aksiya_str}</b>
  └ 🛒 Sotuvda (Float): <b>{sotuvdagi_aksiya_str}</b>
  └ 🔄 Bugungi Oldi-sotdi: <b>{kunlik_hajm_str}</b>
  └ ⏱️ Oylik o'rtacha hajm: <b>{oylik_hajm_str}</b>
━━━━━━━━━━━━━━━━━━━━
💰 <b>Dividend Taqvimi (Faqat Aksiyalar):</b>
  └ ↩️ Oxirgi: <b>{oxirgi_div_narx} USD</b> ({oxirgi_div_sana})
  └ 🔜 Kelgusi: <b>{kelgusi_div_str}</b> ({kelgusi_div_sana})
━━━━━━━━━━━━━━━━━━━━
<b>Fundamental Ko'rsatkichlar:</b>
P/E: <b>{pe_str}</b> | P/B: <b>{pb_str}</b> | EPS: <b>{eps_str}</b>
FCF: <b>{fcf_str}</b> | DCF Qiymati: <b>{dcf_status}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fibonacci (3M):</b>
  38.2%: <b>{fib_38:,.2f} USD</b> | 50.0%: <b>{fib_50:,.2f} USD</b> | 61.8%: <b>{fib_61:,.2f} USD</b>
━━━━━━━━━━━━━━━━━━━━
<b>Dinamika:</b>
1D: <b>{ch_1d:+.2f}%</b> | 1W: <b>{ch_1w:+.2f}%</b> | 1M: <b>{ch_1m:+.2f}%</b>
3M: <b>{ch_3m:+.2f}%</b> | 6M: <b>{ch_6m:+.2f}%</b> | 1Y: <b>{ch_1y:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
<b>Indikatorlar:</b>
RSI (14): <b>{rsi}</b> -> <b>{rsi_signal}</b>
MACD: <b>{macd_signal}</b> | TP: <b>{tp:,.2f}</b> | SL: <b>{sl:,.2f}</b>
━━━━━━━━━━━━━━━━━━━━
<b>BOT BAHOSI: {score}/5.0 {"★"*int(score)+"☆"*(5-int(score))} -> {bot_decision}</b>"""
        
        ai_data = f"{tiker_clean}|{round(narx,2)}|{pe_str}|—|{rsi}|{macd_signal}|{'Halol' if debt_ratio<30 else 'Xavfli'}"
        return javob, tiker_clean, ai_data
    except:
        return f"❌ {tiker.upper()} tahlilida xatolik.", None, None

# ===================== LUG'AT INTERFEYSI =====================
def inline_dictionary(page=1):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if page == 1:
        kb.add(
            types.InlineKeyboardButton("📊 Market Cap", callback_data="dic_mcap"),
            types.InlineKeyboardButton("📈 P/E Ratio", callback_data="dic_pe"),
            types.InlineKeyboardButton("🚨 Debt/Equity", callback_data="dic_debteq"),
            types.InlineKeyboardButton("📉 RSI Indikatori", callback_data="dic_rsi")
        )
        kb.add(types.InlineKeyboardButton("Keyingi sahifa ➡️", callback_data="dic_page_2"))
    elif page == 2:
        kb.add(
            types.InlineKeyboardButton("💰 EPS (Foyda)", callback_data="dic_eps"),
            types.InlineKeyboardButton("👑 ROE (Rentabellik)", callback_data="dic_roe"),
            types.InlineKeyboardButton("💵 FCF (Real Pul)", callback_data="dic_fcf"),
            types.InlineKeyboardButton("📚 P/B Ratio", callback_data="dic_pb")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dic_page_1"))
    return kb

# ===================== MENYULAR TIZIMI =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🏛️ NYSE birjasi"), types.KeyboardButton("💻 NASDAQ birjasi"),
        types.KeyboardButton("🇺🇸 S&P 500 indeks"), types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"), types.KeyboardButton("📰 Fond bozori yangiliklari"),
        types.KeyboardButton("🪙 Kripto bozori"), types.KeyboardButton("🔥 Bozor yetakchilari"),
        types.KeyboardButton("📖 Atamalar lug'ati")
    )
    return kb

def ai_exit_menu():
    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Rejimdan chiqish"))
    return kb

def inline_action(tiker, ai_string):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{ai_string}"),
        types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/")
    )
    return kb

def inline_aksiyalar(tikerlar):
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(*[types.InlineKeyboardButton(text=t, callback_data=f"anz_{t}") for t in tikerlar])
    return kb

# ===================== MESSAGE CONTROLLER =====================
@bot.message_handler(commands=['start'])
def start(message):
    user_modes[message.chat.id] = False
    uz_user_modes[message.chat.id] = False
    save_user(message.chat.id)
    bot.send_message(message.chat.id, "👋 <b>Aksiyalar va Kripto tahlil botiga xush kelibsiz!</b>\n\nTiker yoki Kripto nomini kiriting yozing (Masalan: AAPL yoki BTC):", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(commands=['stat'])
def show_stats(message):
    if message.chat.id == ADMIN_ID:
        bot.send_message(message.chat.id, f"📊 <b>Bot statistikasi:</b>\n\nJami foydalanuvchilar: <b>{get_users_count()} ta</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    save_user(message.chat.id)
    text = message.text.strip()
    user_id = message.chat.id
    
    if text in ["❌ Rejimdan chiqish", "❌ AI Rejimdan chiqish", "chiqish"]:
        user_modes[user_id] = False
        uz_user_modes[user_id] = False
        bot.send_message(user_id, "Asosiy menyuga qaytdingiz.", reply_markup=main_menu())
        return

    if uz_user_modes.get(user_id, False):
        bot.send_chat_action(user_id, 'typing')
        bot.send_message(user_id, uzbekistan_stock_analysis(text), parse_mode="HTML", reply_markup=ai_exit_menu())
        return

    if user_modes.get(user_id, False):
        bot.send_chat_action(user_id, 'typing')
        prompt = f"Siz professional moliyaviy yordamchisiz. Quyidagi savolga o'zbek tilida aniq javob bering: {text}"
        res = ai_request(prompt)
        bot.send_message(user_id, res if res else "🤖 AI xizmati band. Keyinroq urinib ko'ring.", parse_mode="HTML", reply_markup=ai_exit_menu())
        return

    # Asosiy tugmalar filtri
    if text == "🔍 RSI Skriner":
        bot.send_message(user_id, "🔍 <b>RSI Skriner (Eng faol kompaniyalar):</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN"]))
    elif text == "🟢 Halol aksiyalar":
        bot.send_message(user_id, "🟢 <b>AQSh bozoridagi yirik halol aksiyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]))
    elif "NYSE" in text:
        bot.send_message(user_id, "🏛️ <b>NYSE top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["TSCO", "WMT", "KO", "XOM", "JNJ", "NKE"]))
    elif "NASDAQ" in text:
        bot.send_message(user_id, "💻 <b>NASDAQ top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA"]))
    elif "S&P 500" in text:
        bot.send_message(user_id, "🇺🇸 <b>S&P 500 nufuzli aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["SPY", "VOO", "AAPL", "MSFT", "AMZN"]))
    elif text == "📰 Fond bozori yangiliklari":
        bot.send_chat_action(user_id, 'typing')
        bot.send_message(user_id, f"📰 <b>Fond Bozori | So'nggi Muhim Yangiliklar:</b>\n\n{get_market_news()}", parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        bot.send_chat_action(user_id, 'typing')
        bot.send_message(user_id, get_crypto_market_summary(), parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        bot.send_chat_action(user_id, 'typing')
        bot.send_message(user_id, get_market_movers(), parse_mode="HTML")
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        uz_user_modes[user_id] = True
        user_modes[user_id] = False
        welcome_uz = "🇺🇿 <b>Toshkent Respublika Fond Birjasi bo'limi!</b>\n\nKompaniya nomi yoki tikerini yozing (Masalan: <i>NKMK, SQB</i>):"
        bot.send_message(user_id, welcome_uz, parse_mode="HTML", reply_markup=ai_exit_menu())
    elif text == "🤖 AI Tavsiyalari":
        user_modes[user_id] = True
        uz_user_modes[user_id] = False
        welcome_ai = "🤖 <b>Erkin AI muloqot rejimi!</b>\n\nMoliya va bozorga oid savollaringizni yozing:"
        bot.send_message(user_id, welcome_ai, parse_mode="HTML", reply_markup=ai_exit_menu())
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(user_id, "📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    else:
        uz_keywords = ["UZMT", "SQB", "HMKB", "KVTS", "UZAUTO", "URTS", "IPTK", "OKMK", "AGMK", "NKMK", "NGMK"]
        if any(kw in text.upper() for kw in uz_keywords):
            bot.send_chat_action(user_id, 'typing')
            bot.send_message(user_id, uzbekistan_stock_analysis(text), parse_mode="HTML")
        else:
            bot.send_chat_action(user_id, 'typing')
            javob, tiker, ai_str = aksiya_tahlil(text)
            if tiker:
                bot.send_message(user_id, javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
            else:
                bot.send_message(user_id, uzbekistan_stock_analysis(text), parse_mode="HTML")

# ===================== CALLBACK CONTROLLER =====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("anz_"):
        ticker = call.data.split("_")[1]
        javob, tiker_clean, ai_str = aksiya_tahlil(ticker)
        if tiker_clean:
            bot.send_message(call.message.chat.id, javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean, ai_str))
            bot.answer_callback_query(call.id)
            
    elif call.data.startswith("ai_"):
        try:
            p = call.data.split("_")[1].split("|")
            ai_advice = get_ai_advice(p[0], p[1], p[2], p[3], p[4], p[5], p[6])
            bot.send_message(call.message.chat.id, f"🤖 <b>{p[0]} bo'yicha AI Maslahati:</b>\n\n<i>\"{ai_advice}\"</i>", parse_mode="HTML")
            bot.answer_callback_query(call.id)
        except:
            pass

    elif call.data.startswith("dic_"):
        term = call.data.split("_")[1]
        if term == "page":
            p_num = int(call.data.split("_")[2])
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"📖 <b>Moliyaviy tahlil lug'ati ({p_num}-sahifa):</b>", parse_mode="HTML", reply_markup=inline_dictionary(page=p_num))
            return
            
        expl = ""
        if term == "mcap": expl = "📊 <b>Market Cap:</b> Kompaniyaning bozordagi barcha aksiyalarining umumiy qiymati."
        elif term == "pe": expl = "📈 <b>P/E Ratio:</b> Aksiya narxi yillik foydasidan necha barobar qimmatligini bildiradi."
        elif term == "debteq": expl = "🚨 <b>Debt/Equity:</b> Kompaniyaning o'z kapitaliga nisbatan qarz yuklamasi."
        elif term == "rsi": expl = "📉 <b>RSI Indikatori:</b> Texnik tahlilda aktivning haddan ortiq ko'p sotilgan yoki ko'p sotib olinganini ko'rsatadi."
        
        bot.send_message(call.message.chat.id, expl, parse_mode="HTML")
        bot.answer_callback_query(call.id)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    while True:
        try:
            bot.polling(none_stop=True, skip_pending=True, timeout=40)
        except:
            time.sleep(3)
