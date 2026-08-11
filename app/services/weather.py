import requests

from config import WEATHER_API_KEY, DEFAULT_CITY


def get_weather(city=None):

    if city is None:
        city = DEFAULT_CITY

    url = "https://api.weatherapi.com/v1/current.json"

    params = {
        "key": WEATHER_API_KEY,
        "q": city,
        "lang": "uk"
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=(3, 5)
        )

        if response.status_code != 200:
            print(
                f"❌ WeatherAPI помилка: "
                f"{response.status_code} {response.text}"
            )
            return None

        data = response.json()

        return {
            "city": data["location"]["name"],
            "temp": data["current"]["temp_c"],
            "feels_like": data["current"]["feelslike_c"],
            "condition": data["current"]["condition"]["text"],
            "humidity": data["current"]["humidity"],
            "wind": round(
                data["current"]["wind_kph"] / 3.6,
                1
            )
        }

    except requests.Timeout:
        print("❌ WeatherAPI: перевищено час очікування")
        return None

    except Exception as e:
        print(f"❌ Помилка WeatherAPI: {e}")
        return None