import telebot
import requests
import time
import threading

TOKEN = "7972155385:AAHbmTbzE_FK7_yuD3lbrJ0_sV3-p4c4P0Y"
CHAT_ID = 5736191321
FINNHUB_API = "d1ut5j9r01qqt8g82jvgd1ut5j9r01qqt8g82k00"

bot = telebot.TeleBot(TOKEN)
AUTO_ON = False

TICKERS = ["AAPL","MSFT","GOOGL","TSLA","AMZN","META","NVDA","AMD","INTC","NFLX"]

def get_price(ticker):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API}"
        r = requests.get(url, timeout=10).json()
        return r.get('c', 0)
    except:
        return 0

def scan_stocks():
    results = []
    for t in TICKERS:
        price = get_price(t)
        if price > 0:
            change = ((price - 100) / 100) * 5  # oddiy signal
            if abs(change) > 2:
                results.append(f"📈 {t}: ${price:.2f} ({'+' if change>0 else ''}{change:.1f}%)")
        time.sleep(0.5)
    return results

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "✅ Bot tayyor!\n/scan - tekshirish\n/auto_on - avtomatik\n/auto_off - o'chirish")

@bot.message_handler(commands=['scan'])
def scan(m):
    bot.send_message(m.chat.id, "🔍 Tekshirilmoqda...")
    res = scan_stocks()
    if res:
        bot.send_message(m.chat.id, "Halol signal topildi:\n\n" + "\n".join(res[:5]))
    else:
        bot.send_message(m.chat.id, "Hozir signal yo'q")

@bot.message_handler(commands=['auto_on'])
def on(m):
    global AUTO_ON
    AUTO_ON = True
    bot.send_message(m.chat.id, "✅ Avtomatik yoqildi (har 30 daqiqa)")

@bot.message_handler(commands=['auto_off'])
def off(m):
    global AUTO_ON
    AUTO_ON = False
    bot.send_message(m.chat.id, "❌ Avtomatik o'chirildi")

def auto_loop():
    while True:
        if AUTO_ON:
            try:
                res = scan_stocks()
                if res:
                    bot.send_message(CHAT_ID, "🤖 Avto signal:\n" + "\n".join(res[:3]))
            except:
                pass
        time.sleep(1800)  # 30 daqiqa

threading.Thread(target=auto_loop, daemon=True).start()

print("Bot ishga tushdi")
bot.infinity_polling()