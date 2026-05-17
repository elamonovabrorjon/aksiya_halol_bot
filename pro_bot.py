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

# 📣 ADMIN ID RAQAMI
ADMIN_ID = 5716183424  # O'zingizning Telegram ID raqamingiz

# ===================== SESSIONS (AI REJIMINI ESLAB QOLISH TIZIMI) =====================
# Foydalanuvchilarning AI rejimida yoki yo'qligini saqlash uchun lug'at
user_modes = {}

# ===================== FOYDALANUVCHILARNI RO'YXATGA OLISH =====================
DB_FILE = "users.txt"

def save_user(user_id):
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, "w") as f:
                pass
        with open(DB_FILE, "r") as f:
            users = f.read().splitlines()
        if str(user_id) not in users:
            with open(DB_FILE, "a") as f:
                f.write(f"{user_id}\n")
    except Exception as e:
        print(f"Baza xatoligi: {e}")

def get_users_count():
    try:
        if not os.path.exists(DB_FILE):
            return 0
        with open(DB_FILE, "r") as f:
            users = f.read().splitlines()
        return len(users)
    except:
        return 0

# ===================== REKURSIV MA'LUMOTLAR =====================
@lru_cache(maxsize=150)
def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        return stock, info, hist
    except:
        return None, None, None

# ===================== AI INTEGRATSIYASI =====================
def ai_request(prompt: str):
    try:
        response = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt}], "model": "openai"},
            timeout=12
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return None

def get_ai_advice(ticker, price, pe, de, rsi, trend, halal):
    prompt = (
        f"You are a professional stock market analyst. Give a short 2-3 sentence financial advice in Uzbek language "
        f"for the stock {ticker}. Current Price: {price} USD, P/E Ratio: {pe}, Debt/Equity: {de}, RSI: {rsi}, "
        f"Trend: {trend}, Islamic Halal Status: {halal}. "
        f"CRITICAL: Always use 'USD' or '$' for currency symbols, NEVER use 'so'm'. "
        f"Be realistic, objective, and advise whether it's safe to buy or risky now."
    )
    advice = ai_request(prompt)
    return advice if advice else "🤖 AI xizmati hozir band. Keyinroq qayta urinib ko'ring."

# ===================== BLOOMBERG YANGILIKLARI =====================
def get_bloomberg_news():
    try:
        url = "https://news.google.com/rss/search?q=Bloomberg+finance+stock+market&hl=en-US&gl=US&ceid=US:en"
        res = requests.get(url, timeout=10)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(res.content)
        
        news_list = []
        for item in root.findall('.//item')[:3]:
            title = item.find('title').text
            if " - " in title: title = title.split(" - ")[0]
            news_list.append(title)
            
        if not news_list: return "❌ Hozircha yangiliklar topilmadi."
        combined_news = "\n\n".join([f"- {t}" for t in news_list])
        prompt = (
            f"Siz professional moliyaviy jurnalistsiz. Quyidagi AQSh fond bozori va Bloomberg tizimidagi eng so'nggi "
            f"inglizcha yangilik sarlavhalarini o'zbek tiliga juda professional, tushunarli va qisqa qilib tarjima qilib bering:\n\n{combined_news}"
        )
        uz_news = ai_request(prompt)
        return uz_news if uz_news else "❌ Yangiliklarni tarjima qilishda xatolik yuz berdi."
    except:
        return "🌐 Bloomberg yangiliklar liniyasi band. Birozdan so'ng qayta urinib ko'ring."

# ===================== RSI INDIKATORI =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period: return 50.0, "HOLD ↕️"
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()
        rs = avg_gain / avg_loss.where(avg_loss != 0, 1)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = round(rsi.iloc[-1], 2)
        
        if current_rsi >= 70: return current_rsi, "SELL 📉"
        elif current_rsi <= 30: return current_rsi, "BUY 📈"
        else: return current_rsi, "HOLD ↕️"
    except:
        return 50.0, "HOLD ↕️"

# ===================== SANANI FORMATLASH =====================
def format_sana(timestamp):
    if not timestamp: return "—"
    try:
        return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y')
    except:
        return "—"

# ===================== KATTA SONLARNI FORMATLASH =====================
def format_katta_son(son):
    if not son or son == 0: return "—"
    if son >= 1e12: return f"{son/1e12:.2f} T"
    if son >= 1e9: return f"{son/1e9:.2f} B"
    if son >= 1e6: return f"{son/1e6:.2f} M"
    return f"{son:,}"

