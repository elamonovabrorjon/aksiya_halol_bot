def forex_analiz(symbol):
    price = get_forex_price(symbol)
    r1,r2,r3,r4,s1,s2,s3,s4 = calculate_levels(price)
    buy_vol, sell_vol = get_liquidity(symbol)
    total = buy_vol + sell_vol
    buy_pct = round(buy_vol/total*100) if total else 50
    sell_pct = 100 - buy_pct
    name = "OLTIN (XAUUSD)" if 'XAU' in symbol else "BITCOIN (BTCUSD)" if 'BTC' in symbol else "EURUSD"
    vaqt = get_tashkent_time()
    return f"""🚨 {name} - LIVE ANALIZ
━━━━━━━━━━━━━━━━━━━━
💵 Hozirgi narx: ${price:,.2f}
🕐 Yangilandi: {vaqt}
━━━━━━━━━━━━━━━━━━━━
📊 MUHIM DARAJALAR:
🔴 Qarshiliklar:
• R1: ${r1:,.2f} | R2: ${r2:,.2f}
• R3: ${r3:,.2f} | R4: ${r4:,.2f}

🟢 Qo'llab-quvvatlash:
• S1: ${s1:,.2f} | S2: ${s2:,.2f}
• S3: ${s3:,.2f} | S4: ${s4:,.2f}
━━━━━━━━━━━━━━━━━━━━
🐋 KATTA O'YINCHILAR:
• Buy likvidlik: {buy_vol} lot ({buy_pct}%)
• Sell likvidlik: {sell_vol} lot ({sell_pct}%)
• Jami: {total:.1f} lot
━━━━━━━━━━━━━━━━━━━━
💡 BUGUNGI REJA:
Narx ${s1:,.2f} ustida tursa LONG, ${r1:,.2f} dan o'tsa ${r2:,.2f} ga tezlik."""