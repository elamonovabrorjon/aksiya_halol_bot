import telebot  
from telebot import types
import yfinance as yf
import time
import finnhub
import html
from datetime import datetime, timedelta
 # ===================== SOZLAMALAR =====================
TOKEN = '8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8'
FINNHUB_KEY = 'ctv22h9r01qg80atc9vg'

bot = telebot.TeleBot(TOKEN)

try:
    finnhub_client = finnhub.Client(api_key=FINNHUB_KEY)
except Exception as e:
    print(f"Finnhub ogohlantirish: {e}")
    finnhub_client = None

SCREENER_STOCKS = ["AAPL", "MSFT", "AMZN", "NVDA", "TSLA", "META", "GOOGL", "NFLX", "AMD", "MU", "NKE", "DIS", "KO", "WMT", "JPM", "XOM", "JNJ", "PYPL", "V", "BBAI"]

UZSE_STOCKS = {
    "UZAUTO":       {"nom": "UzAuto Motors",         "holat": "🟢 HALOL",    "sabab": "Avtomobil ishlab chiqarish. Halol sanoat."},
    "NAVOIYAZOT":   {"nom": "Navoiyazot",             "holat": "🟢 HALOL",    "sabab": "O'g'it va kimyoviy mahsulotlar ishlab chiqarish. Halol sanoat."},
    "ALMALYK":      {"nom": "Olmaliq KMK (AGMK)",     "holat": "🟢 HALOL",    "sabab": "Rangli metallar konchilik va metallurgiya sanoati. Halol."},
    "KVARZ":        {"nom": "Kvarts AJ",              "holat": "🟢 HALOL",    "sabab": "Oyna va shisha mahsulotlari ishlab chiqarish. Halol."},
    "UZTELECOM":    {"nom": "O'ztelekom (Uztelecom)", "holat": "🟡 SHUBHALI", "sabab": "Aloqa xizmatlari. Kredit yuklamalari sababli ehtiyotkorlik zarur."},
    "HAMKORBANK":   {"nom": "Hamkorbank",             "holat": "🔴 HAROM",    "sabab": "An'anaviy bank faoliyati — ribo (foiz) asosida ishlaydi."},
    "KAPITALBANK":  {"nom": "Kapital Bank",           "holat": "🔴 HAROM",    "sabab": "An'anaviy bank faoliyati — ribo (foiz) va kreditlash tizimi."}
}

# ===================== MENYU (PORTFOLIO O'CHIRILDI) =====================
def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🔍 RSI Skriner (30/70)"),
        types.KeyboardButton("📰 Bozor Yangiliklari"),
        types.KeyboardButton("🟢 Halol aksiyalar"),
        types.KeyboardButton("🔴 Harom aksiyalar"),
        types.KeyboardButton("🟡 Shubhali aksiyalar"),
        types.KeyboardButton("🇺🇸 S&P 500"),
        types.KeyboardButton("🏛️ NASDAQ"),
        types.KeyboardButton("🏢 NYSE"),
        types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"),
        types.KeyboardButton("❓ Yordam")  # "Mening Portfolio" tugmasi olib tashlandi
    )
    return kb

def yordam_inline_button():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➡️ Administrator Lichkasi", url="https://t.me/EAA_7879"))
    return kb

