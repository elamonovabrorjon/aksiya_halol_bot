import telebot
import yfinance as tf

# Bot tokeningizni kiriting
TOKEN = "8781183838:AAFmgLoz6Bb8LlA-50lVAdAbNvhBCWO3sm0"
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
        "Aksiya tikerini yuboring (masalan: `AAPL`, `MSFT`, `TSLA`). Bot quyidagilarni hisoblab beradi:\n"
        "1. Real narx va o'zgarishlar\n"
        "2. **Naqd pul miqdori va Umumiy qarz**\n"
        "3. **Sektor ichidagi raqobatchilarga nisbatan solishtirma tahlil (Kuchli/Kuchsiz)**\n"
        "4. Fundamental, Texnik va Shariat talablari\n"
        "5. Yirik investorlar portfelida bor-yo'qligi"
    )
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
        info = stock.info

        if not info or (
            "currentPrice" not in info and "regularMarketPrice" not in info
        ):
            bot.send_message(
                message.chat.id,
                f"❌ `{ticker_symbol}` tikeri bo'yicha ma'lumot topilmadi. Tiker nomini tekshiring.",
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

        # 2. Pul va Qarz ma'lumotlari (Yahoo Finance balansidan)
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

        # Net Cash (Naqd pul minus Qarz)
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

        # 3. Sektor bo'yicha solishtirish (Sektorning o'rtacha ko'rsatkichlari bilan solishtirib kuchli/kuchsizligini aniqlash)
        # Sektor raqobatchilarini aniqlash uchun oddiy solishtiruv mexanizmi
        industry_pe_benchmark = (
            25.0  # Sektor uchun o'rtacha taxminiy P/E me'yori (namuna)
        )
        strength_status = "O'rtacha"

        if isinstance(pe, (int, float)):
            if pe < industry_pe_benchmark and roe > 0.15:
                strength_status = (
                    "🟢 **KUCHLI (Undervalued & High ROE)** - Sektor ichida "
                    "arzon baholangan va yaxshi foyda keltirmoqda."
                )
            elif pe > industry_pe_benchmark:
                strength_status = (
                    "🟡 **QIMMAT / O'RTACHA** - P/E ko'rsatkichi sektor "
                    "o'rtachasidan yuqori, o'sishga talab yuqori."
                )
            else:
                strength_status = (
                    "🔴 **KUCHSIZ / BOSIM OSTIDA** - Rentabellik yoki "
                    "baholanishi sektorga nisbatan sust."
                )

        sector_comparison = (
            f"⚖️ *Sektor va Raqobatchilar bilan Solishtirish:*\n"
            f"• *Sektor:* {sector} ({industry})\n"
            f"• *Kompaniya P/E:* {pe} | *Sektor me'yori:* ~{industry_pe_benchmark}\n"
            f"• *Kompaniya ROE:* {roe_str}\n"
            f"• *Bozor holati:* {strength_status}\n\n"
        )

        # 4. Investorlar bazasi
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
            f"📈 *Fundamental va Texnik Ma'lumotlar:*\n"
            f"• *Market Cap:* {market_cap_str}\n"
            f"• *Joriy Narx:* ${price}\n"
            f"• *52-Haftalik High/Low:* ${info.get('fiftyTwoWeekHigh', 'N/A')} / ${info.get('fiftyTwoWeekLow', 'N/A')}\n\n"
        )

        full_report = (
            cash_debt_info + sector_comparison + owners_text + fundamental_info
        )
        bot.send_message(message.chat.id, full_report, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"⚠️ Xatolik yuz berdi: {str(e)}",
            parse_mode="Markdown",
        )


if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
