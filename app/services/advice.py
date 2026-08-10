def get_advice(temp, condition):
    advice = []

    if temp < 0:
        advice.append("🧥 Одягни теплу зимову куртку.")
    elif temp < 10:
        advice.append("🧥 Візьми легку куртку.")
    elif temp < 20:
        advice.append("👕 Краще вдягнути кофту.")
    else:
        advice.append("👕 Футболки буде достатньо.")

    condition = condition.lower()

    if "дощ" in condition:
        advice.append("☔ Візьми парасолю.")

    if "гроза" in condition:
        advice.append("⚡ Краще залишатися у приміщенні.")

    if "сніг" in condition:
        advice.append("🥾 Одягни тепле взуття.")

    if "соняч" in condition:
        advice.append("😎 Гарна погода для прогулянки.")

    if "хмар" in condition:
        advice.append("🌥 День буде похмурий.")

    return "\n".join(advice)