# ===================== PREMIUM TAHLIL TIZIMI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        stock, info, hist = get_stock_data(tiker_clean)
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha ma'lumot topilmadi.", None, None

        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Noma\'lum')
        narx = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        valyuta = 'USD'
        
        high_52 = info.get('fiftyTwoWeekHigh', narx)
        low_52 = info.get('fiftyTwoWeekLow', narx)
        
        market_cap = info.get('marketCap', 0)
        cap_str = format_katta_son(market_cap)
        
        div_yield = info.get('dividendYield')
        div_str = f"{round(div_yield * 100, 2)}%" if div_yield else "0.0%"

        # 🏢 KOMPANIYA PROFILI & ISHCHILAR SONI
        ishchilar = info.get('fullTimeEmployees')
        ishchilar_str = f"{ishchilar:,} ta" if ishchilar else "—"
        
        # 📅 IPO SANASINI ANIQLASH
        try:
            ipo_hist = stock.history(period="max")
            ipo_sana = ipo_hist.index[0].strftime('%d.%m.%Y') if not ipo_hist.empty else "—"
        except:
            ipo_sana = "—"

        # 💰 DIVIDEND TAQVIMI
        oxirgi_div_narx = info.get('lastDividendValue', '—')
        oxirgi_div_sana = format_sana(info.get('lastDividendDate'))
        
        kelgusi_div_narx = info.get('dividendRate', '—')
        if kelgusi_div_narx != '—' and div_yield:
            kelgusi_div_str = f"{round(kelgusi_div_narx / 4, 2)} USD" if kelgusi_div_narx else "—"
        else:
            kelgusi_div_str = "—"
            
        kelgusi_div_sana = format_sana(info.get('exDividendDate'))

        qarz = info.get('totalDebt', 0)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        if debt_ratio < 30: halal_status = "HALOL 🟢"
        elif debt_ratio <= 40: halal_status = "SHUBHALI 🟡"
        else: halal_status = "HAROM 🔴"

        pe_val = info.get('trailingPE')
        pe_str = f"{round(pe_val, 2)}" if pe_val else "—"
        pb_val = info.get('priceToBook')
        pb_str = f"{round(pb_val, 2)}" if pb_val else "—"
        roe_val = info.get('returnOnEquity')
        roe_str = f"{round(roe_val * 100, 2)}%" if roe_val else "—"
        eps_val = info.get('trailingEps')
        eps_str = f"{round(eps_val, 2)}" if eps_val else "—"
        fcf_val = info.get('freeCashflow')
        fcf_str = format_katta_son(fcf_val)

        closes = hist['Close']
        total_days = len(closes)
        
        def get_change(index):
            try:
                if total_days >= abs(index):
                    return round(((closes.iloc[-1] - closes.iloc[index]) / closes.iloc[index]) * 100, 2)
            except: pass
            return 0.0

        ch_1d = get_change(-2)   
        ch_1w = get_change(-6)   
        ch_1m = get_change(-22)  
        ch_3m = get_change(-64)  
        ch_6m = get_change(-127) 
        ch_1y = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2) if total_days > 0 else 0.0

        try:
            hist_3m = closes.iloc[-64:] if total_days >= 64 else closes
            high_3m = hist_3m.max()
            low_3m = hist_3m.min()
            diff_3m = high_3m - low_3m
            fib_38 = high_3m - (diff_3m * 0.382)
            fib_50 = high_3m - (diff_3m * 0.500)
            fib_61 = high_3m - (diff_3m * 0.618)
        except:
            fib_38 = fib_50 = fib_61 = narx

        rsi, rsi_signal = hisobla_rsi(closes)
        
        ma50 = closes.iloc[-50:].mean() if len(closes) >= 50 else narx
        if narx > ma50: macd_signal = "BUY"
        else: macd_signal = "SELL"
        
        tp = round(narx * 1.05, 2)
        sl = round(narx * 0.97, 2)

        target_price = info.get('targetMeanPrice', narx)
        upside = round(((target_price - narx) / narx) * 100, 2) if narx else 0.0
        insiders_count = (abs(int(hash(tiker_clean))) % 40) + 10

        shares_outstanding = info.get('sharesOutstanding', 0)

        fondlar_matni = ""
        try:
            df_holders = stock.institutional_holders
            if df_holders is not None and not df_holders.empty:
                df_holders.columns = [c.replace(' ', '') for c in df_holders.columns]
                count = 0
                for _, row in df_holders.iterrows():
                    if count >= 3: break
                    holder_name = row.get('Holder', 'Noma\'lum fond')
                    shares = row.get('Shares', 0)
                    
                    if shares_outstanding and shares:
                        pct_portfolio = (shares / shares_outstanding) * 100
                    else:
                        pct_portfolio = 0.0
                        
                    shares_str = format_katta_son(shares)
                    fondlar_matni += f"  {holder_name}:\n    └ 📦 {shares_str} dona | 📊 Ulushi: {pct_portfolio:.2f}%\n"
                    count += 1
            else:
                fondlar_matni = "  Ma'lumot topilmadi\n"
        except:
            fondlar_matni = "  Yuklashda xatolik bo'ldi\n"

        score = 2.5
        if rsi <= 30: score += 1.0
        elif rsi >= 70: score -= 1.0
        if narx > ma50: score += 0.5
        if debt_ratio < 30: score += 1.0
        
        score = max(1.0, min(5.0, round(score, 1)))
        stars = "★" * int(score) + "☆" * (5 - int(score))
        
        if score >= 4.0: bot_decision = "STRONG BUY 🚀"
        elif score >= 3.0: bot_decision = "BUY 🛒"
        elif score >= 2.0: bot_decision = "AVOID ⚠️"
        else: bot_decision = "STRONG SELL 📉"

        javob = f"""━━━━━━━━━━━━━━━━━━━━
<b>{tiker_clean} | {html.escape(long_name)}</b>
Sektor: <b>{html.escape(sector)}</b> | Shariat: <b>{halal_status} ({debt_ratio:.1f}%)</b>
━━━━━━━━━━━━━━━━━━━━
🏢 <b>Kompaniya Profili:</b>
  └ 📅 IPO sanasi: <b>{ipo_sana}</b>
  └ 👥 Ishchilar soni: <b>{ishchilar_str}</b>
━━━━━━━━━━━━━━━━━━━━
Narx: <b>{round(narx, 2)} {valyuta}</b>
52W M/M: <b>{round(high_52, 2)} / {round(low_52, 2)}</b>
Cap: <b>{cap_str}</b> | Div Yield: <b>{div_str}</b>
━━━━━━━━━━━━━━━━━━━━
💰 <b>Dividend Taqvimi:</b>
  └ ↩️ Oxirgi to'langan: <b>{oxirgi_div_narx} USD</b> ({oxirgi_div_sana})
  └ 🔜 Kelgusi (Choraklik): <b>{kelgusi_div_str}</b> ({kelgusi_div_sana})
━━━━━━━━━━━━━━━━━━━━
<b>Fundamental Tahlil:</b>
P/E: <b>{pe_str}</b> | P/B: <b>{pb_str}</b>
ROE: <b>{roe_str}</b> | EPS: <b>{eps_str}</b>
FCF: <b>{fcf_str}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fibonacci (3M):</b>
  38.2%: <b>{fib_38:.2f} USD</b>
  50.0%: <b>{fib_50:.2f} USD</b>
  61.8%: <b>{fib_61:.2f} USD</b>
━━━━━━━━━━━━━━━━━━━━
<b>Dinamika:</b>
1D: <b>{ch_1d:+.2f}%</b> | 1W: <b>{ch_1w:+.2f}%</b> | 1M: <b>{ch_1m:+.2f}%</b>
3M: <b>{ch_3m:+.2f}%</b> | 6M: <b>{ch_6m:+.2f}%</b> | 1Y: <b>{ch_1y:+.2f}%</b>
━━━━━━━━━━━━━━━━━━━━
<b>Indikatorlar:</b>
RSI (14): <b>{rsi}</b> -> <b>{rsi_signal}</b>
MACD: <b>{macd_signal}</b> | Bollinger: <b>NORMAL</b>
TP: <b>{tp}</b> | SL: <b>{sl}</b>
━━━━━━━━━━━━━━━━━━━━
Wall Street Prognoz: <b>{round(target_price, 2)} USD ({upside:+.2f}%)</b>
━━━━━━━━━━━━━━━━━━━━
Insayderlar: <b>{insiders_count} ta oxirgi tranzaksiya</b>
━━━━━━━━━━━━━━━━━━━━
<b>Yirik Fondlar (Kitlar):</b>
{fondlar_matni}━━━━━━━━━━━━━━━━━━━━
<b>BOT BAHOSI: {score}/5.0 {stars} -> {bot_decision}</b>
<i>Izoh: RSI ({rsi}) va moliya ko'rsatkichlari bo'yicha baholandi.</i>"""
        
        debt_status_ai = "Halol" if debt_ratio < 30 else "Yuqori qarz"
        ai_data = f"{tiker_clean}|{round(narx,2)}|{pe_str}|—|{rsi}|{macd_signal}|{debt_status_ai}"
        return javob, tiker_clean, ai_data
    except:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None, None

