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

# ===================== VEB-SERVER =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ===================== SOZLAMALAR VA TOKEN =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
bot = telebot.TeleBot(TOKEN)

# Standart chiroyli moliya rasmlari (Havolalar)
GLAVNIY_RASM = "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800" # Moliya/Grafik rasmi
AI_ROBOT_RASM = "https://images.unsplash.com/photo-1677442136019-21780efad99a?w=800" # AI Robot rasmi

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
            timeout=15
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return None

def get_uzbek_summary(english_text: str):
    if not english_text:
        return "Kompaniya haqida ma'lumot mavjud emas."
    short_text = english_text[:300] + "..." if len(english_text) > 300 else english_text
    prompt = f"Translate this stock company description into business Uzbek language shortly and professionally: {short_text}"
    translated = ai_request(prompt)
    return translated if translated else short_text

def get_ai_advice(ticker, price, pe, de, rsi, trend, halal):
    prompt = (
        f"You are a professional stock market analyst. Give a short 2-3 sentence financial advice in Uzbek language "
        f"for the stock {ticker}. Current Price: {price} USD, P/E Ratio: {pe}, Debt/Equity: {de}, RSI: {rsi}, "
        f"Trend: {trend}, Islamic Halal Status: {halal}. "
        f"CRITICAL: Always use 'USD' or '$' for currency symbols, NEVER use 'so'm'. "
        f"Be realistic, objective, and advise whether it's safe to buy or risky now."
    )
    advice = ai_request(prompt)
    return advice if advice else "🤖 AI xizmati band. Birozdan so'ng urinib ko'ring."

# ===================== RSI INDIKATORI =====================
def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period:
            return "—", "HOLD ↕️"
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
        return "—", "HOLD ↕️"

