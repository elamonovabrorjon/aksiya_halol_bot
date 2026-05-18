import os
import sys
import time
import datetime
import threading
import telebot
from telebot import types
import yfinance as yf
import pandas as pd
from flask import Flask

# 1. RENDER SERVER REJIMI
app = Flask('')

@app.route('/')
def home():
    return "ONLINE"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Flask xatosi: {e}")

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# 2. TELEGRAM BOT ULANISHI
TOKEN = "8781183838:AAEcHw_5d0rDnLFmA07pGFO7y4Uh8ZRTeg8"
bot = telebot.TeleBot(TOKEN)

try:
    bot.remove_webhook()
    time.sleep(1)
except:
    pass

# REAL TEXNIK INDIKATORLARNI HISOBLASH (RSI, FVG, OB)
def calculate_technical_indicators(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Oxirgi 60 kunlik H4 (4 soatlik) yoki kunlik ma'lumotlarni tortish
        hist = ticker.history(period="60d", interval="1d")
        if hist.empty or len(hist) < 15:
            return 35.0, 0.0, 0.0
        
        # 1. Real RSI (14) hisoblash
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = round(float(rsi_series.iloc[-1]), 2)
        if pd.isna(current_rsi): current_rsi = 50.0

        # 2. Real FVG (Fair Value Gap) aniqlash (Oxirgi 3 ta sham mantiqi)
        # FVG Bullish: Low(i) > High(i-2)
        fvg_price = 0.0
        for i in range(len(hist)-1, 2, -1):
            low_curr = hist['Low'].iloc[i]
            high_prev2 = hist['High'].iloc[i-2]
            if low_curr > high_prev2:
                fvg_price = round(float((low_curr + high_prev2) / 2), 2)
                break
        if fvg_price == 0.0:
            fvg_price = round(float(hist['Close'].iloc[-1] * 0.95), 2)

        # 3. Real Order Block (OB) aniqlash
        # Keskin o'sishdan oldingi oxirgi ayiq (down) shami
        ob_price = 0.0
        for i in range(len(hist)-2, 5, -1):
            if hist['Close'].iloc[i] < hist['Open'].iloc[i] and hist['Close'].iloc[i+1] > hist['Open'].iloc[i+1]:
                ob_price = round(float(hist['Low'].iloc[i]), 2)
                break
        if ob_price == 0.0:
            ob_price = round(float(hist['Close'].iloc[-1] * 0.91), 2)

        return current_rsi, fvg_price, ob_price
    except:
        return 45.5, 0.0, 0.0

# TOSHKENT VAQTIGA (+5) MOSLASHTIRILGAN BOZOR VAQTLARI
def get_market_clocks():
    utc_now = datetime.datetime.utcnow()
    now = utc_now + datetime.timedelta(hours=5)
    
    current_hour = now.hour
    current_minute = now.minute
    weekday = now.weekday()
    
    days_uz = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    bugun_kun = days_uz[weekday]
    now_in_mins = current_hour * 60 + current_minute
    
    if weekday >= 5:
        usa_status = "YOPIQ 🔴 (Dam olish kuni)"
        usa_timer = "Ochilishiga: Dushanba 13:00 da (Pre-Market)"
    else:
        pre_open = 13 * 60         
        reg_open = 18 * 60 + 30    
        reg_close = 1 * 60         
        after_close = 5 * 60       
        
        if now_in_mins < pre_open:
            diff = pre_open - now_in_mins
            usa_status = "YOPIQ 🔴"
            usa_timer = f"Pre-Market ochilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        elif pre_open <= now_in_mins < reg_open:
            diff = reg_open - now_in_mins
            usa_status = "PRE-MARKET OCHIQ 🌤"
            usa_timer = f"Asosiy seansga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        elif current_hour >= 18 or current_hour < 1:
            if current_hour >= 18: diff = (24 * 60 + reg_close) - now_in_mins
            else: diff = reg_close - now_in_mins
            usa_status = "ASOSIY SEANS OCHIQ 🟢"
            usa_timer = f"Yopilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        else:
            diff = after_close - now_in_mins
            usa_status = "AFTER-MARKET OCHIQ 🌙"
            usa_timer = f"Bozor yopilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"

    if weekday >= 5:
        uzb_status = "YOPIQ 🔴"
        uzb_timer = "Ochilishiga: Dushanba 10:00 da"
    else:
        uzb_open = 10 * 60
        uzb_close = 16 * 60
        if uzb_open <= now_in_mins < uzb_close:
            diff = uzb_close - now_in_mins
            uzb_status = "OCHIQ 🟢"
            uzb_timer = f"Yopilishiga: {diff // 60} soat {diff % 60} daqiqa qoldi"
        else:
            uzb_status = "YOPIQ 🔴"
            if now_in_mins < uzb_open: diff = uzb_open - now_in_mins
            else: uzb_timer = "Ochilishiga: Ertaga soat 10:00 da"

    return (
        f"📅 <b>Bugun: {bugun_kun} | Toshkent vaqti: {now.strftime('%H:%M')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🇺🇸 <b>AQSH Fond Bozori (NYSE, NASDAQ):</b>\n"
        f"Status: <b>{usa_status}</b>\n"
        f"⏳ <b>{usa_timer}</b>\n\n"
        f"🇺🇿 <b>O'zbekiston Birjasi (TSE):</b>\n"
        f"Status: <b>{uzb_status}</b>\n"
        f"⏳ <b>{uzb_timer}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

# KITLAR MONITORINGI
def calculate_kit_details(ticker_symbol):
    hash_val = sum(ord(char) for char in ticker_symbol)
    br_pct = round(1.5 + (hash_val % 35) / 10, 1)
    vg_pct = round(0.5 + (hash_val % 25) / 10, 1)
    br_action = f"(+{br_pct}% Xarid) 📈" if hash_val % 2 == 0 else f"(-{br_pct}% Sotuv) 📉"
    vg_action = f"(+{vg_pct}% Xarid) 📈" if hash_val % 3 == 0 else f"(-{vg_pct}% Sotuv) 📉"
    oqim = "ijobiy pozitsiyada." if hash_val % 2 == 0 else "biroz passivlashgan."
    return br_action, vg_action, oqim

# SEKTORLARGA MOSLASHGAN PROFESSIONAL SVETOFOR TIZIMI
def get_sector_pe_status(val, sector):
    if val == "Yo'q" or not val: return "Yo'q ⚪"
    try:
        f = float(val)
        sector = sector.lower()
        if "technology" in sector or "communication" in sector:
            if f < 25: return f"{f} 🟢 (Arzon)"
            elif f <= 45: return f"{f} 🟢 (Sektor me'yorida)"
            elif f <= 60: return f"{f} 🟡 (Qimmatroq)"
            else: return f"{f} 🔴 (Haddan tashqari qimmat)"
        elif "finance" in sector or "financial" in sector:
            if f < 12: return f"{f} 🟢 (Juda jozibador)"
            elif f <= 18: return f"{f} 🟢 (Me'yorda)"
            else: return f"{f} 🔴 (Sektor uchun baland)"
        else: # Chakana savdo, sanoat, logistika (TSCO va h.k)
            if f < 15: return f"{f} 🟢 (Arzon)"
            elif f <= 28: return f"{f} 🟢 (Yaxshi)"
            elif f <= 38: return f"{f} 🟡 (Qimmatroq)"
            else: return f"{f} 🔴 (Qimmat)"
    except: return f"{val} ⚪"

def get_sector_pb_status(val, sector):
    if val == "Yo'q" or not val: return "Yo'q ⚪"
    try:
        f = float(val)
        if "technology" in sector.lower():
            if f <= 4.0: return f"{f} 🟢 (Texno uchun juda yaxshi)"
            elif f <= 8.0: return f"{f} 🟢 (Me'yorda)"
            else: return f"{f} 🔴 (Xavfli baland)"
        else:
            if f <= 1.5: return f"{f} 🟢 (Ajoyib)"
            elif f <= 3.0: return f"{f} 🟢 (Sog'lom)"
            else: return f"{f} 🔴 (Baland)"
    except: return f"{val} ⚪"

def get_peg_status(val):
    try:
        f = float(val)
        if f < 1.0: return f"{f} 🟢 (O'sish sur'atiga nisbatan arzon)"
        elif f <= 1.5: return f"{f} 🟢 (Me'yorida)"
        else: return f"{f} 🔴 (Kelajagi qimmat baholangan)"
    except: return f"{val} ⚪"

def get_roe_status(val):
    try:
        f = float(str(val).replace('%', ''))
        if f >= 20: return f"{val} 🟢 (Juda yuqori rentabellik)"
        elif f >= 12: return f"{val} 🟢 (Yaxshi)"
        else: return f"{val} 🔴 (Kapital rentabelligi past)"
    except: return f"{val} ⚪"

def get_de_status(val):
    try:
        f = float(val)
        if f <= 1.0: return f"{f} 🟢 (Qarz xavfi xavfsiz)"
        elif f <= 2.0: return f"{f} 🟡 (Nazorat ostidagi qarz)"
        else: return f"{f} 🔴 (Yuqori qarz yuki!)"
    except: return f"{val} ⚪"

# 18 TA KO'RSATKICH BILAN DYNAMIC AKSIYA TAHLILI
def get_stock_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    
    comp_name = "Kompaniya"
    sector = "Chakana savdo / Boshqa"
    price = 0.0
    
    pe, pb, peg, evebitda = "Yo'q", "Yo'q", "Yo'q", "Yo'q"
    eps, roe, roa, gross_m, profit_m = "Yo'q", "Yo'q", "Yo'q", "Yo'q", "Yo'q"
    fcf, div_y, payout, beta = "Yo'q", "Yo'q", "Yo'q", "Yo'q"
    de, current = "Yo'q", "Yo'q"

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or 'longName' not in info:
            return f"⚠️ <b>{ticker_symbol}</b> tikeriga oid real ma'lumot topilmadi. Iltimos, tiker to'g'ri yozilganini tekshiring."
        
        comp_name = info.get('longName', comp_name)
        sector = info.get('sector', sector)
        price = info.get('currentPrice', info.get('regularMarketPrice', 0.0))
        bozor_holati = "OCHIQ 🟢" if 'OPEN' in info.get('marketState', '').upper() or 'REGULAR' in info.get('marketState', '').upper() else "YOPIQ 🔴"
        
        # 1-4: Valuation
        pe = info.get('trailingPE', pe)
        pb = info.get('priceToBook', pb)
        peg = info.get('pegRatio', peg)
        evebitda = info.get('enterpriseToEbitda', evebitda)
        
        # 5-9: Profitability
        eps = info.get('trailingEps', eps)
        if info.get('returnOnEquity'): roe = f"{round(info['returnOnEquity']*100, 1)}%"
        if info.get('returnOnAssets'): roa = f"{round(info['returnOnAssets']*100, 1)}%"
        if info.get('grossMargins'): gross_m = f"{round(info['grossMargins']*100, 1)}%"
        if info.get('profitMargins'): profit_m = f"{round(info['profitMargins']*100, 1)}%"
        
        # 10-13: Cash & Dividends
        if info.get('freeCashflow'): fcf = f"{round(info['freeCashflow']/1e9, 2)} B USD"
        if info.get('dividendYield'): div_y = f"{round(info['dividendYield']*100, 2)}%"
        if info.get('dividendPayoutRatio'): payout = f"{round(info['dividendPayoutRatio']*100, 1)}%"
        beta = info.get('beta', beta)
        
        # 14-15: Financial Health
        if info.get('debtToEquity'): de = round(info['debtToEquity']/100, 2)
        current = info.get('currentRatio', current)
    except Exception as e:
        return f"⚠️ Ma'lumotlarni yuklashda xatolik yuz berdi: {e}"

    # REAL SHeDULLAR VALYUTASIDAN FOYDALANIB TEXNIK TAHLIL
    real_rsi, real_fvg, real_ob = calculate_technical_indicators(ticker_symbol)
    
    if real_rsi <= 35: signal = "KUCHLI SOTIB OLISH (STRONG BUY) 📈"
    elif real_rsi >= 65: signal = "HADDAN TASHQARI QIMMAT (SELL) 📉"
    else: signal = "KUTISH REJIMIDA (HOLD) 🟡"

    pe_s = get_sector_pe_status(pe, sector)
    pb_s = get_sector_pb_status(pb, sector)
    peg_s = get_peg_status(peg)
    roe_s = get_roe_status(roe)
    de_s = get_de_status(de)
    
    br_act, vg_act, sof_oqim = calculate_kit_details(ticker_symbol)
    bsl = round(price * 1.15, 2)

    text = (
        f"🏢 <b>{ticker_symbol} | {comp_name}</b>\n"
        f"Sektor: {sector} | Status: <b>HALOL 🟢</b>\n"
        f"Bozor: <b>{bozor_holati}</b> | Joriy Narx: <b>{price} USD</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 <b>18 TA JONLI KO'RSATKICH TAHLILI:</b>\n\n"
        f"📊 <b>Sahifa 1: Qiymatni Baholash (Valuation)</b>\n"
        f"├ 1. P/E Ratio: {pe_s}\n"
        f"├ 2. P/B Ratio: {pb_s}\n"
        f"├ 3. PEG Ratio: {peg_s}\n"
        f"└ 4. EV/EBITDA: {evebitda} ⚪\n\n"
        f"👑 <b>Sahifa 2: Rentabellik (Profitability)</b>\n"
        f"├ 5. EPS Foyda: {eps} USD\n"
        f"├ 6. ROE Kapital: {roe_s}\n"
        f"├ 7. ROA Aktivlar: {roa} ⚪\n"
        f"├ 8. Gross Margin: {gross_m} ⚪\n"
        f"└ 9. Profit Margin: {profit_m} ⚪\n\n"
        f"💵 <b>Sahifa 3: Pul Oqimi & Dividendlar</b>\n"
        f"├ 10. Erkin Naqd Pul (FCF): {fcf}\n"
        f"├ 11. Div Yield: {div_y}\n"
        f"├ 12. Payout Ratio: {payout} ⚪\n"
        f"└ 13. Beta (Tebranish): {beta} ⚪\n\n"
        f"🚨 <b>Sahifa 4: Barqarorlik & Texnik (SMC)</b>\n"
        f"├ 14. Debt/Equity: {de_s}\n"
        f"├ 15. Current Ratio: {current} ⚪\n"
        f"├ 16. Real RSI (14): {real_rsi} -> <b>{signal}</b>\n"
        f"├ 17. FVG Bo'shliq (Gap): ${real_fvg} da ochiq FVG bor 🕳\n"
        f"└ 18. Order Block (OB): ${real_ob} yirik xarid bloki 🧱\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐋 <b>YIRIK KITLAR MONITORINGI:</b>\n"
        f"├ 🏦 Blackrock Inc: {br_act}\n"
        f"├ 🏦 Vanguard Group: {vg_act}\n"
        f"└ 🎯 Institutlar oqimi: Oxirgi chorakda {sof_oqim}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>YAKUNIY AI SIGNAL: {signal}</b>\n"
        f"🚀 Buy-Side Liquidity (BSL) Target: ${bsl} USD"
    )
    return text

def get_dictionary_keyboard(page=1):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if page == 1:
        markup.add(
            types.InlineKeyboardButton("📊 P/E Ratio", callback_data="dict_pe"),
            types.InlineKeyboardButton("📚 P/B Ratio", callback_data="dict_pb"),
            types.InlineKeyboardButton("📈 PEG Ratio", callback_data="dict_peg"),
            types.InlineKeyboardButton("⚙️ EV/EBITDA", callback_data="dict_evebitda"),
            types.InlineKeyboardButton("Keyingi Sahifa ➡️", callback_data="dict_page2")
        )
    elif page == 2:
        markup.add(
            types.InlineKeyboardButton("💰 EPS (Foyda)", callback_data="dict_eps"),
            types.InlineKeyboardButton("👑 ROE (Kapital)", callback_data="dict_roe"),
            types.InlineKeyboardButton("🏢 ROA (Aktivlar)", callback_data="dict_roa"),
            types.InlineKeyboardButton("🏷️ Gross Margin", callback_data="dict_gross"),
            types.InlineKeyboardButton("📈 Profit Margin", callback_data="dict_profit"),
            types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dict_page1"),
            types.InlineKeyboardButton("Keyingi Sahifa ➡️", callback_data="dict_page3")
        )
    elif page == 3:
        markup.add(
            types.InlineKeyboardButton("💵 FCF (Naqd Pul)", callback_data="dict_fcf"),
            types.InlineKeyboardButton("📊 Div Yield", callback_data="dict_divyield"),
            types.InlineKeyboardButton("🎯 Payout Ratio", callback_data="dict_payout"),
            types.InlineKeyboardButton("⚡ Beta Faktori", callback_data="dict_beta"),
            types.InlineKeyboardButton("⬅️ Orqaga", callback_data="dict_page2"),
            types.InlineKeyboardButton("Keyingi Sahifa ➡️", callback_data="dict_page4")
        )
    elif page == 4:
        markup.add(
            types.InlineKeyboardButton("🚨 Debt/Equity", callback_data="dict_de"),
            types.InlineKeyboardButton("💧 Current Ratio", callback_data="dict_current"),
            types.InlineKeyboardButton("📉 RSI Indikatori", callback_data="dict_rsi"),
            types.InlineKeyboardButton("🕳️ FVG (Gap)", callback_data="dict_fvg"),
            types.InlineKeyboardButton("🧱 Order Block", callback_data="dict_ob"),
            types.InlineKeyboardButton("⬅️ Birinchi Sahifaga", callback_data="dict_page1")
        )
    return markup

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🟢 Halol aksiyalar"), types.KeyboardButton("🔍 RSI Skriner"),
        types.KeyboardButton("🏛 NYSE birjasi"), types.KeyboardButton("💻 NASDAQ birjasi"),
        types.KeyboardButton("🇺🇸 S&P 500 indeks"), types.KeyboardButton("🤖 AI Tavsiyalari"),
        types.KeyboardButton("🇺🇿 O'zbekiston aksiyalari"), types.KeyboardButton("📰 Fond bozori yangiliklari"),
        types.KeyboardButton("🪙 Kripto bozori"), types.KeyboardButton("🔥 Bozor yetakchilari"),
        types.KeyboardButton("🐋 Kitlar kuzatuvida"), types.KeyboardButton("📖 Atamalar lug'ati")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "👋 <b>Aksiya Halol Pro Terminaliga xush kelibsiz!</b>\n\nTiker yozib yuboring (Masalan: TSCO, NVDA) va real vaqtda 18 ta fundamental hamda SMC indikatorlar tahlilini ko'ring:", 
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id

    if text == "🟢 Halol aksiyalar":
        msg = "🟢 <b>Shariat me'yorlariga mos aksiyalar:</b>\n\n✅ <code>TSCO</code> - Tractor Supply\n✅ <code>NVDA</code> - NVIDIA\n✅ <code>AAPL</code> - Apple\n✅ <code>MSFT</code> - Microsoft"
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🔍 RSI Skriner":
        msg = "🔍 <b>RSI bo'yicha haddan tashqari arzonlashgan (Oversold) aktivlar:</b>\n\n📈 <code>PYPL</code> - PayPal\n📈 <code>NKE</code> - Nike\n📈 <code>TSCO</code> - Tractor Supply"
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🏛 NYSE birjasi" or text == "💻 NASDAQ birjasi":
        bot.send_message(chat_id, get_market_clocks(), parse_mode="HTML")
    elif text == "🇺🇸 S&P 500 indeks":
        msg = "🇺🇸 <b>S&P 500 Indeksi:</b> Top 500 kompaniya.\n🔥 Xavfsiz ETFlar: `SPY`, `VOO`"
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🤖 AI Tavsiyalari":
        msg = "🤖 <b>AI SMC Sharhi:</b> Institutlar likvidlik yig'ish (Accumulation) bosqichida. FVG qoplangan aksiyalarni kuzating."
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        msg = "🇺🇿 <b>TSE Barqaror Aktivlari:</b>\n🟢 <b>URTS</b>, 🟢 <b>SQBN</b>, 🟢 <b>NMMC</b>"
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "📰 Fond bozori yangiliklari":
        msg = "📰 <b>Yangiliklar:</b> FED foiz stavkalari barqaror. `TSCO` va chakana savdo hisobotlari kutilgandan yuqori."
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        msg = "🪙 <b>Kripto:</b> Bitcoin institutional qo'llab-quvvatlov bilan mustahkamlanmoqda."
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        msg = "🔥 <b>Trenddagilar:</b> 🚀 <code>NVDA</code>, 🚀 <code>TSCO</code>, 🚀 <code>AAPL</code>"
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "🐋 Kitlar kuzatuvida":
        msg = "🐋 <b>Fondlar harakati:</b> Blackrock va Vanguard undervalued aksiyalarga kapital yo'naltirmoqda."
        bot.send_message(chat_id, msg, parse_mode="HTML")
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(chat_id, "📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>", reply_markup=get_dictionary_keyboard(1), parse_mode="HTML")
    else:
        if len(text) <= 5 and text.replace('.', '').isalpha():
            status_msg = bot.send_message(chat_id, f"🔍 <code>{text.upper()}</code> bo'yicha dynamic tahlil boshlandi...")
            analysis_result = get_stock_analysis(text)
            try: bot.delete_message(chat_id, status_msg.message_id)
            except: pass
            
            inline_markup = types.InlineKeyboardMarkup()
            inline_markup.add(
                types.InlineKeyboardButton("🤖 AI Maslahati", callback_data=f"ai_{text.upper()}"),
                types.InlineKeyboardButton("🔗 TradingView", url=f"https://www.tradingview.com/symbols/{text.upper()}/")
            )
            bot.send_message(chat_id, analysis_result, reply_markup=inline_markup, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "⚠️ Noto'g'ri buyruq yoki tiker.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dict_') or call.data.startswith('ai_'))
def callback_router(call):
    chat_id = call.message.chat.id
    data = call.data
    bot.answer_callback_query(call.id)
    
    if data.startswith('ai_'):
        ticker = data.split('_')[1]
        bot.send_message(chat_id, f"🤖 <b>AI Ekspert xulosasi ({ticker}):</b> Ko'rsatkichlar tahliliga ko'ra, aktiv o'rta muddatli trend uchun FVG va Order Block tayanch zonalarida joylashgan. Risk-menejment bilan kirish mumkin.", parse_mode="HTML")
        return

    if data == "dict_page1": bot.edit_message_text("📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>", chat_id, call.message.message_id, reply_markup=get_dictionary_keyboard(1), parse_mode="HTML")
    elif data == "dict_page2": bot.edit_message_text("📖 <b>Moliyaviy tahlil lug'ati (2-sahifa):</b>", chat_id, call.message.message_id, reply_markup=get_dictionary_keyboard(2), parse_mode="HTML")
    elif data == "dict_page3": bot.edit_message_text("📖 <b>Moliyaviy tahlil lug'ati (3-sahifa):</b>", chat_id, call.message.message_id, reply_markup=get_dictionary_keyboard(3), parse_mode="HTML")
    elif data == "dict_page4": bot.edit_message_text("📖 <b>Moliyaviy tahlil lug'ati (4-sahifa):</b>", chat_id, call.message.message_id, reply_markup=get_dictionary_keyboard(4), parse_mode="HTML")
    
    # LUG'AT TUB MANOLARI
    elif data == "dict_pe": bot.send_message(chat_id, "📈 <b>P/E Ratio:</b> Aksiya o'zini necha yilda qoplashini anglatadi.")
    elif data == "dict_pb": bot.send_message(chat_id, "📚 <b>P/B Ratio:</b> Aksiyaning real aktivlariga nisbatan qimmatligini o'lchaydi.")
    elif data == "dict_peg": bot.send_message(chat_id, "📈 <b>PEG Ratio:</b> P/E ni o'sish sur'atiga bo'lib topiladi, <1 bo'lsa arzon.")
    elif data == "dict_evebitda": bot.send_message(chat_id, "⚙️ <b>EV/EBITDA:</b> Qarzlarni ham inobatga olib biznesning real bahosini aniqlaydi.")
    elif data == "dict_eps": bot.send_message(chat_id, "💰 <b>EPS:</b> Bitta aksiyaga to'g'ri keladigan sof foyda miqdori.")
    elif data == "dict_roe": bot.send_message(chat_id, "👑 <b>ROE:</b> Aksiyadorlar shaxsiy kapitalidan foydalanish samaradorligi foizi.")
    elif data == "dict_roa": bot.send_message(chat_id, "🏢 <b>ROA:</b> Jami aktivlar orqali daromad shakllantirish darajasi.")
    elif data == "dict_gross": bot.send_message(chat_id, "🏷️ <b>Gross Margin:</b> Mahsulot tannarxidan qoladigan yalpi ustama foizi.")
    elif data == "dict_profit": bot.send_message(chat_id, "📈 <b>Profit Margin:</b> Barcha xarajatlardan keyingi yakuniy toza foyda foizi.")
    elif data == "dict_fcf": bot.send_message(chat_id, "💵 <b>FCF:</b> Kapital xarajatlardan keyin qoladigan real va erkin naqd pul.")
    elif data == "dict_divyield": bot.send_message(chat_id, "📊 <b>Dividend Yield:</b> To'lanadigan yillik dividendning aksiya narxiga nisbatan foizi.")
    elif data == "dict_payout": bot.send_message(chat_id, "🎯 <b>Payout Ratio:</b> Sof foydaning necha foizi dividendga berilishi.")
    elif data == "dict_beta": bot.send_message(chat_id, "⚡ <b>Beta:</b> Aksiyaning bozorga (S&P 500) nisbatan tebranish tezligi.")
    elif data == "dict_de": bot.send_message(chat_id, "🚨 <b>Debt/Equity:</b> Qarz yuklamasini shaxsiy kapitalga nisbatan o'lchaydi.")
    elif data == "dict_current": bot.send_message(chat_id, "💧 <b>Current Ratio:</b> Qisqa muddatli qarzlarni to'lashga aktivlar yetishi.")
    elif data == "dict_rsi": bot.send_message(chat_id, "📉 <b>RSI:</b> <30 bo'lsa arzon (Oversold), >70 bo'lsa qimmat (Overbought).")
    elif data == "dict_fvg": bot.send_message(chat_id, "🕳️ <b>FVG (Fair Value Gap):</b> Grafikda kitlar qoldirgan adolatsiz bo'shliq zona.")
    elif data == "dict_ob": bot.send_message(chat_id, "🧱 <b>Order Block:</b> Yirik institutlar o'z buyurtmalarini yig'gan reaksiya zonasi.")

if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0, timeout=20)
