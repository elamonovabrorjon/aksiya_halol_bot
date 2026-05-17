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

# ===================== SESSIONS (AI REJIMINI SAQLASH) =====================
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

# ===================== O'ZBEKISTON AKSIYALARI UCHUN AI TAHLILCHISI (YANGI) =====================
def uzbekistan_stock_analysis(text_input: str):
    prompt = (
        f"Siz Toshkent Respublika Fond Birjasi (Toshkent RFB) bo'yicha professional moliya tahlilchisiz.\n"
        f"Foydalanuvchi quyidagi O'zbekiston kompaniyasini tahlil qilishni so'radi: '{text_input}'.\n\n"
        f"Iltimos, ushbu aksiya haqida o'zingizda bor eng so'nggi moliyaviy ma'lumotlar va hisobotlar asosida "
        f"quyidagi tartibli va minimalist strukturada professional tahlil tayyorlab bering:\n\n"
        f"🇺🇿 <b>Kompaniya nomi:</b> [To'liq nomi va qisqartma tikeri]\n"
        f"📊 <b>Fundamental holati:</b> [Kompaniyaning rentabelligi, sof foyda dinamikasi va dividend to'lashi haqida lo'nda baho]\n"
        f"⚠️ <b>Asosiy xavf-xatarlar (Risk):</b> [Investor bilishi kerak bo'lgan kamchiliklar yoki birjadagi likvidlik muammolari]\n"
        f"🎯 <b>YAKUNIY QAROR:</b> [Sotib olish tavsiya etiladimi (BUY) yoki hozircha chetda turgan ma'qulmi (AVOID/SELL) - aniq va lo'nda xulosa]\n\n"
        f"Javob faqat toza o'zbek tilida, chiroyli va qisqa satrlarda bo'lsin. Pul birligi sifatida UZS (so'm) foydalanilsin."
    )
    res = ai_request(prompt)
    if res:
        return f"━━━━━━━━━━━━━━━━━━━━\n🇺🇿 <b>TOSHKENT RFB TAHLILI</b>\n━━━━━━━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━━━━━━━"
    return "❌ O'zbekiston aksiyasi tahlilida xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring."

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
            f"Quyidagi jahon iqtisodiyoti va Bloomberg yangiliklarini professional o'zbek tiliga qisqa va lo'nda "
            f"tarjima qilib bering:\n\n{combined_news}"
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

# ===================== KATTA SONLARNI FORMATLASH =====================
def format_katta_son(son):
    if not son or son == 0: return "—"
    minus = "-" if son < 0 else ""
    son = abs(son)
    if son >= 1e12: return f"{minus}{son/1e12:.2f} T"
    if son >= 1e9: return f"{minus}{son/1e9:.2f} B"
    if son >= 1e6: return f"{minus}{son/1e6:.2f} M"
    return f"{minus}{son:,}"

# ===================== PREMIUM TAHLIL TIZIMI (XALQARO) =====================
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
        ishchilar = info.get('fullTimeEmployees') or info.get('employees') or info.get('fulltimeEmployees') or 0
        ishchilar_str = f"{ishchilar:,} ta" if ishchilar > 0 else "Noma'lum"
        
        # 📅 IPO SANASINI ANIQLASH
        ipo_sana = "—"
        try:
            ipo_data = stock.history(period="1mo", start="1960-01-01")
            if not ipo_data.empty:
                ipo_sana = ipo_data.index[0].strftime('%d.%m.%Y')
        except:
            pass

        # 👥 RAHBARLAR RO'YXATINI ANIQLASH
        rahbarlar_matni = ""
        try:
            officers = info.get('companyOfficers', [])
            if officers:
                for idx, off in enumerate(officers[:3]):
                    name = off.get('name', 'Noma\'lum')
                    title = off.get('title', 'Rahbar')
                    title = title.replace('Chief Executive Officer', 'CEO').replace('Chief Financial Officer', 'CFO').replace('Chief Operating Officer', 'COO')
                    rahbarlar_matni += f"  └ 👤 {name} ({title})\n"
            else:
                rahbarlar_matni = "  └ Ma'lumot topilmadi\n"
        except:
            rahbarlar_matni = "  └ Yuklashda xatolik\n"

        # 💰 DIVIDEND TAQVIMI
        oxirgi_div_narx = info.get('lastDividendValue', '—')
        oxirgi_div_sana = format_sana(info.get('lastDividendDate'))
        
        kelgusi_div_narx = info.get('dividendRate', '—')
        if kelgusi_div_narx and kelgusi_div_narx != '—':
            kelgusi_div_str = f"{round(kelgusi_div_narx / 4, 2)} USD" if div_yield else f"{kelgusi_div_narx} USD"
        else:
            kelgusi_div_str = "—"
            
        kelgusi_div_sana = format_sana(info.get('exDividendDate'))

        qarz = info.get('totalDebt', 0)
        debt_ratio = (qarz / market_cap) * 100 if market_cap else 0
        if debt_ratio < 30: halal_status = "HALOL 🟢"
        elif debt_ratio <= 40: halal_status = "SHUBHALI 🟡"
        else: halal_status = "HAROM 🔴"

        # 📊 FUNDAMENTAL PARAMETRLAR
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

        # 💸 SOF FOYDA VA JAMY NAQD PUL HISOBLAGICHLAI
        sof_foyda = info.get('netIncomeToCommon') or info.get('netIncome', 0)
        naqd_pul = info.get('totalCash') or info.get('totalCashAsOfDateStr', 0)
        
        foyda_status = "FOYDADA 💹" if sof_foyda > 0 else "ZIYONDA 🚨"
        sof_foyda_str = format_katta_son(sof_foyda)
        naqd_pul_str = format_katta_son(naqd_pul)

        # 🎯 DCF (INT-VALUE) TAHLILI
        target_price = info.get('targetMeanPrice', narx)
        upside = round(((target_price - narx) / narx) * 100, 2) if narx else 0.0
        
        if upside > 10:
            dcf_status = f"Undervalued 🟢 ({upside:+.2f}%)"
        elif upside < -10:
            dcf_status = f"Overvalued 🔴 ({upside:+.2f}%)"
        else:
            dcf_status = f"Fair Value 🟡 ({upside:+.2f}%)"

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

        # 👥 INSAYDERLAR TRANZAKSIYASI (YANGILANGAN NOMDA)
        insider_bought = "0"
        insider_sold = "0"
        try:
            df_insider = stock.insider_purchases
            if df_insider is not None and not df_insider.empty:
                df_insider.columns = [c.replace(' ', '') for c in df_insider.columns]
                row_shares = df_insider[df_insider['InsiderPurchases'].str.contains('Shares
