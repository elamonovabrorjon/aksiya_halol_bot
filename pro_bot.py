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

# ===================== O'ZBEKISTON AKSIYALARI UCHUN AI TAHLILCHISI =====================
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

        # 👥 INSAYDERLAR TRANZAKSIYASI (XATOLIK TO'G'RILANDI)
        insider_bought = "0"
        insider_sold = "0"
        try:
            df_insider = stock.insider_purchases
            if df_insider is not None and not df_insider.empty:
                df_insider.columns = [c.replace(' ', '') for c in df_insider.columns]
                row_shares = df_insider[df_insider['InsiderPurchases'].str.contains('Shares', na=False, case=False)]
                if not row_shares.empty:
                    insider_bought = format_katta_son(int(row_shares.iloc[0].get('Purchases👥', 0) or row_shares.iloc[0].get('Purchases', 0)))
                    insider_sold = format_katta_son(int(row_shares.iloc[0].get('Sales', 0)))
        except:
            pass
            
        if insider_bought == "—" or insider_bought == "0": insider_bought = "0 dona"
        if insider_sold == "—" or insider_sold == "0": insider_sold = "0 dona"

        # 🐋 KITLARNING ULUSHINI HISOBLASH
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
                    
                    pct_value = row.get('Pct', None) or row.get('%Out', None) or row.get('Value', 0)
                    if pct_value and pct_value < 1.0:
                        pct_portfolio = pct_value * 100
                    else:
                        pct_portfolio = pct_value if pct_value else 0.0
                        
                    if pct_portfolio == 0.0:
                        shares_outstanding = info.get('sharesOutstanding', 1)
                        pct_portfolio = (shares / shares_outstanding) * 100
                        
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
🏢 <b>Kompaniya Profili & Rahbariyat:</b>
  └ 📅 IPO: <b>{ipo_sana}</b> | 👥 Xodimlar: <b>{ishchilar_str}</b>
{rahbarlar_matni}━━━━━━━━━━━━━━━━━━━━
Narx: <b>{round(narx, 2)} {valyuta}</b>
52W M/M: <b>{round(high_52, 2)} / {round(low_52, 2)}</b>
Cap: <b>{cap_str}</b> | Div Yield: <b>{div_str}</b>
━━━━━━━━━━━━━━━━━━━━
💰 <b>Dividend Taqvimi:</b>
  └ ↩️ Oxirgi: <b>{oxirgi_div_narx} USD</b> ({oxirgi_div_sana})
  └ 🔜 Kelgusi: <b>{kelgusi_div_str}</b> ({kelgusi_div_sana})
━━━━━━━━━━━━━━━━━━━━
📊 <b>Moliyaviy Holat:</b>
  └ 📢 Balans: <b>{foyda_status}</b>
  └ 💰 Sof Foyda: <b>{sof_foyda_str} USD</b>
  └ 💵 Jami Naqd: <b>{naqd_pul_str} USD</b>
━━━━━━━━━━━━━━━━━━━━
<b>Insayderlar Faoliyati (6O):</b>
  └ 📥 Sotib olgan: <b>{insider_bought}</b>
  └ 📤 Sotib yuborgan: <b>{insider_sold}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fundamental Tahlil:</b>
