import asyncio
import threading

import aiohttp


WS_URL = "wss://neptun.in.ua/api/v1/stream"


_lock = threading.Lock()
_threats = {}
_ws_started = False


def _set_snapshot(threats):
    global _threats

    with _lock:
        _threats = {
            threat.get("id"): threat
            for threat in threats
            if isinstance(threat, dict)
            and threat.get("id")
        }


def _upsert(threat):
    if not isinstance(threat, dict):
        return

    threat_id = threat.get("id")

    if not threat_id:
        return

    with _lock:
        _threats[threat_id] = threat


def _remove(threat_id):
    if not threat_id:
        return

    with _lock:
        _threats.pop(threat_id, None)


def get_threats():
    """
    Повертає поточний кеш загроз NEPTUN.

    Дані надходять через WebSocket.
    """

    with _lock:
        threats = list(_threats.values())

    return {
        "threats": threats,
        "source": "websocket",
        "count": len(threats),
    }


async def _websocket_loop():
    global _ws_started

    if _ws_started:
        return

    _ws_started = True

    print("🛰 NEPTUN WebSocket запускається")

    while True:

        try:

            timeout = aiohttp.ClientTimeout(
                total=None,
                sock_connect=10,
                sock_read=None,
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                print(
                    "🔌 Підключення до NEPTUN WebSocket..."
                )

                async with session.ws_connect(
                    WS_URL,
                    autoping=True,
                    heartbeat=None,
                ) as ws:

                    print(
                        "✅ NEPTUN WebSocket підключено"
                    )

                    while True:

                        try:
                            msg = await ws.receive(
                                timeout=45
                            )

                        except asyncio.TimeoutError:

                            print(
                                "⏱️ NEPTUN WS: "
                                "45 сек без повідомлень — перевіряємо з'єднання"
                            )

                            try:
                                await ws.ping()
                                print(
                                    "🏓 NEPTUN WS ping відправлено"
                                )
                                continue

                            except Exception as e:
                                print(
                                    "❌ NEPTUN WS ping error:",
                                    repr(e),
                                )
                                break

                        # =====================================
                        # TEXT
                        # =====================================

                        if msg.type == aiohttp.WSMsgType.TEXT:

                            try:
                                payload = msg.json()

                            except Exception as e:

                                print(
                                    "⚠️ NEPTUN WS JSON error:",
                                    repr(e),
                                )
                                continue

                            event_type = payload.get("type")
                            data = payload.get("data")

                            # =================================
                            # SNAPSHOT
                            # =================================

                            if event_type == "snapshot":

                                threats = (
                                    data.get("threats", [])
                                    if isinstance(data, dict)
                                    else []
                                )

                                _set_snapshot(
                                    threats
                                )

                                print(
                                    "📦 NEPTUN WS snapshot:",
                                    len(threats),
                                )

                            # =================================
                            # UPSERT
                            # =================================

                            elif event_type == "upsert":

                                _upsert(data)

                                if isinstance(data, dict):

                                    print(
                                        "🔄 NEPTUN WS upsert:",
                                        data.get("id"),
                                        data.get("type"),
                                        data.get("locality"),
                                    )

                            # =================================
                            # REMOVE
                            # =================================

                            elif event_type == "remove":

                                threat_id = (
                                    data.get("id")
                                    if isinstance(data, dict)
                                    else None
                                )

                                _remove(
                                    threat_id
                                )

                                print(
                                    "⬜ NEPTUN WS remove:",
                                    threat_id,
                                )

                            # =================================
                            # HEARTBEAT
                            # =================================

                            elif event_type == "heartbeat":

                                pass

                            # =================================
                            # ALERTS
                            # =================================

                            elif event_type == "alerts":

                                print(
                                    "ℹ️ NEPTUN WS alerts update"
                                )

                            # =================================
                            # UNKNOWN
                            # =================================

                            else:

                                print(
                                    "ℹ️ NEPTUN WS event:",
                                    event_type,
                                )

                            continue

                        # =====================================
                        # CLOSE
                        # =====================================

                        if msg.type == aiohttp.WSMsgType.CLOSE:

                            print(
                                "⚠️ NEPTUN WS CLOSE отримано"
                            )
                            break

                        # =====================================
                        # CLOSING
                        # =====================================

                        if msg.type == aiohttp.WSMsgType.CLOSING:

                            print(
                                "⚠️ NEPTUN WS CLOSING отримано"
                            )
                            break

                        # =====================================
                        # CLOSED
                        # =====================================

                        if msg.type == aiohttp.WSMsgType.CLOSED:

                            print(
                                "⚠️ NEPTUN WS CLOSED"
                            )
                            break

                        # =====================================
                        # ERROR
                        # =====================================

                        if msg.type == aiohttp.WSMsgType.ERROR:

                            print(
                                "❌ NEPTUN WS ERROR:",
                                ws.exception(),
                            )
                            break

                    print(
                        "🔚 NEPTUN WS завершив цикл"
                    )

                    print(
                        "   close_code:",
                        ws.close_code,
                    )

                    print(
                        "   exception:",
                        ws.exception(),
                    )

        except asyncio.CancelledError:

            print(
                "🛑 NEPTUN WebSocket зупинений"
            )

            raise

        except Exception as e:

            print(
                "❌ NEPTUN WebSocket помилка:",
                repr(e),
            )

        print(
            "🔁 NEPTUN WebSocket reconnect через 5 сек..."
        )

        await asyncio.sleep(5)


def start_threats_websocket():
    """
    Запускає фоновий NEPTUN WebSocket
    у поточному asyncio event loop.
    """

    try:

        loop = asyncio.get_running_loop()

    except RuntimeError:

        print(
            "❌ Неможливо запустити NEPTUN WebSocket: "
            "немає running event loop"
        )

        return None

    return loop.create_task(
        _websocket_loop()
    )