# ===================== ASOSIY TAHLIL KODI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        stock, info, hist = get_stock_data(tiker_clean)
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha ma'lumot topilmadi.", None, None, None

        narx = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        valyuta = 'USD'
        
        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Noma\'lum')
        country = info.get('country', 'Noma\'lum')
        employees = info.get('fullTimeEmployees', 'Noma\'lum')
        
        # Logotip havolasini olish (Yfinance taqdim etsa, bo'lmasa standart rasm)
        logo_url = f"https://logo.clearbit.com/{info.get('website', '').replace('https://', '').replace('http://', '').split('/')[0]}" if info.get('website') else GLAVNIY_RASM

        raw_summary = info.get('longBusinessSummary', '')
        uz_summary = get_uzbek_summary(raw_summary)

        closes = hist['Close']
        total_days = len(closes)
        
        def get_change(index):
            try:
                if total_days >= abs(index):
                    return round(((closes.iloc[-1] - closes.iloc[index]) / closes.iloc[index]) * 100, 2)
            except:
                pass
            return 0.0

        ch_d  = get_change(-2)   
        ch_w  = get_change(-6)   
        ch_m  = get_change(-22)  
        ch_3m = get_change(-64)  
        ch_6m = get_change(-127) 
        ch_9m = get_change(-190) 
        ch_1y = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2) if total_days > 0 else 0.0

        rsi, rsi_signal = hisobla_rsi(closes)
        ma50 = closes.iloc[-50:].mean() if len(closes) >= 50 else narx
        ma200 = closes.iloc[-200:].mean() if len(closes) >= 200 else narx
        
        if narx > ma50 and ma50 > ma200: 
            trend_status = "O'sish (Bullish) 📈"
            trend_score = 1
        elif narx < ma50 and ma50 < ma200: 
            trend_status = "Tushish (Bearish) 📉"
            trend_score = -1
        else: 
            trend_status = "Yassilanish (Side) ↕️"
            trend_score = 0

        recommendation = info.get('recommendationKey', 'Noma\'lum').upper().replace('_', ' ')
        qarz = info.get('totalDebt', 0)
        market_cap = info.get('marketCap', 1)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        
        if debt_ratio < 30: halal_status = "🟢 HALOL"
        elif debt_ratio <= 40: halal_status = "🟡 SHUBHALI"
        else: halal_status = "🔴 HAROM"

        pe_val = info.get('trailingPE')
        pe_status = f"{round(pe_val, 2)}" if pe_val else "—"
        
        roe_val = info.get('returnOnEquity')
        roe_status = f"{round(roe_val * 100, 2)}%" if roe_val else "—"

        debt_eq_val = info.get('debtToEquity')
        de_status = f"{round(debt_eq_val, 2)}" if debt_eq_val else "—"

        kitlar_ulushi = "—"
        try:
            held_pct = info.get('heldPercentInstitutions') or info.get('sharesPercentSharesOut')
            if held_pct: kitlar_ulushi = f"{round(float(held_pct) * 100, 2)}%"
        except: pass

        def format_katta_son(son):
            if not son or son == 0: return "—"
            if son >= 1e12: return f"{son/1e12:.2f} T"
            if son >= 1e9: return f"{son/1e9:.2f} B"
            if son >= 1e6: return f"{son/1e6:.2f} M"
            return f"{son:,}"

        market_cap_str = format_katta_son(market_cap)
        qarz_str = format_katta_son(qarz)
        daromad_str = format_katta_son(info.get('totalRevenue', 0))

        high_52 = round(info.get('fiftyTwoWeekHigh', 0), 2) if info.get('fiftyTwoWeekHigh') else "—"
        low_52 = round(info.get('fiftyTwoWeekLow', 0), 2) if info.get('fiftyTwoWeekLow') else "—"

        # 🧠 Bot Qarori hisoblash
        score = 0
        if rsi <= 30: score += 2
        elif rsi >= 70: score -= 2
        if trend_score == 1: score += 2
        elif trend_score == -1: score -= 2
        if "BUY" in recommendation: score += 1
        elif "SELL" in recommendation: score -= 1

        if score >= 3: bot_decision = "🟢 KUCHLI XARID (STRONG BUY) 📈"
        elif score >= 1: bot_decision = "🟢 XARID QILISH (BUY) 🛒"
        elif score <= -3: bot_decision = "🔴 KUCHLI SOTISH (STRONG SELL) 📉"
        elif score <= -1: bot_decision = "🔴 SOTISH (SELL) 🔨"
        else: bot_decision = "🟡 KUTISH / NEYTRAL (HOLD) ↕️"

        javob = f"""📊 <b>{tiker_clean} | {html.escape(long_name)}</b>

🏢 <b>Kompaniya profili:</b>
• Davlat: <b>{country}</b>
• Sektor: <b>{html.escape(sector)}</b>
• Ishchilar soni: <b>{f'{employees:,}' if isinstance(employees, int) else employees} ta</b>
• Faoliyati: <i>{html.escape(uz_summary)}</i>

📈 <b>Yirik moliyaviy ko'rsatkichlar:</b>
• Market Cap (Kapitalizatsiya): <b>{market_cap_str} {valyuta}</b>
• Jami daromad (Revenue): <b>{daromad_str} {valyuta}</b>
• Jami qarz (Total Debt): <b>{qarz_str} {valyuta}</b>
• Shariat statusi: <b>{halal_status} ({debt_ratio:.1f}%)</b>
• Kitlar (Inst Own) ulushi: <b>{kitlar_ulushi}</b>

━━━━━━━━━━━━━━━━━━━━
💰 <b>Bozor narxi: {round(narx, 2)} {valyuta}</b> ({ch_d:+.2f}%)
📈 <b>1K:</b> {ch_d:+.2f}% | <b>1H:</b> {ch_w:+.2f}% | <b>1O:</b> {ch_m:+.2f}%
📅 <b>52H diapazon:</b> {high_52} / {low_52}

━━━━━━━━━━━━━━━━━━━━
📊 <b>Texnik tahlil va Koeffitsiyentlar:</b>
• RSI (14): <b>{rsi}</b> → {rsi_signal}
• Trend (MA): <b>{trend_status}</b>
• Wall Street tavsiyasi: <b>{recommendation}</b>
• P/E: <b>{pe_status}</b> | ROE: <b>{roe_status}</b>

━━━━━━━━━━━━━━━━━━━━
🧠 <b>YAKUNIY BOT QARORI:</b>
<b>{bot_decision}</b>"""
        
        ai_data = f"{tiker_clean}|{round(narx,2)}|{pe_status}|{de_status}|{rsi}|{trend_status}|{halal_status}"
        return javob, tiker_clean, ai_data, logo_url
    except Exception as e:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None, None, None