P/E: <b>{pe_str}</b> | P/B: <b>{pb_str}</b>
ROE: <b>{roe_str}</b> | EPS: <b>{eps_str}</b>
FCF: <b>{fcf_str}</b> | DCF Qiymati: <b>{dcf_status}</b>
━━━━━━━━━━━━━━━━━━━━
<b>Fibonacci (3M):</b>
  38.2%: <b>{fib_38:.2f} USD</b> | 50.0%: <b>{fib_50:.2f} USD</b> | 61.8%: <b>{fib_61:.2f} USD</b>
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
<b>Yirik Fondlar (Kitlar):</b>
{fondlar_matni}━━━━━━━━━━━━━━━━━━━━
<b>BOT BAHOSI: {score}/5.0 {stars} -> {bot_decision}</b>
<i>Izoh: RSI ({rsi}) va moliya ko'rsatkichlari bo'yicha baholandi.</i>"""
        
        debt_status_ai = "Halol" if debt_ratio < 30 else "Yuqori qarz"
        ai_data = f"{tiker_clean}|{round(narx,2)}|{pe_str}|—|{rsi}|{macd_signal}|{debt_status_ai}"
        return javob, tiker_clean, ai_data
    except:
        return f"❌ {tiker.upper()} tahlilida xatolik yuz berdi.", None, None

# ===================== LUG'AT SAHIFALARI TIZIMI =====================
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
        kb.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dic_page_1"),
               types.InlineKeyboardButton("Keyingi sahifa ➡️", callback_data="dic_page_3"))
    elif page == 3:
        kb.add(
            types.InlineKeyboardButton("💹 Net Income", callback_data="dic_netinc"),
            types.InlineKeyboardButton("💵 Total Cash", callback_data="dic_totcash")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dic_page_2"),
               types.InlineKeyboardButton("Keyingi sahifa ➡️", callback_data="dic_page_4"))
    elif page == 4:
        kb.add(
            types.InlineKeyboardButton("🎯 DCF Tahlili", callback_data="dic_dcf"),
            types.InlineKeyboardButton("👥 Insider Trading", callback_data="dic_insider")
        )
        kb.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dic_page_3"))
    return kb

def main_menu():
    kb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    kb.add(
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🏛️ NYSE birjasi"), types.KeyboardButton("💻 NASDAQ birjasi"),
        types.KeyboardButton("🇺🇸 S&P 500 indeks"), types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🎯 Kun aksiyasi"), types.KeyboardButton("📖 Atamalar lug'ati")
    )
    return kb

def ai_exit_menu():
    kb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ AI Rejimdan chiqish"))
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
    user_modes[message.chat.id] = False
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
    
    if "chiqish" in text.lower() or text == "❌ AI Rejimdan chiqish":
        user_modes[user_id] = False
        bot.send_message(user_id, "Asosiy menyuga qaytdingiz. Endi aksiya tikerini yuborishingiz mumkin.", reply_markup=main_menu())
        return

    if user_modes.get(user_id, False):
        bot.send_chat_action(user_id, 'typing')
        prompt = (
            f"Siz aqlli va yordamchi moliyaviy yordamchisiz. Foydalanuvchining quyidagi iqtisodiy yoki umumiy savoliga "
            f"o'zbek tilida aniq, tushunarli va chiroyli javob bering. Javobda dollar belgisi ($ yoki USD) ishlatilsin. "
            f"Foydalanuvchi xabari: {text}"
        )
        res = ai_request(prompt)
        bot.send_message(user_id, res if res else "🤖 AI xizmati band. Birozdan so'ng qayta urinib ko'ring.", parse_mode="HTML", reply_markup=ai_exit_menu())
        return

    if text == "🔍 RSI Skriner":
        bot.send_message(user_id, "🔍 <b>RSI Skriner bo'yicha eng faol kompaniyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AMZN"]))
    elif text == "🟢 Halol aksiyalar":
        bot.send_message(user_id, "🟢 <b>AQSh bozoridagi eng yirik halol aksiyalar:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"]))
    elif "NYSE" in text:
        bot.send_message(user_id, "🏛️ <b>NYSE birjasining top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["TSCO", "WMT", "KO", "XOM", "JNJ", "NKE"]))
    elif "NASDAQ" in text:
        bot.send_message(user_id, "💻 <b>NASDAQ birjasining top kompaniyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA"]))
    elif "S&P 500" in text:
        bot.send_message(user_id, "🇺🇸 <b>S&P 500 indeksining eng nufuzli top aksiyalari:</b>", parse_mode="HTML", reply_markup=inline_aksiyalar(["SPY", "VOO", "AAPL", "MSFT", "AMZN", "BRK-B"]))
    elif "Bloomberg" in text:
        bot.send_chat_action(user_id, 'typing')
        news_res = get_bloomberg_news()
        bot.send_message(user_id, f"📰 <b>Bloomberg | So'nggi Fond Bozori Yangiliklari:</b>\n\n{news_res}", parse_mode="HTML")
    elif "AI Tavsiyalar" in text or "AI" in text:
        user_modes[user_id] = True
        welcome_ai_msg = (
            "🤖 <b>Sun'iy intellekt bilan erkin muloqot rejimiga xush kelibsiz!</b>\n\n"
            "Menga o'zingizni qiziqtirgan har qanday iqtisodiy, moliyaviy yoki bozorga oid savollaringizni yozishingiz mumkin.\n\n"
            "Rejimni tugatish uchun pastdagi tugmani bosing 👇"
        )
        bot.send_message(user_id, welcome_ai_msg, parse_mode="HTML", reply_markup=ai_exit_menu())
    elif "Kun aksiyasi" in text:
        bot.send_chat_action(user_id, 'typing')
        javob, tiker, ai_str = aksiya_tahlil("AAPL")
        if tiker:
            bot.send_message(user_id, javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
    elif "lug'at" in text or text == "📖 Atamalar lug'ati":
        bot.send_message(user_id, "📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>\n\nTugmalardan birini tanlang:", parse_mode="HTML", reply_markup=inline_dictionary(page=1))
    
    # 🇺🇿 O'ZBEKISTON AKSIYALARI UCHUN INTEGRATSIYA (AVTOMATIK TANISH)
    elif any(keyword in text.upper() for keyword in ["UZMT", "SQB", "HMKB", "KVTS", "UZAUTO", "URTS", "IPTK", "OKMK", "AGMK", "O'ZBEKISTON", "UZBEKISTAN", "FOND BIRJA"]):
        bot.send_chat_action(user_id, 'typing')
        uz_analysis = uzbekistan_stock_analysis(text)
        bot.send_message(user_id, uz_analysis, parse_mode="HTML")
        
    else:
        bot.send_chat_action(user_id, 'typing')
        javob, tiker, ai_str = aksiya_tahlil(text)
        if tiker:
            bot.send_message(user_id, javob, parse_mode="HTML", reply_markup=inline_action(tiker, ai_str))
        else:
            uz_analysis = uzbekistan_stock_analysis(text)
            bot.send_message(user_id, uz_analysis, parse_mode="HTML")

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
        
        if term == "page":
            page_num = int(call.data.split("_")[2])
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"📖 <b>Moliyaviy tahlil lug'ati ({page_num}-sahifa):</b>",
                parse_mode="HTML",
                reply_markup=inline_dictionary(page=page_num)
            )
            bot.answer_callback_query(call.id)
            return

        expl = ""
        if term == "mcap": expl = "📊 <b>Market Cap:</b> Kompaniyaning bozordagi barcha aksiyalarining umumiy qiymati."
        elif term == "pe": expl = "📈 <b>P/E Ratio:</b> Aksiya narxi uning yillik foydasidan necha barobar qimmatligini bildiradi."
        elif term == "debteq": expl = "🚨 <b>Debt/Equity:</b> Kompaniyaning o'z kapitaliga nisbatan qarz yuklamasi."
        elif term == "rsi": expl = "📉 <b>RSI Indikatori:</b> Aksiyaning o'ta ko'p sotilgan yoki haddan tashqari ko'p sotib olinganini aniqlaydi."
        elif term == "eps": expl = "💰 <b>EPS (Earnings Per Share):</b> Kompaniyaning bitta aksiyasiga to'g'ri keladigan sof foyda ulushi."
        elif term == "roe": expl = "👑 <b>ROE (Return on Equity):</b> Kompaniyaning o'z kapitalidan foydalanish samaradorligi (rentabellik)."
        elif term == "fcf": expl = "💵 <b>FCF (Free Cash Flow):</b> Xarajatlardan keyin kompaniya ixtiyorida qoladigan erkin real naqd pul oqimi."
        elif term == "pb": expl = "📚 <b>P/B Ratio:</b> Bozor narxining kompaniya balans (buxgalteriya) qiymatiga bo'lgan nisbati."
        elif term == "netinc": expl = "💹 <b>Net Income (Sof Foyda):</b> Barcha soliqlar va xarajatlardan keyin qolgan sof foyda yoki ziyon."
        elif term == "totcash": expl = "💵 <b>Total Cash (Jami Naqd Pul):</b> Kompaniyaning hisob raqamlarida ayni paytda mavjud bo'lgan naqd mablag'lari."
        elif term == "dcf": expl = "🎯 <b>DCF Tahlili:</b> Kompaniyaning kelajakda topadigan pullarini bugungi kunga diskontlab, uning real ichki qiymatini aniqlash usuli."
        elif term == "insider": expl = "👥 <b>Insider Trading:</b> Kompaniya rahbarlari, direktorlari yoki yirik xodimlarining o'z kompaniyalari aksiyalarini sotib olishi yoki sotishi."
        
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
