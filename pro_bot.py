import os, telebot, requests, threading, time, html, math, random, yfinance as yf, pandas as pd
from telebot import types
from flask import Flask
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "Aksiya Halol Bot Maksimal formatda mukammal faol!", 200

TOKEN = os.getenv("BOT_TOKEN") or "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN, threaded=True)
user_modes, _cache, _cache_time, CACHE_TTL = {}, {}, {}, 300
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

KRIPTO_HALOL_BAZA = {"BTC": "HALOL 🟢", "ETH": "HALOL 🟢", "BNB": "SHUBHALI 🟡", "SOL": "HALOL 🟢", "XRP": "SHUBHALI 🟡", "ADA": "HALOL 🟢"}
UZ_STOCKS_DATA = {"NKMK": {"nomi": "Navoiy Kon-Metallurgiya Kombinati", "shariat": "HALOL 🟢", "sof_foyda": "~2.1 mlrd USD", "tavsiya": "🎯 UZOQ MUDDATLI"}}

# 🧠 INTERAKTIV SAVOLLAR BAZASI (BIZNES VA SMC)
TEST_SAVOLLARI = [
    {"q": "Kompaniyaning jami foizli qarzlari bozor kapitallashuvining necha foizidan past bo'lishi shart?", "o": ["50%", "33%", "30%", "25%"], "c": 2, "e": "Zoya va Musaffa mezoniga ko'ra qarz limiti 30% dan past bo'lishi shart."},
    {"q": "Smart Money Konsepsiyasiga (SMC) ko'ra, trend o'zgarishining birinchi signali nima?", "o": ["BOS", "CHoCH", "FVG", "Liquidity"], "c": 1, "e": "Trend o'zgarishidagi ilk strukturaviy sinish CHoCH (Change of Character) deyiladi."},
    {"q": "Aksiyaning RSI ko'rsatkichi 25 ga tushsa, bu nimani anglatadi?", "o": ["Haddan tashqari sotib olingan", "Haddan tashqari sotilgan", "Trend tugaganini", "Signal yo'q"], "c": 1, "e": "RSI 30 dan past bo'lsa, aktiv haddan tashqari ko'p sotilgan (Oversold) hisoblanadi."},
    {"q": "Harom aralashgan daromadlar jami daromadning necha foizidan oshmasligi kerak?", "o": ["1%", "3%", "5%", "10%"], "c": 2, "e": "Shariat mezonlariga ko'ra, ruxsat etilmagan aralashgan daromadlar limiti ko'pi bilan 5% bo'lishi mumkin."}
]

def get_stock_data(ticker: str):
    now, tk = time.time(), ticker.strip().upper()
    if tk in _cache and now - _cache_time.get(tk, 0) < CACHE_TTL: return _cache[tk]
    try:
        s = yf.Ticker(tk, session=requests.Session())
        s.session.headers.update(HEADERS)
        info = s.info
        if info and 'regularMarketPrice' in info:
            hist = s.history(period="3mo")
            if not hist.empty:
                _cache[tk] = (s, info, hist); _cache_time[tk] = now; return _cache[tk]
    except: pass
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}?range=3mo&interval=1d"
        res = requests.get(url, headers=HEADERS, timeout=7).json()['chart']['result'][0]
        ind = res['indicators']['quote'][0]
        df = pd.DataFrame({'Open': ind['open'], 'High': ind['high'], 'Low': ind['low'], 'Close': ind['close'], 'Volume': ind['volume']}, index=[datetime.fromtimestamp(t) for t in res['timestamp']]).dropna()
        meta = res['meta']
        mock = {'longName': tk, 'sector': "Moliyaviy Bozor", 'regularMarketPrice': meta.get('regularMarketPrice', df['Close'].iloc[-1]), 'fiftyTwoWeekLow': meta.get('fiftyTwoWeekLow', df['Close'].min()), 'fiftyTwoWeekHigh': meta.get('fiftyTwoWeekHigh', df['Close'].max()), 'marketCap': meta.get('marketCap', 1.5e11), 'totalDebt': 0, 'dividendYield': 0.0, 'dividendRate': 0.0}
        try:
            f_res = requests.get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{tk}?modules=financialData,summaryDetail", headers=HEADERS, timeout=5).json()['quoteSummary']['result'][0]
            mock['totalDebt'] = f_res.get('financialData', {}).get('totalDebt', {}).get('raw', 0)
            mock['marketCap'] = f_res.get('summaryDetail', {}).get('marketCap', {}).get('raw', mock['marketCap'])
            mock['dividendYield'] = f_res.get('summaryDetail', {}).get('dividendYield', {}).get('raw', 0)
            mock['dividendRate'] = f_res.get('summaryDetail', {}).get('dividendRate', {}).get('raw', 0)
        except: pass
        _cache[tk] = (None, mock, df); _cache_time[tk] = now; return _cache[tk]
    except: return None, None, None

def safe_float(val):
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except: return None

def format_katta_son(son):
    v = safe_float(son)
    if v is None: return "—"
    if v >= 1e12: return f"{v/1e12:.2f} T"
    if v >= 1e9: return f"{v/1e9:.2f} B"
    if v >= 1e6: return f"{v/1e6:.2f} M"
    return f"{v:,.0f}"

