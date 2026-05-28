
# ==================== TUGMALAR ====================
    if text == "📖 Lug'at":
        bot.reply_to(message, "📖 Lug'at bo‘limi tez orada to‘liq ishga tushadi.", parse_mode="HTML")

    elif text == "⏰ Bozor vaqti":
        bot.reply_to(message, "⏰ Bozor vaqti bo‘limi tez orada yangilanadi.", parse_mode="HTML")

    elif text == "📰 Yangiliklar":
        bot.reply_to(message, "📰 Yangiliklar bo‘limi tayyorlanmoqda...", parse_mode="HTML")

    elif text == "📊 Bookmap":
        bot.reply_to(message, """📊 <b>Bookmap rejimi yoqildi!</b>

Endi istalgan ticker yuboring:
• AAPL
• BTC-USD
• TSLA
• GC=F (Oltin)

Bot sizga grafika + tahlil yuboradi.""", parse_mode="HTML")

    elif text == "🐳 Kitlar & Siyosat":
        bot.reply_to(message, "🐳 Kitlar & Siyosat bo‘limi tayyorlanmoqda...", parse_mode="HTML")

    elif text == "⚔️ Raqobat tahlili":
        bot.reply_to(message, "⚔️ Raqobat tahlili uchun 2-5 ta tiker yozing (masalan: AAPL MSFT NVDA)", parse_mode="HTML")

    elif text in ["📈 Fond bozori", "₿ Crypto", "🌍 Forex", "🛢 Xomashyo"]:
        bot.reply_to(message, "✅ Tahlil qilmoqchi bo‘lgan tiker yuboring.", parse_mode="HTML")

    elif text == "🆘 Adminlik (Yordam)":
        bot.reply_to(message, "🆘 Yordam kerak bo‘lsa savolingizni yozing.", parse_mode="HTML")

    # ==================== TIKER TAHLILI ====================
    else:
        # Bookmap rejimi
        if len(text) <= 12 and text.replace('-','').replace('=','').isalnum():
            send_bookmap_chart(message, text)
            analysis = get_18_point_analysis(text)
            bot.reply_to(message, analysis, parse_mode="HTML")
        else:
            # Oddiy tahlil
            analysis = get_18_point_analysis(text)
            bot.reply_to(message, analysis, parse_mode="HTML")


if name == "main":
    print("🚀 Aksiya Halol Bot ishga tushdi...")
    bot.infinity_polling(none_stop=True, interval=0)