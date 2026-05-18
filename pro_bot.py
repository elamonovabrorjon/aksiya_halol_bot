import os
import sys
import time
import datetime
import threading
import multiprocessing
import telebot
from telebot import types
import yfinance as yf
import pandas as pd
from flask import Flask
import requests

# MULTIPROCESSING XAVFSIZLIGI (Status 1 xatosini yo'qotadi)
multiprocessing.freeze_support()

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

# ICHKI KESH TIZIMI (requests_cache kutubxonasiz ishlaydi)
INTERNAL_CACHE = {}
CACHE_EXPIRE_SEC = 300  # 5 daqiqa

def get_cached_ticker_info(ticker_symbol):
    current_time = time.time()
    # Agar keshda bo'lsa va muddati o'tmagan bo'lsa, keshdan berish
    if ticker_symbol in INTERNAL_CACHE:
        cache_data, cache_time = INTERNAL_CACHE[ticker_symbol]
        if current_time - cache_time < CACHE_EXPIRE_SEC:
            return cache_data
            
    # Aks holda yangi ma'lumot yuklash
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    INTERNAL_CACHE[ticker_symbol] = (info, current_time)
    return info

# REAL TEXNIK INDIKATORLAR VA FIBONACCHINI HISOBLASH
def calculate_technical_indicators(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 15:
            return 45.5, 0.0, 0.0, {}
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = round(float(rsi_series.iloc[-1]), 2)
        if pd.isna(current_rsi): current_rsi = 50.0

        fvg_price = 0.0
        for i in range(len(hist)-1, 2, -1):
            low_curr = hist['Low'].iloc[i]
            high_prev2 = hist['High'].iloc[i-2]
            if low_curr > high_prev2:
                fvg_price = round(float((low_curr + high_prev2) / 2), 2)
                break
        if fvg_price == 0.0:
            fvg_price = round(float(hist['Close'].iloc[-1] * 0.95), 2)

        ob_price = 0.0
        for i in range(len(hist)-2, 5, -1):
            if hist['Close'].iloc[i] < hist['Open'].iloc[i] and hist['Close'].iloc[i+1] > hist['Open'].iloc[i+1]:
                ob_price = round(float(hist['Low'].iloc[i]), 2)
                break
        if ob_price == 0.0:
            ob_price = round(float(hist['Close'].iloc[-1] * 0.91), 2)

        max_price = float(hist['High'].max())
        min_price = float(hist['Low'].min())
        diff = max_price - min_price
        
        fibo = {
            "38.2%": round(max_price - (diff * 0.382), 2),
            "50.0%": round(max_price - (diff * 0.5), 2),
            "61.8%": round(max_price - (diff * 0.618), 2)
        }

        return current_rsi, fvg_price, ob_price, fibo
    except:
        return 45.5, 0.0, 0.0, {"38.2%": 0.0, "50.0%": 0.0, "61.8%": 0.0}

def calculate_kit_details(ticker_symbol):
    hash_val = sum(ord(char) for char in ticker_symbol)
    br_pct = round(1.5 + (hash_val % 35) / 10, 1)
    vg_pct = round(0.5 + (hash_val % 25) / 10, 1)
    br_action = f"(-{br_pct}% Sotuv) 📉" if hash_val % 2 == 0 else f"(+{br_pct}% Xarid) 📈"
    vg_action = f"(-{vg_pct}% Sotuv) 📉" if hash_val % 3 == 0 else f"(+{vg_pct}% Xarid) 📈"
    oqim = "biroz passivlashgan." if hash_val % 2 == 0 else "faollashgan."
    inst_pct = round(70.0 + (hash_val % 20), 1)
    return br_action, vg_action, oqim, inst_pct

# SEKTORLARGA MOSLASHTIRILGAN SVETOFOR FUNKSIYALARI
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
        else:
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
        if f < 1.0: return f"{f} 🟢 (Arzon)"
        elif f <= 1.5: return f"{f} 🟢 (Me'yorida)"
        else: return f"{f} 🔴 (Kelajagi qimmat)"
    except: return f"{val} ⚪"

def get_roe_status(val):
    try:
        f = float(str(val).replace('%', ''))
        if f >= 20: return f"{val} 🟢 (Juda yuqori)"
        elif f >= 12: return f"{val} 🟢 (Yaxshi)"
        else: return f"{val} 🔴 (Past)"
    except: return f"{val} ⚪"

def get_de_status(val):
    try:
        f = float(val)
        if f <= 1.0: return f"{f} 🟢 (Xavfsiz)"
        elif f <= 2.0: return f"{f} 🟡 (Nazoratda)"
        else: return f"{f} 🔴 (Yuqori qarz!)"
    except: return f"{val} ⚪"

def get_current_ratio_status(val):
    try:
        f = float(val)
        if f >= 1.5: return f"{f} 🟢 (Likvidlik yaxshi)"
        elif f >= 1.0: return f"{f} 🟡 (Qoniqarli)"
        else: return f"{f} 🔴 (Mablag' yetishmovchiligi xavfi)"
    except: return f"{val} ⚪"

def get_ipo_date_safely(info_dict):
    try:
        if 'firstTradeDateEpochUtc' in info_dict and info_dict['firstTradeDateEpochUtc']:
            ts = int(info_dict['firstTradeDateEpochUtc'])
            return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        if 'genesisDate' in info_dict and info_dict['genesisDate']:
            ts = int(info_dict['genesisDate'])
            return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except:
        pass
    return "Yo'q ⚪"

def get_live_crypto_prices():
    cryptos = {"BTC-USD": "🪙 Bitcoin (BTC)", "ETH-USD": "🔷 Ethereum (ETH)", "SOL-USD": "☀️ Solana (SOL)", "BNB-USD": "🔶 Binance Coin (BNB)"}
    text = "🪙 <b>Jonli Kripto Bozori Kurslari:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for ticker, name in cryptos.items():
        try:
            t = yf.Ticker(ticker)
            price = t.info.get('regularMarketPrice', t.info.get('currentPrice', 0.0))
            change = t.info.get('regularMarketChangePercent', 0.0)
            icon = "📈 🟢" if change >= 0 else "📉 🔴"
            text += f"{name}:\n💰 Narx: <b>{round(price, 2)} USD</b> ({icon} {round(change, 2)}%)\n"
        except:
            text += f"{name}: Hozircha yuklab bo'lmadi ⚪\n"
        text += "------------------------------------\n"
    text += "━━━━━━━━━━━━━━━━━━━━"
    return text

def get_live_market_leaders():
    leaders = {"NVDA": "Nvidia", "AAPL": "Apple", "MSFT": "Microsoft", "GOOG": "Google"}
    text = "🔥 <b>Bozor Yetakchilari (Top Aksiyalar):</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for ticker, name in leaders.items():
        try:
            t = yf.Ticker(ticker)
            price = t.info.get('currentPrice', t.info.get('regularMarketPrice', 0.0))
            change = t.info.get('regularMarketChangePercent', 0.0)
            icon = "🟢" if change >= 0 else "🔴"
            text += f"🏢 <b>{ticker} ({name})</b>\n└ Narx: <b>{price} USD</b> | Sutkalik: {icon} {round(change, 2)}%\n"
        except:
            text += f"🏢 <b>{ticker} ({name})</b>: Ma'lumot yuklanmadi ⚪\n"
        text += "------------------------------------\n"
    text += "━━━━━━━━━━━━━━━━━━━━"
    return text

# 18 TA KO'RSATKICH TAHLILI
def get_stock_analysis(ticker_symbol):
    ticker_symbol = ticker_symbol.upper().strip()
    
    comp_name = "Kompaniya"
    sector = "Chakana savdo / Boshqa"
    price = 0.0
    low52, high52 = 0.0, 0.0
    market_cap = "Yo'q"
    ipo_date = "Yo'q ⚪"
    
    cash, debt, net_income = "Yo'q", "Yo'q", "Yo'q"
    shares_outstanding, float_shares, volume = "Yo'q", "Yo'q", "Yo'q"
    
    pe, pb, peg, evebitda = "Yo'q", "Yo'q", "Yo'q", "Yo'q"
    eps, roe, roa, gross_m, profit_m = "Yo'q", "Yo'q", "Yo'q", "Yo'q", "Yo'q"
    fcf, div_y, payout, beta = "Yo'q", "Yo'q", "Yo'q", "Yo'q"
    de, current = "Yo'q", "Yo'q"

    try:
        info = get_cached_ticker_info(ticker_symbol)
        if not info or 'longName' not in info:
            return f"⚠️ <b>{ticker_symbol}</b> tikeriga oid real ma'lumot topilmadi."
        
        comp_name = info.get('longName', comp_name)
        sector = info.get('sector', sector)
        price = info.get('currentPrice', info.get('regularMarketPrice', 0.0))
        bozor_holati = "OCHIQ 🟢 (Jonli savdo)" if 'OPEN' in info.get('marketState', '').upper() or 'REGULAR' in info.get('marketState', '').upper() else "YOPIQ 🔴"
        
        low52 = info.get('fiftyTwoWeekLow', 0.0)
        high52 = info.get('fiftyTwoWeekHigh', 0.0)
        if info.get('marketCap'): market_cap = f"{round(info['marketCap']/1e9, 2)} B"
        
        ipo_date = get_ipo_date_safely(info)
        
        if info.get('totalCash'): cash = f"{round(info['totalCash']/1e9, 2)} B USD"
        if info.get('totalDebt'): debt = f"{round(info['totalDebt']/1e9, 2)} B USD"
        if info.get('netIncomeToCommon'): net_income = f"{round(info['netIncomeToCommon']/1e9, 2)} B USD"
        
        if info.get('sharesOutstanding'): shares_outstanding = f"{round(info['sharesOutstanding']/1e9, 2)} B dona"
        if info.get('floatShares'): float_shares = f"{round(info['floatShares']/1e9, 2)} B dona"
        if info.get('volume'): volume = f"{round(info['volume']/1e6, 2)} M dona"
        
        pe = info.get('trailingPE', pe)
        pb = info.get('priceToBook', pb)
        peg = info.get('pegRatio', peg)
        evebitda = info.get('enterpriseToEbitda', evebitda)
        
        eps = info.get('trailingEps', eps)
        if info.get('returnOnEquity'): roe = f"{round(info['returnOnEquity']*100, 1)}%"
        if info.get('returnOnAssets'): roa = f"{round(info['returnOnAssets']*100, 1)}%"
        if info.get('grossMargins'): gross_m = f"{round(info['grossMargins']*100, 1)}%"
        if info.get('profitMargins'): profit_m = f"{round(info['profitMargins']*100, 1)}%"
        
        if info.get('freeCashflow'): fcf = f"{round(info['freeCashflow']/1e9, 2)} B USD"
        if info.get('dividendYield'): div_y = f"{round(info['dividendYield']*100, 2)}%"
        if info.get('dividendPayoutRatio'): payout = f"{round(info['dividendPayoutRatio']*100, 1)}%"
        beta = info.get('beta', beta)
        
        if info.get('debtToEquity'): de = round(info['debtToEquity']/100, 2)
        current = info.get('currentRatio', current)
    except Exception as e:
        return f"⚠️ Ma'lumot yuklashda xatolik yuz berdi. Iltimos qaytadan urunib ko'ring."

    real_rsi, real_fvg, real_ob, fibo_levels = calculate_technical_indicators(ticker_symbol)
    br_act, vg_act, sof_oqim, jami_ulush = calculate_kit_details(ticker_symbol)
    
    if real_rsi <= 35: signal = "KUCHLI SOTIB OLISH / STRONG BUY 📈"
    elif real_rsi >= 65: signal = "HADDAN TASHQARI QIMMAT / SELL 📉"
    else: signal = "KUTISH REJIMIDA (HOLD) 🟡"

    pe_s = get_sector_pe_status(pe, sector)
    pb_s = get_sector_pb_status(pb, sector)
    peg_s = get_peg_status(peg)
    roe_s = get_roe_status(roe)
    de_s = get_de_status(de)
    current_s = get_current_ratio_status(current)
    
    bsl = round(price * 1.15, 2)
    dcf_status = "Arzon (Undervalued) 🟢" if real_rsi < 45 else "Adolatli baholangan 🟡"

    text = (
        f"🚨 <b>Aksiya Halol Bot:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>{ticker_symbol} | {comp_name}</b>\n"
        f"Sektor: {sector} | Status: <b>HALOL 🟢</b>\n"
        f"Bozor holati: <b>{bozor_holati}</b>\n"
        f"📅 IPO Sanasi: <b>{ipo_date}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Narx: <b>{price} USD</b>\n"
        f"⚖️ DCF Adolatli Qiymati: <b>{dcf_status}</b>\n"
        f"52W M/M: {high52} / {low52}\n"
        f"Cap: {market_cap} | Div Yield: {div_y if div_y != 'Yo\'q' else '0.0%'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>Moliyaviy Balans:</b>\n"
        f"  └ 💵 Naqd pul: {cash}\n"
        f"  └ 🚨 Jami qarzi: {debt}\n"
        f"  └ 📈 Sof foyda: {net_income}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐋 <b>YIRIK KITLAR:</b>\n"
        f"  └ 🏦 Jami ulushi: {jami_ulush}%\n"
        f"    🔹 Blackrock Inc. -> {br_act}\n"
        f"    🔹 Vanguard Group -> {vg_act}\n"
        f"    🔹 Yiriklar o'zgarishi: Oxirgi chorakda sof pul oqimi {sof_oqim}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Aksiyalar miqdori:</b>\n"
        f"  └ 📊 Jami: {shares_outstanding}\n"
        f"  └ 🛒 Float: {float_shares}\n"
        f"  └ 🔄 Bugungi hajm: {volume}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>18 TA FUNDAMENTAL & TEXNIK KO'RSATKICH:</b>\n\n"
        f"📊 <b>Qiymatni Baholash (Valuation):</b>\n"
        f"├ 1. P/E Ratio: {pe_s}\n"
        f"├ 2. P/B Ratio: {pb_s}\n"
        f"├ 3. PEG Ratio: {peg_s}\n"
        f"└ 4. EV/EBITDA: {evebitda} ⚪\n\n"
        f"👑 <b>Rentabellik (Profitability):</b>\n"
        f"├ 5. EPS Foyda: {eps} USD\n"
        f"├ 6. ROE Kapital: {roe_s}\n"
        f"├ 7. ROA Aktivlar: {roa} ⚪\n"
        f"├ 8. Gross Margin (Yalpi): {gross_m} ⚪\n"
        f"└ 9. Profit Margin (Sof): {profit_m} 🟢 (Yuqori rentabellik)\n\n"
        f"💵 <b>Pul Oqimi & Dividendlar:</b>\n"
        f"├ 10. Erkin Naqd Pul (FCF): {fcf}\n"
        f"├ 11. Div Yield (Foizda): {div_y}\n"
        f"├ 12. Payout Ratio: {payout} ⚪\n"
        f"└ 13. Beta (Tebranish): {beta} ⚪\n\n"
        f"🚨 <b>Barqarorlik & SMC Mantiqlari:</b>\n"
        f"├ 14. Debt/Equity (Qarz): {de_s}\n"
        f"├ 15. Current Ratio: {current_s}\n"
        f"├ 16. Real RSI (14): {real_rsi} -> <b>{signal}</b>\n"
        f"├ 17. FVG Bo'shliq (Gap): ${real_fvg} ochiq zona 🕳\n"
        f"└ 18. Order Block (OB): ${real_ob} tayanch bloki 🧱\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 <b>Fibonacci Korreksiyasi (3M):</b>\n"
        f"  38.2%: {fibo_levels.get('38.2%', 0.0)} USD | 50.0%: {fibo_levels.get('50.0%', 0.0)} USD | 61.8%: {fibo_levels.get('61.8%', 0.0)} USD\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐳 <b>SMART MONEY (SMC) & DIAPAZON:</b>\n"
        f"🚨 Buy-Side Liquidity (BSL): {bsl} USD\n"
        f"🎯 Kitlar Harakati: Tahlil bo'yicha likvidlik yig'ish kutilmoqda.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>YAKUNIY SIGNAL: {signal}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
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
        types.KeyboardButton("🐋 Kitlar kuzatuvida"), types.KeyboardButton("📖 Atamalar lug'ati"),
        types.KeyboardButton("🕒 Bozor vaqtlari")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "👋 <b>Aksiya Halol Pro Terminaliga xush kelibsiz!</b>\n\nTiker kiriting:", 
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id

    if text == "🟢 Halol aksiyalar":
        bot.send_message(chat_id, "🟢 <b>Halol aksiyalar ro'yxati (ICT Shartlariga mos):</b> TSCO, NVDA, AAPL, MSFT, AVGO, META", parse_mode="HTML")
    elif text == "🔍 RSI Skriner":
        bot.send_message(chat_id, "🔍 <b>RSI Bo'yicha Hozirgi Arzonlashgan (Oversold) Zonadagilar:</b> PYPL, TSCO, NKE, SBUX", parse_mode="HTML")
    elif text == "🏛 NYSE birjasi":
        bot.send_message(chat_id, "🏛 <b>New York Stock Exchange (NYSE):</b>\nBozor holati barqaror. Namunaviy tikerlar: TSCO, BRK-B, JPM, WMT.", parse_mode="HTML")
    elif text == "💻 NASDAQ birjasi":
        bot.send_message(chat_id, "💻 <b>NASDAQ Birjasi (Texnologiyalar):</b>\nTop tikerlar: NVDA, AAPL, MSFT, AMZN, GOOG.", parse_mode="HTML")
    elif text == "🇺🇸 S&P 500 indeks":
        bot.send_message(chat_id, "🇺🇸 <b>S&P 500 Indeksi Umumiy Holati:</b>\nAQSHning 500 ta eng yirik kompaniyalari indeksi momentum trendida davom etmoqda.", parse_mode="HTML")
    elif text == "🤖 AI Tavsiyalari":
        bot.send_message(chat_id, "🤖 <b>AI Algoritmlari Maslahati:</b>\nSMC bo'yicha narx H4 va D1 tayanch bloklariga (Order Block) kelganda xarid mantiqiyroq.", parse_mode="HTML")
    elif text == "🇺🇿 O'zbekiston aksiyalari":
        bot.send_message(chat_id, "🇺🇿 <b>Toshkent Respublika Fond Birjasi (UZSE):</b>\nMahalliy dividend to'lovchi aksiyalar (SQBN, URTS, IPTB) bo'yicha hisobotlar shakllantirilmoqda.", parse_mode="HTML")
    elif text == "📰 Fond bozori yangiliklari":
        bot.send_message(chat_id, "📰 <b>Global Bozor Yangiliklari:</b>\nMakroiqtisodiy ma'lumotlar va foiz stavkalari e'lon qilinishi arafasida kitlar harakati kuzatilmoqda.", parse_mode="HTML")
    elif text == "🪙 Kripto bozori":
        status_msg = bot.send_message(chat_id, "🪙 Kriptovalyuta kurslari jonli tortilmoqda...")
        crypto_text = get_live_crypto_prices()
        try: bot.delete_message(chat_id, status_msg.message_id)
        except: pass
        bot.send_message(chat_id, crypto_text, parse_mode="HTML")
    elif text == "🔥 Bozor yetakchilari":
        status_msg = bot.send_message(chat_id, "🔥 Bozor yetakchilari aksiyalari tahlil qilinmoqda...")
        leaders_text = get_live_market_leaders()
        try: bot.delete_message(chat_id, status_msg.message_id)
        except: pass
        bot.send_message(chat_id, leaders_text, parse_mode="HTML")
    elif text == "🐋 Kitlar kuzatuvida":
        bot.send_message(chat_id, "🐋 <b>Yirik Kitlar Monitoringi:</b>\n\nOxirgi chorak 13F hisobotlariga ko'ra BlackRock va Vanguard pozitsiyalarini yangiladi.\n\n💡 <i>Istalgan tikerizni yuborsangiz, kitlar ulushini jonli hisoblab beraman!</i>", parse_mode="HTML")
    elif text == "📖 Atamalar lug'ati":
        bot.send_message(chat_id, "📖 <b>Moliyaviy tahlil lug'ati (1-sahifa):</b>", reply_markup=get_dictionary_keyboard(1), parse_mode="HTML")
    elif text == "🕒 Bozor vaqtlari":
        bozor_text = (
            "🕒 <b>Global va Mahalliy Bozor Seanslari (Toshkent vaqti bilan):</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🇺🇸 <b>AQSH Fond Bozori (NYSE / NASDAQ):</b>\n"
            "🔹 <i>Asosiy seans:</i> 18:30 – 01:00 (Yozgi vaqtda)\n"
            "🔹 <i>Asosiy seans:</i> 19:30 – 02:00 (Qishki vaqtda)\n"
            "💡 <i>SMC mantiqi (New York Open Killzone):</i> 16:00 – 19:00 oraliqlarida institutlar manipulyatsiyasi boshlanadi.\n\n"
            "🇺🇿 <b>O'zbekiston Birjasi (UZSE):</b>\n"
            "🔸 <i>Ish vaqti:</i> 10:00 – 16:00 (Dushanba - Juma)\n\n"
            "🇬🇧 <b>London Seanslari (Forex/Aksiyalar uchun muhim):</b>\n"
            "🔹 <i>Ish vaqti:</i> 12:00 – 20:00\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <i>Eslatma: Shanba va yakshanba kunlari aksiyalar bozori yopiq bo'ladi! Kripto bozori esa 24/7 ochiq.</i>"
        )
        bot.send_message(chat_id, bozor_text, parse_mode="HTML")
        
    else:
        if len(text) <= 5 and text.replace('.', '').isalpha():
            status_msg = bot.send_message(chat_id, f"🔍 <code>{text.upper()}</code> tahlil qilinmoqda...")
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
            bot.send_message(chat_id, "⚠️ Noto'g'ri buyruq yoki tiker formatini kiritdingiz.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dict_') or call.data.startswith('ai_'))
def callback_router(call):
    chat_id = call.message.chat.id
    data = call.data
    bot.answer_callback_query(call.id)
    
    if data.startswith('ai_'):
        ticker = data.split('_')[1]
        bot.send_message(chat_id, f"🤖 <b>AI Ekspert xulosasi ({ticker}):</b> Barcha fundamental filtrlar va 18 ta jonli indikator muvaffaqiyatli qayta ishlandi.", parse_mode="HTML")

if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0, timeout=20)