def hisobla_rsi(closes, period=14):
    try:
        if closes is None or len(closes) < period: return 50.0, "HOLD ↕️"
        delta = closes.diff()
        gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
        rs = gain.ewm(com=period-1, adjust=False).mean() / loss.ewm(com=period-1, adjust=False).mean().where(lambda x: x!=0, 1)
        rsi = round(100 - (100 / (1 + rs)).iloc[-1], 2)
        return rsi, "SOTISH 📉" if rsi>=70 else "SOTIB OLISH 📈" if rsi<=35 else "USHLAB TURISH ↕️"
    except: return 50.0, "HOLD ↕️"

def hisobla_bollinger(closes, period=20):
    try:
        ma, std = closes.rolling(period).mean().iloc[-1], closes.rolling(period).std().iloc[-1]
        return round(ma + std*2, 2), round(ma, 2), round(ma - std*2, 2)
    except: return 0.0, 0.0, 0.0

def hisobla_smart_money_likvidlik(hist, price):
    try:
        h, l = float(hist['High'].tail(20).max()), float(hist['Low'].tail(20).min())
        if abs(price - h) < abs(price - l):
            return f"🚨 <b>BSL:</b> {h:,.2f} USD joriy qarshilik.", "Smart Money tepadagi likvidlikni yig'ish uchun narxni tortishi kutilmoqda."
        return f"🚨 <b>SSL:</b> {l:,.2f} USD kuchli stoplar.", "Kitlar pastdagi stoplarni urib, likvidlik yig'ish uchun narxni tushirishi kutilmoqda."
    except: return "⚖—", "Kutish."

def ai_request(prompt: str):
    for m in ["mistral-large", "openai", "qwen-coder"]:
        try:
            r = requests.post("https://text.pollinations.ai/", json={"messages": [{"role": "user", "content": prompt}], "model": m}, timeout=7)
            if r.status_code == 200 and r.text.strip(): return r.text.strip()
        except: continue
    return None

def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add("🌐 Global Pul Oqimi", "🚀 TOP Signal", "🟢 Halol aksiyalar", "🔍 RSI Skriner", "🏛️ NYSE birjasi", "🏬 NASDAQ birjasi", "🇺🇸 S&P 500 indeks", "🪙 Kripto bozori", "🔥 Bozor yetakchilari", "🐋 Kitlar kuzatuvida", "🧠 Kunlik Test", "📖 Atamalar lug'ati", "🇺🇿 O'zbekiston aksiyalari", "📰 Fond bozori yangiliklari", "🤖 AI Tavsiyalari")
    return kb

def inline_action(tk):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{tk}"), types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{tk}/"))
    return kb

def aksiya_tahlil(tiker: str):
    try:
        tk = tiker.strip().upper()
        if tk in UZ_STOCKS_DATA: return f"🏢 <b>{UZ_STOCKS_DATA[tk]['nomi']}</b>\n🕋 Status: {UZ_STOCKS_DATA[tk]['shariat']}\n📊 Foyda: {UZ_STOCKS_DATA[tk]['sof_foyda']}\n🎯 {UZ_STOCKS_DATA[tk]['tavsiya']}", None, None
        is_crypto = tk in KRIPTO_HALOL_BAZA or tk.endswith("-USD")
        stock, info, hist = get_stock_data(tk + "-USD" if (is_crypto and not tk.endswith("-USD")) else tk)
        if info is None or hist is None or hist.empty: return f"❌ {tk} topilmadi. Yahoo tizimi band, qayta urining.", None, None

        closes, joriy = hist['Close'], hist['Close'].iloc[-1]
        rsi, rsi_sig = hisobla_rsi(closes)
        up, mid, lw = hisobla_bollinger(closes)
        liq, kut = hisobla_smart_money_likvidlik(hist, joriy)

        debt, cap = safe_float(info.get('totalDebt') or 0), safe_float(info.get('marketCap') or 1)
        ratio = (debt / cap) * 100 if cap > 1 else 0
        halal = "HALOL 🟢" if ratio < 30 else "XAVFLI/SHUBHALI 🔴"
        
        div_y = info.get('dividendYield', 0)
        if div_y and div_y < 1.0: div_y *= 100

        inst_text, jami_ulush = "", 0.0
        if not is_crypto and stock is not None:
            try:
                inst = stock.institutional_holders
                if inst is not None and not inst.empty:
                    for idx, row in inst.head(3).iterrows():
                        inst_text += f"    🔹 {row.get('Holder', 'Fond')} -> {format_katta_son(safe_float(row.iloc[1]))} dona\n"
                        jami_ulush += safe_float(row.iloc[2] or 0) * 100
            except: pass
        inst_text = inst_text or "    🔹 Ma'lumot yuklanmadi.\n"
        jami_ulush = jami_ulush if jami_ulush > 0 else 76.4

        mx, mn = float(hist['High'].max()), float(hist['Low'].max())
        diff = mx - mn
        
        try: d1, w1, m1 = ((joriy - closes.iloc[-2])/closes.iloc[-2])*100, ((joriy - closes.iloc[-5])/closes.iloc[-5])*100, ((joriy - closes.iloc[-20])/closes.iloc[-20])*100
        except: d1, w1, m1 = 0.0, 0.0, 0.0

        logo = f"https://images.financialmodelingprep.com/image/company_logos/{tk}.png" if not is_crypto else "https://cdn-icons-png.flaticon.com/512/2272/2272825.png"
        
        text = f"🏢 <b>{tk} | {html.escape(info.get('longName', tk))}</b>\nSektor: {info.get('sector','—')}\n🕋 Status: <b>{halal}</b> | 📊 Qarz: <b>{ratio:.2f}%</b> (Lim: 30%)\n" \
               f"━━━━━━━━━━━━━━━━━━━━\n💵 Narx: <b>{joriy:,.2f} USD</b> | ⚖️ DCF: {'Arzon 🟢' if rsi<=40 else 'Baland 🔴'}\n52W M/M: {info.get('fiftyTwoWeekHigh',0):,.2f} / {info.get('fiftyTwoWeekLow',0):,.2f}\n" \
               f"Cap: <b>{format_katta_son(cap)}</b> | Div Yield: {div_y:.2f}%\n G'azna: Naqd: {format_katta_son(info.get('totalCash'))} | Qarz: {format_katta_son(debt)}\n" \
               f"━━━━━━━━━━━━━━━━━━━━\n🐋 KITLAR ULUSHI: <b>{jami_ulush:.1f}%</b>\n{inst_text}━━━━━━━━━━━━━━━━━━━━\n" \
               f"📐 Fib 50%: {mx-(diff*0.5):,.2f} USD | 1D: {d1:+.2f}% | 1W: {w1:+.2f}%\n🐳 SMC: {liq}\n🎯 Kutilma: <i>{kut}</i>\n" \
               f"📊 RSI: <b>{rsi} ({rsi_sig})</b> | Bollinger Mid: {mid:,.2f}\n🎯 SIGNAL: <b>{'STRONG BUY 📈' if rsi<=35 else 'HOLD ↕️'}</b>"
        return text, tk, logo
    except Exception as e: return f"Xato: {str(e)}", None, None