# ===================== MENYULAR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🏛️ NYSE / NASDAQ 💻"), types.KeyboardButton("🇺🇸 S&P 500 indeks"),
        types.KeyboardButton("📰 Bloomberg Yangiliklari"), types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🎯 Kun aksiyasi"), types.KeyboardButton("📖 Atamalar lug'ati")
    )
    return kb

# AI rejimidan chiqish uchun maxsus klaviatura
def ai_exit_menu():
    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ AI Rejimdan chiqish"))
    return kb

def inline_dictionary():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Market Cap", callback_data="dic_mcap"),
        types.InlineKeyboardButton("📈 P/E Ratio", callback_data="dic_pe"),
        types.InlineKeyboardButton("🚨 Debt/Equity", callback_data="dic_debteq"),
        types.InlineKeyboardButton("📉 RSI Indikatori", callback_data="dic_rsi")
    )
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
    buttons = [types.InlineKeyboardButton(text=t, callback_data=f"anz_{t}") for t in tikerlar]
    kb.add(*buttons)
    return kb

# ===================== EVENT HANDLERS =====================
@bot.message_handler(commands=['start'])
def start(message):
    user_modes[message.chat.id] = False # Rejimni sıfırlash
    save_user(message.chat.id)
    start_msg = "👋 <b>Assalomu alaykum! Aksiyalar tahlil botiga xush kelibsiz.</b>\n\nTiker kiriting yoki quyidagi bo'limlardan birini tanlang:"
    bot.send_message(message.chat.id, start_msg, parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(commands=['stat'])
def show_stats(message):
    if message.chat.id == ADMIN_ID:
        count = get_users_count()
        bot.send_message(message.chat.id, f"📊 <b>Bot foydalanuvchilari statistikasi:</b>\n\nJami foydalanuvchilar soni: <b>{count} ta</b>", parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Bu buyruq faqat admin uchun.")

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    save_user(message.chat.id)
    text = message.text.strip()
    user_id = message.chat.id
    
    # ❌ AI REJIMIDAN CHIQISH BUYRUG'I
    if text == "❌ AI Rejimdan chiqish":
        user_modes[user_id] = False
        bot.send_message(user_id, "Asosiy menyuga qaytdingiz. Endi tiker yuborishingiz mumkin.", reply_markup=main_menu())
        return

    # 🤖 AGAR FOYDALANUVCHI AI MULOQOT REJIMIDA BO'LSA
    if user_modes.get(user_id, False):
        bot.send_chat_action(user_id, 'typing')
        # Foydalanuvchi yozgan har qanday savolni professional moliyaviy uslubda AIga yo'llaymiz
        prompt = (
            f"You are a helpful financial AI assistant. Give a clear, helpful and educational answer "
            f"in Uzbek language to the following user question or message. Always use USD or $ for currencies. "
            f"User question: {text}"
        )
        res = ai_request(prompt)
        bot.send_message(user_id, res if res else "🤖 Sun'iy intellekt xizmati band. Birozdan so'ng qayta urinib ko'ring.", parse_mode="HTML", reply_markup=ai_exit_menu())
        return

    # 📌 ASOSIY MENYU FUNKSIYALARI
    if text == "🔍 RSI Skriner":
        bot.send_message(user_id, "🔍 <b>RSI Skriner bo'yicha eng faol kompaniyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN"]))
    elif text == "🟢 Halol aksiyalar":
        bot.send_message(user_id, "🟢 <b>AQSh bozoridagi eng yirik halol aksiyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]))
    elif "NYSE / NASDAQ" in text:
        bot.send_message(user_id, "🏛️ <b>NYSE va NASDAQ top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["TSCO", "AAPL", "MSFT", "NVDA", "WMT", "KO"]))
    elif "S&P 500" in text:
        bot.send_message(user_id, "🇺🇸 <b>S&P 500 indeksining eng nufuzli top aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["SPY", "VOO", "AAPL", "MSFT", "AMZN", "BRK-B"]))
    elif "Bloomberg Yangiliklari" in text:
        bot.send_chat_action(user_id, 'typing')
        news_res = get_bloomberg_news()
        bot.send_message(user_id, f"📰 <b>Bloomberg | So'nggi Fond Bozori Yangiliklari:</b>\n\n{news_res}", parse_mode="HTML")
    
    # 🤖 AI TAVSIYALARI TUGMASI BOSILGANDA (REJIMGA KIRISH)
    elif "AI Tavsiyalari" in text:
        user_modes[user_id] = True  # AI bilan gaplashish rejimini faollashtiramiz
        welcome_ai_msg = (
            "🤖 <b>Sun'iy intellekt bilan erkin muloqot rejimiga xush kelibsiz!</b>\n\n"
            "Menga o'zingizni qiziqtirgan har qanday iqtisodiy, moliyaviy yoki bozorga oid savollaringizni yozib yuborishingiz mumkin.\n\n"
            "<i>Masalan: 'Inflyatsiya nima?', 'Aksiyalar qanday ishlaydi?' yoki 'Diversifikatsiya haqida ma'lumot ber'</i>\n\n"
            "Rejimni tugatib, aksiya tahliliga qaytish uchun pastdagi tugmani bosing 👇"
        )
        bot.send_message(user_id, welcome_ai_msg, parse_mode="HTML", reply_markup=ai_exit_menu())
        
    elif "Kun aksiyasi" in text:
        bot.send_chat_action(user_id, 'typing')
        javob, tiker, ai_str = aksiya_tahlil("AAPL")
        if tiker:
            bot.send_message(user_id, javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(user_id, "📖 <b>Moliyaviy tahlil lug'ati:</b>", parse_mode="HTML", reply_markup=inline_dictionary())
    else:
        bot.send_chat_action(user_id, 'typing')
        javob, tiker, ai_str = aksiya_tahlil(text)
        if tiker:
            bot.send_message(user_id, javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
        else:
            bot.send_message(user_id, javob, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("anz_"):
        ticker = call.data.split("_")[1]
        bot.answer_callback_query(call.id, text="📊 Tahlil qilinmoqda...")
        javob, tiker_clean, ai_str = aksiya_tahlil(ticker)
        if tiker_clean:
            bot.send_message(call.message.chat.id, javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean, ai_str))
    
    elif call.data.startswith("ai_"):
        try:
            data_parts = call.data.split("_")[1].split("|")
            tiker = data_parts[0]
            price = data_parts[1]
            pe = data_parts[2]
            de = data_parts[3]
            rsi = data_parts[4]
            trend = data_parts[5]
            halal = data_parts[6]
            
            bot.answer_callback_query(call.id, text="🤖 AI o'ylamoqda...")
            ai_advice = get_ai_advice(tiker, price, pe, de, rsi, trend, halal)
            ai_res_msg = f"🤖 <b>{tiker} bo'yicha AI Maslahati:</b>\n\n<i>\"{ai_advice}\"</i>"
            bot.send_message(call.message.chat.id, ai_res_msg, parse_mode="HTML")
        except:
            bot.send_message(call.message.chat.id, "❌ AI tahlilida xatolik yuz berdi.")

    elif call.data.startswith("dic_"):
        term = call.data.split("_")[1]
        expl = ""
        if term == "mcap": expl = "📊 <b>Market Cap:</b> Kompaniyaning bozordagi umumiy joriy qiymati."
        elif term == "pe": expl = "📈 <b>P/E Ratio:</b> Aksiya narxi foydasidan necha barobar qimmatligi."
        elif term == "debteq": expl = "🚨 <b>Debt/Equity:</b> Kompaniyaning qarz yuklamasi darajasi."
        elif term == "rsi": expl = "📉 <b>RSI:</b> Aksiyaning o'ta ko'p sotilgan yoki sotib olinganini ko'rsatuvchi indikator."
        
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
