import requests

from config import WEATHER_API_KEY, DEFAULT_CITY


URL = "https://api.weatherapi.com/v1/current.json"


def get_weather(city=None):

    if city is None:
        city = DEFAULT_CITY

    # Для WeatherAPI використовуємо координати,
    # якщо місто є в нашому довіднику.
    try:
        from app.data.cities import CITY_API

        weather_query = CITY_API.get(
            city,
            city,
        )
    except Exception:
        weather_query = city

    params = {
        "key": WEATHER_API_KEY,
        "q": weather_query,
        "lang": "uk",
    }

    try:

        response = requests.get(
            URL,
            params=params,
            timeout=(3, 5)
        )

        print(
            f"🌤 Weather API status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                f"❌ Weather API error: "
                f"{response.text}"
            )

            return None

        data = response.json()

        current = data.get(
            "current",
            {}
        )

        condition = current.get(
            "condition",
            {}
        ).get(
            "text",
            "Невідомо"
        )

        wind_kph = current.get(
            "wind_kph",
            0
        )

        result = {
            "temp": current.get(
                "temp_c"
            ),

            "feels_like": current.get(
                "feelslike_c"
            ),

            "humidity": current.get(
                "humidity"
            ),

            "wind": round(
                wind_kph / 3.6,
                2
            ),

            "condition": condition,
        }

        print(
            f"✅ WEATHER DATA | "
            f"{city} | {result}"
        )

        return result

    except requests.Timeout:

        print(
            "⏱️ Weather API: "
            "перевищено час очікування"
        )

        return None

    except Exception as e:

        print(
            f"❌ Помилка Weather API: {e}"
        )

        return None