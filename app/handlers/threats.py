from aiogram import Router
from aiogram.types import Message

from app.database.db import get_city
from app.data.regions import CITY_REGIONS

from app.services.threats import get_threats


router = Router()


@router.message(
    lambda message: message.text == "🛰 Загрози"
)
async def threats(message: Message):

    city = get_city(
        message.from_user.id
    )

    data = get_threats()

    if data is None:

        await message.answer(
            "❌ Не вдалося отримати список загроз."
        )

        return

    all_threats = data.get(
        "threats",
        []
    )

    # Беремо тільки активні загрози
    active_threats = []

    for threat in all_threats:

        status = threat.get(
            "status",
            "active"
        )

        if status in (
            "active",
            "stale"
        ):

            active_threats.append(
                threat
            )

    # ==========================================
    # ПОШУК ЗАГРОЗ ДЛЯ МІСТА
    # ==========================================

    keywords = CITY_REGIONS.get(
        city,
        [city.lower()]
    )

    result = []

    for threat in active_threats:

        region = str(
            threat.get("region", "")
        ).lower()

        district = str(
            threat.get("district", "")
        ).lower()

        locality = str(
            threat.get("locality", "")
        ).lower()

        title = str(
            threat.get("title", "")
        )

        explanation = str(
            threat.get(
                "explanationShort",
                ""
            )
        )

        search_text = (
            f"{region} "
            f"{district} "
            f"{locality} "
            f"{title} "
            f"{explanation}"
        ).lower()

        matched = any(
            keyword.lower() in search_text
            for keyword in keywords
        )

        if not matched:
            continue

        threat_type = threat.get(
            "type",
            "unknown"
        )

        icon = {
            "uav": "🛸",
            "missile": "🚀",
            "ballistic": "💥",
            "kab": "💣",
            "mig31k": "✈️",
            "recon": "👀",
            "unknown": "❓"
        }.get(
            threat_type,
            "❓"
        )

        threat_title = threat.get(
            "title",
            "Невідома загроза"
        )

        threat_region = threat.get(
            "region",
            ""
        )

        explanation_short = threat.get(
            "explanationShort",
            ""
        )

        text = (
            f"{icon} <b>{threat_title}</b>\n"
            f"📍 {threat_region}"
        )

        if explanation_short:

            text += (
                f"\n"
                f"ℹ️ {explanation_short}"
            )

        result.append(
            text
        )

    # ==========================================
    # РЕЗУЛЬТАТ
    # ==========================================

    if not result:

        await message.answer(
            f"🛰 <b>Загрози</b>\n\n"
            f"📍 <b>{city}</b>\n\n"
            "🟢 Поблизу активних загроз "
            "не виявлено.",
            parse_mode="HTML"
        )

        return

    text = (
        f"🛰 <b>Активні загрози</b>\n\n"
        f"📍 <b>{city}</b>\n\n"
        + "\n\n".join(result)
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )