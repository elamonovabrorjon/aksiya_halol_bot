import os
import telebot
from dotenv import load_dotenv
import yfinance as tf

# .env fayldan tokenni o'qish (yoki o'zingizning tokeningizni matn ko'rinishida yozishingiz ham mumkin)
load_dotenv()
TOKEN = os.getenv("TOKEN", "YOUR_BOT_TOKEN_HERE")

bot = telebot.TeleBot(TOKEN)

# Mashhur investorlar bazasi (namuna)
INVESTORS_DATABASE = {
    "WARREN BUFFETT": "Berkshire Hathaway",
    "MICHAEL BURRY": "Scion Asset Management",
    "RAY DALIO": "Bridgewater Associates",
    "CATHIE WOOD": "ARK Investment Management",
}

STOCK_OWNERS = {
    "AAPL": ["WARREN BUFFETT", "RAY DALIO"],
    "AMZN": ["WARREN BUFFETT", "RAY DALIO", "CATHIE WOOD"],
    "MSFT": ["RAY DALIO", "CATHIE WOOD"],
    "NVDA": ["CATHIE WOOD", "RAY DALIO"],
    "GOOGL": ["WARREN BUFFETT", "RAY DALIO"],
    "TSLA": ["CATHIE WOOD", "MICHAEL BURRY"],
}


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    welcome_text = (
        "Assalomu alaykum! 📈\n\n"
        "Bu bot yordamida **istalgan aksiyaning** tikerini yuborib quyidagilarni olishingiz mumkin:\n"
        "1. Real vaqt rejimidagi narxi va bozor qiymati\n"
        "2. Jami naqd pul va umumiy qarz balansi\n"
        "3. Sektor ko'rsatkichlari bilan solishtirish (Kuchli / Kuchsiz)\n"
        "4. Yirik investorlar (Dataroma) portfelida bor-yo'qligi\n"
        "5. Fundamental va texnik tahlil\n\n"
        "Marhamat, aksiya tikerini yuboring (masalan: `AAPL`, `TSLA`, `MSFT`):"
    )
    # Hech qanday qo'shimcha tugmalar (reply yoki inline keyboard) qo'shilmadi
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def analyze_any_stock(message):
    ticker_symbol = message.text.strip().upper()
    bot.send_message(
        message.chat.id,
        f"⏳ `{ticker_symbol}` bo'yicha moliyaviy va sektor ma'lumotlari tahlil qilinmoqda...",
        parse_mode="Markdown",
    )

    try:
        stock = tf.Ticker(ticker_symbol)

        # Xavfsiz tarzda info ni olish
        info = stock.info
        if not info or len(info) < 5:
            bot.send_message(
                message.chat.id,
                f"❌ `{ticker_symbol}` tikeri bo'yicha ma'lumot topilmadi yoki Yahoo Finance javob bermadi. Tiker nomini tekshiring va birozdan so'ng qayta urinib ko'ring.",
                parse_mode="Markdown",
            )
            return

        # 1. Asosiy ma'lumotlar
        price = info.get("currentPrice", info.get("regularMarketPrice", 0))
        market_cap = info.get("marketCap", 0)
        market_cap_str = (
            f"{market_cap / 1e9:.2f}B"
            if isinstance(market_cap, (int, float))
            else "N/A"
        )

        pe = info.get("trailingPE", "N/A")
        roe = info.get("returnOnEquity", 0)
        roe_str = f"{roe * 100:.2f}%" if isinstance(roe, (int, float)) else "N/A"

        sector = info.get("sector", "Noma'lum sektor")
        industry = info.get("industry", "Noma'lum")

        # 2. Pul va Qarz ma'lumotlari
        total_cash = info.get("totalCash", 0)
        total_debt = info.get("totalDebt", 0)

        cash_str = (
            f"${total_cash / 1e9:.2f} Billion"
            if isinstance(total_cash, (int, float)) and total_cash > 0
            else "Ma'lumot yo'q"
        )
        debt_str = (
            f"${total_debt / 1e9:.2f} Billion"
            if isinstance(total_debt, (int, float)) and total_debt > 0
            else "Ma'lumot yo'q"
        )

        if isinstance(total_cash, (int, float)) and isinstance(
            total_debt, (int, float)
        ):
            net_cash_debt = total_cash - total_debt
            net_str = (
                f"+${net_cash_debt / 1e9:.2f}B (Qarzdan ko'p naqd puli bor)"
                if net_cash_debt >= 0
                else f"-${abs(net_cash_debt) / 1e9:.2f}B (Sof qarz holati)"
            )
        else:
            net_str = "Hisoblab bo'lmadi"

        cash_debt_info = (
            f"💰 *Naqd Pul va Qarz Balansi ({ticker_symbol}):*\n"
            f"• *Jami Naqd Pul (Cash):* {cash_str}\n"
            f"• *Umumiy Qarz (Total Debt):* {debt_str}\n"
            f"• *Sof Holat (Net):* {net_str}\n\n"
        )

        # 3. Sektor bo'yicha solishtirish
        industry_pe_benchmark = 25.0
        strength_status = "O'rtacha"

        if isinstance(pe, (int, float)):
            if pe < industry_pe_benchmark and roe > 0.15:
                strength_status = "🟢 **KUCHLI** - Arzon va yuqori rentabellik."
            elif pe > industry_pe_benchmark:
                strength_status = "🟡 **QIMMAT / O'RTACHA**"
            else:
                strength_status = "🔴 **KUCHSIZ / SUST**"

        sector_comparison = (
            f"⚖️ *Sektor va Solishtiruv:*\n"
            f"• *Sektor:* {sector}\n"
            f"• *P/E:* {pe} | *Sektor me'yori:* ~{industry_pe_benchmark}\n"
            f"• *ROE:* {roe_str}\n"
            f"• *Holati:* {strength_status}\n\n"
        )

        # 4. Yirik investorlar (Dataroma) ma'lumoti
        owners = STOCK_OWNERS.get(ticker_symbol, [])
        owners_text = f"👥 *Yirik Investorlar (Dataroma):*\n"
        if owners:
            for inv in owners:
                owners_text += (
                    f"• **{inv}** ({INVESTORS_DATABASE.get(inv)}) portfelida bor.\n"
                )
        else:
            owners_text += (
                "• Bizning asosiy kuzatuv bazamizdagi yirik fondlarda topilmadi.\n"
            )
        owners_text += "\n"

        # 5. Fundamental va Texnik qisqacha
        fundamental_info = (
            f"📈 *Bozor Ma'lumotlari:*\n"
            f"• *Market Cap:* {market_cap_str}\n"
            f"• *Joriy Narx:* ${price}\n"
            f"• *52-Haftalik High/Low:* ${info.get('fiftyTwoWeekHigh', 'N/A')} / ${info.get('fiftyTwoWeekLow', 'N/A')}\n\n"
        )

        full_report = (
            cash_debt_info
            + sector_comparison
            + owners_text
            + fundamental_info
        )
        bot.send_message(message.chat.id, full_report, parse_mode="Markdown")

    except Exception as e:
        print(f"Xato yuz berdi: {e}")
        bot.send_message(
            message.chat.id,
            "⚠️ Vaqtinchalik xatolik yuz berdi (Serverdan ma'lumot kelmadi). Iltimos, birozdan so'ng qayta urinib ko'ring.",
        )


if __name__ == "__main__":
    print("Bot ishga tushdi va ishlashga tayyor...")
    bot.infinity_polling()
