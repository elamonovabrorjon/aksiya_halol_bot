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
from deep_translator import GoogleTranslator

# ===================== VEB-SERVER (RENDER LIVE STATUS) =====================
app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ===================== SOZLAMALAR VA ASLIY TOKEN =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
bot = telebot.TeleBot(TOKEN)

@lru_cache(maxsize=150)
def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        return stock, info, hist
    except:
        return None, None, None

# ===================== TEKIN AI INTEGRATSIYASI =====================
def get_ai_advice(ticker, price, pe, de, rsi, trend, halal):
    try:
        prompt = (
            f"You are a professional stock market analyst. Give a short 2-3 sentence financial advice in Uzbek language "
            f"for the stock {ticker}. Current Price: {price}, P/E Ratio: {pe}, Debt/Equity: {de}, RSI: {rsi}, "
            f"Trend: {trend}, Islamic Halal Status: {halal}. Be realistic, objective, and advise whether it's safe to buy or risky now."
        )
        response = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": [{"role": "user", "content": prompt}], "model": "openai"},
            timeout=15
        )
        if response.status_code == 200:
            return response.text.strip()
        else:
            return "🤖 AI xizmati band. Iltimos, birozdan so'ng qayta urinib ko'ring."
    except:
        return "🤖 AI bilan bog'lanishda xatolik yuz berdi."

# ===================== TEXNIK INDIKATORLAR =====================
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

