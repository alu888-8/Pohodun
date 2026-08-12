async def group_alert_monitor(bot: Bot):

    print(
        "🚨 Моніторинг початку та відбою тривог запущений"
    )

    print(
        f"⏱ Інтервал перевірки: "
        f"{MONITOR_INTERVAL} секунд"
    )

    while True:

        try:

            cities = await asyncio.to_thread(
                get_users_cities
            )

            print(
                f"📍 Міста для моніторингу: {cities}"
            )

            if not cities:

                print(
                    "ℹ️ Немає міст для моніторингу"
                )

                await asyncio.sleep(
                    MONITOR_INTERVAL
                )

                continue

            cleanup_old_cities(
                cities
            )

            # ==========================================
            # ОДИН ЗАПИТ ТРИВОГ
            # ==========================================

            alerts_data = await asyncio.to_thread(
                get_alerts
            )

            if alerts_data is None:

                print(
                    "⚠️ Не вдалося отримати API тривог"
                )

            # ==========================================
            # ПЕРЕВІРЯЄМО КОЖНЕ МІСТО
            # ==========================================

            for city in cities:

                try:

                    if city not in _city_states:

                        _city_states[city] = {
                            "alert": None
                        }

                    state = _city_states[city]

                    if alerts_data is None:
                        continue

                    active = is_city_alert_active(
                        city,
                        alerts_data
                    )

                    previous = state["alert"]

                    # ==================================
                    # ПЕРШИЙ ЗАПУСК
                    # ==================================

                    if previous is None:

                        state["alert"] = active

                        print(
                            f"📡 Початковий стан "
                            f"{city}: тривога={active}"
                        )

                    # ==================================
                    # ПОЧАТОК ТРИВОГИ
                    # ==================================

                    elif active and not previous:

                        await send_to_group(
                            bot,

                            "🚨 <b>ПОВІТРЯНА ТРИВОГА!</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "⚠️ Негайно перейдіть "
                            "у безпечне місце."
                        )

                        state["alert"] = True

                        print(
                            f"🚨 Початок тривоги: {city}"
                        )

                    # ==================================
                    # ВІДБІЙ
                    # ==================================

                    elif not active and previous:

                        await send_to_group(
                            bot,

                            "🟢 <b>ВІДБІЙ "
                            "ПОВІТРЯНОЇ ТРИВОГИ</b>\n\n"
                            f"📍 <b>{city}</b>\n\n"
                            "✅ Небезпека минула."
                        )

                        state["alert"] = False

                        print(
                            f"🟢 Відбій тривоги: {city}"
                        )

                except Exception as city_error:

                    print(
                        f"❌ Помилка моніторингу "
                        f"{city}: {city_error}"
                    )

        except Exception as e:

            print(
                f"❌ Помилка моніторингу: {e}"
            )

        await asyncio.sleep(
            MONITOR_INTERVAL
        )