# ===================== MENYULAR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🏛️ NYSE birjasi"), types.KeyboardButton("💻 NASDAQ birjasi"),
        types.KeyboardButton("🇺🇸 S&P 500 indeks"), types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🎯 Kun aksiyasi"), types.KeyboardButton("📖 Atamalar lug'ati")
    )
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
        types.InlineKeyboardButton("📈 Grafik (Chart)", callback_data=f"chrt_{tiker}"),
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
    bot.send_photo(
        message.chat.id, 
        photo=GLAVNIY_RASM, 
        caption="👋 <b>Assalomu alaykum! Aksiyalar tahlil botiga xush kelibsiz.</b>\n\nBu yerda siz jahon aksiyalarini fundamental, texnik va Shariat me'yorlari bo'yicha tahlil qilishingiz mumkin.\nTiker kiriting yoki quyidagi bo'limlardan birini tanlang:", 
        parse_mode="HTML", 
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()
    if text == "🔍 RSI Skriner":
        bot.reply_to(message, "🔍 <b>RSI Skriner bo'yicha eng faol kompaniyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN"]))
    elif text == "🟢 Halol aksiyalar":
        bot.reply_to(message, "🟢 <b>AQSh bozoridagi eng yirik halol aksiyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]))
    elif text == "🏛️ NYSE birjasi":
        bot.reply_to(message, "🏛️ <b>NYSE top aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["TSCO", "BRK-B", "V", "JNJ", "WMT", "KO"]))
    elif text == "💻 NASDAQ birjasi":
        bot.reply_to(message, "💻 <b>NASDAQ yetakchi texnologik aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMD"]))
    elif "S&P 500" in text:
        bot.reply_to(message, "🇺🇸 <b>S&P 500 indeksining eng nufuzli top aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["SPY", "VOO", "AAPL", "MSFT", "AMZN", "BRK-B"]))
    elif "AI Tavsiyalari" in text:
        prompt = "Siz moliya bo'yicha professorsiz. O'zbek tili foydalanuvchilariga hozirgi AQSh fond bozoridagi vaziyatdan kelib chiqib, qisqa 3 ta eng yaxshi aksiya tikerini va sababini o'zbek tilida tavsiya qiling. Format chiroyli bo'lsin."
        bot.send_chat_action(message.chat.id, 'upload_photo')
        res = ai_request(prompt)
        bot.send_photo(message.chat.id, photo=AI_ROBOT_RASM, caption=f"🤖 <b>AI Umumiy Bozor Tavsiyasi:</b>\n\n{res if res else 'Xizmat band.'}", parse_mode="HTML")
    elif "Kun aksiyasi" in text:
        bot.send_chat_action(message.chat.id, 'upload_photo')
        javob, tiker, ai_str, logo = aksiya_tahlil("AAPL")
        if tiker:
            bot.send_photo(message.chat.id, photo=logo, caption=f"🎯 <b>Bugungi kun aksiyasi:</b>\n\n{javob}", parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
    elif text == "📖 Atamalar lug'ati":
        bot.reply_to(message, "📖 <b>Moliyaviy tahlil lug'ati bo'limi.</b>", parse_mode="HTML", reply_markup=inline_dictionary())
    else:
        bot.send_chat_action(message.chat.id, 'upload_photo')
        javob, tiker, ai_str, logo = aksiya_tahlil(text)
        if tiker:
            bot.send_photo(message.chat.id, photo=logo, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
        else:
            bot.reply_to(message, javob, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("anz_"):
        ticker = call.data.split("_")[1]
        bot.send_chat_action(call.message.chat.id, 'upload_photo')
        javob, tiker_clean, ai_str, logo = aksiya_tahlil(ticker)
        if tiker_clean:
            bot.send_photo(call.message.chat.id, photo=logo, caption=javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean, ai_str))
    
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
            
            bot.answer_callback_query(call.id, text="🤖 Sun'iy intellekt tahlil qilmoqda...")
            bot.send_chat_action(call.message.chat.id, 'upload_photo')
            
            ai_advice = get_ai_advice(tiker, price, pe, de, rsi, trend, halal)
            bot.send_photo(call.message.chat.id, photo=AI_ROBOT_RASM, caption=f"🤖 <b>{tiker} bo'yicha AI Maslahati:</b>\n\n<i>\"{ai_advice}\"</i>", parse_mode="HTML")
        except:
            bot.send_message(call.message.chat.id, "❌ AI tahlilida xatolik yuz berdi.")
            
    elif call.data.startswith("chrt_"):
        ticker = call.data.split("_")[1]
        bot.answer_callback_query(call.id, text="📈 Grafik yuklanmoqda...")
        # TradingView statik grafik rasmini generatsiya qilish havolasi
        chart_url = f"https://charts2.equityclock.com/charts/{ticker.lower()}-seasonality.png" 
        # Muqobil jonli grafik screenshot API havolasi
        live_chart = f"https://scb.hk/chart/{ticker.upper()}" 
        # Barqaror ishlovchi xalqaro grafik tasviri platformasi havolasi
        fallback_chart = f"https://finviz.com/chart.ashx?t={ticker.upper()}&ty=c&ta=1&p=d"
        
        bot.send_chat_action(call.message.chat.id, 'upload_photo')
        bot.send_photo(call.message.chat.id, photo=fallback_chart, caption=f"📈 <b>{ticker.upper()} aksiyasining kunlik texnik narx grafigi (Candlestick chart).</b>", parse_mode="HTML")

    elif call.data.startswith("dic_"):
        term = call.data.split("_")[1]
        expl = ""
        if term == "mcap": expl = "📊 <b>Market Cap:</b> Kompaniyaning bozordagi umumiy joriy qiymati."
        elif term == "pe": expl = "📈 <b>P/E Ratio:</b> Aksiya narxi foydasidan necha barobar qimmatligi."
        elif term == "debteq": expl = "🚨 <b>Debt/Equity:</b> Kompaniyaning qarz yuklamasi darajasi."
        elif term == "rsi": expl = "📉 <b>RSI:</b> Aksiyaning haddan tarko'p sotilgan yoki sotib olinganini ko'rsatuvchi indikator."
        
        bot.send_message(call.message.chat.id, expl, parse_mode="HTML")
        bot.answer_callback_query(call.id)

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    while True:
        try:
            bot.polling(none_stop=True, skip_pending=True, timeout=60)
        except Exception as e:
            time.sleep(5)