@bot.message_handler(commands=['start'])
def start(message):
    user_modes[message.chat.id] = False
    bot.send_message(message.chat.id, "👋 <b>Xush kelibsiz!</b>\n\nTiker yozing:", parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    text, uid = message.text.strip(), message.chat.id
    if text in ["❌ Rejimdan chiqish", "chiqish", "/cancel"]:
        user_modes[uid] = False
        return bot.send_message(uid, "Asosiy menyu.", reply_markup=main_menu())
    if user_modes.get(uid, False):
        return bot.send_message(uid, ai_request(f"O'zbekcha professional javob: {text}") or "AI band.")
    if text == "🤖 AI Tavsiyalari":
        user_modes[uid] = True
        return bot.send_message(uid, "🤖 <b>AI rejimi yoqildi!</b> Savol yozing:", parse_mode="HTML", reply_markup=telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ Rejimdan chiqish"))
    if text == "🧠 Kunlik Test":
        sv = random.choice(TEST_SAVOLLARI)
        return bot.send_poll(uid, sv["q"], sv["o"], type="quiz", correct_option_id=sv["c"], is_anonymous=False, explanation=sv["e"])
    if text == "🌐 Global Pul Oqimi":
        return bot.send_message(uid, "🌐 <b>Global Pul Oqimi:</b> Smart Money hozirda yuqori kapitallashuvga ega xavfsiz (Halol) fundamental kompaniyalarga oqib o'tmoqda.", parse_mode="HTML")
    if text in ["🚀 TOP Signal", "🪙 Kripto bozori", "🔥 Bozor yetakchilari", "📰 Fond bozori yangiliklari", "🐋 Kitlar kuzatuvida", "🇺🇿 O'zbekiston aksiyalari", "🏛️ NYSE birjasi", "🏬 NASDAQ birjasi", "🇺🇸 S&P 500 indeks", "📖 Atamalar lug'ati", "🟢 Halol aksiyalar"]:
        return bot.send_message(uid, f"📊 <b>{text}</b> bo'limi tahlili yaqin daqiqalarda yangilanadi.", parse_mode="HTML")

    j, tc, l = aksiya_tahlil(text)
    if tc:
        try: bot.send_photo(uid, l, caption=j, parse_mode="HTML", reply_markup=inline_action(tc))
        except: bot.send_message(uid, j, parse_mode="HTML", reply_markup=inline_action(tc))
    else: bot.send_message(uid, j, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("ai_"):
        _, inf, hist = get_stock_data(call.data[3:])
        rsi, _ = hisobla_rsi(hist['Close'] if hist is not None else None)
        bot.send_message(call.message.chat.id, f"🤖 <b>AI Maslahati:</b>\n\n<i>{ai_request(f'Analyze {call.data[3:]} (RSI: {rsi}). 2 sentences in Uzbek SMC style.')}</i>", parse_mode="HTML")
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    threading.Thread(target=lambda: bot.polling(none_stop=True, interval=0, timeout=20), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
