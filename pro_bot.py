def get_market_status():
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    weekday = now.weekday()  # 0: Dushanba, ..., 4: Juma, 5: Shanba, 6: Yakshanba

    # Birja vaqtlari (Toshkent vaqti bilan minutlarda hisoblash uchun)
    now_in_minutes = current_hour * 60 + current_minute
    
    uzse_start = 10 * 60       # 10:00
    uzse_end = 16 * 60         # 16:00
    
    us_start = 18 * 60 + 30    # 18:30 (Yozgi vaqt standarti olingan)
    us_end = 1 * 60            # Tungi 01:00 (keyingi kun)

    # 1. DAM OLISH KUNLARI METODIKASI
    if weekday in [5, 6]:
        # Dushanba 10:00 gacha qolgan vaqtni taxminiy hisoblash
        days_to_monday = 7 - weekday if weekday == 5 else 1
        return f"⚠️ **Dam olish kuni!**\n🇺🇿 UzSE va 🇺🇸 AQSH birjalari yopiq.\n⏳ Bozorlar dushanba kuni soat 10:00 da ochiladi."

    status_report = ""

    # 2. O'ZBEKISTON BIRJASI (UzSE) TAHLILI
    if uzse_start <= now_in_minutes < uzse_end:
        rem_min = uzse_end - now_in_minutes
        status_report += f"🇺🇿 **UzSE Bozor:** OCHIQ 🟢\n🛑 Yopilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"
    else:
        status_report += "🇺🇿 **UzSE Bozor:** YOPIQ 🔴\n"
        if now_in_minutes < uzse_start:
            rem_min = uzse_start - now_in_minutes
            status_report += f"⏳ Ochilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"
        else:
            # Keyingi kun 10:00 gacha
            rem_min = (24 * 60 - now_in_minutes) + uzse_start
            status_report += f"⏳ Keyingi seansga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi.\n"

    status_report += "━━━━━━━━━━━━━━━━━━━━\n"

    # 3. AQSH BIRJASI (NYSE/NASDAQ) TAHLILI
    # AQSH bozori 18:30 dan tungi 01:00 gacha ochiq bo'ladi
    is_us_open = False
    if now_in_minutes >= us_start or now_in_minutes < us_end:
        is_us_open = True

    if is_us_open:
        # Yopilishigacha qolgan vaqtni hisoblash
        if now_in_minutes >= us_start:
            rem_min = (24 * 60 - now_in_minutes) + us_end
        else:
            rem_min = us_end - now_in_minutes
        status_report += f"🇺🇸 **AQSH Bozori:** OCHIQ 🟢\n🛑 Yopilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi."
    else:
        status_report += "🇺🇸 **AQSH Bozori:** YOPIQ 🔴\n"
        if now_in_minutes < us_start:
            rem_min = us_start - now_in_minutes
            status_report += f"⏳ Ochilishiga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi."
        else:
            rem_min = (24 * 60 - now_in_minutes) + us_start
            status_report += f"⏳ Keyingi seansga: **{rem_min // 60} soat, {rem_min % 60} minut** qoldi."

    # SMC New York Open Killzone eslatmasi (16:00 - 19:00)
    if 16 <= current_hour < 19:
        status_report += "\n\n⚡ **SMC Info:** NY Open Killzone faol! Institutlar manipulyatsiyasi bo'lishi mumkin."

    return status_report