# ===================== INDIKATORLAR =====================
def hisobla_rsi(closes, period=14):
    try:
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period-1, adjust=False).mean()
        avg_loss = loss.ewm(com=period-1, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        if rsi >= 70: signal = "SELL 📉"
        elif rsi <= 30: signal = "BUY 📈"
        else: signal = "WAIT ↕️ (Normal)"
        return round(rsi, 2), signal
    except:
        return 50.0, "WAIT ↕️"

def hisobla_macd(closes):
    try:
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        if macd_line.iloc[-1] > signal_line.iloc[-1]: macd_signal = "BUY 📈"
        else: macd_signal = "SELL 📉"
        return round(macd_line.iloc[-1], 2), round(signal_line.iloc[-1], 2), macd_signal
    except:
        return 0, 0, "Noma'lum"

def hisobla_bollinger(closes, period=20):
    try:
        sma = closes.rolling(window=period).mean().iloc[-1]
        std = closes.rolling(window=period).std().iloc[-1]
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        joriy = closes.iloc[-1]
        if joriy > upper: bb_signal = "SELL 📉"
        elif joriy < lower: bb_signal = "BUY 📈"
        else: bb_signal = "NORMAL ↕️"
        return round(upper, 2), round(lower, 2), bb_signal
    except:
        return 0, 0, "Noma'lum"

# ===================== TAHLIL FUNKSIYASI =====================
def aksiya_tahlil(tiker):
    stock = yf.Ticker(tiker)
    try: info = stock.info
    except: return None, None

    if not info or 'currentPrice' not in info: return None, None

    narx = info.get('currentPrice', 0)
    valyuta = info.get('currency', 'USD')
    market_cap_raw = info.get('marketCap', 1)
    pe = info.get('trailingPE', "Noma'lum")
    sektor = info.get('sector', "Noma'lum")

    high_52w = info.get('fiftyTwoWeekHigh', 0)
    low_52w = info.get('fiftyTwoWeekLow', 0)

    div_yield_raw = info.get('dividendYield', 0)
    div_yield = f"{div_yield_raw * 100:.2f}%" if div_yield_raw else "To'lamaydi ❌"

    def format_raqam(raqam):
        if not raqam or raqam == "Noma'lum": return "Noma'lum"
        if raqam >= 1e12: return f"{raqam / 1e12:.2f} T"
        elif raqam >= 1e9: return f"{raqam / 1e9:.2f} B"
        elif raqam >= 1e6: return f"{raqam / 1e6:.2f} M"
        return f"{raqam:,}"

    market_cap = format_raqam(market_cap_raw)

    pb = info.get('priceToBook', "Noma'lum")
    if isinstance(pb, (int, float)): pb = round(pb, 2)
    
    roe_raw = info.get('returnOnEquity', None)
    roe = f"{roe_raw * 100:.2f}%" if roe_raw else "Noma'lum"
    
    eps = info.get('trailingEps', 0)
    income_status = "📈 Foyda" if (isinstance(eps, (int, float)) and eps >= 0) else "📉 Zarar"

    fcf_raw = info.get('freeCashflow', None)
    fcf = format_raqam(fcf_raw) if fcf_raw else "Noma'lum"

    try:
        tarix = stock.history(period="1y")
        yopilish = tarix['Close']
        uzunlik = len(yopilish)
    except: return "❌ Birja tarixi yuklanmadi.", tiker

    rsi, rsi_signal = hisobla_rsi(yopilish)
    macd_val, _, macd_signal = hisobla_macd(yopilish)
    bb_upper, bb_lower, bb_signal = hisobla_bollinger(yopilish)

    if uzunlik > 60:
        oxirgi_3m = yopilish.iloc[-60:]
        max_3m = oxirgi_3m.max()
        min_3m = oxirgi_3m.min()
        diff = max_3m - min_3m
        fib_382 = max_3m - (diff * 0.382)
        fib_500 = max_3m - (diff * 0.500)
        fib_618 = max_3m - (diff * 0.618)
        fib_text = f"  • 🔵 38.2%: {round(fib_382, 2)} {valyuta}\n  • 🟡 50.0% (Equil): {round(fib_500, 2)} {valyuta}\n  • 🟠 61.8% (Golden): {round(fib_618, 2)} {valyuta}"
    else:
        fib_text = "  • Tarix yetarli emas."

    qarz = info.get('totalDebt', 0)
    nisbat = (qarz / market_cap_raw) * 100 if market_cap_raw else 0
    if nisbat < 30: halal_status = f"🟢 HALOL ({nisbat:.2f}%)"
    elif 30 <= nisbat <= 33: halal_status = f"🟡 SHUBHALI ({nisbat:.2f}%)"
    else: halal_status = f"🔴 HAROM ({nisbat:.2f}%)"

    kitlar_text = ""
    try:
        holders = stock.institutional_holders
        if holders is not None and not holders.empty:
            for index, row in holders.head(3).iterrows():
                holder_name = row.get('Holder', 'Noma\'lum fond')
                shares_held = row.get('Shares', 0)
                kitlar_text += f"  • 🏢 {html.escape(str(holder_name))}: {format_raqam(shares_held)} ta\n"
        else: kitlar_text = "  • Fondlar topilmadi.\n"
    except: kitlar_text = "  • Fondlar topilmadi.\n"

    target_text = "  • Prognoz mavjud emas."
    target_mean = info.get('targetMeanPrice')
    if target_mean:
        potential = ((target_mean - narx) / narx) * 100
        potential_str = f"+{potential:.2f}%" if potential > 0 else f"{potential:.2f}%"
        target_text = f"  • 🎯 O'rtacha maqsad: {round(target_mean, 2)} {valyuta} (📈 {potential_str})"

    insider_text = "  • Oxirgi o'zgarishlar barqaror."
    if finnhub_client:
        try:
            insider_trans = finnhub_client.stock_insider_transactions(tiker)
            if insider_trans and 'data' in insider_trans and insider_trans['data']:
                trades = insider_trans['data'][:2]
                insider_lines = []
                for t in trades:
                    name = t.get('name', 'Insayder')
                    share_change = t.get('share', 0)
                    action = "🟢 S.OLDI" if share_change > 0 else "🔴 SOTDI"
                    insider_lines.append(f"  • {html.escape(name[:15])}: {action} ({abs(share_change):,})")
                insider_text = "\n".join(insider_lines)
        except: pass

    news_text = "  • Yangiliklar e'lon qilinmadi."

    ball = 3.0
    if halal_status.startswith("🔴"): ball -= 1.5
    else: ball += 0.5
    
    if rsi >= 70: ball -= 1.0
    elif rsi <= 30: ball += 1.5
    
    if income_status == "📈 Foyda": ball += 0.5
    ball = max(1.0, min(5.0, ball))
    yulduzlar = "⭐" * int(round(ball))

    if halal_status.startswith("🔴"):
        maslahat_turi = "🔴 SHARIATGA MOS EMAS ⛔"
    elif ball >= 4.5:
        maslahat_turi = "🔥 STRONG BUY 🟢"
    elif 3.5 <= ball < 4.5:
        maslahat_turi = "📈 ACCUMULATE 🟢"
    else:
        maslahat_turi = "HOLD (Kuzatish) 🟡"

    izoh_punktlari = []
    if halal_status.startswith("🔴"): izoh_punktlari.append("• ⛔ Qarz yuklamasi yuqori (Ribo).")
    else: izoh_punktlari.append("• ✅ Qarz yuklamasi me'yorda (Halol).")
    
    if rsi >= 70: izoh_punktlari.append(f"• ⚠️ RSI ({rsi}): Aksiya haddan taxation qizigan.")
    elif rsi <= 30: izoh_punktlari.append(f"• 🎯 RSI ({rsi}): Narx juda arzon zonada.")
    else: izoh_punktlari.append(f"• ⚖️ RSI ({rsi}): Narx muvozanatda.")
    bot_izohi = "\n".join(izoh_punktlari)

    javob = f"""📊 <b>{tiker}</b> | {html.escape(info.get('longName', 'Noma\'lum'))}
Sektor: {html.escape(sektor)} | ⚖️ Shariat: {halal_status}

━━━━━━━━━━━━━━━━━━━━
💰 Narx ko'rsatkichlari:
📌 Joriy narx: {round(narx, 2)} USD
📅 52W M/M: {high_52w} / {low_52w}
💎 Cap: {market_cap} | 💰 Div: {div_yield}

━━━━━━━━━━━━━━━━━━━━
📊 Chuqur Fundamental Tahlil:
📌 P/E Nisbati: {f'{pe:.2f}' if isinstance(pe, (int, float)) else pe} | {income_status}
📌 P/B: {pb} | ROE: {roe} | EPS: {eps}
📌 Erkin pul oqimi (FCF): {fcf}

━━━━━━━━━━━━━━━━━━━━
📐 Fibonacci Darajalari (3M):
{fib_text}

━━━━━━━━━━━━━━━━━━━━
📈 Dinamika: 1D: {change_1d:+.2f}% | 1W: {change_1w:+.2f}% | 1M: {change_1m:+.2f}%

━━━━━━━━━━━━━━━━━━━━
🧭 Indikatorlar:
📌 RSI (14): {rsi} → {rsi_signal}
📌 MACD: {macd_signal} | Bollinger: {bb_signal}

━━━━━━━━━━━━━━━━━━━━
🎯 Wall Street Prognozi:
{target_text}

━━━━━━━━━━━━━━━━━━━━
👥 Insayderlar Harakati:
{insider_text}

━━━━━━━━━━━━━━━━━━━━
🐋 Yirik Fondlar:
{kitlar_text}
━━━━━━━━━━━━━━━━━━━━
📰 Yangiliklar:
{news_text}

━━━━━━━━━━━━━━━━━━━━
🧠 BOT DIAGNOSTIKASI:
Baho: {ball:.1f}/5.0 {yulduzlar} -> {maslahat_turi}
📝 Izoh: {bot_izohi}"""

    return javob, tiker

# ===================== TEXT HANDLER =====================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    text = message.text.strip()

    if text == "🔍 RSI Skriner (30/70)":
        status_msg = bot.reply_to(message, "⏳ Bozor tahlil qilinmoqda...")
        oversold, overbought, normal_low = [], [], []
        for ticker in SCREENER_STOCKS:
            try:
                stock = yf.Ticker(ticker)
                tarix = stock.history(period="1mo")
                if not tarix.empty:
                    closes = tarix['Close']
                    delta = closes.diff()
                    gain = delta.clip(lower=0)
                    loss = -delta.clip(upper=0)
                    avg_gain = gain.ewm(com=13, adjust=False).mean()
                    avg_loss = loss.ewm(com=13, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs.iloc[-1]))
                    if rsi <= 30: oversold.append((ticker, round(rsi, 1)))
                    elif rsi >= 70: overbought.append((ticker, round(rsi, 1)))
                    elif 30 < rsi <= 40: normal_low.append((ticker, round(rsi, 1)))
            except: pass

        matn = "🔍 <b>RSI Skriner Natijalari:</b>\n\n🟢 <b>🔥 OVERSOLD (RSI &lt;= 30):</b>\n"
        if oversold:
            for t, r in sorted(oversold, key=lambda x: x[1]): matn += f"• <b>{t}</b> — RSI: <code>{r}</code> 🎯\n"
        else: matn += f"• <i>RSI 30 dan past aksiya yo'q.</i>\n"

        matn += "\n🟡 <b>KUZATUV HUDUDI (30-40):</b>\n"
        if normal_low:
            for t, r in sorted(normal_low, key=lambda x: x[1]): matn += f"• <b>{t}</b> — RSI: <code>{r}</code> ⏳\n"
        
        matn += "\n🔴 <b>🔥 OVERBOUGHT (RSI &gt;= 70):</b>\n"
        if overbought:
            for t, r in sorted(overbought, key=lambda x: x[1], reverse=True): matn += f"• <b>{t}</b> — RSI: <code>{r}</code> ⚠️\n"
        else: matn += f"• <i>RSI 70 dan baland aksiya yo'q.</i>\n"
            
        kb = types.InlineKeyboardMarkup(row_width=4)
        all_detected = [t for t, _ in (oversold + normal_low + overbought)]
        kb.add(*[types.InlineKeyboardButton(t, callback_data=f"analyze_{t}") for t in all_detected])
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(message.chat.id, matn, parse_mode="HTML", reply_markup=kb)
        return

    elif text == "📰 Bozor Yangiliklari":
        status_msg = bot.reply_to(message, "⏳ Global yangiliklar yuklanmoqda...")
        matn = "📰 <b>Global Fond Bozori Yangiliklari:</b>\n\n"
        if finnhub_client:
            try:
                general_news = finnhub_client.general_news('general', min_id=0)
                if general_news:
                    for n in general_news[:5]:
                        headline = html.escape(n.get('headline', 'Sarlavha yo\'q'))
                        url = html.escape(n.get('url', '#'))
                        source = html.escape(n.get('source', 'Manba'))
                        matn += f"🔥 <b>{headline}</b>\nManba: <i>{source}</i>\n🔗 <a href='{url}'>O'qish</a>\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
                else: matn += "<i>Yangi xabarlar topilmadi.</i>"
            except:
                matn += f"<i>Yangiliklarni yuklashda cheklov yuz berdi.</i>"
        else:
            matn += "<i>Finnhub API ulanmagan.</i>"
        
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(message.chat.id, matn, parse_mode="HTML", disable_web_page_preview=True)
        return

    elif text in ["🟢 Halol aksiyalar", "🔴 Harom aksiyalar", "🟡 Shubhali aksiyalar", "🇺🇸 S&P 500", "🏛️ NASDAQ", "🏢 NYSE"]:
        tickers_map = {
            "🟢 Halol aksiyalar": ["AAPL", "TSLA", "NVDA", "MSFT", "JNJ", "MU"],
            "🔴 Harom aksiyalar": ["JPM", "BAC", "MCD", "NFLX"],
            "🟡 Shubhali aksiyalar": ["AMZN", "META", "V", "PYPL"],
            "🇺🇸 S&P 500": ["AAPL", "MSFT", "AMZN", "GOOGL"],
            "🏛️ NASDAQ": ["NVDA", "TSLA", "META", "MU"],
            "🏢 NYSE": ["NKE", "DIS", "KO", "WMT"]
        }
        kb = types.InlineKeyboardMarkup(row_width=3)
        kb.add(*[types.InlineKeyboardButton(t, callback_data=f"analyze_{t}") for t in tickers_map[text]])
        bot.send_message(message.chat.id, f"{text} ro'yxati:", reply_markup=kb)
        return

    elif text == "🇺🇿 O'zbekiston aksiyalari":
        matn = "🇺🇿 <b>O'zbekiston aksiyalari (UZSE) Tasnifi:</b>\n\n"
        for ticker, data in UZSE_STOCKS.items():
            matn += f"📌 <b>{ticker}</b> — {data['nom']}\n{data['holat']} | <i>{data['sabab']}</i>\n\n"
        bot.reply_to(message, matn, parse_mode="HTML")
        return

    elif text == "❓ Yordam":
        yordam_matni = "❓ <b>Yordam va Aloqa bo'limi</b>\n\nAdministrator bilan bog'lanish uchun quyidagi tugmani bosing:"
        bot.send_message(message.chat.id, yordam_matni, parse_mode="HTML", reply_markup=yordam_inline_button())
        return

    elif text == "/start":
        bot.send_message(message.chat.id, "Kerakli bo'limni tanlang:", reply_markup=main_menu())
        return

    try:
        tiker = text.upper()
        bot.send_chat_action(message.chat.id, 'typing')
        javob, _ = aksiya_tahlil(tiker)
        if not javob:
            bot.reply_to(message, "❌ Aksiya topilmadi.")
            return
        inline_kb = types.InlineKeyboardMarkup(row_width=2)
        inline_kb.add(
            types.InlineKeyboardButton("📈 TradingView", url=f"https://www.tradingview.com/symbols/{tiker}/"),
            types.InlineKeyboardButton("📊 Jonli Grafik", url=f"https://s.tradingview.com/widgetembed/?symbol={tiker}&interval=D")
        )
        bot.reply_to(message, javob, parse_mode="HTML", reply_markup=inline_kb)
    except: 
        bot.reply_to(message, "❌ Xatolik yuz berdi.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("analyze_"))
def callback_analyze_stock(call):
    ticker = call.data.split("_")[1]
    bot.send_chat_action(call.message.chat.id, 'typing')
    javob, _ = aksiya_tahlil(ticker)
    if javob:
        inline_kb = types.InlineKeyboardMarkup(row_width=2)
        inline_kb.add(
            types.InlineKeyboardButton("📈 TradingView", url=f"https://www.tradingview.com/symbols/{ticker}/"),
            types.InlineKeyboardButton("📊 Jonli Grafik", url=f"https://s.tradingview.com/widgetembed/?symbol={ticker}&interval=D")
        )
        bot.send_message(call.message.chat.id, javob, parse_mode="HTML", reply_markup=inline_kb)
    bot.answer_callback_query(call.id)

# ===================== ISHGA TUSHIRISH =====================
print("🔥 PRO BOT xatolarsiz muvaffaqiyatli ishga tushdi!")
bot.infinity_polling(timeout=60, long_polling_timeout=5)
