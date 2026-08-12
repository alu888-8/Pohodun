import requests

from config import WEATHER_API_KEY, DEFAULT_CITY


WEATHER_API_URL = (
    "https://api.weatherapi.com/v1/forecast.json"
)


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
            WEATHER_API_URL,
            params=params,
            timeout=(3, 7),
        )

        print(
            f"📅 Forecast API | "
            f"city={city} | "
            f"status={response.status_code}"
        )

        if response.status_code != 200:

            print(
                f"❌ Forecast API error: "
                f"{response.text}"
            )

            return None

        data = response.json()

        if "forecast" not in data:

            print(
                "❌ Forecast API: "
                "у відповіді немає forecast"
            )

            return None

        return data

    except requests.Timeout:

        print(
            f"⏱️ Forecast API timeout | "
            f"city={city}"
        )

        return None

    except requests.RequestException as e:

        print(
            f"❌ Forecast API request error: {e}"
        )

        return None

    except ValueError as e:

        print(
            f"❌ Forecast API JSON error: {e}"
        )

        return None

    except Exception as e:

        print(
            f"❌ Forecast API unexpected error: {e}"
        )

        return None