# ===================== ASOSIY PROFESSIONAL TAHLIL KODI =====================
def aksiya_tahlil(tiker: str):
    try:
        tiker_clean = tiker.strip().upper()
        stock, info, hist = get_stock_data(tiker_clean)
        
        if info is None or hist is None or hist.empty:
            return f"❌ <b>{tiker_clean}</b> bo'yicha ma'lumot topilmadi.", None, None

        narx = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        valyuta = info.get('currency', 'USD')
        long_name = info.get('longName') or info.get('shortName') or tiker_clean
        sector = info.get('sector', 'Noma\'lum')
        country = info.get('country', 'Noma\'lum')
        
        summary = info.get('longBusinessSummary', '')
        if summary:
            if len(summary) > 250:
                summary = summary[:250] + "..."
            try:
                summary = GoogleTranslator(source='en', target='uz').translate(summary)
            except:
                pass
        else:
            summary = "Kompaniya haqida ma'lumot mavjud emas."

        closes = hist['Close']
        if len(closes) >= 22:
            change_1d = round(((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100, 2)
            change_1w = round(((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100, 2)
            change_1m = round(((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21]) * 100, 2)
        else:
            change_1d = change_1w = change_1m = 0

        rsi, rsi_signal = hisobla_rsi(closes)
        ma50 = closes.iloc[-50:].mean() if len(closes) >= 50 else narx
        ma200 = closes.iloc[-200:].mean() if len(closes) >= 200 else narx
        
        if narx > ma50 and ma50 > ma200:
            trend_status = "O'sish (Bullish) 📈"
        elif narx < ma50 and ma50 < ma200:
            trend_status = "Tushish (Bearish) 📉"
        else:
            trend_status = "Yassilanish (Side/Flat) ↕️"

        recommendation = info.get('recommendationKey', 'Noma\'lum').upper().replace('_', ' ')

        qarz = info.get('totalDebt', 0)
        market_cap = info.get('marketCap', 1)
        daromad = info.get('totalRevenue', 0)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        
        if debt_ratio < 30: halal_status = "🟢 HALOL"
        elif debt_ratio <= 40: halal_status = "🟡 SHUBHALI"
        else: halal_status = "🔴 HAROM"

        # =============== AVTOMATIK FUNDAMENTAL BAHOLASH TIZIMI ===============
        pe_val = info.get('trailingPE')
        if pe_val is not None:
            pe_val = float(pe_val)
            if pe_val <= 0: pe_status = f"{pe_val:.2f} (Zararda 🚨)"
            elif pe_val <= 25: pe_status = f"{pe_val:.2f} (Arzon/Yaxshi ✅)"
            elif pe_val <= 40: pe_status = f"{pe_val:.2f} (Me'yorda 🟡)"
            else: pe_status = f"{pe_val:.2f} (Qimmat 🚨)"
        else: pe_status = "—"

        roe_val = info.get('returnOnEquity')
        if roe_val is not None:
            roe_pct = float(roe_val) * 100
            if roe_pct >= 15: roe_status = f"{roe_pct:.2f}% (Yuqori/A'lo ✅)"
            elif roe_pct >= 5: roe_status = f"{roe_pct:.2f}% (O'rtacha 🟡)"
            else: roe_status = f"{roe_pct:.2f}% (Past/Yomon 🚨)"
        else: roe_status = "—"

        debt_eq_val = info.get('debtToEquity')
        if debt_eq_val is not None:
            de_val = float(debt_eq_val)
            if de_val <= 50 or de_val <= 0.5: de_status = f"{de_val} (Qarzi kam ✅)"
            else: de_status = f"{de_val} (Ko'p qarz 🚨)"
        else: de_status = "—"

        current_ratio_val = info.get('currentRatio')
        cr_status = f"{current_ratio_val:.2f}" if current_ratio_val else "—"

        kitlar_ulushi = "—"
        try:
            held_pct = info.get('sharesPercentSharesOut') or info.get('heldPercentInstitutions')
            if held_pct: kitlar_ulushi = f"{round(float(held_pct) * 100, 2)}%"
        except: pass

        def format_katta_son(son):
            if not son or isinstance(son, str) or son == 0: return "—"
            if son >= 1e12: return f"{son/1e12:.2f} T"
            if son >= 1e9: return f"{son/1e9:.2f} B"
            if son >= 1e6: return f"{son/1e6:.2f} M"
            return f"{son:,}"

        market_cap_str = format_katta_son(market_cap)
        qarz_str = format_katta_son(qarz)
        daromad_str = format_katta_son(daromad)

        high_52 = round(info.get('fiftyTwoWeekHigh', 0), 2) if info.get('fiftyTwoWeekHigh') else "—"
        low_52 = round(info.get('fiftyTwoWeekLow', 0), 2) if info.get('fiftyTwoWeekLow') else "—"

        javob = f"""📊 <b>{tiker_clean} | {html.escape(long_name)}</b>

🏢 <b>Kompaniya profili:</b>
• Davlat: <b>{country}</b> | Sektor: {html.escape(sector)}
• Faoliyati: <i>{html.escape(summary)}</i>

📈 <b>Yirik moliyaviy ko'rsatkichlar:</b>
• Market Cap: <b>{market_cap_str} {valyuta}</b>
• Jami daromad (Revenue): <b>{daromad_str} {valyuta}</b>
• Shariat statusi: <b>{halal_status} ({debt_ratio:.1f}%)</b>
• Kitlar (Whales) ulushi: <b>{kitlar_ulushi}</b>

⚖️ <b>Fundamental Baholash (Avtomatik):</b>
• <b>P/E Ratio:</b> {pe_status}
• <b>ROE:</b> {roe_status}
• <b>Debt/Equity (Qarz):</b> {de_status}
• <b>Current Ratio (Likvidlik):</b> {cr_status}

━━━━━━━━━━━━━━━━━━━━
💰 <b>Bozor narxi: {round(narx, 2)} {valyuta}</b> ({change_1d:+.2f}%)
📈 1K: {change_1d:+.2f}% | 1H: {change_1w:+.2f}% | 1O: {change_1m:+.2f}%
📅 52H diapazon: {high_52} / {low_52}

━━━━━━━━━━━━━━━━━━━━
📊 <b>Texnik tahlil:</b>
• RSI (14): <b>{rsi}</b> → {rsi_signal}
• Trend (MA): <b>{trend_status}</b>
• Wall Street tavsiyasi: <b>{recommendation}</b>

━━━━━━━━━━━━━━━━━━━━
🔗 <a href='https://www.tradingview.com/symbols/{tiker_clean}/'>TradingView tahlili</a>"""
        
        ai_data = f"{tiker_clean}|{round(narx,2)}|{pe_status}|{de_status}|{rsi}|{trend_status}|{halal_status}"
        return javob, tiker_clean, ai_data
    except Exception as e:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None, None

# ===================== KLAVIATURALAR =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🏛️ NYSE birjasi"), types.KeyboardButton("💻 NASDAQ birjasi"),
        types.KeyboardButton("🎯 Kun aksiyasi"), types.KeyboardButton("📖 Atamalar lug'ati"),
        types.KeyboardButton("❓ Yordam")
    )
    return kb

def inline_dictionary():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 Market Cap", callback_data="dic_mcap"),
        types.InlineKeyboardButton("📈 P/E Ratio", callback_data="dic_pe"),
        types.InlineKeyboardButton("💰 ROE nima?", callback_data="dic_roe"),
        types.InlineKeyboardButton("🚨 Debt/Equity", callback_data="dic_debteq"),
        types.InlineKeyboardButton("📉 RSI Indikatori", callback_data="dic_rsi"),
        types.InlineKeyboardButton("🐋 Kitlar kimlar?", callback_data="dic_whales")
    )
    return kb

def inline_action(tiker, ai_string):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{ai_string}"),
        types.InlineKeyboardButton("📈 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/")
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
    bot.send_message(message.chat.id, "👋 Assalomu alaykum! Aksiyalar tahlil botiga xush kelibsiz.\nTiker kiriting yoki quyidagi bo'limlardan birini tanlang:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text = message.text.strip()
    if text == "🔍 RSI Skriner":
        bot.reply_to(message, "🔍 <b>RSI Skriner bo'yicha top kompaniyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN"]))
    elif text == "🟢 Halol aksiyalar":
        bot.reply_to(message, "🟢 <b>AQSh bozoridagi halol aksiyalardan namunalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]))
    elif text == "🏛️ NYSE birjasi":
        bot.reply_to(message, "🏛️ <b>NYSE top aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["TSCO", "BRK-B", "V", "JNJ", "WMT", "KO"]))
    elif text == "💻 NASDAQ birjasi":
        bot.reply_to(message, "💻 <b>NASDAQ yetakchi aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMD"]))
    elif text == "🎯 Kun aksiyasi":
        bot.send_chat_action(message.chat.id, 'typing')
        javob, tiker, ai_str = aksiya_tahlil("MSFT")
        bot.reply_to(message, f"🎯 <b>Bugungi kun aksiyasi tavsiyasi:</b>\n\n{javob}", parse_mode="HTML", reply_markup=inline_action(tiker, ai_str) if tiker else None, disable_web_page_preview=True)
    elif text == "📖 Atamalar lug'ati":
        bot.reply_to(message, "📖 <b>Moliyaviy tahlil lug'ati bo'limi.</b>", parse_mode="HTML", reply_markup=inline_dictionary())
    elif text == "❓ Yordam":
        bot.reply_to(message, "❓ Tahlil qilmoqchi bo'lgan aksiyangiz tikerini inglizcha kiriting. Masalan: <code>AAPL</code>", parse_mode="HTML")
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        javob, tiker, ai_str = aksiya_tahlil(text)
        if tiker:
            bot.reply_to(message, javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str), disable_web_page_preview=True)
        else:
            bot.reply_to(message, javob, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("anz_"):
        ticker = call.data.split("_")[1]
        bot.send_chat_action(call.message.chat.id, 'typing')
        javob, tiker_clean, ai_str = aksiya_tahlil(ticker)
        bot.send_message(call.message.chat.id, javob, parse_mode="HTML", reply_markup=inline_action(tiker_clean, ai_str) if tiker_clean else None, disable_web_page_preview=True)
    
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
            bot.send_chat_action(call.message.chat.id, 'typing')
            
            ai_advice = get_ai_advice(tiker, price, pe, de, rsi, trend, halal)
            bot.send_message(call.message.chat.id, f"🤖 <b>{tiker} bo'yicha Sun'iy Intellekt Maslahati:</b>\n\n<i>\"{ai_advice}\"</i>", parse_mode="HTML")
        except Exception as e:
            bot.send_message(call.message.chat.id, "❌ AI tahlilini yuklashda xatolik yuz berdi.")
            
    elif call.data.startswith("dic_"):
        term = call.data.split("_")[1]
        expl = ""
        if term == "mcap": expl = "📊 <b>Market Cap:</b> Kompaniyaning bozordagi umumiy joriy qiymati."
        elif term == "pe": expl = "📈 <b>P/E Ratio:</b> Aksiya narxi uning foydasidan necha barobar qimmatligi. 15-25 orasi yaxshi."
        elif term == "roe": expl = "💰 <b>ROE:</b> Kompaniya o'z investorlarining pulidan qanchalik samarali foyda ko'rayotgani."
        elif term == "debteq": expl = "🚨 <b>Debt/Equity:</b> Qarz yuklamasi. 0.50 dan past bo'lsa xavfsiz va yaxshi."
        elif term == "rsi": expl = "📉 <b>RSI:</b> Aksiyaning arzon (30 dan past) yoki qimmatligini (70 dan baland) ko'rsatadi."
        elif term == "whales": expl = "🐋 <b>Kitlar:</b> Bozordagi trillionlab dollarlarni boshqaradigan yirik banklar va investitsiya fondlari."
        
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
