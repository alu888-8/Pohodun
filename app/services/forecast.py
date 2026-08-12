import requests

from config import WEATHER_API_KEY, DEFAULT_CITY


URL = "https://api.weatherapi.com/v1/forecast.json"


def get_forecast(city=None):

    if city is None:
        city = DEFAULT_CITY

    params = {
        "key": WEATHER_API_KEY,
        "q": city,
        "days": 3,
        "lang": "uk",
    }

    try:

        response = requests.get(
            URL,
            params=params,
            timeout=(3, 7)
        )

        print(
            f"🌤 Forecast API status: {response.status_code}"
        )

        if response.status_code != 200:

            print(
                f"❌ Forecast API error: {response.text}"
            )

            return None

        return response.json()

    except requests.Timeout:

        print(
            "⏱️ Forecast API: перевищено час очікування"
        )

        return None

    except Exception as e:

        print(
            f"❌ Помилка Forecast API: {e}"
        )

        return None